"""T24B routed-vs-blind (H2) on Modal — reproduces the 8-GPU node run.

The original ran on an 8-GPU box (src/bin/launch_t24_brev.sh); that node
is gone, so this re-hosts the *identical* recipe on Modal. One Modal container per
arm/round with 4×A100-80GB replicates the node's `--gpus device=0,1,2,3` exactly
(verl runs single-node, Ray inits in-container). Training code, reward, data prep,
merge, and eval harness are all reused verbatim from src/ — the only new code is
this Modal wrapper.

Design invariants (must match it6 / launch_t24_brev.sh so the ablation is clean):
  - from-base retrain, LR 5e-7, BATCH 32, MICRO 16, EPOCHS 3, GRAD_CKPT False,
    NGPUS 4, ROLLOUT_N 8, SAVE_FREQ 25, TEST_FREQ 25
  - the ONE difference between arms is the pack merged into the v3 corpus:
    routed -> routed_pack_it4.jsonl,  blind -> blind_pack_t24.jsonl
  - 2 rounds per arm give per-arm variance (GRPO rollouts are stochastic).

Usage (from repo root, with the miniconda modal that holds the auth):
  # 1. cheap smoke: 1 arm, ~10 steps, validates image+multiGPU+ckpt (~$3)
  modal run src/train/modal_t24.py --mode smoke
  # 2. full ablation: 4 runs (2 arms x 2 rounds), 2-wide parallel, then eval
  modal run src/train/modal_t24.py --mode full
  # 3. eval only (if training already on the volume)
  modal run src/train/modal_t24.py --mode eval
  # pull results back:
  modal volume get guard-t24 /results ./results/modal_t24 --force
"""

import modal

VERL_IMAGE = "verlai/verl:app-verl0.5-vllm0.10.0-mcore0.13.0-te2.2"
MODEL = "nvidia/Nemotron-Content-Safety-Reasoning-4B"
GPU = "A100-80GB:4"       # training: matches the node's 4-GPU device set
EVAL_GPU = "A100-80GB:1"  # eval: single GPU serves the merged checkpoint

app = modal.App("guard-t24")

# The verl image already carries verl 0.5 + vllm 0.10 + torch. We only add our
# repo code and the raw corpora (a few MB). `datasets` is needed for OOD eval.
image = (
    modal.Image.from_registry(VERL_IMAGE, add_python=None)
    # The app-verl0.5 image ships verl's *deps* (torch/vllm/megatron/TE) but not
    # verl itself — the node mounted its own /verl checkout. Clone the matching
    # v0.5.0 tag and install with --no-deps so the image's pinned stack is intact.
    .run_commands(
        "git clone --depth 1 --branch v0.5.0 https://github.com/volcengine/verl /verl",
        "cd /verl && pip install --no-deps -e .",
        "python3 -c 'import verl; print(\"verl\", verl.__file__)'",
    )
    .pip_install("datasets>=2.19")
    .add_local_dir("src", "/workspace/src", copy=True)
    .add_local_dir("data", "/workspace/data", copy=True)
    .add_local_file("results/probe_set_it4.jsonl", "/workspace/raw/probe_set_it4.jsonl", copy=True)
    .add_local_file("results/attack_set_it4.jsonl", "/workspace/raw/attack_set_it4.jsonl", copy=True)
    .add_local_file("results/train_data_v3.jsonl", "/workspace/raw/train_data_v3.jsonl", copy=True)
    .add_local_file("results/routed_pack_it4.jsonl", "/workspace/raw/routed_pack_it4.jsonl", copy=True)
    .add_local_file("results/blind_pack_t24.jsonl", "/workspace/raw/blind_pack_t24.jsonl", copy=True)
)

hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)   # warm weights
work = modal.Volume.from_name("guard-t24", create_if_missing=True)      # data + ckpts + results
secrets = [modal.Secret.from_name("hf-secret"), modal.Secret.from_name("wandb-secret")]

VOLS = {"/root/.cache/huggingface": hf_cache, "/work": work}
ARMS = {"routed": "routed_pack_it4.jsonl", "blind": "blind_pack_t24.jsonl"}
ROUNDS = [1, 2]


def _run(cmd, **kw):
    import subprocess
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


