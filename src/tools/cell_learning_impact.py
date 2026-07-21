#!/usr/bin/env python3
"""T48 (s5.7 R1): per-cell learning-impact analysis — the coverage engine's
routing signal.

Input: the T48 scoring pass's per-row files (grid_probe --save-rows), one per
checkpoint: results/t48/{exp}_step_{N}_probe.json.rows.jsonl (+ shared
baseline_step_0). Each row = {cell, label, pass_rate} where pass_rate is the
fraction of n=8 rollouts (T=0.7) that matched the constructed label on a FRESH
never-trained probe prompt.

Signals per cell (all from the same pass; s5.7 signal menu):
  traj        — mean pass rate per checkpoint (the learning curve)
  clim        — cell-level LIM alignment score, adapted from LIMR
                (arXiv:2502.11886): s_c = 1 - sum_k (r_c^k - rbar_k)^2
                                            / sum_k (1 - rbar_k)^2
  vote_split  — fraction of the cell's rows with 0 < pass_rate < 1 at the
                LAST checkpoint (mixed rollouts = expand signal)
  zero_adv    — fraction of rows with pass_rate in {0,1} at the last
                checkpoint (offline analogue of GRPO zero-advantage groups)

Taxonomy -> action (thresholds are v1 defaults, stated not hidden):
  saturated  start high (>=0.9) and stay high             -> prune generation
  frontier   rise >= +0.1 from step0 to last              -> expand instances
  stuck      end < 0.6 with no rise                        -> audit labels
  degrading  fall >= -0.1 while the global mean rises      -> amendment candidate
  steady     everything else                               -> no action

Usage: python3 src/tools/cell_learning_impact.py --dir results/t48 \
           --exp grpo-t24-blind-r2 [--min-n 3] [--out results/t48/impact_<exp>.json]
"""

import argparse
import glob
import json
import os
import re
from collections import defaultdict


def load_rows(path):
    return [json.loads(l) for l in open(path) if l.strip()]


def step_files(dirpath, exp):
    """(step:int, rows_path) for baseline + each checkpoint, sorted by step."""
    out = [(0, os.path.join(dirpath, "baseline_step_0_probe.json.rows.jsonl"))]
    for p in glob.glob(os.path.join(dirpath, f"{exp}_step_*_probe.json.rows.jsonl")):
        m = re.search(r"_step_(\d+)_probe", p)
        if m and int(m.group(1)) != 0:
            out.append((int(m.group(1)), p))
    return sorted(p for p in out if os.path.exists(p[1]))


def cell_series(files, min_n, keys=5):
    """cell -> {steps, traj, last_rows}; cells with < min_n rows are dropped.
    keys<5 truncates the cell id (topic|mechanism|shape|depth|form) to its
    first `keys` fields — the L2 back-off when exact cells are too thin."""
    per_step = {}
    for step, path in files:
        rows = defaultdict(list)
        for r in load_rows(path):
            cid = "|".join(r["cell"].split("|")[:keys])
            rows[cid].append(r["pass_rate"])
        per_step[step] = rows
    steps = sorted(per_step)
    cells = set.intersection(*(set(per_step[s]) for s in steps))
    series = {}
    for c in cells:
        if any(len(per_step[s][c]) < min_n for s in steps):
            continue
        series[c] = {
            "steps": steps,
            "traj": [round(sum(per_step[s][c]) / len(per_step[s][c]), 3)
                     for s in steps],
            "last_rows": per_step[steps[-1]][c],
            "n": len(per_step[steps[-1]][c]),
        }
    return series


def clim_score(traj, mean_traj):
    """Cell-level LIM alignment (LIMR eq. adapted sample->cell, fresh rows)."""
    num = sum((r - m) ** 2 for r, m in zip(traj, mean_traj))
    den = sum((1 - m) ** 2 for m in mean_traj)
    return round(1 - num / den, 3) if den > 0 else None


def classify(traj, global_rising, clim=None):
    """v2 (2026-07-21): stuck also fires on clim < 0 — a principled floor
    (the cell deviates from the field's mean curve more than the mean
    deviates from perfection). v1's absolute end<0.6 missed the privacy
    region (flat at 0.80 in a 0.97 field, clim -10.02); the C-LIM floor
    is structural, not tuned to that case, and is checked AFTER frontier
    so rising cells are never flagged."""
    start, end = traj[0], traj[-1]
    delta = end - start
    if start >= 0.9 and min(traj) >= 0.85:
        return "saturated"
    if delta >= 0.1:
        return "frontier"
    if delta <= -0.1 and global_rising:
        return "degrading"
    if end < 0.6 or (clim is not None and clim < 0):
        return "stuck"
    return "steady"


ACTIONS = {"saturated": "prune", "frontier": "expand", "stuck": "audit",
           "degrading": "amend", "steady": "none"}


def analyze(dirpath, exp, min_n, keys=5):
    files = step_files(dirpath, exp)
    if len(files) < 3:
        raise SystemExit(f"need >=3 scored checkpoints, found {len(files)}: {files}")
    series = cell_series(files, min_n, keys)
    mean_traj = [sum(v["traj"][i] for v in series.values()) / len(series)
                 for i in range(len(files))]
    global_rising = mean_traj[-1] > mean_traj[0] + 0.01
    cells = []
    for c, v in sorted(series.items()):
        last = v["last_rows"]
        clim = clim_score(v["traj"], mean_traj)
        cls = classify(v["traj"], global_rising, clim)
        cells.append({
            "cell": c, "n": v["n"], "traj": v["traj"],
            "clim": clim,
            "vote_split": round(sum(0 < r < 1 for r in last) / len(last), 3),
            "zero_adv": round(sum(r in (0.0, 1.0) for r in last) / len(last), 3),
            "class": cls, "action": ACTIONS[cls],
        })
    counts = defaultdict(int)
    for c in cells:
        counts[c["class"]] += 1
    return {
        "exp": exp, "steps": [s for s, _ in files], "min_n": min_n, "keys": keys,
        "n_cells": len(cells), "mean_traj": [round(m, 3) for m in mean_traj],
        "class_counts": dict(counts), "cells": cells,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="results/t48")
    ap.add_argument("--exp", required=True)
    ap.add_argument("--min-n", type=int, default=3)
    ap.add_argument("--keys", type=int, default=5,
                    help="cell-id fields used (2 = topic|mechanism back-off)")
    ap.add_argument("--out")
    args = ap.parse_args()
    result = analyze(args.dir, args.exp, args.min_n, args.keys)
    suffix = "" if args.keys == 5 else f"_k{args.keys}"
    out = args.out or os.path.join(args.dir, f"impact_{args.exp}{suffix}.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print(f"{result['exp']}: {result['n_cells']} cells over steps {result['steps']}")
    print(f"mean traj {result['mean_traj']}")
    print(f"classes  {result['class_counts']}")
    for cls in ("degrading", "stuck"):
        worst = [c for c in result["cells"] if c["class"] == cls][:5]
        for c in worst:
            print(f"  {cls:10} {c['cell'][:60]:60} traj={c['traj']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
