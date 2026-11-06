"""Invented observations only; no cohort readers, checkpoint or source paths."""

import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from dmv_mat_cvd.thresholds import (
    RANKING,
    THRESHOLDS,
    VALIDATION_STATUS,
    descriptive_sweep,
    operating_point,
    reconcile_ranking,
    summarize_draws,
)


def invented():
    rng = np.random.default_rng(44)
    y = np.r_[np.ones(7), np.zeros(33)]
    scores = rng.uniform(0, 0.7, (10, len(y)))
    rows = [operating_point(y, p) for p in scores]
    refs = {k: {"per_draw": [r[k] for r in rows], "mean": np.mean([r[k] for r in rows])} for k in RANKING}
    return y, scores, refs


def test_counts_orientation_and_formulas():
    row = operating_point([0, 0, 0, 1, 1], [0.1, 0.2, 0.6, 0.5, 0.3])
    assert [row[k] for k in ("TN", "FP", "FN", "TP")] == [2, 1, 1, 1]
    assert row["accuracy"] == 3 / 5
    assert row["precision"] == row["recall"] == row["f1"] == 1 / 2
    assert row["specificity"] == 2 / 3
    assert row["balanced_accuracy"] == (1 / 2 + 2 / 3) / 2


def test_no_positive_predictions_is_not_successful_detection():
    row = operating_point([0, 0, 1], [0.01, 0.02, 0.03])
    assert row["precision"] is None
    assert row["recall"] == row["f1"] == 0
    assert row["specificity"] == 1
    assert row["accuracy"] == 2 / 3


def test_float32_inputs_follow_original_float64_metric_convention():
    y = np.array([0, 1, 0, 1], dtype=np.float32)
    p = np.array([0.13, 0.27, 0.08, 0.31], dtype=np.float32)
    assert operating_point(y, p)["brier"] == float(np.mean((p.astype(float) - y.astype(int)) ** 2))


@pytest.mark.parametrize("labels", [[0, 0], [1, 1]])
def test_single_class_is_explicitly_undefined(labels):
    row = operating_point(labels, [0.1, 0.1])
    assert row["auroc"] is None
    if labels[0] == 0:
        assert row["ap"] is row["recall"] is row["f1"] is None
    else:
        assert row["specificity"] is None
    assert row["balanced_accuracy"] is None


def test_threshold_equality_and_monotonic_counts():
    assert operating_point([1], [0.05], 0.05)["TP"] == 1
    y, scores, refs = invented()
    result = descriptive_sweep(y, scores, reference=refs)
    totals = [r["per_draw"][0]["TP"] + r["per_draw"][0]["FP"] for r in result["conditions"]]
    assert totals == sorted(totals, reverse=True)
    assert tuple(c["threshold"] for c in result["conditions"]) == THRESHOLDS


def test_all_ranking_metrics_immutable_and_inputs_unchanged():
    y, scores, refs = invented()
    before = scores.copy()
    report = descriptive_sweep(y, scores, reference=refs)
    assert np.array_equal(before, scores)
    for condition in report["conditions"]:
        for i, row in enumerate(condition["per_draw"]):
            assert all(row[k] == refs[k]["per_draw"][i] for k in RANKING)


def test_shared_draws_are_not_pooled_or_ensembled():
    y, scores, refs = invented()
    result = descriptive_sweep(y, scores, reference=refs)
    assert result["distinct_participants"] == 40
    assert result["draw_count"] == 10
    assert result["probability_ensemble"] is False
    summary = result["conditions"][0]["summary"]["recall"]
    values = [r["recall"] for r in result["conditions"][0]["per_draw"]]
    assert summary["mean"] == np.mean(values)
    assert summary["sd"] == np.std(values, ddof=1)
    assert summary["n_defined"] == 10


def test_source_only_is_one_vector_without_invented_draw_variation():
    y, scores, refs = invented()
    refs = {k: {"per_draw": v["per_draw"][:1], "mean": v["per_draw"][0]} for k, v in refs.items()}
    report = descriptive_sweep(y, scores[:1], reference=refs)
    assert report["draw_count"] == 1
    assert report["conditions"][0]["summary"]["recall"]["sd"] is None


def test_no_test_threshold_selection_available():
    y, scores, refs = invented()
    report = descriptive_sweep(y, scores, reference=refs)
    assert report["test_threshold_selected"] is False
    assert report["validation_status"] == VALIDATION_STATUS
    assert not any("optimal" in k or "best" in k for k in report)


@pytest.mark.parametrize("metric", RANKING)
@pytest.mark.parametrize("part", ["per_draw", "mean"])
def test_reconciliation_fail_closed(metric, part):
    y, scores, refs = invented()
    altered = copy.deepcopy(refs)
    if part == "mean":
        altered[metric][part] += 0.001
    else:
        altered[metric][part][0] += 0.001
    with pytest.raises(ValueError, match="reconciliation"):
        descriptive_sweep(y, scores, reference=altered)


def test_reordered_draws_rejected():
    y, scores, refs = invented()
    with pytest.raises(ValueError):
        descriptive_sweep(y, scores[::-1], reference=refs)


@pytest.mark.parametrize(
    "y,p,t",
    [
        ([], [], 0.5),
        ([2], [0.2], 0.5),
        ([1], [float("nan")], 0.5),
        ([1], [1.1], 0.5),
        ([1], [0.3], -1),
        ([1], [0.3], float("nan")),
        ([1, 0], [0.1], 0.5),
        ([1], [[0.1]], 0.5),
    ],
)
def test_invalid_inputs_rejected(y, p, t):
    with pytest.raises(ValueError):
        operating_point(y, p, t)


def test_undefined_summaries_and_invalid_references():
    assert summarize_draws([{"precision": None}])["precision"] == {
        "mean": None,
        "sd": None,
        "min": None,
        "max": None,
        "n_defined": 0,
        "n_undefined": 1,
    }
    with pytest.raises(ValueError):
        summarize_draws([])
    with pytest.raises(ValueError):
        reconcile_ranking([operating_point([0, 1], [0.1, 0.2])], {})


def test_confusion_svg_has_actual_rows_predicted_columns():
    path = Path(__file__).resolve().parents[1] / "examples" / "threshold_demo.py"
    spec = importlib.util.spec_from_file_location("invented_demo", path)
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    row = operating_point([0, 0, 0, 1, 1], [0.1, 0.2, 0.6, 0.5, 0.3])
    svg = demo.confusion_svg(row)
    assert "SYNTHETIC ONLY" in svg and "Actual label" in svg and "Predicted label" in svg
    assert "TN = 2" in svg and "FP = 1" in svg and "FN = 1" in svg and "TP = 1" in svg
    with pytest.raises(ValueError, match="integer"):
        demo.confusion_svg({**row, "TP": 1.5})
