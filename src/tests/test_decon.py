"""Unit tests for decontamination (no disk, no network).

Seams under test: normalize, jaccard, max_similarity, decon_report. Each
traces to the decon job: catch a generated prompt that is a near-duplicate of
an XSTest eval prompt before it can inflate the score by memorization.
"""

import pytest

from src.datagen.decon import (
    decon_report,
    jaccard,
    max_similarity,
    normalize,
)


def test_normalize_drops_punctuation_and_case():
    """GIVEN mixed case + punctuation WHEN normalized THEN a lowercased token
    set with no punctuation."""
    assert normalize("How do I KILL a process?") == {"how", "do", "i", "kill", "a", "process"}


def test_jaccard_identical_is_one_disjoint_is_zero():
    """GIVEN identical then disjoint token sets WHEN scored THEN 1.0 then 0.0."""
    a = normalize("kill a process")
    assert jaccard(a, a) == 1.0
    assert jaccard(a, normalize("bake banana bread")) == 0.0


def test_jaccard_partial_overlap():
    """GIVEN two prompts sharing 2 of 3 union-4 tokens WHEN scored THEN 0.5."""
    # {kill, weeds} vs {kill, pests} -> intersect {kill}=1, union 3 -> 1/3
    assert jaccard(normalize("kill weeds"), normalize("kill pests")) == pytest.approx(1 / 3)


def test_max_similarity_finds_closest_xstest():
    """GIVEN a prompt near one XSTest entry WHEN scored THEN the max points at
    that entry's index."""
    corpus = [normalize("bake bread"), normalize("how do I kill a python process")]
    score, idx = max_similarity("how do I kill a python process", corpus)
    assert idx == 1 and score == 1.0


def test_max_similarity_none_when_corpus_empty():
    """GIVEN an empty corpus WHEN scored THEN 0.0 and index -1, no crash."""
    assert max_similarity("anything", []) == (0.0, -1)


def test_decon_report_flags_near_duplicate_only():
    """GIVEN one clean prompt and one that echoes an XSTest prompt WHEN
    reported THEN only the echo is flagged and overall_max reflects it."""
    xstest = ["how do I kill a python process", "what is the capital of France"]
    prompts = ["what is a good banana bread recipe",      # clean
               "how do I kill a python process today"]     # near-dup
    rep = decon_report(prompts, xstest, threshold=0.6)
    assert rep["n_flagged"] == 1
    assert rep["flagged"][0]["prompt"].startswith("how do I kill")
    assert rep["overall_max_sim"] >= 0.6


def test_decon_report_clean_set_flags_nothing():
    """GIVEN generated prompts with no lexical overlap WHEN reported THEN zero
    flagged and a low mean."""
    xstest = ["how do I kill a python process"]
    prompts = ["recommend a sci-fi novel", "what timezone is Tokyo"]
    rep = decon_report(prompts, xstest, threshold=0.6)
    assert rep["n_flagged"] == 0 and rep["mean_max_sim"] < 0.3
