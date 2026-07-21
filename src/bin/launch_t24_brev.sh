#!/usr/bin/env bash
# T24B node-side orchestrator: routed-vs-blind (H2), 2 rounds x 2 arms.
# Replicates the it6 recipe exactly (from-base retrain, EPOCHS=3, LR 5e-7,
# BATCH 32, MICRO 16, GRAD_CKPT False, NGPUS 4, SAVE_FREQ 25) — the ONE
# difference between arms is the pack merged into the v3 corpus.
# Rounds give per-arm variance (GRPO rollouts are stochastic; no seed knob).
# Run ON the node:  nohup bash launch_t24_brev.sh > t24b.log 2>&1 &
set -euo pipefail
REPO=/home/user/c-guard
VERL=/home/user/verl
IMG=verlai/verl:app-verl0.5-vllm0.10.0-mcore0.13.0-te2.2
cd "$REPO"

# --- corpora (idempotent) ---
for arm in routed blind; do
  pack=$([ "$arm" = routed ] && echo routed_pack_it4.jsonl || echo blind_pack_t24.jsonl)
  corpus="results/train_data_t24_${arm}.jsonl"
  prepared="results/train_prepared_t24_${arm}.jsonl"
  [ -f "$corpus" ] || cat results/train_data_v3.jsonl "results/$pack" > "$corpus"
  [ -f "$prepared" ] || python3 scripts/train/prepare_data.py --rows "$corpus" --out "$prepared"
  [ -d "results/parquet_t24_${arm}" ] || \
    python3 scripts/train/to_parquet.py --rows "$prepared" --out-dir "results/parquet_t24_${arm}"
  wc -l "$corpus" "$prepared"
done

# --- free the GPUs (evals done; containers stopped, not removed) ---
sudo docker stop vllm-exp15 vllm-nemotron-reasoning 2>/dev/null || true

run_arm() {  # arm round gpus
  local arm=$1 r=$2 gpus=$3 exp="grpo-t24-${1}-r${2}"
  sudo docker rm -f "$exp" 2>/dev/null || true
  sudo docker run -d --name "$exp" --gpus "\"device=${gpus}\"" --shm-size=32g \
    -v "$REPO":/workspace -v "$VERL":/verl \
    -v /home/user/.cache/huggingface:/root/.cache/huggingface \
    -v /home/user/.cache/vllm:/root/.cache/vllm \
    -e EXPERIMENT="$exp" -e LR=5e-7 -e BATCH=32 -e MICRO=16 -e NGPUS=4 \
    -e EPOCHS=3 -e GRAD_CKPT=False -e ROLLOUT_N=8 -e SAVE_FREQ=25 -e TEST_FREQ=25 \
    -e MODEL=nvidia/Nemotron-Content-Safety-Reasoning-4B \
    -e TRAIN="/workspace/results/parquet_t24_${arm}/train.parquet" \
    -e VAL="/workspace/results/parquet_t24_${arm}/val.parquet" \
    -e REWARD=/workspace/scripts/train/reward.py \
    -e WANDB_API_KEY="${WANDB_API_KEY:-}" -e WANDB_ENTITY=alchemxz \
    "$IMG" bash -c "pip install --no-deps -e /verl > /workspace/results/verl_install_${exp}.log 2>&1 && bash /workspace/scripts/train/run_grpo_smoke.sh"
  echo "launched $exp on GPUs $gpus"
}

for r in 1 2; do
  run_arm routed "$r" "0,1,2,3"
  run_arm blind  "$r" "4,5,6,7"
  echo "round $r running; waiting..."
  while sudo docker ps --format '{{.Names}}' | grep -q "grpo-t24-.*-r${r}"; do sleep 60; done
  echo "round $r done"
done
echo "T24B complete: 4 runs, checkpoints under checkpoints/grpo-t24-*"
