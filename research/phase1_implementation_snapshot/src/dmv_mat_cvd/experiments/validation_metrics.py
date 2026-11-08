"""Selector recovery and prediction summaries are intentionally separate."""
from __future__ import annotations

from itertools import combinations
from typing import Iterable

import numpy as np


def mask_jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    a, b = set(left), set(right)
    return len(a & b) / len(a | b) if a | b else 1.0


def recovery_metrics(predicted: dict[str, bool], truth: dict[str, bool | None]) -> dict:
    known = {name: value for name, value in truth.items() if value is not None}
    if not known or set(known) - set(predicted):
        raise ValueError("Recovery requires predictions for all known ground-truth modules")
    positives = {name for name, value in known.items() if value}
    selected = {name for name in known if predicted[name]}
    tp, fp, fn = len(selected & positives), len(selected - positives), len(positives - selected)
    negatives = len(known) - len(positives)
    return {
        "selection_precision": tp / len(selected) if selected else None,
        "selection_recall": tp / len(positives) if positives else None,
        "selection_f1": 2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 1.0,
        "exact_mask_accuracy": float(selected == positives),
        "false_adaptation_rate": fp / negatives if negatives else None,
        "missed_adaptation_rate": fn / len(positives) if positives else None,
        "selection_jaccard": mask_jaccard(selected, positives),
        "known_modules": len(known), "ground_truth_adapt_count": len(positives),
    }


def pairwise_mask_jaccard(masks: list[dict[str, bool]], views_only: bool = False) -> float | None:
    sets = [{name for name, value in mask.items() if value and (not views_only or name.startswith("view:"))}
            for mask in masks]
    pairs = [mask_jaccard(a, b) for a, b in combinations(sets, 2)]
    return float(np.mean(pairs)) if pairs else None


def transfer_metrics(adapted: dict, source_only: dict) -> dict:
    result = {}
    for key in ("ap", "auroc"):
        a, b = adapted.get(key), source_only.get(key)
        gain = float(a - b) if a is not None and b is not None else None
        result[f"transfer_gain_{key}"] = gain
        result[f"negative_transfer_{key}"] = gain < 0 if gain is not None else None
    return result


def describe(values: Iterable[float | None]) -> dict:
    arr = np.array([value for value in values if value is not None], dtype=float)
    if not len(arr):
        return {"n": 0, "mean": None, "std": None, "median": None, "min": None, "max": None}
    if not np.isfinite(arr).all():
        raise ValueError("Nonfinite values must not enter validation summaries")
    return {"n": len(arr), "mean": float(arr.mean()), "std": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
            "median": float(np.median(arr)), "min": float(arr.min()), "max": float(arr.max())}
