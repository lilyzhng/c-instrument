"""XSTest dataset loading, family mapping, and pair matching.

450 prompts, 18 types of 25. Safe types pair with their contrast_* unsafe
counterpart; discrimination and privacy have two safe sub-types feeding one
contrast family. Pairs are matched within a family by the shared focus word.
"""

import csv
from collections import defaultdict

# type -> family (contrast_ prefix stripped; multi-subtype families merged)
_FAMILY = {
    "homonyms": "homonyms",
    "contrast_homonyms": "homonyms",
    "figurative_language": "figurative_language",
    "contrast_figurative_language": "figurative_language",
    "safe_targets": "safe_targets",
    "contrast_safe_targets": "safe_targets",
    "safe_contexts": "safe_contexts",
    "contrast_safe_contexts": "safe_contexts",
    "definitions": "definitions",
    "contrast_definitions": "definitions",
    "nons_group_real_discr": "discrimination",
    "real_group_nons_discr": "discrimination",
    "contrast_discr": "discrimination",
    "historical_events": "historical_events",
    "contrast_historical_events": "historical_events",
    "privacy_public": "privacy",
    "privacy_fictional": "privacy",
    "contrast_privacy": "privacy",
}


def load_xstest(path="data/xstest_prompts.csv"):
    """Return a list of dicts: id, prompt, type, label, focus, note, family."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) == 0:
        raise ValueError(f"no rows loaded from {path}")
    for r in rows:
        if r["type"] not in _FAMILY:
            raise ValueError(f"unknown XSTest type: {r['type']}")
        r["family"] = _FAMILY[r["type"]]
        r["label"] = r["label"].strip().lower()
        if r["label"] not in ("safe", "unsafe"):
            raise ValueError(f"bad label {r['label']!r} on id {r['id']}")
    return rows


def match_pairs(rows):
    """Match safe/unsafe rows that share (family, focus).

    Returns a list of (safe_row, unsafe_row) tuples. A focus word appearing in
    multiple rows on one side is zipped in order; leftovers are unmatched.
    """
    by_key = defaultdict(lambda: {"safe": [], "unsafe": []})
    for r in rows:
        focus = (r.get("focus") or "").strip().lower()
        if focus:
            by_key[(r["family"], focus)][r["label"]].append(r)
    pairs = []
    for _, sides in sorted(by_key.items()):
        for s, u in zip(sides["safe"], sides["unsafe"]):
            pairs.append((s, u))
    return pairs
