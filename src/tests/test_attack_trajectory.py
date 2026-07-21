"""Unit tests for T49 attack-channel ASR trajectory analysis (s5.7)."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.getcwd())
from src.tools.attack_trajectory import (  # noqa: E402
    ACTIONS, analyze, cell_series, classify, step_files)


@pytest.mark.parametrize("asr,field,expected", [
    ([0.05, 0.15, 0.30], True, "loophole"),   # ASR climbs = guard degrades
    ([0.10, 0.12, 0.16], True, "loophole"),    # boundary: delta exactly +0.05...
    ([0.30, 0.25, 0.20], True, "fragile"),     # high throughout, never controlled
    ([0.40, 0.20, 0.02], True, "hardened"),    # driven down to ~0
    ([0.0, 0.0, 0.0], False, "clean"),         # attack gets no traction
    ([0.10, 0.08, 0.10], False, "steady"),     # wobble, not rising, not fragile
])
def test_classify_shapes(asr, field, expected):
    assert classify(asr, 0.05, field) == expected


def test_loophole_needs_field_context_or_rise():
    # a rise but the whole field is falling (field_rising False) still counts
    # as loophole only via the >= rise branch; here delta = +0.2 so it fires
    assert classify([0.1, 0.2, 0.3], 0.05, False) == "loophole"


def test_every_class_has_action():
    assert set(ACTIONS) == {"loophole", "fragile", "hardened", "clean", "steady"}


def _mk(tmp, exp, step, cells):
    name = ("baseline_step_0_attack.json.rows.jsonl" if step == 0
            else f"{exp}_step_{step}_attack.json.rows.jsonl")
    with open(os.path.join(tmp, name), "w") as f:
        for c, hits in cells.items():
            for h in hits:
                f.write(json.dumps({"cell": c, "label": "attack",
                                    "asr_hit": h}) + "\n")


def test_analyze_ranks_worst_loophole_first(tmp_path):
    tmp = str(tmp_path)
    shapes = {
        "loop_big": ([0.0] * 4, [0.2] * 4, [0.4] * 4),   # +0.4
        "loop_sm":  ([0.0] * 4, [0.05] * 4, [0.1] * 4),  # +0.1
        "hard":     ([0.4] * 4, [0.1] * 4, [0.0] * 4),   # hardened
    }
    for i, step in enumerate((0, 25, 50)):
        _mk(tmp, "expA", step, {c: list(v[i]) for c, v in shapes.items()})
    r = analyze(tmp, "expA", min_n=3, rise=0.05)
    loopholes = [c["cell"] for c in r["cells"] if c["class"] == "loophole"]
    assert loopholes[0] == "loop_big"        # ranked worst-first
    assert set(loopholes) == {"loop_big", "loop_sm"}
    assert r["class_counts"]["hardened"] == 1


def test_analyze_requires_three_checkpoints(tmp_path):
    tmp = str(tmp_path)
    _mk(tmp, "expA", 0, {"c": [0.1] * 3})
    _mk(tmp, "expA", 25, {"c": [0.1] * 3})
    with pytest.raises(SystemExit):
        analyze(tmp, "expA", min_n=3, rise=0.05)


def test_cell_series_min_n(tmp_path):
    tmp = str(tmp_path)
    for step in (0, 25, 50):
        _mk(tmp, "expA", step, {"big": [0.1, 0.1, 0.1], "small": [0.1]})
    series = cell_series(step_files(tmp, "expA"), min_n=3)
    assert "big" in series and "small" not in series
