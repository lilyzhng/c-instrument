#!/usr/bin/env bash
# T14 daemon: keep evaluating new checkpoints from every sweep arm as they
# land. Serial over experiments (one t14-serve on the eval GPU at a time);
# eval_checkpoints.sh is idempotent so each pass only does new steps.
# Stops itself when all training containers are gone and every checkpoint is
# evaluated. Log: results/t14/daemon.log
set -u
REPO=~/c-instrument
EXPS=${EXPS:-"grpo-2k grpo-2k-lr5e7 grpo-2k-n16"}

while true; do
  for exp in $EXPS; do
    EXPERIMENT=$exp bash "$REPO/src/bin/eval_checkpoints.sh" || true
  done
  WANDB_DIR=~/wandb_eval python3 -m src.harness.t14_to_wandb --dir "$REPO/results/t14" >/dev/null 2>&1 || true
  # exit when no trainer is running and nothing new appeared this pass
  if ! sudo docker ps --format '{{.Names}}' | grep -q '^grpo-t13'; then
    pending=0
    for exp in $EXPS; do
      for ckpt in "$REPO"/checkpoints/$exp/global_step_*; do
        [ -d "$ckpt/actor" ] || continue
        step=$(basename "$ckpt" | sed 's/global_step_//')
        [ -f "$REPO/results/t14/${exp}_step_${step}.json" ] || [ -f "$REPO/results/t14/step_${step}.json" ] || pending=1
      done
    done
    [ "$pending" = 0 ] && { echo "all done"; break; }
  fi
  sleep 60
done
