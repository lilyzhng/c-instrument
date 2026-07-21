#!/usr/bin/env python3
"""T24-A: blind-fill control pack for the routed-vs-blind experiment (H2 #2).

The control arm for H2: same generator (GLM-5.2), same 3-judge ensemble,
same decon rule, same size and safe/unsafe balance as the routed pack
(results/routed_pack_it4.jsonl: 1,860 rows, 930/930) — the ONE difference
is budget allocation: uniform over the full constitution grid instead of
probe-routed to wavering cells. Any outcome difference between the two
arms is then attributable to routing, not pipeline drift.

Stages (each resumable via the intermediate files):
  1. generate  — generate.run() n_pairs per cell over ALL grid cells
                 -> results/blind_pack_raw.jsonl
  2. filter    — keep judge-agreed rows only, decon vs XSTest (Jaccard 0.6)
  3. sample    — uniform random downsample (fixed seed) to exactly match
                 the routed pack's size + label balance
                 -> results/blind_pack_t24.jsonl

Usage:  AQ_KEY=... python3 src/datagen/blind_pack.py [--n-pairs 3] [--workers 48]
        python3 src/datagen/blind_pack.py --skip-generate   # redo filter+sample only

T32-blind (exp15-budget study): --target-rows N overrides the routed-pack size
mirror — e.g. --target-rows 4728 --raw-path results/blind_pack7k_raw.jsonl
--out results/blind_pack_7k.jsonl builds the blind replacement for it6's
hardex+breadth+routed packs (equal budget, 50/50 balance), so exp15 can be
compared against pure blind coverage at the same 7,241-row corpus size.
"""

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.getcwd())
from src.datagen.generate import run as generate_run  # noqa: E402
from src.datagen.decon import (  # noqa: E402
    load_xstest_prompts, max_similarity, normalize, DEFAULT_THRESHOLD)

RAW_PATH = "results/blind_pack_raw.jsonl"
OUT_PATH = "results/blind_pack_t24.jsonl"
ROUTED_PATH = "results/routed_pack_it4.jsonl"
SEED = 24  # fixed so the sample is reproducible


def target_from_routed():
    rows = [json.loads(l) for l in open(ROUTED_PATH)]
    n = {"safe": 0, "unsafe": 0}
    for r in rows:
        n[r["constructed_label"]] += 1
    return n


def filter_and_sample(target, raw_path=RAW_PATH, out_path=OUT_PATH):
    rows = [json.loads(l) for l in open(raw_path)]
    agreed = [r for r in rows if r.get("agrees")]
    corpus_sets = [normalize(x) for x in load_xstest_prompts()]
    clean = [r for r in agreed
             if max_similarity(r["prompt"], corpus_sets)[0] < DEFAULT_THRESHOLD]
    print(f"raw {len(rows)} -> judge-agreed {len(agreed)} -> decon-clean {len(clean)}")

    rng = random.Random(SEED)
    picked = []
    for label, want in target.items():
        pool = [r for r in clean if r["constructed_label"] == label]
        if len(pool) < want:
            print(f"WARNING: only {len(pool)} {label} rows for target {want} "
                  f"— rerun stage 1 with a higher --n-pairs")
            picked += pool
        else:
            picked += rng.sample(pool, want)
    rng.shuffle(picked)
    with open(out_path, "w") as f:
        for r in picked:
            f.write(json.dumps(r) + "\n")
    got = {"safe": sum(r["constructed_label"] == "safe" for r in picked),
           "unsafe": sum(r["constructed_label"] == "unsafe" for r in picked)}
    print(f"wrote {out_path}: {len(picked)} rows {got} (target {target})")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-pairs", type=int, default=4,
                   help="pairs per cell; 4 leaves headroom for agree+decon losses")
    p.add_argument("--workers", type=int, default=48)
    p.add_argument("--skip-generate", action="store_true",
                   help="reuse existing raw file; redo filter+sample only")
    p.add_argument("--target-rows", type=int,
                   help="override routed-pack size mirror: N rows, 50/50 balance")
    p.add_argument("--raw-path", default=RAW_PATH)
    p.add_argument("--out", default=OUT_PATH)
    args = p.parse_args()

    if args.target_rows:
        target = {"safe": args.target_rows // 2,
                  "unsafe": args.target_rows - args.target_rows // 2}
        print(f"target (override): {target}")
    else:
        target = target_from_routed()
        print(f"target (from routed pack): {target}")
    if not args.skip_generate:
        generate_run(args.n_pairs, 0, args.raw_path, args.workers)
    filter_and_sample(target, raw_path=args.raw_path, out_path=args.out)


if __name__ == "__main__":
    main()
