"""P2 figure: the scoreboard is blind to the safety tax.

Two panels, base (SFT) vs ship (grpo-7k-it6-s125), across three evals:
the XSTest scoreboard, and the independent WildGuardTest adversarial / vanilla
slices. Left panel = over-refusal (the visible win, drops everywhere). Right
panel = under-refusal: XSTest looks flat while the independent slices regress,
so a single-sided scoreboard hides the tax.

Numbers computed from results/ (no GPU):
  over-refusal   XSTest 0.224->0.128, WG-adv 0.108->0.062, WG-van 0.114->0.043
  under-refusal  XSTest 0.025->0.030, WG-adv 0.267->0.328, WG-van 0.128->0.155

Style matches build_paper_figs.py: white canvas, no top/right spines, dashed
y-grid, value labels on bars, shared top legend.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "latex" / "figure"

BASE_C = "#B9B9B9"   # SFT base, neutral grey
SHIP_C = "#2A6DB9"   # ship, blue (the reasoning-guard color used elsewhere)
GOOD = "#4C9A52"
BAD = "#C0553D"

EVALS = ["XSTest\n(scoreboard)", "WildGuard\nadversarial", "WildGuard\nvanilla"]

OVER = {"base": [0.224, 0.108, 0.114], "ship": [0.128, 0.062, 0.043]}
UNDER = {"base": [0.025, 0.267, 0.128], "ship": [0.030, 0.328, 0.155]}


def style_axis(ax):
    ax.set_facecolor("white")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, color="#DDDDDD", zorder=0)
    ax.tick_params(labelsize=9)


def bars(ax, data, title, arrow_good_dir):
    x = np.arange(len(EVALS))
    w = 0.36
    b1 = ax.bar(x - w / 2, data["base"], w, label="SFT base", color=BASE_C, zorder=3)
    b2 = ax.bar(x + w / 2, data["ship"], w, label="RL ship", color=SHIP_C, zorder=3)
    for bars_ in (b1, b2):
        for rect in bars_:
            h = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2, h + 0.006,
                    f"{h:.2f}".lstrip("0"), ha="center", va="bottom",
                    fontsize=8, color="#444")
    # delta arrow per eval: green if it moved the good way, red if bad
    for i in range(len(EVALS)):
        d = data["ship"][i] - data["base"][i]
        good = (d < 0) if arrow_good_dir == "down" else (d > 0)
        col = GOOD if good else BAD
        top = max(data["base"][i], data["ship"][i])
        ax.annotate(f"{d:+.2f}".replace("+0.", "+.").replace("-0.", "−."),
                    xy=(x[i], top + 0.045), ha="center", fontsize=8.5,
                    color=col, fontweight="bold")
    style_axis(ax)
    ax.set_xticks(x)
    ax.set_xticklabels(EVALS, fontsize=8.5)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=10)
    ax.set_ylim(0, max(max(data["base"]), max(data["ship"])) + 0.11)
    ax.set_ylabel("error rate", fontsize=9)


def main():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(9.4, 3.7), facecolor="white")
    # both panels are error rates: lower is always better, so good = "down"
    bars(axL, OVER, "Over-refusal: the visible win", "down")
    bars(axR, UNDER, "Under-refusal: the hidden tax", "down")

    # the punchline annotation on the right panel
    axR.annotate("scoreboard\nlooks flat", xy=(0, 0.030), xytext=(0.02, 0.135),
                 fontsize=8, color="#666", ha="center",
                 arrowprops=dict(arrowstyle="->", color="#999", lw=0.9))
    axR.annotate("independent\nsets regress", xy=(1.16, 0.33), xytext=(1.9, 0.35),
                 fontsize=8, color=BAD, ha="center", va="center",
                 arrowprops=dict(arrowstyle="->", color=BAD, lw=0.9))

    handles, labels = axL.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False,
               fontsize=9.5, bbox_to_anchor=(0.5, 1.06))
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.subplots_adjust(right=0.9)  # generous right padding, croppable
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"fig-p2-tradeoff.{ext}", dpi=200, bbox_inches="tight",
                    facecolor="white")
    print("wrote", OUT / "fig-p2-tradeoff.png")


if __name__ == "__main__":
    main()
