"""Unit tests for the T48 per-cell learning-impact analysis (s5.7 R1).

Covers the pure logic: C-LIM alignment score, trajectory classification,
cell-series assembly (min-n filter, intersection of cells), and the end-to-end
analyze() on synthetic row files — happy path, boundaries, empty/degenerate
inputs.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.getcwd())
from src.tools.cell_learning_impact import (  # noqa: E402
    ACTIONS, analyze, cell_series, classify, clim_score, step_files)


# ---------------------------------------------------------------- clim_score --

def test_clim_perfect_alignment_is_one():
    assert clim_score([0.5, 0.7, 0.9], [0.5, 0.7, 0.9]) == 1.0


def test_clim_misaligned_below_aligned():
    mean = [0.5, 0.7, 0.9]
    aligned = clim_score([0.55, 0.72, 0.88], mean)
    misaligned = clim_score([0.9, 0.5, 0.2], mean)  # anti-trend
    assert aligned > misaligned


def test_clim_degenerate_mean_all_ones_returns_none():
    # den = sum((1-1)^2) = 0 -> undefined, must be None not ZeroDivisionError
    assert clim_score([1.0, 1.0], [1.0, 1.0]) is None


def test_clim_can_go_negative_for_far_off_cells():
    # a cell pinned at 0 while the model masters everything else
    assert clim_score([0.0, 0.0, 0.0], [0.5, 0.8, 0.95]) < 0


# ------------------------------------------------------------------ classify --

@pytest.mark.parametrize("traj,rising,expected", [
    ([0.95, 0.95, 0.97], True, "saturated"),   # high start, stays high
    ([0.90, 0.92, 0.95], True, "saturated"),   # boundary: start exactly 0.9
    ([0.40, 0.60, 0.80], True, "frontier"),    # clear rise
    ([0.70, 0.75, 0.80], True, "frontier"),    # boundary: delta exactly +0.1
    ([0.80, 0.70, 0.65], True, "degrading"),   # falls while global rises
    ([0.50, 0.50, 0.50], True, "stuck"),       # flat and low
    ([0.70, 0.72, 0.68], True, "steady"),      # small wobble, ends >= 0.6
])
def test_classify_shapes(traj, rising, expected):
    assert classify(traj, rising) == expected


def test_classify_fall_without_global_rise_is_not_degrading():
    # degrading requires the CONTRAST with a rising global mean; if the whole
    # model is collapsing this cell is not a boundary conflict
    assert classify([0.8, 0.7, 0.65], False) != "degrading"


def test_classify_clim_floor_flags_flat_outlier():
    # privacy case: flat ~0.8 in a rising 0.97 field, clim << 0 -> stuck (v2)
    assert classify([0.77, 0.79, 0.80], True, clim=-10.0) == "stuck"


def test_classify_rise_beats_clim_floor():
    # early-jump cell with mildly negative clim must stay frontier
    assert classify([0.78, 0.97, 0.97], True, clim=-0.3) == "frontier"


def test_classify_saturated_needs_to_hold():
    # dips below 0.85 mid-run -> not saturated even if ends high
    assert classify([0.95, 0.80, 0.95], True) != "saturated"


def test_every_class_has_an_action():
    assert set(ACTIONS) == {"saturated", "frontier", "stuck", "degrading", "steady"}


# ----------------------------------------------------------- file-level logic --

def _write_rows(path, rows):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _mk_step(tmp, exp, step, cells):
    """cells: {cell_name: [pass_rates]}"""
    name = ("baseline_step_0_probe.json.rows.jsonl" if step == 0
            else f"{exp}_step_{step}_probe.json.rows.jsonl")
    rows = [{"cell": c, "label": "safe", "pass_rate": pr}
            for c, prs in cells.items() for pr in prs]
    _write_rows(os.path.join(tmp, name), rows)


def test_step_files_orders_and_includes_baseline(tmp_path):
    tmp = str(tmp_path)
    _mk_step(tmp, "expA", 0, {"c": [1.0]})
    _mk_step(tmp, "expA", 50, {"c": [1.0]})
    _mk_step(tmp, "expA", 25, {"c": [1.0]})
    files = step_files(tmp, "expA")
    assert [s for s, _ in files] == [0, 25, 50]


def test_cell_series_min_n_filter(tmp_path):
    tmp = str(tmp_path)
    for step in (0, 25, 50):
        _mk_step(tmp, "expA", step,
                 {"big": [1.0, 1.0, 0.5], "small": [1.0]})
    series = cell_series(step_files(tmp, "expA"), min_n=3)
    assert "big" in series and "small" not in series
    assert series["big"]["n"] == 3


def test_cell_series_drops_cells_missing_at_any_step(tmp_path):
    tmp = str(tmp_path)
    _mk_step(tmp, "expA", 0, {"a": [1.0], "b": [1.0]})
    _mk_step(tmp, "expA", 25, {"a": [1.0]})  # b missing here
    _mk_step(tmp, "expA", 50, {"a": [1.0], "b": [1.0]})
    series = cell_series(step_files(tmp, "expA"), min_n=1)
    assert set(series) == {"a"}


def test_analyze_end_to_end_classifies_and_counts(tmp_path):
    tmp = str(tmp_path)
    # 4 cells x 3 checkpoints, 4 rows each, engineered shapes
    shapes = {
        "sat":  ([1.0] * 4, [1.0] * 4, [1.0] * 4),
        "front": ([0.25] * 4, [0.5, 0.5, 0.75, 0.75], [0.75, 1.0, 1.0, 1.0]),
        "stuck": ([0.25] * 4, [0.25] * 4, [0.25] * 4),
        "degr": ([1.0] * 4, [0.75] * 4, [0.5, 0.5, 0.75, 0.75]),
    }
    for i, step in enumerate((0, 25, 50)):
        _mk_step(tmp, "expA", step, {c: list(v[i]) for c, v in shapes.items()})
    result = analyze(tmp, "expA", min_n=3)
    got = {c["cell"]: c["class"] for c in result["cells"]}
    assert got == {"sat": "saturated", "front": "frontier",
                   "stuck": "stuck", "degr": "degrading"}
    assert result["class_counts"] == {"saturated": 1, "frontier": 1,
                                      "stuck": 1, "degrading": 1}
    # vote_split/zero_adv computed on last checkpoint
    front = next(c for c in result["cells"] if c["cell"] == "front")
    assert front["vote_split"] == 0.25   # one row at 0.75
    assert front["zero_adv"] == 0.75     # three rows at 1.0


def test_analyze_requires_three_checkpoints(tmp_path):
    tmp = str(tmp_path)
    _mk_step(tmp, "expA", 0, {"c": [1.0] * 3})
    _mk_step(tmp, "expA", 25, {"c": [1.0] * 3})
    with pytest.raises(SystemExit):
        analyze(tmp, "expA", min_n=3)


def test_analyze_empty_dir_raises_cleanly(tmp_path):
    with pytest.raises(SystemExit):
        analyze(str(tmp_path), "expA", min_n=3)
