"""Generation grid: turn each topic constitution into a set of cells to
generate, adapting HaloGuard's coverage axes (deep-dive note §4.4).

One boundary becomes many rows by crossing it against three stylistic axes
that are orthogonal to the harm topic, so breadth comes from the grid, not
from the generator's randomness:

    interaction_shape : direct_request · roleplay_frame · hypothetical
    information_depth  : overview · step_by_step · technical_detail
    content_form       : prose · list · qa

A grid cell is (topic × mechanism × interaction_shape × information_depth ×
content_form). The generator writes one intent-flip pair per cell; empty
cells are countable and regenerated, so coverage is a number.

Tier-aware pruning (HaloGuard: "a sensitive boundary exposes only the
mildest cells; a critical one gets the full grid"). Sensitive topics never
emit step_by_step / technical_detail / roleplay cells, so we do not
manufacture amplified unsafe prompts where the boundary is delicate.

Pure logic (parse_constitution, allowed_axes, enumerate_cells, build_grid)
is unit-tested in src/tests/test_grid.py; only load_constitutions touches disk.
"""

import os
import re
from pathlib import Path

# the three orthogonal diversity axes (full value sets)
COVERAGE_AXES = {
    "interaction_shape": ["direct_request", "roleplay_frame", "hypothetical"],
    "information_depth": ["overview", "step_by_step", "technical_detail"],
    "content_form": ["prose", "list", "qa"],
}

# tier-aware pruning: allowed axis values per normalized tier. Higher tier ->
# fuller grid; sensitive -> only the mildest shapes/depths. content_form is
# stylistic (not risk-amplifying), so it stays wide except we drop nothing.
TIER_AXIS_ALLOW = {
    "high": COVERAGE_AXES,  # full grid
    "moderate": {
        "interaction_shape": ["direct_request", "hypothetical"],
        "information_depth": ["overview", "step_by_step"],
        "content_form": ["prose", "list", "qa"],
    },
    "sensitive": {
        "interaction_shape": ["direct_request"],
        "information_depth": ["overview"],
        "content_form": ["prose", "qa"],
    },
    "baseline": {  # 'general' topic: plain safe coverage, no mechanism twins
        "interaction_shape": ["direct_request"],
        "information_depth": ["overview"],
        "content_form": ["prose", "list", "qa"],
    },
}

_SRC = Path(__file__).resolve().parent.parent
TOPICS_DIR = _SRC / "constitutions" / "topics"
_TOPIC_RE = re.compile(r"# Topic constitution:\s*(\S+)")
_TIER_RE = re.compile(r"\*\*Tier:\*\*\s*(.+)")
_MECH_RE = re.compile(r"\*\*Mechanisms in play:\*\*\s*(.+)")
_FIG_RE = re.compile(r"\*\*Figurative flag:\*\*\s*(\w+)")


# ---- pure logic (unit-tested, no disk) ----

def normalize_tier(raw):
    """Collapse a Tier line ('High', 'Sensitive (...)', '— (baseline...)') to
    one of high/moderate/sensitive/baseline. The first token decides it; the
    em/en-dash placeholder means the general baseline topic."""
    if raw is None:
        return "moderate"
    head = raw.strip().lower()
    if head.startswith(("-", "—", "–")):
        return "baseline"
    for tier in ("sensitive", "high", "moderate"):
        if head.startswith(tier):
            return tier
    return "moderate"  # unknown -> safe middle


def parse_constitution(text):
    """Extract {topic, tier, mechanisms, figurative} from a constitution
    file's body. mechanisms is a list; 'none ...' -> []."""
    topic_m = _TOPIC_RE.search(text)
    tier_m = _TIER_RE.search(text)
    mech_m = _MECH_RE.search(text)
    fig_m = _FIG_RE.search(text)

    mechs = []
    if mech_m:
        raw = mech_m.group(1)
        if not raw.strip().lower().startswith("none"):
            for part in raw.split(","):
                # strip parenthetical qualifiers, e.g. 'definition (knowledge-vs-how-to)'
                name = re.sub(r"\(.*?\)", "", part).strip()
                if name:
                    mechs.append(name)
    return {
        "topic": topic_m.group(1) if topic_m else None,
        "tier": normalize_tier(tier_m.group(1) if tier_m else None),
        "mechanisms": mechs,
        "figurative": bool(fig_m and fig_m.group(1).lower() == "yes"),
    }


def allowed_axes(tier):
    """Axis -> allowed values for a normalized tier (tier-aware pruning)."""
    return TIER_AXIS_ALLOW.get(tier, TIER_AXIS_ALLOW["moderate"])


def enumerate_cells(constitution):
    """Every grid cell for one parsed constitution: mechanism × the tier's
    allowed interaction_shape × information_depth × content_form. A topic with
    no mechanisms (the baseline) yields one mechanism-less pass per style
    combination (unpaired safe coverage, no intent-flip twin)."""
    tier = constitution["tier"]
    ax = allowed_axes(tier)
    mechs = constitution["mechanisms"] or [None]
    cells = []
    for mech in mechs:
        for shape in ax["interaction_shape"]:
            for depth in ax["information_depth"]:
                for form in ax["content_form"]:
                    cells.append({
                        "topic": constitution["topic"],
                        "tier": tier,
                        "mechanism": mech,
                        "interaction_shape": shape,
                        "information_depth": depth,
                        "content_form": form,
                        "paired": mech is not None,
                    })
    return cells


def build_grid(constitutions):
    """Flatten all topics into one cell list plus a per-topic coverage count.
    Returns {cells, coverage: {topic: n_cells}, total}."""
    cells = []
    coverage = {}
    for c in constitutions:
        topic_cells = enumerate_cells(c)
        coverage[c["topic"]] = len(topic_cells)
        cells += topic_cells
    return {"cells": cells, "coverage": coverage, "total": len(cells)}


# ---- disk IO (not in the pure path) ----

def load_constitutions(topics_dir=TOPICS_DIR):
    """Parse every topic constitution file in the directory (sorted)."""
    out = []
    for path in sorted(Path(topics_dir).glob("*.md")):
        out.append(parse_constitution(path.read_text()))
    return out


def main():
    import argparse
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topics-dir", default=TOPICS_DIR)
    p.add_argument("--out", default="results/generation_grid.json")
    args = p.parse_args()
    grid = build_grid(load_constitutions(args.topics_dir))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(grid, f, indent=2)
    print(f"{grid['total']} cells across {len(grid['coverage'])} topics")
    for topic, n in sorted(grid["coverage"].items(), key=lambda kv: -kv[1]):
        print(f"  {topic:20s} {n:4d} cells")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
