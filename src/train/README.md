# Training harness (Phase 4, §5.4)

GRPO on [verl](https://github.com/volcengine/verl), base **Nemotron-Content-Safety-Reasoning-4B**, on the Brev node (8×A100 80GB). Design: `deliverables/design_doc.md` §4.3.

## Files

| File | Role |
|---|---|
| `reward.py` | Rule reward (§4.3.3): label +1 in the answer slot, format −0.2, category +0.2. `compute_score` is verl's custom-reward entrypoint. Anti-hacking: label read only after `</think>`. |
| `prepare_data.py` | Generated rows (`pilot.jsonl` / `train_data.jsonl`) → training records. Trains only on judge-trusted rows (`agrees == True`); drops contradicted ones. |
| `to_parquet.py` | Training records JSONL → `train.parquet` / `val.parquet` (verl schema). |
| `../bin/run_grpo_smoke.sh` | GRPO smoke run (T12): GRPO + `filter_groups` (online probing, §4.3.2) + rule reward + W&B. Runs inside the verl image. |

All pure logic is unit-tested in `src/tests/test_train.py` (run `python -m pytest src/tests/test_train.py`).

## Run on Brev (node `vast-sapphire-halibut`)

```bash
# 1. on the node: pull this repo, prep data
cd ~/c-guard && git pull
python3 -m src.train.prepare_data --rows results/pilot.jsonl --out results/train_pilot.jsonl
python3 -m src.train.to_parquet --rows results/train_pilot.jsonl --out-dir results/parquet   # needs pandas

# 2. launch inside the verl image (W&B key from the container env, never committed)
IMG=verlai/verl:app-verl0.5-vllm0.10.0-mcore0.13.0-te2.2
sudo docker run --rm --gpus all --shm-size=32g \
  -e WANDB_API_KEY="$WANDB_API_KEY" -e WANDB_ENTITY=<your-wandb-entity> \
  -v ~/c-guard:/workspace \
  "$IMG" bash /workspace/src/bin/run_grpo_smoke.sh
```

## Smoke-run gate (T12)

Watch in W&B (project `guard-grpo`): **reward mean should rise** and the **`filter_groups` drop-rate should be < 1.0** (some groups retain variance). If every group is dropped (all-agree), the pilot is too easy → regenerate closer to the boundary (§4.3.2). Nonzero advantage = go for the real run (T13) on the 2K corpus.
