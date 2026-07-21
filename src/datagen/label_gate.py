"""Label-correctness gate: does a generator's *constructed* label match a
neutral judge panel's verdict?

The generator bake-off scored structural quality (valid / length / shared
trigger / diversity). This gate scores the property that actually matters
for a single-point-of-failure generator: is the "safe" side truly safe and
the "unsafe" side truly unsafe? Each generated prompt is classified by a
panel that excludes *both* generator candidates (no self-preference), and
we check whether the majority verdict matches the label the pair was built
with.

Panel: DeepSeek-V4-Pro + Grok-4.5 + Kimi K3 (neutral to GPT and GLM).
Candidates scored head-to-head on the same pairs from generator_bakeoff.json.

Pure logic (majority_vote, score_gate) is unit-tested in
src/tests/test_datagen.py; only run() touches the network.

Usage: AQ_KEY=... python -m src.datagen.label_gate --n-pairs 18 --workers 4
"""

import argparse
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.getcwd())
from src.datagen.judge_bakeoff import SYS, parse_verdict  # noqa: E402

# panel excludes both generator candidates (GPT, GLM) -> no self-preference
GATE_JUDGES = ["deepseek/deepseek-v4-pro", "x-ai/grok-4.5", "moonshotai/kimi-k3"]
GEN_CANDIDATES = ["openai/gpt-5.6-sol", "z-ai/glm-5.2"]
BAKEOFF_PATH = "results/generator_bakeoff.json"
PROGRESS_PATH = "results/label_gate_progress.txt"
CHUNK = 24  # calls per bounded batch; barrier here gives progress, not a burst


# ---- pure logic (unit-tested, no network) ----

def majority_vote(verdicts):
    """Majority label among non-None verdicts. None on all-None or a tie
    (no strict majority), so an undecided panel never fakes agreement."""
    votes = [v for v in verdicts if v is not None]
    if not votes:
        return None
    counts = Counter(votes)
    top, n = counts.most_common(1)[0]
    if list(counts.values()).count(n) > 1:  # tie
        return None
    return top


def score_gate(items):
    """items: list of {"constructed": label, "majority": label|None}.
    Correct = the panel's majority matches the constructed label. Undecided
    (majority None) counts against the generator: a pair the panel cannot
    confidently label is not usable training data."""
    n = len(items)
    if n == 0:
        return {"n": 0}
    safe = [it for it in items if it["constructed"] == "safe"]
    unsafe = [it for it in items if it["constructed"] == "unsafe"]

    def acc(group):
        if not group:
            return None
        return round(sum(it["majority"] == it["constructed"] for it in group)
                     / len(group), 3)

    return {
        "n": n,
        "overall": acc(items),
        "safe_acc": acc(safe),
        "unsafe_acc": acc(unsafe),
        "undecided": sum(it["majority"] is None for it in items),
    }


# ---- orchestration (network) ----

def run(n_pairs, out_path, workers=6):
    """One bounded pool over every (prompt, judge) call for a generator, so
    concurrency is capped at `workers` and stays busy across prompts instead
    of idling in a 3-wide per-prompt pool. Bounded == controlled rate, not a
    burst (same principle as the judge bake-off's speedup)."""
    from src.datagen._aq import chat
    from src.datagen.ratelimit import AdaptiveLimiter
    from concurrent.futures import ThreadPoolExecutor

    limiter = AdaptiveLimiter() if workers == 1 else None

    def classify(model, prompt):
        if limiter is not None:
            time.sleep(limiter.next_delay())
        content, ok, retry_after = chat(model, SYS, prompt)
        if limiter is not None:
            limiter.record(ok, retry_after)
        return parse_verdict(content)

    def log_progress(msg):
        with open(PROGRESS_PATH, "a") as f:
            f.write(msg + "\n")
        print(msg, flush=True)

    bakeoff = json.load(open(BAKEOFF_PATH))
    os.makedirs("results", exist_ok=True)
    open(PROGRESS_PATH, "w").close()
    log_progress(f"panel: {GATE_JUDGES}  candidates: {GEN_CANDIDATES}  "
                 f"n_pairs<={n_pairs}  workers={workers}")

    result = {"panel": GATE_JUDGES, "per_generator": {}, "raw": {}}
    for gen in GEN_CANDIDATES:
        pairs = bakeoff["raw"].get(gen, [])[:n_pairs]
        # flat job list: one call per (pair, side, judge); key groups the panel
        jobs = []
        for pi, p in enumerate(pairs):
            for side in ("safe", "unsafe"):
                if p.get(side):
                    for j in GATE_JUDGES:
                        jobs.append(((pi, side), j, p[side]))
        verdicts = []
        for start in range(0, len(jobs), CHUNK):
            batch = jobs[start:start + CHUNK]
            if workers == 1:
                verdicts += [classify(j, prompt) for _k, j, prompt in batch]
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    verdicts += list(pool.map(lambda job: classify(job[1], job[2]), batch))
            log_progress(f"  [{gen}] {len(verdicts)}/{len(jobs)} calls")

        # regroup verdicts per (pair, side) and majority-vote the panel
        panel = {}
        for (key, _j, prompt), v in zip(jobs, verdicts):
            panel.setdefault(key, {"prompt": prompt, "votes": []})["votes"].append(v)
        items, raw = [], []
        for (pi, side), rec in sorted(panel.items()):
            maj = majority_vote(rec["votes"])
            items.append({"constructed": side, "majority": maj})
            raw.append({"side": side, "prompt": rec["prompt"],
                        "votes": rec["votes"], "majority": maj})
        s = score_gate(items)
        result["per_generator"][gen] = s
        result["raw"][gen] = raw
        log_progress(f"  DONE {gen}: overall={s.get('overall')} "
                     f"safe={s.get('safe_acc')} unsafe={s.get('unsafe_acc')} "
                     f"undecided={s.get('undecided')} n={s['n']}")

    open(out_path, "w").write(json.dumps(result, indent=2))
    log_progress(f"wrote {out_path}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-pairs", type=int, default=18,
                   help="pairs per generator to score (same N for fairness)")
    p.add_argument("--out", default="results/label_gate.json")
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    run(args.n_pairs, args.out, args.workers)


if __name__ == "__main__":
    main()
