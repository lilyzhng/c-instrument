"""Unit tests for the generation grid (no disk, no network).

Seams under test (a bug in any silently distorts coverage): normalize_tier,
parse_constitution, allowed_axes, enumerate_cells, build_grid. Each test
traces to a grid property from the HaloGuard adaptation (deep-dive §4.4):
tier-aware pruning, mechanism × axes crossing, baseline unpaired coverage.
"""

import math

import pytest

from src.datagen.grid import (
    COVERAGE_AXES,
    TIER_AXIS_ALLOW,
    allowed_axes,
    build_grid,
    enumerate_cells,
    normalize_tier,
    parse_constitution,
)

VIOLENCE = """# Topic constitution: violence

- **Tier:** High
- **Figurative flag:** yes (rich idiomatic/technical benign uses)
- **XSTest map:** homonyms, figurative_language, safe_targets, safe_contexts
- **Mechanisms in play:** homonym, figurative, safe-target, safe-context

## Boundary
"""

SELF_HARM = """# Topic constitution: self_harm

- **Tier:** Sensitive (highest false-positive risk; benign-heavy generation)
- **Figurative flag:** yes ("this is killing me")
- **Mechanisms in play:** figurative, definition, safe-context
"""

FRAUD = """# Topic constitution: fraud

- **Tier:** Moderate
- **Figurative flag:** no
- **Mechanisms in play:** definition (knowledge-vs-how-to)
"""

GENERAL = """# Topic constitution: general

- **Tier:** — (baseline coverage)
- **Figurative flag:** n/a
- **Mechanisms in play:** none (unpaired coverage only)
"""


# ---- normalize_tier ----

@pytest.mark.parametrize("raw,expected", [
    ("High", "high"),
    ("Sensitive (highest false-positive risk)", "sensitive"),
    ("Moderate", "moderate"),
    ("— (baseline coverage)", "baseline"),
    ("- baseline", "baseline"),
])
def test_normalize_tier_reads_first_token(raw, expected):
    """GIVEN a Tier line with optional parenthetical WHEN normalized THEN the
    leading token (or dash placeholder) selects the tier."""
    assert normalize_tier(raw) == expected


def test_normalize_tier_unknown_defaults_to_moderate():
    """GIVEN an unrecognized tier string WHEN normalized THEN fall back to the
    safe middle tier, never the full grid."""
    assert normalize_tier("Spicy") == "moderate"
    assert normalize_tier(None) == "moderate"


# ---- parse_constitution ----

def test_parse_extracts_all_fields():
    """GIVEN a High topic body WHEN parsed THEN topic/tier/mechanisms/fig are
    all recovered."""
    c = parse_constitution(VIOLENCE)
    assert c["topic"] == "violence"
    assert c["tier"] == "high"
    assert c["mechanisms"] == ["homonym", "figurative", "safe-target", "safe-context"]
    assert c["figurative"] is True


def test_parse_strips_parenthetical_from_mechanism():
    """GIVEN a mechanism with a qualifier 'definition (knowledge-vs-how-to)'
    WHEN parsed THEN only the bare mechanism name is kept."""
    c = parse_constitution(FRAUD)
    assert c["mechanisms"] == ["definition"]
    assert c["figurative"] is False


def test_parse_none_mechanisms_is_empty_list():
    """GIVEN the baseline topic with 'none (unpaired ...)' WHEN parsed THEN
    mechanisms is [] so it generates unpaired coverage, not twins."""
    c = parse_constitution(GENERAL)
    assert c["mechanisms"] == []
    assert c["tier"] == "baseline"


# ---- allowed_axes / tier pruning ----

def test_high_tier_gets_full_grid():
    """GIVEN a High topic WHEN asking allowed axes THEN every value is open."""
    assert allowed_axes("high") == COVERAGE_AXES


def test_sensitive_tier_drops_amplifying_values():
    """GIVEN a Sensitive topic WHEN asking allowed axes THEN step_by_step,
    technical_detail, roleplay_frame, hypothetical are all pruned."""
    ax = allowed_axes("sensitive")
    assert ax["interaction_shape"] == ["direct_request"]
    assert "step_by_step" not in ax["information_depth"]
    assert "technical_detail" not in ax["information_depth"]
    assert "roleplay_frame" not in ax["interaction_shape"]


# ---- enumerate_cells ----

def test_high_tier_cell_count_is_full_cross_product():
    """GIVEN violence (4 mechanisms, full 3×3×3 grid) WHEN enumerated THEN
    cell count = 4 × 27 = 108, the exact cross product."""
    cells = enumerate_cells(parse_constitution(VIOLENCE))
    assert len(cells) == 4 * 3 * 3 * 3
    assert len(cells) == 108


def test_sensitive_cells_never_emit_pruned_values():
    """GIVEN self_harm (Sensitive) WHEN enumerated THEN no cell carries a
    pruned axis value, and count = 3 mech × 1 × 1 × 2 forms = 6."""
    cells = enumerate_cells(parse_constitution(SELF_HARM))
    assert len(cells) == 3 * 1 * 1 * 2
    for c in cells:
        assert c["interaction_shape"] == "direct_request"
        assert c["information_depth"] == "overview"
        assert c["content_form"] in ("prose", "qa")
        assert c["paired"] is True


def test_baseline_topic_yields_unpaired_cells():
    """GIVEN general (no mechanisms) WHEN enumerated THEN each cell has
    mechanism=None and paired=False (safe coverage, no intent-flip twin)."""
    cells = enumerate_cells(parse_constitution(GENERAL))
    assert all(c["mechanism"] is None and c["paired"] is False for c in cells)
    # baseline axes: 1 shape × 1 depth × 3 forms
    assert len(cells) == 1 * 1 * 3


def test_moderate_tier_is_between_sensitive_and_high():
    """GIVEN fraud (Moderate, 1 mechanism) WHEN enumerated THEN count =
    1 × 2 shapes × 2 depths × 3 forms = 12, strictly between the tiers."""
    cells = enumerate_cells(parse_constitution(FRAUD))
    assert len(cells) == 1 * 2 * 2 * 3


# ---- build_grid ----

def test_build_grid_aggregates_and_counts_per_topic():
    """GIVEN several parsed topics WHEN building the grid THEN total equals the
    sum of per-topic coverage and every cell is present."""
    cons = [parse_constitution(t) for t in (VIOLENCE, SELF_HARM, FRAUD, GENERAL)]
    grid = build_grid(cons)
    assert grid["total"] == sum(grid["coverage"].values())
    assert grid["coverage"]["violence"] == 108
    assert grid["coverage"]["self_harm"] == 6
    assert len(grid["cells"]) == grid["total"]
