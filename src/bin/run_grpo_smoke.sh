#!/usr/bin/env bash
# GRPO smoke run (T12): overfit the pilot to prove advantage does not collapse
# (design §4.3). Adapts verl's examples/grpo_trainer/run_qwen2-7b.sh with:
#   - our base model (Nemotron reasoning 4B)
#   - online probing: algorithm.filter_groups.enable=True (§4.3.2)
#   - rule reward: custom_reward_function -> src/train/reward.py (§4.3.3)
#   - W&B logging (trainer.logger=['console','wandb'])
#
# Runs INSIDE the verl image. Env knobs: MODEL, TRAIN, VAL, REWARD, NGPUS,
# EPOCHS, WANDB_PROJECT, WANDB_ENTITY (WANDB_API_KEY comes from the container
# env). This is the smoke config (small batch, few epochs); the real run
# (T13) reuses it with the 2K corpus and the §4.3.4 hyperparameters.
set -x

MODEL=${MODEL:-nvidia/Nemotron-Content-Safety-Reasoning-4B}
TRAIN=${TRAIN:-/workspace/train/parquet/train.parquet}
VAL=${VAL:-/workspace/train/parquet/val.parquet}
REWARD=${REWARD:-/workspace/train/reward.py}
NGPUS=${NGPUS:-2}
GRAD_CKPT=${GRAD_CKPT:-True}
MICRO=${MICRO:-4}
EPOCHS=${EPOCHS:-8}
BATCH=${BATCH:-16}
LR=${LR:-1e-7}
ROLLOUT_N=${ROLLOUT_N:-8}
WANDB_PROJECT=${WANDB_PROJECT:-guard-grpo}
WANDB_ENTITY=${WANDB_ENTITY:-alchemxz}
EXPERIMENT=${EXPERIMENT:-pilot-smoke}
SAVE_FREQ=${SAVE_FREQ:--1}     # T13: 25 (checkpoints feed the 4-curve eval); smoke: -1
TEST_FREQ=${TEST_FREQ:-5}
CKPT_DIR=${CKPT_DIR:-/workspace/checkpoints/$EXPERIMENT}

# NOTE: do NOT pin VLLM_ATTENTION_BACKEND=XFORMERS (old verl-example carryover):
# XFORMERS lacks gemma3 interleaved-attention support, so vLLM 0.10 caps
# max_model_len to the 1024 sliding window and rejects our 1536. The default
# FlashAttention backend handles it.

python3 -m verl.trainer.main_ppo \
    algorithm.adv_estimator=grpo \
    +algorithm.filter_groups.enable=True \
    +algorithm.filter_groups.metric=acc \
    +algorithm.filter_groups.max_num_gen_batches=4 \
    algorithm.use_kl_in_reward=False \
    data.train_files="$TRAIN" \
    data.val_files="$VAL" \
    data.train_batch_size=$BATCH \
    +data.gen_batch_size=$((BATCH * 3)) \
    data.max_prompt_length=1024 \
    data.max_response_length=512 \
    data.return_multi_modal_inputs=False \
    data.filter_overlong_prompts=True \
    data.truncation='error' \
    custom_reward_function.path="$REWARD" \
    custom_reward_function.name=compute_score \
    actor_rollout_ref.model.path="$MODEL" \
    actor_rollout_ref.model.use_remove_padding=True \
    actor_rollout_ref.model.enable_gradient_checkpointing=$GRAD_CKPT \
    actor_rollout_ref.actor.optim.lr=$LR \
    actor_rollout_ref.actor.ppo_mini_batch_size=8 \
    actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=$MICRO \
    "+actor_rollout_ref.actor.fsdp_config.wrap_policy.transformer_layer_cls_to_wrap=[Gemma3DecoderLayer,SiglipVisionEmbeddings,SiglipEncoderLayer]" \
    "+actor_rollout_ref.ref.fsdp_config.wrap_policy.transformer_layer_cls_to_wrap=[Gemma3DecoderLayer,SiglipVisionEmbeddings,SiglipEncoderLayer]" \
    actor_rollout_ref.actor.use_kl_loss=True \
    actor_rollout_ref.actor.kl_loss_coef=0.001 \
    actor_rollout_ref.actor.kl_loss_type=low_var_kl \
    actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.rollout.name=vllm \
    actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.6 \
    actor_rollout_ref.rollout.n=$ROLLOUT_N \
    actor_rollout_ref.rollout.temperature=0.7 \
    actor_rollout_ref.ref.log_prob_micro_batch_size_per_gpu=16 \
    actor_rollout_ref.ref.fsdp_config.param_offload=True \
    trainer.critic_warmup=0 \
    trainer.logger=['console','wandb'] \
    trainer.project_name="$WANDB_PROJECT" \
    trainer.experiment_name="$EXPERIMENT" \
    trainer.n_gpus_per_node=$NGPUS \
    trainer.nnodes=1 \
    trainer.default_local_dir="$CKPT_DIR" \
    trainer.save_freq=$SAVE_FREQ \
    trainer.test_freq=$TEST_FREQ \
    trainer.total_epochs=$EPOCHS "$@"