# ------------------------------------------------------------ probe (CPU) --
@app.function(image=image, timeout=600)
def probe():
    """Locate verl + the interpreter that can import it, inside the image."""
    import subprocess
    for cmd in (
        "which python python3 || true",
        "for p in python python3 /opt/conda/bin/python; do echo \"-- $p\"; $p -c 'import verl,sys; print(verl.__file__)' 2>&1 | head -1; done",
        "pip show verl 2>/dev/null | head -3 || true",
        "find / -name 'main_ppo.py' -path '*verl*' 2>/dev/null | head",
        "ls /opt 2>/dev/null; ls / | head -40",
    ):
        print(f"\n$ {cmd}")
        print(subprocess.run(["bash", "-lc", cmd], capture_output=True, text=True).stdout)


# ---------------------------------------------------------------- prep (CPU) --
@app.function(image=image, volumes=VOLS, timeout=1800)
def prep():
    """Build both arms' corpora -> prepared jsonl -> train/val parquet on the
    volume. Idempotent: skips an arm whose parquet already exists."""
    import os
    for arm, pack in ARMS.items():
        pdir = f"/work/parquet_t24_{arm}"
        if os.path.exists(f"{pdir}/train.parquet"):
            print(f"{arm}: parquet exists, skip")
            continue
        corpus = f"/work/train_data_t24_{arm}.jsonl"
        prepared = f"/work/train_prepared_t24_{arm}.jsonl"
        with open(corpus, "w") as out:
            for src in ("/workspace/raw/train_data_v3.jsonl", f"/workspace/raw/{pack}"):
                out.write(open(src).read())
        _run(["python3", "/workspace/src/train/prepare_data.py", "--rows", corpus, "--out", prepared])
        _run(["python3", "/workspace/src/train/to_parquet.py", "--rows", prepared, "--out-dir", pdir])
    work.commit()
    return sorted(os.listdir("/work"))


# ------------------------------------------------------------- train (4 GPU) --
@app.function(image=image, gpu=GPU, volumes=VOLS, secrets=secrets, timeout=4 * 3600)
def train_arm(arm: str, rnd: int, smoke: bool = False):
    """One GRPO run for (arm, round). Reuses run_grpo_smoke.sh verbatim; the it6
    hyperparameters come in via env, exactly as the node launcher set them."""
    import os
    exp = f"grpo-t24-{arm}-r{rnd}" + ("-smoke" if smoke else "")
    pdir = f"/work/parquet_t24_{arm}"
    ckpt = f"/work/checkpoints/{exp}"
    env = {
        **os.environ,
        "MODEL": MODEL,
        "TRAIN": f"{pdir}/train.parquet",
        "VAL": f"{pdir}/val.parquet",
        "REWARD": "/workspace/src/train/reward.py",
        "NGPUS": "4",
        "LR": "5e-7", "BATCH": "32", "MICRO": "16", "EPOCHS": "3",
        "GRAD_CKPT": "False", "ROLLOUT_N": "8",
        "SAVE_FREQ": "25", "TEST_FREQ": "25",
        "EXPERIMENT": exp, "CKPT_DIR": ckpt,
        "WANDB_PROJECT": "guard-t24", "WANDB_ENTITY": "alchemxz",
    }
    if smoke:  # cheap validation: tiny + save early so the ckpt path is exercised
        env.update({"EPOCHS": "1", "SAVE_FREQ": "5", "TEST_FREQ": "5", "BATCH": "16", "MICRO": "8"})
    _run(["bash", "/workspace/src/bin/run_grpo_smoke.sh"], env=env, cwd="/workspace")
    work.commit()
    steps = sorted(os.listdir(ckpt)) if os.path.exists(ckpt) else []
    print(f"{exp}: checkpoints -> {steps}")
    return exp, steps


