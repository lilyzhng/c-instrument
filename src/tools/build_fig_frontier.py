"""Concept figure for the discussion: the over/under-refusal drift tax.

Pure schematic, no measured points. One message only: RL moved a safety guard
ALONG the tradeoff curve (over-refusal down, under-refusal up = the "drift
tax"), it did NOT improve both at once. The open goal is to push the whole
curve outward so both costs go down together.

Minimal by design: one curve, two dots (base, ship), one solid red arrow
between them labeled "drift tax", one faded dashed arrow pointing further
down-left labeled "goal (open)". Four short labels total, nothing else.

Style matches build_fig_p2_tradeoff.py: white canvas, no top/right spines.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "latex" / "figure"

BASE_C = "#B9B9B9"
SHIP_C = "#2A6DB9"
BAD = "#C0553D"
GOOD = "#4C9A52"


def frontier(x, k=1.0):
    # convex tradeoff curve: lower-left is better
    return k / (x + 0.15) * 0.12


def main():
    fig, ax = plt.subplots(figsize=(5.4, 4.2), facecolor="white")

    xs = np.linspace(0.10, 0.62, 200)
    ax.plot(xs, frontier(xs), color="#999", lw=2, zorder=2)

    # two points on the current frontier: base and ship (a move ALONG it)
    bx, by = 0.40, frontier(0.40)   # base: high over-refusal, low under-refusal
    sx, sy = 0.19, frontier(0.19)   # ship: low over-refusal, high under-refusal
    ax.scatter([bx], [by], s=90, color=BASE_C, zorder=5, edgecolor="white", linewidth=1.3)
    ax.scatter([sx], [sy], s=90, color=SHIP_C, zorder=5, edgecolor="white", linewidth=1.3)

    ax.text(bx + 0.022, by + 0.006, "base", color="#666", fontsize=10, ha="left", va="center")
    ax.text(sx, sy + 0.028, "ship", color=SHIP_C, fontsize=10, ha="center", va="bottom", fontweight="bold")

    # drift-tax arrow: base -> ship, points up and to the left
    ax.annotate("", xy=(sx, sy), xytext=(bx, by),
                arrowprops=dict(arrowstyle="-|>", color=BAD, lw=2.2, mutation_scale=18),
                zorder=6)
    mx, my = (bx + sx) / 2, (by + sy) / 2
    ax.text(mx + 0.028, my + 0.006, "drift tax", color=BAD, fontsize=10.5,
            ha="left", va="center", fontweight="bold", rotation=0)

    # goal arrow: faded dashed, pointing further down-left from ship (open, not yet achieved)
    gx, gy = sx - 0.06, sy - 0.09
    ax.annotate("", xy=(gx, gy), xytext=(sx, sy),
                arrowprops=dict(arrowstyle="-|>", color=GOOD, lw=1.8, ls="dashed",
                                 alpha=0.85, mutation_scale=15),
                zorder=4)
    ax.text(gx + 0.012, gy - 0.008, "goal (open)", color=GOOD, fontsize=9.5,
            ha="left", va="top")

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_xlim(0.05, 0.62)
    ax.set_ylim(0.0, 0.46)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("over-refusal  (helpfulness cost)", fontsize=10)
    ax.set_ylabel("under-refusal  (harmlessness cost)", fontsize=10)
    ax.set_title("RL moved the guard along the tradeoff, not past it",
                 fontsize=11.5, fontweight="bold", pad=10)

    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"fig-frontier.{ext}", dpi=200, bbox_inches="tight",
                    facecolor="white")
    print("wrote", OUT / "fig-frontier.png")


if __name__ == "__main__":
    main()
