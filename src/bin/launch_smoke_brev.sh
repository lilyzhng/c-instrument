#!/usr/bin/env bash
# Node-side launcher for the T12 GRPO smoke run (runs ON the Brev node).
# Wraps the README §"Run on Brev" docker command + the bug-#1 fix (app image
# ships deps but not verl: mount the v0.5.0 checkout at /verl, editable-install
# at start). WANDB_API_KEY must be in the env (never committed).
# Detached, named container -> logs survive exit: sudo docker logs -f grpo-smoke
set -euo pipefail

: "${WANDB_API_KEY:?set WANDB_API_KEY in the env}"

REPO=~/c-instrument
VERL=~/verl
IMG=verlai/verl:app-verl0.5-vllm0.10.0-mcore0.13.0-te2.2
GPUS=${GPUS:-'"device=3,4"'}   # 0-2 host the T8 vLLM servers; keep off them

sudo docker rm -f grpo-smoke 2>/dev/null || true
sudo docker run -d --name grpo-smoke --gpus "$GPUS" --shm-size=32g \
  -e WANDB_API_KEY="$WANDB_API_KEY" -e WANDB_ENTITY=alchemxz \
  -e TRAIN=/workspace/results/parquet/train.parquet \
  -e VAL=/workspace/results/parquet/val.parquet \
  -e REWARD=/workspace/src/train/reward.py \
  -e NGPUS=2 \
  -v "$REPO":/workspace -v "$VERL":/verl \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v ~/.cache/vllm:/root/.cache/vllm \
  "$IMG" bash -c 'pip install --no-deps -e /verl > /workspace/results/verl_install.log 2>&1 && bash /workspace/src/bin/run_grpo_smoke.sh'
