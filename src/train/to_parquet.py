"""Convert prepared training records (JSONL from prepare_data.py) into the
train/val parquet pair verl reads (design §4.3.4).

verl expects columns: data_source, prompt (chat messages), reward_model
(dict with ground_truth), extra_info. We add a deterministic train/val split
that keeps intent-flip pairs on the same side is not required here (the pilot
rows are already flattened), but the split is seeded-free and deterministic
(every Nth row to val) so reruns are reproducible.

Runs wherever pandas is available (the verl image has it). No network.
"""

import argparse
import json
import os

DATA_SOURCE = "xstest_synth_guard"
VAL_EVERY = 10  # every 10th record goes to val (deterministic, ~10%)


def to_frame_rows(records):
    """Attach data_source and split each record deterministically. Returns
    (train_rows, val_rows) as plain dicts ready for a DataFrame."""
    train, val = [], []
    for i, r in enumerate(records):
        row = {
            "data_source": DATA_SOURCE,
            "prompt": r["prompt"],
            "reward_model": r["reward_model"],
            "extra_info": {**r.get("extra_info", {}), "index": i},
        }
        (val if i % VAL_EVERY == VAL_EVERY - 1 else train).append(row)
    return train, val


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows", default="results/train_pilot.jsonl")
    p.add_argument("--out-dir", default="results/parquet")
    args = p.parse_args()

    import pandas as pd  # local import so the pure split stays testable
    records = [json.loads(l) for l in open(args.rows)]
    train, val = to_frame_rows(records)
    os.makedirs(args.out_dir, exist_ok=True)
    train_path = os.path.join(args.out_dir, "train.parquet")
    val_path = os.path.join(args.out_dir, "val.parquet")
    pd.DataFrame(train).to_parquet(train_path)
    pd.DataFrame(val).to_parquet(val_path)
    print(f"train={len(train)} -> {train_path}")
    print(f"val={len(val)} -> {val_path}")


if __name__ == "__main__":
    main()
