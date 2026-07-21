#!/usr/bin/env python3
"""Pull the T24 (routed-vs-blind) GRPO reward curves from W&B and plot them.

Reward = critic/score/mean: the fraction of the step's rollouts whose verdict
matches the gold label (rule reward, src/train/reward.py), logged every step.
Val = val-core/xstest_synth_guard/reward/mean@1, logged every 25 steps on the
arm's own val split.

Caveat (stated on the figure): each arm trains/validates on its OWN corpus, so
these curves compare optimization speed on the arm's own data — NOT safety
capability. XSTest checkpoint evals (results/t24_modal/) remain the verdict.

Usage: WANDB_API_KEY=... python3 src/tools/pull_t24_wandb_curves.py
Writes: results/t24_wandb_curves.json + deliverables/figures/t24-reward-curves.png
"""

import json
import os

RUNS = ["grpo-t24-routed-r1", "grpo-t24-routed-r2",
        "grpo-t24-blind-r1", "grpo-t24-blind-r2"]
ENTITY_PROJECT = "alchemxz/guard-t24"
OUT_JSON = "results/t24_wandb_curves.json"
OUT_PNG = "deliverables/figures/t24-reward-curves.png"

# categorical hues (validated pair + lighter steps for r2): routed=warm, blind=cool
COLORS = {"routed": "#B95D2A", "blind": "#2A6DB9"}


def pull():
    import wandb
    api = wandb.Api()
    curves = {}
    for run in api.runs(ENTITY_PROJECT):
        name = run.config.get("trainer", {}).get("experiment_name") or run.name
        if name not in RUNS or name in curves:
            continue
        hist = run.history(keys=["training/global_step", "critic/score/mean"],
                           pandas=False)
        val = run.history(keys=["training/global_step",
                                "val-core/xstest_synth_guard/reward/mean@1"],
                          pandas=False)
        curves[name] = {
            "train": [(h["training/global_step"], h["critic/score/mean"])
                      for h in hist if h.get("critic/score/mean") is not None],
            "val": [(h["training/global_step"],
                     h["val-core/xstest_synth_guard/reward/mean@1"])
                    for h in val
                    if h.get("val-core/xstest_synth_guard/reward/mean@1") is not None],
        }
    return curves


def plot(curves):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharex=True)
    for ax, key, title in [(axes[0], "train", "Train reward (own batch, every step)"),
                           (axes[1], "val", "Val reward (own val split, every 25)")]:
        for name in RUNS:
            if name not in curves or not curves[name][key]:
                continue
            arm, rnd = name.split("-")[2], name.split("-")[3]
            xs, ys = zip(*sorted(curves[name][key]))
            ax.plot(xs, ys, color=COLORS[arm],
                    linestyle="-" if rnd == "r1" else "--",
                    linewidth=2, alpha=0.9 if rnd == "r1" else 0.65,
                    label=f"{arm}-{rnd}")
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("global step")
        ax.grid(alpha=0.2, linewidth=0.5)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("reward (verdict-match rate)")
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle("T24 GRPO reward curves — each arm on its OWN corpus "
                 "(optimization speed, not safety capability)", fontsize=11)
    fig.tight_layout()
    os.makedirs(os.path.dirname(OUT_PNG), exist_ok=True)
    fig.savefig(OUT_PNG, dpi=150)
    print(f"wrote {OUT_PNG}")


def main():
    curves = pull()
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(curves, f)
    for name, c in curves.items():
        print(f"{name}: {len(c['train'])} train pts, {len(c['val'])} val pts")
    plot(curves)


if __name__ == "__main__":
    main()
