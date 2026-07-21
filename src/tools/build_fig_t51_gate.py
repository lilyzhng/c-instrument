"""Fig 5 (Lens 3): the benefit gate rejects a topic that hurts the board.

T51 adds a new topic row (sexual_content) to the board. The topic learns itself
(gate G1 passes), but per-family accuracy on the existing board regresses:
global balanced accuracy 0.944 -> 0.916, worst on privacy and discrimination.
The gate (G2 no global regress, G3 no negative transfer) fails, so the topic is
rejected. This validates the expand move's guardrail.

Numbers from results/topic_impact_s125.json (topic-r1 s125 vs loop-r1 s150).
Style matches build_fig_p2_tradeoff.py.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "latex" / "figure"

BAD = "#C0553D"    # negative transfer (bad)
NEUTRAL = "#B9B9B9"  # flat

FAMILY_LABEL = {
    "privacy": "privacy",
    "discrimination": "discrimination",
    "safe_contexts": "safe contexts",
    "safe_targets": "safe targets",
    "figurative_language": "figurative",
    "definitions": "definitions",
    "historical_events": "historical",
    "homonyms": "homonyms",
}


def style_axis(ax):
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="x", linestyle="--", linewidth=0.6, color="#DDDDDD", zorder=0)
    ax.tick_params(labelsize=9)


def main():
    d = json.load(open(ROOT / "results" / "topic_impact_s125.json"))
    deltas = d["per_family_delta"]
    gb = d["global_balanced"]
    # sort most-negative first, so the worst hits sit at the top
    items = sorted(deltas.items(), key=lambda kv: kv[1])
    labels = [FAMILY_LABEL.get(k, k) for k, _ in items]
    vals = [v for _, v in items]
    colors = [BAD if v < 0 else NEUTRAL for v in vals]

    fig, ax = plt.subplots(figsize=(6.4, 3.6), facecolor="white")
    y = range(len(labels))
    ax.barh(list(y), vals, color=colors, zorder=3, height=0.66)
    for i, v in enumerate(vals):
        ax.text(v - 0.002 if v < 0 else 0.002, i,
                f"{v:+.3f}".replace("+0.000", "0"),
                va="center", ha="right" if v < 0 else "left",
                fontsize=8.5, color="#444")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()  # worst on top
    ax.axvline(0, color="#888", linewidth=0.9, zorder=2)
    style_axis(ax)
    ax.set_xlabel("per-family accuracy change after adding the new topic", fontsize=9)
    ax.set_xlim(-0.085, 0.02)
    ax.set_title("The benefit gate rejects a topic that hurts the board",
                 fontsize=11.5, fontweight="bold", pad=10)

    # verdict text moved to the figure caption; keep the plot clean

    fig.tight_layout()
    fig.subplots_adjust(right=0.94)
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"fig-t51-gate.{ext}", dpi=200, bbox_inches="tight",
                    facecolor="white")
    print("wrote", OUT / "fig-t51-gate.png")


if __name__ == "__main__":
    main()
