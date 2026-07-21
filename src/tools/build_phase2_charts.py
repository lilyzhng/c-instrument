"""Phase 2 charts from results/ JSONs: per-family baselines + probe routing.

Usage: python src/tools/build_phase2_charts.py
Writes SVGs to deliverables/figures/. House plot style: grey page #F4F4F4,
white panels, forest green primary, clay accent, mono numbers.
"""

import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GREY, PANEL = "#F4F4F4", "#FFFFFF"
INK, MUTE = "#1c1c1a", "#8a887f"
FOREST, CLAY, OAT = "#245F2B", "#C4633F", "#D1CFC5"

RESULTS = pathlib.Path("results")
OUT = pathlib.Path("deliverables/figures")
MODELS = ["wildguard", "nemotron-reasoning", "nemotron-safety"]
MODEL_COLORS = {"wildguard": OAT, "nemotron-reasoning": FOREST,
                "nemotron-safety": "#7a9a6d"}


def _load(name, kind):
    return json.load(open(RESULTS / f"{name}_{kind}.json"))


def _style_axes(ax):
    ax.set_facecolor(PANEL)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(OAT)
    ax.tick_params(colors=INK, labelsize=9)
    ax.yaxis.grid(True, color=GREY, linewidth=1)
    ax.set_axisbelow(True)


def per_family_chart():
    data = {m: _load(m, "baseline")["metrics"]["per_family_acc"] for m in MODELS}
    families = sorted(data[MODELS[0]])
    fig, ax = plt.subplots(figsize=(11, 4.2))
    fig.patch.set_facecolor(GREY)
    _style_axes(ax)
    width = 0.26
    for i, m in enumerate(MODELS):
        xs = [x + (i - 1) * width for x in range(len(families))]
        ax.bar(xs, [data[m][f] for f in families], width,
               label=m, color=MODEL_COLORS[m])
    ax.set_xticks(range(len(families)))
    ax.set_xticklabels([f.replace("_", "\n") for f in families], fontsize=8.5)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("accuracy", fontsize=9)
    ax.axhline(1.0, color=OAT, linewidth=0.8)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("Baseline accuracy by XSTest family (greedy, 450 prompts)",
                 loc="left", fontsize=11, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "phase2-baseline-per-family.svg",
                facecolor=GREY, bbox_inches="tight")


def routing_chart():
    order = ["consistent_correct", "inconsistent", "consistent_wrong", "unparseable"]
    labels = ["already solved", "inconsistent (RL-addressable)",
              "always wrong (knowledge gap)", "unparseable"]
    colors = [OAT, FOREST, CLAY, MUTE]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    fig.patch.set_facecolor(GREY)
    _style_axes(ax)
    ax.xaxis.grid(True, color=GREY, linewidth=1)
    ax.yaxis.grid(False)
    for yi, m in enumerate(reversed(MODELS)):
        routing = _load(m, "probe")["metrics"]["routing"]
        left = 0
        for key, color in zip(order, colors):
            v = routing.get(key, 0)
            if v:
                ax.barh(yi, v, left=left, color=color, height=0.55)
                if v >= 18:
                    ax.text(left + v / 2, yi, str(v), ha="center", va="center",
                            fontsize=8.5, color=PANEL if color in (FOREST, CLAY, MUTE) else INK,
                            family="monospace")
            left += v
    ax.set_yticks(range(len(MODELS)))
    ax.set_yticklabels(list(reversed(MODELS)), fontsize=9)
    ax.set_xlim(0, 450)
    ax.set_xlabel("prompts (of 450)", fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    ax.legend(handles, labels, frameon=False, fontsize=8.5,
              ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.28))
    ax.set_title("Probe routing (n=8, temperature 0.7): where each model's prompts land",
                 loc="left", fontsize=11, color=INK, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "phase2-probe-routing.svg",
                facecolor=GREY, bbox_inches="tight")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    per_family_chart()
    routing_chart()
    print(f"wrote {OUT}/phase2-baseline-per-family.svg and phase2-probe-routing.svg")