# -------------------------------------------------------------- eval (1 GPU) --
@app.function(image=image, gpu=EVAL_GPU, volumes=VOLS, secrets=secrets, timeout=2 * 3600)
def eval_arm(exp: str, ood: bool = False, only_step: int = 0):
    """Merge every checkpoint of `exp` to HF, serve with vLLM, run the §4.1
    harness (xstest scoreboard + fresh probe/ASR; +OOD if asked). Mirrors
    src/bin/eval_checkpoints.sh. Results -> /work/results/t24/.
    only_step>0 restricts to that single checkpoint (path validation)."""
    import os, glob, time, subprocess, urllib.request
    ckdir = f"/work/checkpoints/{exp}"
    outdir = "/work/results/t24"
    os.makedirs(outdir, exist_ok=True)
    written = []
    for ck in sorted(glob.glob(f"{ckdir}/global_step_*")):
        if not os.path.isdir(f"{ck}/actor"):
            continue
        step = os.path.basename(ck).replace("global_step_", "")
        if only_step and int(step) != only_step:
            continue
        out = f"{outdir}/{exp}_step_{step}.json"
        if os.path.exists(out) and not ood:
            print(f"step {step}: done, skip"); continue
        merged = f"/work/merged/{exp}/step_{step}"
        if not os.path.exists(f"{merged}/config.json"):
            _run(["python3", "/workspace/src/train/merge_ckpt.py",
                  "--local_dir", f"{ck}/actor", "--target_dir", merged])
        # OOD sets (ToxicChat) have long real-traffic prompts that overflow 2048
        # and make vLLM 400; give the OOD path more context.
        mml = "4096" if ood else "2048"
        srv = subprocess.Popen(
            ["python3", "-m", "vllm.entrypoints.openai.api_server", "--model", merged,
             "--served-model-name", f"step_{step}", "--port", "8000",
             "--max-model-len", mml, "--gpu-memory-utilization", "0.85"])
        try:
            for _ in range(120):
                try:
                    urllib.request.urlopen("http://localhost:8000/v1/models", timeout=5); break
                except Exception:
                    time.sleep(5)
            else:
                raise RuntimeError(f"step {step}: vLLM never came up")
            datasets = ["xstest"] + (["toxicchat", "wildguardtest"] if ood else [])
            for ds in datasets:
                o = out if ds == "xstest" else f"{outdir}/{exp}_step_{step}_{ds}.json"
                if os.path.exists(o):
                    continue
                _run(["python3", "-m", "src.harness.evaluate", "--model", "nemotron-reasoning",
                      "--dataset", ds, "--base-url", "http://localhost:8000",
                      "--served-model", f"step_{step}", "--out", o], cwd="/workspace")
                written.append(o)
        finally:
            srv.terminate(); srv.wait()
    work.commit()
    return written


# ----------------------------------------------------- T48 cell scoring (1 GPU) --
@app.function(image=image, gpu=EVAL_GPU, volumes=VOLS, secrets=secrets, timeout=2 * 3600)
def score_cells(exp: str, attack: bool = False, only_step: int = 0):
    """T48 (s5.7 R1): per-cell learning-impact scoring pass. For the baseline +
    each merged checkpoint of `exp`, serve vLLM and run the probe channel
    (grid_probe, n=8 T=0.7, fresh never-trained rows) with per-row pass rates
    saved. One pass yields all three primary signals: per-cell trajectory,
    vote-split, pseudo-zero-advantage fraction. -> /work/results/t48/
    attack=True (T49): also run the disguise channel (attack_set) → per-cell
    ASR trajectory, the discovery signal (rising ASR = a loophole)."""
    import os, glob, time, subprocess, urllib.request
    outdir = "/work/results/t48"
    os.makedirs(outdir, exist_ok=True)
    # merge the requested checkpoint(s) from the training dir if not merged yet,
    # so this runs WHILE training is still producing later steps (auto-eval).
    for ck in sorted(glob.glob(f"/work/checkpoints/{exp}/global_step_*")):
        step = os.path.basename(ck).replace("global_step_", "")
        if only_step and int(step) != only_step:
            continue
        merged = f"/work/merged/{exp}/step_{step}"
        if os.path.isdir(f"{ck}/actor") and not os.path.exists(f"{merged}/config.json"):
            _run(["python3", "/workspace/src/train/merge_ckpt.py",
                  "--local_dir", f"{ck}/actor", "--target_dir", merged])
    # (model_path, step_tag): baseline HF model = step 0, then merged ckpts
    targets = [(MODEL, "step_0")] if not only_step else []
    for m in sorted(glob.glob(f"/work/merged/{exp}/step_*")):
        tag = os.path.basename(m)
        if only_step and tag != f"step_{only_step}":
            continue
        targets.append((m, tag))
    written = []
    for model_path, tag in targets:
        # baseline is run-independent: shared artifact, scored once
        base = "baseline_step_0" if tag == "step_0" else f"{exp}_{tag}"
        out = f"{outdir}/{base}_probe.json"
        atk = f"{outdir}/{base}_attack.json"
        need_probe = not os.path.exists(out + ".rows.jsonl")
        need_atk = attack and not os.path.exists(atk + ".rows.jsonl")
        if not need_probe and not need_atk:
            print(f"{tag}: done, skip"); continue
        srv = subprocess.Popen(
            ["python3", "-m", "vllm.entrypoints.openai.api_server", "--model", model_path,
             "--served-model-name", tag, "--port", "8000",
             "--max-model-len", "2048", "--gpu-memory-utilization", "0.85"])
        try:
            for _ in range(120):
                try:
                    urllib.request.urlopen("http://localhost:8000/v1/models", timeout=5); break
                except Exception:
                    time.sleep(5)
            else:
                raise RuntimeError(f"{tag}: vLLM never came up")
            if need_probe:
                _run(["python3", "-m", "src.harness.grid_probe",
                      "--probe", "/workspace/raw/probe_set_it4.jsonl",
                      "--base-url", "http://localhost:8000", "--served-model", tag,
                      "--out", out, "--save-rows"], cwd="/workspace")
                written.append(out)
            if need_atk:  # T49 disguise channel -> per-cell ASR trajectory
                _run(["python3", "-m", "src.harness.grid_probe",
                      "--attack", "/workspace/raw/attack_set_it4.jsonl",
                      "--base-url", "http://localhost:8000", "--served-model", tag,
                      "--out", atk, "--save-rows"], cwd="/workspace")
                written.append(atk)
        finally:
            srv.terminate(); srv.wait()
        work.commit()
    return written


