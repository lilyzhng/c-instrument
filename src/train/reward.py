"""Rule-based GRPO reward for the guard model (design §4.3.3).

Not a reward model: a rule. Each rollout must emit a think block then the
label verdict; it is scored

  label     +1.0  if the label in the ANSWER SLOT (after </think>) matches gold
  format    -0.2  if the output does not parse into that shape
  category  +0.2  (category-emitting model only) when the category is well-formed

Anti-hacking is the whole point: with 2-10 token verdicts, matching a label
anywhere in the text lets a rollout emit both labels and game the reward. So
the label is read ONLY from the answer slot after </think>; reasoning text
inside the think block can never earn the point. An unparseable rollout gets
the format penalty and cannot earn the label point.

Pure logic (parse_completion, compute_reward); unit-tested in
src/tests/test_train.py. No framework import, so verl wires this in as its
custom reward without pulling test deps.
"""

import json
import re

LABEL_BONUS = 1.0
FORMAT_PENALTY = -0.2
CATEGORY_BONUS = 0.2
LABELS = ("safe", "unsafe")

_VERDICT_JSON = re.compile(r'"user\s*safety"\s*:\s*"(safe|unsafe)"', re.IGNORECASE)
_VERDICT_TEXT = re.compile(r"user\s*safety\s*[:=]\s*(safe|unsafe)", re.IGNORECASE)
_ANY_LABEL = re.compile(r"\b(safe|unsafe)\b", re.IGNORECASE)


def _answer_slot(text):
    """The text after the LAST </think>, or None if the think shape is
    malformed (no </think>, or a </think> with no preceding <think>)."""
    if "</think>" not in text:
        return None
    if "<think>" not in text or text.index("<think>") > text.index("</think>"):
        return None
    return text.rsplit("</think>", 1)[1]


def parse_completion(text):
    """Return {label, category, well_formed}. label/category are read ONLY
    from the answer slot (after </think>); well_formed means the think shape
    is intact AND the slot yields a label."""
    text = text or ""
    slot = _answer_slot(text)
    if slot is None:
        return {"label": None, "category": None, "well_formed": False}

    label = None
    m = _VERDICT_JSON.search(slot) or _VERDICT_TEXT.search(slot)
    if m:
        label = m.group(1).lower()
    else:
        # bare label in the slot (still after </think>, so not hacked)
        m2 = _ANY_LABEL.search(slot)
        if m2:
            label = m2.group(1).lower()

    category = None
    cm = re.search(r'"safety\s*categories"\s*:\s*"([^"]*)"', slot, re.IGNORECASE)
    if cm:
        category = cm.group(1).strip() or None

    return {"label": label, "category": category, "well_formed": label in LABELS}


def compute_reward(completion, gold_label, use_category=False):
    """Scalar reward for one rollout vs its gold label (design §4.3.3).
    Format penalty and label bonus are independent: a well-formed rollout
    with the wrong label still avoids the penalty but earns no label point."""
    p = parse_completion(completion)
    reward = 0.0
    if not p["well_formed"]:
        reward += FORMAT_PENALTY
    if p["label"] is not None and p["label"] == gold_label:
        reward += LABEL_BONUS
    if use_category and p["category"]:
        reward += CATEGORY_BONUS
    return reward


def reward_fn(completions, gold_labels, use_category=False):
    """Batch wrapper (verl calls per-sample; this is for eval/tests)."""
    return [compute_reward(c, g, use_category)
            for c, g in zip(completions, gold_labels)]


def compute_score(data_source, solution_str, ground_truth, extra_info=None):
    """verl custom-reward entrypoint (config: custom_reward_function.path =
    this file, .name = compute_score). verl passes the rollout text as
    solution_str and the record's ground_truth (our gold label); we return the
    §4.3.3 scalar. `filter_groups` uses these scores to drop zero-variance
    groups each step (online probing, §4.3.2)."""
    return compute_reward(solution_str, ground_truth)
