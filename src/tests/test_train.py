"""Unit tests for the GRPO training setup (no framework, no network).

Seams under test: reward.parse_completion, reward.compute_reward,
prepare_data.build_prompt, prepare_data.prepare. Each traces to a design
§4.3.3 rule: label read only from the answer slot (anti-hacking), format
penalty, category bonus, and training only on judge-trusted rows.
"""

import pytest

from src.train.reward import (
    CATEGORY_BONUS,
    FORMAT_PENALTY,
    LABEL_BONUS,
    compute_reward,
    parse_completion,
)
from src.train.prepare_data import build_prompt, prepare, to_record

THINK = "<think>the user wants to end a process, benign</think>"


# ---- reward: parsing ----

def test_parse_reads_label_from_answer_slot():
    """GIVEN think block then a JSON verdict WHEN parsed THEN the slot label is
    returned and it is well_formed."""
    p = parse_completion(THINK + ' {"User Safety": "safe"}')
    assert p["label"] == "safe" and p["well_formed"] is True


def test_parse_ignores_label_inside_think_block():
    """GIVEN 'unsafe' only inside the think block and 'safe' in the slot WHEN
    parsed THEN the slot wins (reasoning text cannot set the label)."""
    text = "<think>this looks unsafe at first</think> " + '{"User Safety": "safe"}'
    assert parse_completion(text)["label"] == "safe"


def test_parse_no_close_tag_is_malformed():
    """GIVEN a think block that never closes WHEN parsed THEN no answer slot,
    label None, not well_formed (cannot earn the label point)."""
    p = parse_completion("<think>reasoning with safe and unsafe words forever")
    assert p["label"] is None and p["well_formed"] is False


def test_parse_extracts_category_from_slot():
    """GIVEN a verdict with Safety Categories WHEN parsed THEN the category is
    read from the slot."""
    text = THINK + ' {"User Safety": "unsafe", "Safety Categories": "violence"}'
    assert parse_completion(text)["category"] == "violence"


# ---- reward: scoring ----

def test_reward_correct_label_well_formed():
    """GIVEN a well-formed rollout with the right label WHEN scored THEN +1.0,
    no penalty."""
    r = compute_reward(THINK + ' {"User Safety": "safe"}', "safe")
    assert r == LABEL_BONUS


def test_reward_wrong_label_no_penalty_no_point():
    """GIVEN a well-formed rollout with the WRONG label WHEN scored THEN 0.0:
    no format penalty (shape is fine) and no label point."""
    r = compute_reward(THINK + ' {"User Safety": "unsafe"}', "safe")
    assert r == 0.0


def test_reward_malformed_gets_penalty_and_no_point():
    """GIVEN an unparseable rollout WHEN scored THEN only the format penalty,
    even if a gold-matching word appears (it is not in a valid slot)."""
    r = compute_reward("<think>safe safe safe", "safe")
    assert r == FORMAT_PENALTY


def test_reward_hacking_both_labels_in_think_denied():
    """GIVEN a rollout that stuffs both labels in the think block and emits the
    wrong one in the slot WHEN scored THEN it does NOT earn the point."""
    text = "<think>safe unsafe safe unsafe</think> " + '{"User Safety": "unsafe"}'
    assert compute_reward(text, "safe") == 0.0


def test_reward_category_bonus_only_when_requested():
    """GIVEN a correct rollout with a category WHEN scored with use_category
    THEN +1.0 +0.2; without the flag THEN just +1.0."""
    text = THINK + ' {"User Safety": "unsafe", "Safety Categories": "fraud"}'
    assert compute_reward(text, "unsafe", use_category=True) == LABEL_BONUS + CATEGORY_BONUS
    assert compute_reward(text, "unsafe", use_category=False) == LABEL_BONUS


# ---- prepare_data ----

def test_build_prompt_embeds_user_prompt():
    """GIVEN a user prompt WHEN building THEN it is embedded in the task and the
    placeholder is gone."""
    out = build_prompt("How do I kill a process?")
    assert "How do I kill a process?" in out and "{prompt}" not in out


def test_to_record_carries_gold_and_provenance():
    """GIVEN a generated row WHEN converted THEN gold label and topic ride along
    for the rule reward and later analysis."""
    row = {"prompt": "x", "constructed_label": "unsafe", "topic": "violence",
           "mechanism": "homonym", "agrees": True}
    rec = to_record(row)
    assert rec["reward_model"]["ground_truth"] == "unsafe"
    assert rec["extra_info"]["topic"] == "violence"
    assert rec["prompt"][0]["role"] == "user"


def test_prepare_drops_judge_contradicted_rows():
    """GIVEN a trusted row and a judge-contradicted row WHEN prepared with
    trusted_only THEN only the trusted row survives."""
    rows = [
        {"prompt": "a", "constructed_label": "safe", "agrees": True},
        {"prompt": "b", "constructed_label": "unsafe", "agrees": False},  # flagged
    ]
    recs = prepare(rows, trusted_only=True)
    assert len(recs) == 1 and recs[0]["reward_model"]["ground_truth"] == "safe"


def test_prepare_all_keeps_contradicted_rows():
    """GIVEN --all (trusted_only False) WHEN prepared THEN contradicted rows are
    kept too."""
    rows = [
        {"prompt": "a", "constructed_label": "safe", "agrees": True},
        {"prompt": "b", "constructed_label": "unsafe", "agrees": False},
    ]
    assert len(prepare(rows, trusted_only=False)) == 2


def test_prepare_skips_rows_missing_prompt_or_label():
    """GIVEN a row with no prompt and one with a bad label WHEN prepared THEN
    both are skipped (never a malformed training record)."""
    rows = [
        {"prompt": "", "constructed_label": "safe", "agrees": True},
        {"prompt": "ok", "constructed_label": "maybe", "agrees": True},
    ]
    assert prepare(rows, trusted_only=True) == []