# --------------------------------------------------- auto-eval helpers (CPU) --
@app.function(image=image, volumes=VOLS, timeout=300)
def list_ckpts(exp: str):
    """Steps whose actor shard is fully written, for the overlap watcher."""
    import glob, os
    work.reload()
    steps = []
    for ck in sorted(glob.glob(f"/work/checkpoints/{exp}/global_step_*")):
        if os.path.isdir(f"{ck}/actor"):
            steps.append(int(os.path.basename(ck).replace("global_step_", "")))
    return sorted(steps)


# ------------------------------------------------------------- orchestration --
@app.local_entrypoint()
def main(mode: str = "smoke", arg: str = ""):
    if mode == "probe":
        probe.remote()
        return

    if mode == "t48":
        # score the contrast pair: best blind run + the drift-y routed run
        handles = [score_cells.spawn(e) for e in ("grpo-t24-blind-r2", "grpo-t24-routed-r1")]
        for h in handles:
            print("T48 wrote:", h.get())
        print("Pull: modal volume get guard-t24 /results/t48 ./results/t48 --force")
        return

    if mode == "train_eval":
        # auto-eval: eval fires per checkpoint WHILE training runs, not after.
        # arg = "<arm> [rnd] [attack]", e.g. "amend 1 attack"
        import time
        parts = (arg or "amend 1").split()
        arm = parts[0]
        rnd = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
        attack = "attack" in parts
        exp = f"grpo-t24-{arm}-r{rnd}"
        th = train_arm.spawn(arm, rnd)
        seen, evals, done = set(), [], False
        while not done:
            try:
                th.get(timeout=0)        # non-blocking: raises if still training
                done = True
            except Exception:
                done = False
            for s in list_ckpts.remote(exp):
                if s not in seen:
                    seen.add(s)
                    evals.append(score_cells.spawn(exp, attack, s))
                    print(f"auto-eval spawned for {exp} step {s}")
            if not done:
                time.sleep(45)
        for e in evals:
            print("eval:", e.get())
        print(f"train_eval done for {exp}")
        return

    if mode == "smoke":
        prep.remote()
        exp, steps = train_arm.remote("routed", 1, smoke=True)
        print(f"SMOKE OK: {exp} produced {len(steps)} checkpoints: {steps}")
        return

    if mode in ("full", "train"):
        prep.remote()
        # 4-wide: all arms x rounds at once (16 GPUs; extras queue if quota-capped).
        # Each arm's eval is spawned the moment ITS training returns (pipeline,
        # no barrier) — profiling showed sequential rounds, not step time, was
        # the wall-clock bottleneck (120 steps x ~26s = ~55 min per run).
        handles = [(arm, rnd, train_arm.spawn(arm, rnd)) for rnd in ROUNDS for arm in ARMS]
        evals = []
        for arm, rnd, h in handles:
            exp, steps = h.get()
            print(f"TRAIN DONE: {exp} ({len(steps)} ckpts)")
            if mode == "full":
                evals.append((exp, eval_arm.spawn(exp)))
        for exp, h in evals:
            print(f"EVAL wrote ({exp}):", h.get())
        print("ALL DONE. Pull: modal volume get guard-t24 /results ./results/modal_t24 --force")
