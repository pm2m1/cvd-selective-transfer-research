from __future__ import annotations

from typing import Dict

import numpy as np
from itertools import product


def _minmax(values: Dict[str, float]) -> Dict[str, float]:
    arr = np.array(list(values.values()), dtype=float)
    lo, hi = float(arr.min()), float(arr.max())
    if abs(hi - lo) < 1e-12:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def select_adaptation_mask(
    scores: Dict[str, Dict[str, float]],
    discrepancy_weight: float = 0.65,
    adapt_fraction: float = 0.5,
):
    """Proposed deterministic corrected selector.

    Higher domain discrepancy pushes a module toward adaptation.
    Lower target discriminability also pushes a module toward adaptation.

    Returns a dict where True means ADAPT and False means SHARE/FREEZE.
    """
    if not 0 <= discrepancy_weight <= 1 or not 0 <= adapt_fraction <= 1 or not scores:
        raise ValueError("Nonempty scores and selector fractions/weights in [0, 1] required")
    if any(not np.isfinite(v[key]) or v[key] < 0 for v in scores.values() for key in ("mmd", "discriminability")):
        raise ValueError("Selector statistics must be finite and nonnegative")
    normalized = normalize_scores(scores)
    mmd_norm, disc_norm = normalized["mmd"], normalized["discriminability"]

    adapt_score = {
        k: discrepancy_weight * mmd_norm[k]
        + (1.0 - discrepancy_weight) * (1.0 - disc_norm[k])
        for k in scores
    }

    names = sorted(adapt_score, key=lambda name: (-adapt_score[name], name))
    n_adapt = 0 if adapt_fraction == 0 else max(1, int(round(adapt_fraction * len(names))))
    adapt_set = set(names[:n_adapt])
    mask = {name: name in adapt_set for name in scores}
    return mask, adapt_score


def normalize_scores(scores: Dict[str, Dict[str, float]]) -> dict[str, dict[str, float]]:
    return {statistic: _minmax({name: values[statistic] for name, values in scores.items()})
            for statistic in ("mmd", "discriminability")}


def random_budget_mask(model, reference_mask: dict[str, bool], seed: int):
    """Uniform draw among closest parameter-count masks, including the reference.

    Exhaustive enumeration is exact for the seven-module architecture. The head
    is always trained and thus contributes the same count to every candidate.
    """
    modules = model.selectable_modules()
    if set(reference_mask) != set(modules):
        raise ValueError("Reference mask must specify every selectable module")
    if len(modules) > 16:
        raise ValueError("Exhaustive budget matching is intended for small module sets")
    counts = np.array([sum(p.numel() for p in m.parameters()) for m in modules.values()])
    target = int(sum(counts[i] for i, name in enumerate(modules) if reference_mask[name]))
    candidates = list(product((False, True), repeat=len(modules)))
    errors = np.array([abs(int(np.dot(candidate, counts)) - target) for candidate in candidates])
    best = np.flatnonzero(errors == errors.min())
    choice = int(np.random.default_rng(seed).choice(best))
    mask = dict(zip(modules, candidates[choice]))
    return mask, {"parameter_budget_error": int(errors[choice]), "candidate_count": len(best),
                  "same_as_adaptive": mask == reference_mask, "reference_selectable_parameters": target}


# Explicit Milestone-2 version. The original function and defaults are unchanged.
legacy_topk = select_adaptation_mask


def diverse_random_budget_mask(model, reference_mask: dict[str, bool], seed: int, *,
                               tolerance_fraction: float = .005, views_only: bool = False):
    """Uniform near-budget control, without excluding or preferring the reference.

    A predeclared tolerance of 0.5% of total parameters relaxes accidental exact
    subset-sum degeneracy. The head is common. The legacy exact matcher remains.
    """
    if not 0 <= tolerance_fraction <= .1:
        raise ValueError("Random budget tolerance must be between 0 and 0.1")
    modules = model.selectable_modules()
    if set(reference_mask) != set(modules):
        raise ValueError("Reference must specify every module")
    names = [name for name in modules if not views_only or name.startswith("view:")]
    if any(value and name not in names for name, value in reference_mask.items()):
        raise ValueError("Reference violates selectable scope")
    counts = np.array([sum(p.numel() for p in modules[name].parameters()) for name in names])
    target = int(sum(count for name, count in zip(names, counts) if reference_mask[name]))
    candidates = list(product((False, True), repeat=len(names)))
    errors = np.array([abs(int(np.dot(candidate, counts)) - target) for candidate in candidates])
    tolerance = int(tolerance_fraction * sum(p.numel() for p in model.parameters()))
    eligible = np.flatnonzero(errors <= errors.min() + tolerance)
    chosen = int(np.random.default_rng(seed).choice(eligible))
    mask = dict.fromkeys(modules, False)
    mask.update(zip(names, candidates[chosen]))
    return mask, {"parameter_budget_error": int(errors[chosen]), "candidate_count": len(eligible),
                  "exact_candidate_count": int(np.sum(errors == errors.min())),
                  "equality_probability": 1 / len(eligible), "same_as_adaptive": mask == reference_mask,
                  "reference_selectable_parameters": target, "budget_tolerance_parameters": tolerance}
