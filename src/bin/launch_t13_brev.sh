#!/usr/bin/env bash
# Node-side launcher for the T13 real GRPO run (2K corpus, design §4.3.4 start
# hyperparameters: lr 1e-7, batch 32, n=8, temp 0.7, 3 epochs). Same container
# recipe as launch_smoke_brev.sh; GPUs 5-6 so it can run beside the smoke rerun
# (3-4) and the T8 vLLM servers (0-2). Checkpoints every 25 steps land in
# checkpoints/<EXPERIMENT>/ on the repo mount for the §4.3.5 4-curve eval.
set -euo pipefail

: "${WANDB_API_KEY:?set WANDB_API_KEY in the env}"

REPO=~/c-guard
VERL=~/verl
IMG=verlai/verl:app-verl0.5-vllm0.10.0-mcore0.13.0-te2.2
GPUS=${GPUS:-'"device=5,6"'}
EXPERIMENT=${EXPERIMENT:-grpo-2k}
CONTAINER=${CONTAINER:-grpo-t13}
LR=${LR:-1e-7}
ROLLOUT_N=${ROLLOUT_N:-8}
DATA_DIR=${DATA_DIR:-parquet_2k}
MODEL=${MODEL:-nvidia/Nemotron-Content-Safety-Reasoning-4B}
EPOCHS=${EPOCHS:-3}
NGPUS=${NGPUS:-2}
GRAD_CKPT=${GRAD_CKPT:-True}
MICRO=${MICRO:-4}

sudo docker rm -f "$CONTAINER" 2>/dev/null || true
sudo docker run -d --name "$CONTAINER" --gpus "$GPUS" --shm-size=32g \
  -e WANDB_API_KEY="$WANDB_API_KEY" -e WANDB_ENTITY=alchemxz \
  -e TRAIN=/workspace/results/$DATA_DIR/train.parquet \
  -e VAL=/workspace/results/$DATA_DIR/val.parquet \
  -e REWARD=/workspace/src/train/reward.py \
  -e NGPUS="$NGPUS" -e BATCH=32 -e EPOCHS="$EPOCHS" -e MODEL="$MODEL" \
  -e GRAD_CKPT="$GRAD_CKPT" -e MICRO="$MICRO" \
  -e EXPERIMENT="$EXPERIMENT" -e LR="$LR" -e ROLLOUT_N="$ROLLOUT_N" -e SAVE_FREQ=25 -e TEST_FREQ=25 \
  -v "$REPO":/workspace -v "$VERL":/verl \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -v ~/.cache/vllm:/root/.cache/vllm \
  "$IMG" bash -c 'pip install --no-deps -e /verl > /workspace/results/verl_install_t13.log 2>&1 && bash /workspace/src/bin/run_grpo_smoke.sh'
