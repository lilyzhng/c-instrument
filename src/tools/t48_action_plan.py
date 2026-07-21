#!/usr/bin/env python3
"""T48 (s5.7 R1): turn a cell-impact ledger into the loop's action plan.

Input: impact_<exp>.json from cell_learning_impact.py.
Output: an action-plan JSON that IS the decision ledger for the next
iteration — including pre-registered predictions so the loop closure (#9)
is a test, not a story:

  prune   saturated cells -> generate NOTHING new there next iteration
          (their existing rows stay in the corpus: retention set, L3)
  expand  frontier cells + steady-but-split cells (vote_split >= --split-floor)
          -> n_pairs each, sized by how far from mastered
  audit   stuck cells -> small spot-check list (no deep dive; 2026-07-20)
  amend   degrading cells -> court-protocol candidates

Predictions registered (checked after the loop retrain):
  P1 each expanded cell's fresh-probe pass rate rises >= +0.05
  P2 pruned cells hold (drop <= 0.05) despite zero new data
  P3 global XSTest does not regress beyond noise (>= best-anchor - 0.01)

Usage: python3 src/tools/t48_action_plan.py --impact results/t48/impact_<exp>.json
"""

import argparse
import json


def build_plan(impact, split_floor=0.3, expand_pairs=4):
    plan = {"exp": impact["exp"], "steps_scored": impact["steps"],
            "prune": [], "expand": [], "audit": [], "amend": []}
    for c in impact["cells"]:
        cls, cell = c["class"], c["cell"]
        if cls == "saturated":
            plan["prune"].append(cell)
        elif cls == "frontier":
            plan["expand"].append({"cell": cell, "n_pairs": expand_pairs,
                                   "why": "frontier", "traj": c["traj"]})
        elif cls == "steady" and c["vote_split"] >= split_floor:
            plan["expand"].append({"cell": cell, "n_pairs": expand_pairs,
                                   "why": f"vote_split={c['vote_split']}",
                                   "traj": c["traj"]})
        elif cls == "stuck":
            plan["audit"].append({"cell": cell, "traj": c["traj"]})
        elif cls == "degrading":
            plan["amend"].append({"cell": cell, "traj": c["traj"],
                                  "clim": c["clim"]})
    plan["predictions"] = {
        "P1_expand_rise": {"cells": [e["cell"] for e in plan["expand"]],
                           "threshold": "+0.05 fresh-probe pass rate"},
        "P2_prune_hold": {"cells": plan["prune"],
                          "threshold": "drop <= 0.05 with zero new data"},
        "P3_global_no_regress": {"metric": "XSTest balanced",
                                 "threshold": ">= anchor best - 0.01"},
    }
    plan["counts"] = {k: len(plan[k]) for k in ("prune", "expand", "audit", "amend")}
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--impact", required=True)
    ap.add_argument("--split-floor", type=float, default=0.3)
    ap.add_argument("--expand-pairs", type=int, default=4)
    ap.add_argument("--out")
    args = ap.parse_args()
    impact = json.load(open(args.impact))
    plan = build_plan(impact, args.split_floor, args.expand_pairs)
    out = args.out or args.impact.replace("impact_", "plan_")
    with open(out, "w") as f:
        json.dump(plan, f, indent=1)
    print(f"{plan['exp']}: {plan['counts']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
