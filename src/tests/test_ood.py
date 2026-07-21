"""Offline unit tests for the OOD loaders' pure normalizers (T14b).

Network loading (HF datasets) is not tested here; `python -m
src.harness.ood` is the online smoke check on the node.
"""

import pytest

from src.harness.metrics import summarize
from src.harness.ood import _norm_toxicchat, _norm_wildguard


def tc(user_input="hi", toxicity=0, jailbreaking=0, human_annotation=True):
    return {"user_input": user_input, "toxicity": toxicity,
            "jailbreaking": jailbreaking, "human_annotation": human_annotation}


def wg(prompt="hi", harm="unharmful", adversarial=False):
    return {"prompt": prompt, "prompt_harm_label": harm,
            "adversarial": adversarial}


class TestToxicChat:
    def test_label_mapping(self):
        rows = _norm_toxicchat([tc(), tc(toxicity=1)])
        assert [r["label"] for r in rows] == ["safe", "unsafe"]

    def test_jailbreak_flag_wins_family_and_is_unsafe(self):
        # jailbreaking=1 with toxicity=0 still counts unsafe (attempt on the
        # guard), and gets its own family so the slice is readable.
        (row,) = _norm_toxicchat([tc(toxicity=0, jailbreaking=1)])
        assert row["label"] == "unsafe"
        assert row["family"] == "tc_jailbreak"

    def test_families(self):
        rows = _norm_toxicchat([tc(), tc(toxicity=1), tc(jailbreaking=1)])
        assert [r["family"] for r in rows] == \
            ["tc_benign", "tc_toxic", "tc_jailbreak"]

    def test_drops_non_human_and_empty(self):
        rows = _norm_toxicchat(
            [tc(human_annotation=False), tc(user_input="  "), tc()])
        assert len(rows) == 1

    def test_raises_on_no_usable_rows(self):
        with pytest.raises(ValueError):
            _norm_toxicchat([tc(human_annotation=False)])

    def test_ids_unique(self):
        rows = _norm_toxicchat([tc(), tc(), tc()])
        assert len({r["id"] for r in rows}) == 3


class TestWildGuard:
    def test_label_mapping(self):
        rows = _norm_wildguard([wg(), wg(harm="harmful")])
        assert [r["label"] for r in rows] == ["safe", "unsafe"]

    def test_adversarial_family(self):
        rows = _norm_wildguard([wg(adversarial=True), wg()])
        assert [r["family"] for r in rows] == ["wg_adversarial", "wg_vanilla"]

    def test_drops_missing_harm_label(self):
        rows = _norm_wildguard([wg(harm=""), wg(harm="None"), wg()])
        assert len(rows) == 1

    def test_raises_on_no_usable_rows(self):
        with pytest.raises(ValueError):
            _norm_wildguard([wg(harm="")])


def test_summarize_accepts_ood_rows_without_pairs():
    # No focus words -> no pairs -> pair_consistency None; per-family and
    # per-label accs still computed. This is the contract evaluate.py relies
    # on to reuse the XSTest metrics unchanged.
    rows = _norm_toxicchat([tc(), tc(toxicity=1)])
    records = [{"row": r, "labels": [r["label"]]} for r in rows]
    m = summarize(records)
    assert m["n_prompts"] == 2
    assert m["safe_acc"] == 1.0 and m["unsafe_acc"] == 1.0
    assert m["pair_consistency"] is None and m["n_pairs"] == 0
    assert set(m["per_family_acc"]) == {"tc_benign", "tc_toxic"}
