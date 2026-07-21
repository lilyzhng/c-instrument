#!/usr/bin/env bash
# T14 node-side loop: for each verl checkpoint of the grpo-2k run,
#   merge FSDP shards -> HF format (verl.model_merger, inside the verl image)
#   serve merged model with vLLM on a spare GPU (default 7; training holds 5-6)
#   run the §4.1 harness (src.harness.evaluate) against it -> per-step JSON
# Idempotent: skips steps whose results JSON already exists, so re-run it as
# new checkpoints land. Results: results/t14/step_<N>.json
set -euo pipefail

REPO=~/c-guard
VERL=~/verl
IMG=verlai/verl:app-verl0.5-vllm0.10.0-mcore0.13.0-te2.2
VLLM_IMG=vllm/vllm-openai:latest
EXPERIMENT=${EXPERIMENT:-grpo-2k}
EVAL_GPU=${EVAL_GPU:-7}
PORT=${PORT:-8010}
# OOD=1 adds the T14b real-world battery (ToxicChat + WildGuardTest) per step.
# Needs: pip install datasets; HF_TOKEN with accepted allenai/wildguardmix
# license. Default off — run it on baseline + ship-candidate steps, not every
# daemon pass. Rationale: src/harness/ood.py.
OOD=${OOD:-0}

mkdir -p "$REPO/results/t14" "$REPO/merged/$EXPERIMENT"

for ckpt in "$REPO"/checkpoints/"$EXPERIMENT"/global_step_*; do
  [ -d "$ckpt/actor" ] || continue
  step=$(basename "$ckpt" | sed 's/global_step_//')
  out="$REPO/results/t14/${EXPERIMENT}_step_${step}.json"
  need=0
  [ -f "$out" ] || need=1
  if [ "$OOD" = 1 ]; then
    for ds in toxicchat wildguardtest; do
      [ -f "$REPO/results/t14/${EXPERIMENT}_step_${step}_${ds}.json" ] || need=1
    done
  fi
  [ "$need" = 0 ] && { echo "step $step: done, skip"; continue; }

  merged="$REPO/merged/$EXPERIMENT/step_${step}"
  if [ ! -f "$merged/config.json" ]; then
    echo "step $step: merging FSDP -> HF"
    sudo docker run --rm -v "$REPO":/workspace -v "$VERL":/verl \
      -v ~/.cache/huggingface:/root/.cache/huggingface \
      "$IMG" bash -c "pip install --no-deps -e /verl -q && \
        python3 /workspace/src/train/merge_ckpt.py \
          --local_dir /workspace/checkpoints/$EXPERIMENT/global_step_${step}/actor \
          --target_dir /workspace/merged/$EXPERIMENT/step_${step}"
  fi

  echo "step $step: serving on GPU $EVAL_GPU"
  sudo docker rm -f t14-serve 2>/dev/null || true
  sudo docker run -d --name t14-serve --gpus "\"device=$EVAL_GPU\"" \
    -p $PORT:8000 -v "$REPO/merged":/models \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    "$VLLM_IMG" --model /models/$EXPERIMENT/step_${step} \
    --served-model-name step_${step} --max-model-len 2048 --gpu-memory-utilization 0.85

  for i in $(seq 1 60); do
    curl -sf localhost:$PORT/v1/models >/dev/null && break
    sleep 5
  done
  curl -sf localhost:$PORT/v1/models >/dev/null || { echo "step $step: server failed"; sudo docker logs --tail 20 t14-serve; exit 1; }

  echo "step $step: evaluating"
  cd "$REPO"
  [ -f "$out" ] || python3 -m src.harness.evaluate \
    --model nemotron-reasoning --base-url http://localhost:$PORT \
    --served-model step_${step} --out "$out"
  if [ "$OOD" = 1 ]; then
    for ds in toxicchat wildguardtest; do
      oodout="$REPO/results/t14/${EXPERIMENT}_step_${step}_${ds}.json"
      [ -f "$oodout" ] || python3 -m src.harness.evaluate \
        --model nemotron-reasoning --dataset "$ds" \
        --base-url http://localhost:$PORT \
        --served-model step_${step} --out "$oodout"
    done
  fi
  sudo docker rm -f t14-serve
  echo "step $step: wrote $out"
done
echo "all available checkpoints evaluated"
