"""Camera-ready (paper-plot style) versions of fig6 and fig7.

fig6-xstest-distribution-v2: XSTest composition (per-family counts + length hist).
fig7-baseline-per-family-v2: per-family baseline accuracy, three guard models.

Style: white canvas, no top/right spines, light dashed y-grid, bold sans titles,
shared top legend, value labels on bars (Zhang/Khattab fig7 grammar).
"""

import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "latex" / "figure"

SAFE = "#4C9A52"
UNSAFE = "#C0553D"
MODELS = [
    ("wildguard", "#B9B9B9"),
    ("nemotron-reasoning", "#2A6DB9"),
    ("nemotron-safety", "#4C9A52"),
]
FAMILY_LABEL = {
    "homonyms": "homonyms",
    "figurative_language": "figurative",
    "safe_targets": "safe targets",
    "safe_contexts": "safe contexts",
    "definitions": "definitions",
    "discrimination": "discrimination",
    "historical_events": "historical",
    "privacy": "privacy",
}
FAMILY_ORDER = list(FAMILY_LABEL)


def style_axis(ax):
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, color="#DDDDDD", zorder=0)
    ax.tick_params(labelsize=9)


def family_of(row_type: str) -> str:
    t = row_type.removeprefix("contrast_")
    if "discr" in t:
        return "discrimination"
    if "privacy" in t:
        return "privacy"
    return t


def build_fig6():
    rows = list(csv.DictReader(open(ROOT / "data" / "xstest_prompts.csv")))
    counts = Counter((family_of(r["type"]), r["label"]) for r in rows)
    lengths = [len(r["prompt"].split()) for r in rows]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(9.2, 3.4), width_ratios=[1.15, 1], facecolor="white"
    )

    y = np.arange(len(FAMILY_ORDER))[::-1]
    safe = [counts[(f, "safe")] for f in FAMILY_ORDER]
    unsafe = [counts[(f, "unsafe")] for f in FAMILY_ORDER]
    h = 0.38
    ax1.barh(y + h / 2, safe, h, color=SAFE, label="safe", zorder=3)
    ax1.barh(y - h / 2, unsafe, h, color=UNSAFE, label="unsafe", zorder=3)
    for yi, v in zip(y + h / 2, safe):
        ax1.text(v + 1, yi, str(v), va="center", fontsize=8, color=SAFE, fontweight="bold")
    for yi, v in zip(y - h / 2, unsafe):
        ax1.text(v + 1, yi, str(v), va="center", fontsize=8, color=UNSAFE, fontweight="bold")
    ax1.set_yticks(y, [FAMILY_LABEL[f] for f in FAMILY_ORDER])
    ax1.set_xlim(0, 58)
    ax1.set_title("Prompts per family", fontsize=11, fontweight="bold")
    style_axis(ax1)
    ax1.grid(axis="y", visible=False)
    ax1.grid(axis="x", linestyle="--", linewidth=0.6, color="#DDDDDD", zorder=0)
    ax1.legend(loc="upper right", fontsize=9, frameon=False)

    bins = np.arange(min(lengths) - 0.5, max(lengths) + 1.5)
    ax2.hist(lengths, bins=bins, color=SAFE, edgecolor="white", zorder=3)
    med = np.median(lengths)
    ax2.axvline(med, color="#222222", linestyle="--", linewidth=1)
    ax2.text(med + 2.2, ax2.get_ylim()[1] * 0.93, f"median {med:.0f}",
             fontsize=8.5, va="top")
    ax2.set_title("Prompt length (words)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("words per prompt", fontsize=9)
    ax2.set_ylabel("prompts", fontsize=9)
    style_axis(ax2)

    fig.suptitle("XSTest: 450 prompts, 250 safe / 200 unsafe, trigger-matched pairs",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    for ext in ("svg", "png"):
        fig.savefig(OUT / f"fig6-xstest-distribution-v2.{ext}", dpi=220,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_fig7():
    acc = {}
    for model, _ in MODELS:
        d = json.load(open(ROOT / "results" / f"{model}_baseline.json"))
        acc[model] = d["metrics"]["per_family_acc"]

    fig, ax = plt.subplots(figsize=(9.2, 3.2), facecolor="white")
    x = np.arange(len(FAMILY_ORDER))
    w = 0.26
    for i, (model, color) in enumerate(MODELS):
        vals = [acc[model][f] for f in FAMILY_ORDER]
        xs = x + (i - 1) * w
        ax.bar(xs, vals, w, color=color, label=model, zorder=3)
        for xi, v in zip(xs, vals):
            ax.text(xi, v + 0.015, f"{v:.2f}".lstrip("0"), ha="center",
                    fontsize=7, color=color, fontweight="bold")
    ax.set_xticks(x, [FAMILY_LABEL[f] for f in FAMILY_ORDER], fontsize=9)
    ax.set_ylim(0, 1.12)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylabel("accuracy", fontsize=10)
    style_axis(ax)
    ax.set_title("Baseline accuracy by XSTest family (greedy, 450 prompts)",
                 fontsize=12, fontweight="bold", pad=28)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.14), ncol=3,
              fontsize=9, frameon=False)
    fig.tight_layout()
    for ext in ("svg", "png"):
        fig.savefig(OUT / f"fig7-baseline-per-family-v2.{ext}", dpi=220,
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    build_fig6()
    build_fig7()
    print("wrote fig6/fig7 v2 to", OUT)
