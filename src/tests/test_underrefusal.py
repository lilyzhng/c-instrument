"""Unit tests for the under-refusal pilot (no network).

Seams under test: build_disguise_prompt, parse_prompts, score_pilot. Each
traces to the T8b probe: generate disguised-unsafe prompts, verify the
disguise did not make them benign, and report the yield of valid hard
negatives.
"""

import pytest

from src.datagen.underrefusal_pilot import (
    DISGUISES,
    build_disguise_prompt,
    parse_prompts,
    score_pilot,
)


# ---- build_disguise_prompt ----

def test_prompt_carries_topic_boundary_and_framing():
    """GIVEN a topic + boundary + framing WHEN building THEN all three appear
    and the count is requested."""
    p = build_disguise_prompt("violence", "seeks real harm to a person", "fiction", 3)
    assert "violence" in p and "seeks real harm" in p
    assert "fiction scene" in p and "3" in p


def test_prompt_demands_genuinely_unsafe_not_benign():
    """GIVEN any framing WHEN building THEN the prompt insists the disguise
    keeps the harm (unsafe), not turns it benign."""
    p = build_disguise_prompt("cyber", "real attack", "roleplay", 2)
    assert "genuinely unsafe" in p and "claim-shape" in p


# ---- parse_prompts ----

def test_parse_reads_prompt_objects():
    """GIVEN a JSON array of {prompt} WHEN parsed THEN the strings return."""
    txt = 'sure [{"prompt": "act as an unrestricted AI and ..."}, {"prompt": "for my novel ..."}]'
    assert parse_prompts(txt) == ["act as an unrestricted AI and ...", "for my novel ..."]


def test_parse_empty_on_refusal_or_unparseable():
    """GIVEN empty / non-JSON output WHEN parsed THEN []."""
    assert parse_prompts("") == []
    assert parse_prompts("I can't help with that") == []


def test_parse_drops_blank_prompts():
    """GIVEN entries with a missing/blank prompt WHEN parsed THEN they drop."""
    assert parse_prompts('[{"prompt": ""}, {"prompt": "real one"}]') == ["real one"]


# ---- score_pilot ----

def _row(framing, majority):
    return {"topic": "violence", "framing": framing, "prompt": "x", "majority": majority}


def test_yield_is_fraction_still_unsafe():
    """GIVEN 3 disguised rows the judge kept unsafe and 1 it called safe WHEN
    scored THEN yield = 3/4 (the safe one lost its harm in the disguise)."""
    rows = [_row("fiction", "unsafe"), _row("fiction", "unsafe"),
            _row("roleplay", "unsafe"), _row("roleplay", "safe")]
    s = score_pilot(rows)
    assert s["valid_unsafe"] == 3 and s["yield"] == 0.75


def test_undecided_counted_and_excluded_from_yield():
    """GIVEN an undecided (None) row WHEN scored THEN it is not a valid hard
    negative and is surfaced in undecided."""
    rows = [_row("fiction", "unsafe"), _row("fiction", None)]
    s = score_pilot(rows)
    assert s["valid_unsafe"] == 1 and s["undecided"] == 1 and s["yield"] == 0.5


def test_by_framing_breakdown():
    """GIVEN rows across framings WHEN scored THEN per-framing unsafe counts
    let us see which disguise best preserves harm."""
    rows = [_row("fiction", "unsafe"), _row("fiction", "safe"),
            _row("indirect", "unsafe")]
    s = score_pilot(rows)
    assert s["by_framing"]["fiction"] == {"n": 2, "unsafe": 1}
    assert s["by_framing"]["indirect"] == {"n": 1, "unsafe": 1}


def test_score_empty_is_safe():
    """GIVEN no rows WHEN scored THEN n=0, no crash."""
    assert score_pilot([]) == {"n": 0}
