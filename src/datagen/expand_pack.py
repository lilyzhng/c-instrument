#!/usr/bin/env python3
"""T48 (s5.7 R1): generate the expand pack from an action plan.

Reads plan_<exp>.json (t48_action_plan.py), generates n_pairs fresh instances
for each cell on the expand list — same generator/judges as always — then
filters to judge-agreed + decon-clean rows. The 'expand' half of the
prune/expand loop; the prune half is simply generating nothing for pruned
cells (their existing rows remain as the retention set).

Usage: AQ_KEY=... python3 src/datagen/expand_pack.py \
           --plan results/t48/plan_<exp>.json --out results/expand_pack_t48.jsonl
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from src.datagen.generate import run as generate_run  # noqa: E402
from src.datagen.grid import build_grid, load_constitutions, TOPICS_DIR  # noqa: E402
from src.datagen.decon import (  # noqa: E402
    load_xstest_prompts, max_similarity, normalize, DEFAULT_THRESHOLD)

CELL_KEYS = ("topic", "mechanism", "interaction_shape",
             "information_depth", "content_form")


def expand_prefixes(prefixes):
    """Plan cells may be topic|mechanism prefixes (the L2 k=2 back-off);
    map each prefix to every matching full 5-field grid cell id."""
    grid = build_grid(load_constitutions(TOPICS_DIR))
    full = ["|".join(str(c.get(k, "-")) for k in CELL_KEYS)
            for c in grid["cells"]]
    out = [f for f in full if any(f.startswith(p) for p in prefixes)]
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", default="results/expand_pack_t48.jsonl")
    ap.add_argument("--workers", type=int, default=48)
    args = ap.parse_args()

    plan = json.load(open(args.plan))
    expand = plan["expand"]
    if not expand:
        raise SystemExit("plan has no expand cells — nothing to generate")
    prefixes = [e["cell"] for e in expand]
    cell_ids = expand_prefixes(prefixes)
    n_pairs = max(e["n_pairs"] for e in expand)
    print(f"{len(prefixes)} plan prefixes -> {len(cell_ids)} grid cells, "
          f"n_pairs={n_pairs}")

    raw = args.out.replace(".jsonl", "_raw.jsonl")
    generate_run(n_pairs, 0, raw, args.workers, cell_ids=cell_ids)

    rows = [json.loads(l) for l in open(raw)]
    agreed = [r for r in rows if r.get("agrees")]
    corpus_sets = [normalize(x) for x in load_xstest_prompts()]
    clean = [r for r in agreed
             if max_similarity(r["prompt"], corpus_sets)[0] < DEFAULT_THRESHOLD]
    with open(args.out, "w") as f:
        for r in clean:
            f.write(json.dumps(r) + "\n")
    n = {"safe": sum(r["constructed_label"] == "safe" for r in clean),
         "unsafe": sum(r["constructed_label"] == "unsafe" for r in clean)}
    print(f"raw {len(rows)} -> agreed {len(agreed)} -> clean {len(clean)} {n}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
