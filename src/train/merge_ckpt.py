"""Merge a verl FSDP checkpoint to HF format for a Gemma3 checkpoint.

verl 0.5.0's model_merger maps any `*ForConditionalGeneration` architecture to
AutoModelForVision2Seq, whose registry lacks Gemma3Config (transformers 4.53
files Gemma3ForConditionalGeneration under AutoModelForImageTextToText). We
patch only that class-picker; the merge itself is stock verl. Runs inside the
verl image:

    python3 src/train/merge_ckpt.py \
        --local_dir checkpoints/grpo-2k/global_step_25/actor \
        --target_dir merged/grpo-2k/step_25
"""

import argparse
import os

from transformers import AutoModelForImageTextToText

from verl.model_merger.base_model_merger import BaseModelMerger, ModelMergerConfig
from verl.model_merger.fsdp_model_merger import FSDPModelMerger

BaseModelMerger.get_transformers_auto_model_class = lambda self: AutoModelForImageTextToText


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local_dir", required=True)
    ap.add_argument("--target_dir", required=True)
    args = ap.parse_args()

    config = ModelMergerConfig(
        operation="merge",
        backend="fsdp",
        local_dir=args.local_dir,
        target_dir=args.target_dir,
        hf_model_config_path=os.path.join(args.local_dir, "huggingface"),
    )
    os.makedirs(args.target_dir, exist_ok=True)
    merger = FSDPModelMerger(config)
    merger.merge_and_save()
    print(f"merged -> {args.target_dir}")


if __name__ == "__main__":
    main()
