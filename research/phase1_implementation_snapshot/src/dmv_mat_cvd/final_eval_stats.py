"""Pure prespecified final-test statistics. This module cannot load cohort data.

Predictions from frozen models must be supplied by a separately authorized,
one-time evaluator. Participant bootstrap indices are common to every model
and adaptation draw in each replicate; draw pairing is never broken.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


METRICS = ("ap", "auroc", "brier")


def _metric(y: np.ndarray, p: np.ndarray, name: str) -> float | None:
    if name == "ap":
        return float(average_precision_score(y, p)) if np.any(y == 1) else None
    if name == "auroc":
        return float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None
    if name == "brier":
        return float(brier_score_loss(y, p))
    raise ValueError("Unknown registered metric")


def validate_predictions(labels: np.ndarray, predictions: Mapping[str, np.ndarray]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    y = np.asarray(labels)
    if y.ndim != 1 or len(y) < 2 or not np.isin(y, [0, 1]).all() or len(np.unique(y)) != 2:
        raise ValueError("Evaluation requires a nonempty observed two-class binary test")
    if not predictions:
        raise ValueError("At least one frozen model prediction is required")
    out = {}
    for name, values in predictions.items():
        matrix = np.asarray(values, dtype=float)
        if matrix.ndim != 2 or matrix.shape[1] != len(y) or matrix.shape[0] < 1:
            raise ValueError(f"{name}: expected draws by participants matrix")
        if not np.isfinite(matrix).all() or (matrix < 0).any() or (matrix > 1).any():
            raise ValueError(f"{name}: predictions must be finite probabilities")
        out[name] = matrix
    return y.astype(int), out


def _draw_values(y: np.ndarray, probabilities: np.ndarray, metric: str) -> list[float] | None:
    values = [_metric(y, row, metric) for row in probabilities]
    return None if any(value is None for value in values) else [float(value) for value in values]


def _paired_difference(y: np.ndarray, left: np.ndarray, right: np.ndarray,
                       metric: str) -> float | None:
    if left.shape[0] != right.shape[0] and min(left.shape[0], right.shape[0]) != 1:
        raise ValueError("Contrasted methods need paired adaptation draws or one fixed source model")
    a, b = _draw_values(y, left, metric), _draw_values(y, right, metric)
    if a is None or b is None:
        return None
    return float(np.mean(np.asarray(a) - np.asarray(b)))


def _interval(values: list[float | None], *, alpha: float = .05) -> dict:
    good = np.array([x for x in values if x is not None], dtype=float)
    if not len(good):
        return {"lower": None, "upper": None, "valid_replicates": 0,
                "discarded_replicates": len(values)}
    return {"lower": float(np.quantile(good, alpha / 2)),
            "upper": float(np.quantile(good, 1 - alpha / 2)),
            "valid_replicates": len(good), "discarded_replicates": len(values) - len(good)}


def paired_participant_bootstrap(labels: np.ndarray, predictions: Mapping[str, np.ndarray],
                                 contrasts: Sequence[tuple[str, str]], *,
                                 seed: int, replicates: int = 2000) -> dict:
    """Joint participant resampling with within-repetition model pairing.

    Point estimates average per-draw metrics, not pooled probabilities.
    Bootstrap percentiles describe participant sampling uncertainty conditional
    on the fixed overlapping adaptation draws; no draw is treated as a new test.
    """
    y, models = validate_predictions(labels, predictions)
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0 or replicates < 20:
        raise ValueError("A fixed seed and at least 20 bootstrap replicates are required")
    if len(set(contrasts)) != len(contrasts) or any(a not in models or b not in models for a, b in contrasts):
        raise ValueError("Contrast methods must be registered and unique")
    for a, b in contrasts:
        if models[a].shape[0] != models[b].shape[0] and min(models[a].shape[0], models[b].shape[0]) != 1:
            raise ValueError("Contrast draws cannot be paired")
    observed = {name: {metric: {"per_draw": _draw_values(y, matrix, metric),
                                "mean": float(np.mean(_draw_values(y, matrix, metric)))
                                if _draw_values(y, matrix, metric) is not None else None}
                       for metric in METRICS}
                for name, matrix in models.items()}
    contrast_observed = {f"{a}_minus_{b}": {metric: _paired_difference(y, models[a], models[b], metric)
                                             for metric in METRICS}
                         for a, b in contrasts}
    model_samples = {name: {metric: [] for metric in METRICS} for name in models}
    contrast_samples = {f"{a}_minus_{b}": {metric: [] for metric in METRICS} for a, b in contrasts}
    rng = np.random.default_rng(seed)
    for _ in range(replicates):
        index = rng.integers(len(y), size=len(y))
        sample_y = y[index]
        sampled = {name: matrix[:, index] for name, matrix in models.items()}
        values = {name: {metric: _draw_values(sample_y, matrix, metric)
                         for metric in METRICS} for name, matrix in sampled.items()}
        for name, by_metric in values.items():
            for metric, per_draw in by_metric.items():
                model_samples[name][metric].append(float(np.mean(per_draw)) if per_draw is not None else None)
        for a, b in contrasts:
            key = f"{a}_minus_{b}"
            for metric in METRICS:
                left, right = values[a][metric], values[b][metric]
                contrast_samples[key][metric].append(
                    float(np.mean(np.asarray(left) - np.asarray(right)))
                    if left is not None and right is not None else None)
    return {"bootstrap_seed": seed, "replicates": replicates,
            "participant_count": len(y), "positive_count": int(y.sum()),
            "estimand": "mean_per_draw_metric_with_shared_test_participants",
            "models": {name: {metric: {**observed[name][metric],
                                        "interval": _interval(model_samples[name][metric])}
                              for metric in METRICS} for name in models},
            "contrasts": {key: {metric: {"estimate": contrast_observed[key][metric],
                                           "interval": _interval(contrast_samples[key][metric])}
                                for metric in METRICS} for key in contrast_samples}}


def fixed_reliability_bins(labels: np.ndarray, probabilities: np.ndarray,
                           edges: tuple[float, ...] = (0., .05, .10, 1.)) -> list[list[dict]]:
    """Descriptive fixed bins only; no model or calibrator is fitted."""
    y, models = validate_predictions(labels, {"frozen": probabilities})
    if edges != (0., .05, .10, 1.):
        raise ValueError("Final reliability bins are prespecified")
    out=[]
    for draw in models["frozen"]:
        bins=[]
        for lower, upper in zip(edges[:-1], edges[1:]):
            # The final bin includes p=1; interior boundaries go to the upper bin.
            mask=(draw>=lower)&((draw<upper) if upper<1 else (draw<=upper))
            count=int(mask.sum())
            bins.append({"lower": lower,"upper": upper,"n":count,
                         "mean_predicted":float(draw[mask].mean()) if count else None,
                         "observed_fraction":float(y[mask].mean()) if count else None})
        out.append(bins)
    return out
