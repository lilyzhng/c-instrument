#!/usr/bin/env bash
# Post-v3 orchestration (T29 done -> T30, T25 inputs). Runs ON the node.
# 1. wait for grpo-t13-v3 to finish; 2. eval every v3 checkpoint (merge+serve+
# harness) -> results/t14/grpo-2k-v3_step_*.json; 3. re-probe the ASR channel
# on the final v3 checkpoint (T30) -> did the amendment close the drift?;
# 4. push results to W&B. Log: results/t14/post_v3.log
set -u
REPO=~/c-guard
cd "$REPO"

echo "[post-v3] waiting for grpo-t13-v3 to finish..."
while sudo docker ps --format '{{.Names}}' | grep -q '^grpo-t13-v3$'; do sleep 30; done
echo "[post-v3] v3 training done; evaluating checkpoints"

EXPS="grpo-2k-v3" bash src/bin/eval_checkpoints.sh || true
WANDB_DIR=~/wandb_eval python3 -m src.harness.t14_to_wandb --dir results/t14 >/dev/null 2>&1 || true

# T30: ASR re-probe on the final v3 checkpoint (highest step)
last=$(ls -d checkpoints/grpo-2k-v3/global_step_* 2>/dev/null | sort -t_ -k3 -n | tail -1 | sed 's/.*global_step_//')
if [ -n "$last" ]; then
  merged="merged/grpo-2k-v3/step_${last}"
  echo "[post-v3] T30: ASR re-probe on v3 step ${last}"
  sudo docker rm -f t14-serve 2>/dev/null
  sudo docker run -d --name t14-serve --gpus '"device=7"' -p 8010:8000 \
    -v "$REPO/merged":/models -v ~/.cache/huggingface:/root/.cache/huggingface \
    vllm/vllm-openai:latest --model /models/grpo-2k-v3/step_${last} \
    --served-model-name v3_step_${last} --max-model-len 2048 --gpu-memory-utilization 0.85 >/dev/null
  for i in $(seq 1 60); do curl -sf localhost:8010/v1/models >/dev/null && break; sleep 5; done
  python3 -m src.harness.grid_probe --attack results/attack_set_it4.jsonl \
    --base-url http://localhost:8010 --served-model v3_step_${last} \
    --out results/grid_probe_v3_attack.json
  # T25 memorization audit: pass-rate on TRAINED rows vs FRESH probe rows.
  echo "[post-v3] T25: memorization audit (trained vs fresh pass-rate)"
  python3 -m src.harness.grid_probe --probe results/t25_trained_sample.jsonl \
    --base-url http://localhost:8010 --served-model v3_step_${last} \
    --out results/t25_trained_probe.json
  python3 -m src.harness.grid_probe --probe results/probe_set_it4.jsonl \
    --base-url http://localhost:8010 --served-model v3_step_${last} \
    --out results/t25_fresh_probe.json
  sudo docker rm -f t14-serve 2>/dev/null
fi
echo "[post-v3] done"
