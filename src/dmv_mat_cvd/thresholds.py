"""Portable descriptive operating points; no file reader or test-cutoff optimizer.

The controlled-data executor remains separate. These functions cannot establish
participant alignment, permission, checkpoint provenance or disclosure approval.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

THRESHOLDS = tuple(i / 100 for i in range(5, 51, 5))
VALIDATION_STATUS = "ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED"
RANKING = ("ap", "auroc", "brier")


def operating_point(labels, probabilities, threshold=0.5):
    """Positive iff p >= threshold; undefined ratios are None, never forced zero."""
    y, p = np.asarray(labels), np.asarray(probabilities)
    if (
        y.ndim != 1
        or p.shape != y.shape
        or not y.size
        or not np.isin(y, [0, 1]).all()
        or p.dtype.kind not in "fiu"
        or not np.isfinite(p).all()
        or ((p < 0) | (p > 1)).any()
    ):
        raise ValueError("Matching finite binary labels and probabilities required")
    if (
        not isinstance(threshold, (int, float, np.floating))
        or not np.isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise ValueError("Threshold must be finite and inside [0, 1]")
    y, p = y.astype(int), p.astype(float)
    pred = p >= threshold
    tp, tn = int(np.sum(pred & (y == 1))), int(np.sum(~pred & (y == 0)))
    fp, fn = int(np.sum(pred & (y == 0))), int(np.sum(~pred & (y == 1)))

    def divide(a, b):
        return float(a / b) if b else None

    recall, specificity = divide(tp, tp + fn), divide(tn, tn + fp)
    return {
        "threshold": float(threshold),
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "accuracy": divide(tp + tn, len(y)),
        "precision": divide(tp, tp + fp),
        "recall": recall,
        "specificity": specificity,
        "f1": divide(2 * tp, 2 * tp + fp + fn),
        "balanced_accuracy": (recall + specificity) / 2
        if recall is not None and specificity is not None
        else None,
        "ap": float(average_precision_score(y, p)) if y.sum() else None,
        "auroc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None,
        "brier": float(np.mean((p - y) ** 2)),
    }


def summarize_draws(rows):
    """Mean of per-draw metrics, sample SD/range and explicit definedness counts."""
    if not rows or any(set(row) != set(rows[0]) for row in rows):
        raise ValueError("Nonempty rows with identical metric keys required")
    summary = {}
    for key in rows[0]:
        values = np.asarray([row[key] for row in rows if row[key] is not None], dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("Nonfinite metric")
        summary[key] = {
            "n_defined": len(values),
            "n_undefined": len(rows) - len(values),
            "mean": float(values.mean()) if len(values) else None,
            "sd": float(values.std(ddof=1)) if len(values) > 1 else None,
            "min": float(values.min()) if len(values) else None,
            "max": float(values.max()) if len(values) else None,
        }
    return summary


def reconcile_ranking(rows, reference):
    """Fail before sweeping unless every per-draw value AND arithmetic mean match.

    References must be supplied by an independently verified caller. Matching
    numbers alone do not authenticate source data. Tolerances match the original
    supplementary calculator (atol=rtol=1e-8) and are not configurable here.
    """
    if set(reference) != set(RANKING):
        raise ValueError("AP, AUROC and Brier references required")
    for metric in RANKING:
        got = [row[metric] for row in rows]
        expected = reference[metric]
        if (
            any(value is None for value in got)
            or set(expected) != {"per_draw", "mean"}
            or len(expected["per_draw"]) != len(got)
            or not np.allclose(got, expected["per_draw"], atol=1e-8, rtol=1e-8)
            or not np.isclose(np.mean(got), expected["mean"], atol=1e-8, rtol=1e-8)
        ):
            raise ValueError("Frozen ranking reconciliation failed")


def descriptive_sweep(labels, score_draws, *, reference):
    """Same aligned participants in each row, no ensemble, no optimal test cutoff.

    A source-only reference can have one row. Membership/provenance validation is
    a caller responsibility; this portable API is not a controlled-data runner.
    """
    matrix = np.asarray(score_draws)
    if matrix.ndim != 2 or not len(matrix):
        raise ValueError("Nonempty draw-by-participant matrix required")
    baseline = [operating_point(labels, p) for p in matrix]
    reconcile_ranking(baseline, reference)
    conditions = []
    for threshold in THRESHOLDS:
        rows = [operating_point(labels, p, threshold) for p in matrix]
        if any(row[key] != original[key] for row, original in zip(rows, baseline) for key in RANKING):
            raise ValueError("Ranking metric changed with threshold")
        conditions.append({"threshold": threshold, "per_draw": rows, "summary": summarize_draws(rows)})
    return {
        "analysis": "SUPPLEMENTARY_DESCRIPTIVE_ONLY",
        "test_threshold_selected": False,
        "validation_status": VALIDATION_STATUS,
        "distinct_participants": len(labels),
        "draw_count": len(matrix),
        "shared_population_across_draws": True,
        "probability_ensemble": False,
        "sd_ddof": 1,
        "conditions": conditions,
    }
