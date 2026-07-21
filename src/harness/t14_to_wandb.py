"""Push T14 checkpoint-eval results into W&B so the XSTest curves sit next to
the training curves. One W&B run per arm, named eval-<experiment>, with
step-indexed points (safe_acc, unsafe_acc, balanced_acc, pair_consistency,
per-family accs). Idempotent: rerunning overwrites the same eval runs (id =
eval-<experiment>).

Usage (node or laptop, needs WANDB_API_KEY):
    python3 -m src.harness.t14_to_wandb --dir results/t14
"""

import argparse
import json
import os
import re
from collections import defaultdict

import wandb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="results/t14")
    ap.add_argument("--project", default="guard-grpo")
    ap.add_argument("--entity", default="alchemxz")
    args = ap.parse_args()

    by_exp = defaultdict(dict)
    for fn in sorted(os.listdir(args.dir)):
        m = re.match(r"(.+)_step_(\d+)\.json$", fn)
        if not m:
            continue
        exp, step = m.group(1), int(m.group(2))
        with open(os.path.join(args.dir, fn)) as f:
            by_exp[exp][step] = json.load(f)["metrics"]

    for exp, steps in by_exp.items():
        run = wandb.init(project=args.project, entity=args.entity,
                         id=f"eval-{exp}", name=f"eval-{exp}",
                         resume="allow", reinit=True)
        for step in sorted(steps):
            m = steps[step]
            payload = {k: m[k] for k in
                       ("safe_acc", "unsafe_acc", "balanced_acc", "pair_consistency")}
            payload.update({f"family/{f}": v for f, v in m["per_family_acc"].items()})
            run.log(payload, step=step)
        run.finish()
        print(f"logged {exp}: steps {sorted(steps)}")


if __name__ == "__main__":
    main()
