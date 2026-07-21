"""Unit tests for the grid-driven generation pipeline (no network).

Seams under test: extract_section, build_cell_prompt, parse_pairs,
assemble_rows, pilot_metrics. Each traces to a pipeline behavior: prompt is
grounded in the constitution + cell axes, parsing survives refusals, rows are
labeled by construction, pilot numbers split by label. chat() is imported
lazily inside run(), so these need no API key.
"""

import pytest

from src.datagen.generate import (
    assemble_rows,
    build_cell_prompt,
    extract_section,
    parse_pairs,
    pilot_metrics,
)

BODY = """# Topic constitution: violence

- **Tier:** High
- **Mechanisms in play:** homonym

## Boundary

Safe when non-literal; unsafe when it seeks real harm to a person.

## Benign confusions

kill a process, killing time
"""


def _cell(paired=True, **over):
    c = {"topic": "violence", "tier": "high", "mechanism": "homonym",
         "interaction_shape": "direct_request", "information_depth": "overview",
         "content_form": "prose", "paired": paired}
    c.update(over)
    return c


# ---- extract_section ----

def test_extract_section_returns_body_under_heading():
    """GIVEN a constitution WHEN extracting 'Boundary' THEN its text is
    returned and stops before the next section."""
    sec = extract_section(BODY, "Boundary")
    assert "seeks real harm" in sec
    assert "Benign confusions" not in sec  # stopped at next '##'


def test_extract_section_missing_heading_is_empty():
    """GIVEN no such heading WHEN extracting THEN empty string, not a crash."""
    assert extract_section(BODY, "Nonexistent") == ""


# ---- build_cell_prompt ----

def test_paired_prompt_carries_mechanism_axes_and_boundary():
    """GIVEN a paired cell WHEN building the prompt THEN it names the
    mechanism, the intent-flip instruction, the style axes, and the
    constitution boundary."""
    p = build_cell_prompt(BODY, _cell(), n_pairs=3)
    assert "homonym" in p
    assert "intent-flip" in p and "3" in p
    assert "direct request" in p and "overview" in p and "natural sentence" in p
    assert "seeks real harm" in p  # boundary grounding


def test_unpaired_prompt_asks_for_safe_only():
    """GIVEN a baseline cell (paired=False) WHEN building the prompt THEN it
    asks for safe prompts with no unsafe twin."""
    p = build_cell_prompt(BODY, _cell(paired=False, mechanism=None), n_pairs=4)
    assert "no unsafe twin" in p
    assert "intent-flip" not in p


# ---- parse_pairs ----

def test_parse_pairs_reads_valid_array():
    """GIVEN a JSON array of pairs WHEN parsed THEN the dicts are returned."""
    txt = 'prose [{"safe": "kill a process", "unsafe": "kill a person"}] tail'
    got = parse_pairs(txt)
    assert got == [{"safe": "kill a process", "unsafe": "kill a person"}]


def test_parse_pairs_empty_on_refusal():
    """GIVEN an empty / refused generation WHEN parsed THEN []."""
    assert parse_pairs("") == []
    assert parse_pairs("I can't help with that.") == []


def test_parse_pairs_drops_entries_without_safe():
    """GIVEN an array with a malformed entry WHEN parsed THEN only entries
    with a 'safe' field survive."""
    txt = '[{"unsafe": "x"}, {"safe": "ok", "unsafe": "bad"}]'
    assert parse_pairs(txt) == [{"safe": "ok", "unsafe": "bad"}]


# ---- assemble_rows ----

def test_paired_pair_becomes_safe_and_unsafe_rows():
    """GIVEN a paired cell and one pair WHEN assembled THEN two rows with the
    correct constructed labels."""
    rows = assemble_rows(_cell(), [{"safe": "kill a process", "unsafe": "kill a person"}])
    assert [r["constructed_label"] for r in rows] == ["safe", "unsafe"]
    assert rows[0]["prompt"] == "kill a process"
    assert rows[1]["topic"] == "violence" and rows[1]["mechanism"] == "homonym"


def test_unpaired_cell_yields_only_safe_rows():
    """GIVEN a baseline cell WHEN assembled THEN only safe rows, even if an
    unsafe field slips in."""
    rows = assemble_rows(_cell(paired=False), [{"safe": "banana bread recipe", "unsafe": "x"}])
    assert len(rows) == 1 and rows[0]["constructed_label"] == "safe"


def test_degenerate_pair_is_dropped():
    """GIVEN a pair whose sides are identical WHEN assembled THEN it is
    dropped (not a real contrast)."""
    rows = assemble_rows(_cell(), [{"safe": "same text", "unsafe": "same text"}])
    assert rows == []


def test_missing_safe_side_skips_pair():
    """GIVEN a pair with no safe side WHEN assembled THEN it is skipped."""
    rows = assemble_rows(_cell(), [{"safe": "", "unsafe": "bad"}])
    assert rows == []


# ---- pilot_metrics ----

def _row(label, prompt, majority):
    return {"constructed_label": label, "prompt": prompt, "majority": majority}


def test_pilot_metrics_splits_agreement_by_label():
    """GIVEN labeled rows WHEN scored THEN safe/unsafe agreement are reported
    separately (safe is the mission axis)."""
    rows = [_row("safe", "a", "safe"), _row("safe", "b", "unsafe"),
            _row("unsafe", "c", "unsafe"), _row("unsafe", "d", "unsafe")]
    m = pilot_metrics(rows)
    assert m["safe_agreement"] == 0.5 and m["unsafe_agreement"] == 1.0
    assert m["label_agreement"] == 0.75


def test_pilot_metrics_counts_undecided_and_diversity():
    """GIVEN a duplicate prompt and an undecided (None majority) row WHEN
    scored THEN diversity < 1 and undecided is counted."""
    rows = [_row("safe", "dup", "safe"), _row("safe", "dup", None)]
    m = pilot_metrics(rows)
    assert m["diversity"] == 0.5 and m["undecided"] == 1


def test_pilot_metrics_empty_is_safe():
    """GIVEN no rows WHEN scored THEN n=0 and no crash."""
    assert pilot_metrics([]) == {"n": 0}
