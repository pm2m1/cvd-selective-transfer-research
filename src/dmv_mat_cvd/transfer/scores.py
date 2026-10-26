from __future__ import annotations

from typing import Dict
from dataclasses import dataclass

import numpy as np
import torch

from ..evaluation import ModuleRepresentations
from ..safeguards import SplitRole, require_role


def class_discriminability(features: np.ndarray, labels: np.ndarray, eps: float = 1e-8) -> float:
    """Legacy primitive; use checked_discriminability for explicit validity state."""
    f0 = features[labels == 0]
    f1 = features[labels == 1]
    if len(f0) < 2 or len(f1) < 2:
        return 0.0
    c0 = f0.mean(axis=0)
    c1 = f1.mean(axis=0)
    between = np.linalg.norm(c1 - c0)
    within = (
        np.linalg.norm(f0 - c0, axis=1).mean()
        + np.linalg.norm(f1 - c1, axis=1).mean()
    ) / 2.0
    return float(between / (within + eps))


@dataclass(frozen=True)
class DiscriminabilityResult:
    value: float | None
    status: str
    class_counts: tuple[int, int]


class InsufficientDiscriminability(ValueError):
    pass


def checked_discriminability(features: np.ndarray, labels: np.ndarray) -> DiscriminabilityResult:
    """Same centroid formula, with invalid cases distinguished from poor separation.

    The 1e-8 denominator stabilizer is negligible for ordinary representation
    scales. Below that scatter scale the statistic is declared degenerate.
    """
    _validate_pair(features, features)
    if labels.ndim != 1 or len(features) != len(labels) or not np.isin(labels, [0, 1]).all():
        raise ValueError("Discriminability requires matching binary labels")
    counts = (int(np.sum(labels == 0)), int(np.sum(labels == 1)))
    if min(counts) < 2:
        return DiscriminabilityResult(None, "insufficient_class_samples", counts)
    scatter = sum(np.linalg.norm(features[labels == c] - features[labels == c].mean(axis=0), axis=1).mean()
                  for c in (0, 1)) / 2
    if not np.isfinite(scatter) or scatter <= 1e-8:
        return DiscriminabilityResult(None, "degenerate_within_class_scatter", counts)
    value = class_discriminability(features, labels)
    if not np.isfinite(value):
        return DiscriminabilityResult(None, "nonfinite_statistic", counts)
    return DiscriminabilityResult(value, "valid", counts)


def _rbf_kernel(x: torch.Tensor, y: torch.Tensor, bandwidth: float) -> torch.Tensor:
    d2 = torch.cdist(x, y, p=2).pow(2)
    return torch.exp(-d2 / (2.0 * bandwidth * bandwidth))


def multi_kernel_mmd(
    source: np.ndarray,
    target: np.ndarray,
    bandwidths=(0.5, 1.0, 2.0, 4.0),
    max_samples: int = 1024,
    seed: int = 0,
) -> float:
    """Biased multi-kernel MMD^2; higher means greater source-target discrepancy."""
    if max_samples < 2 or not bandwidths or any(not np.isfinite(bw) or bw <= 0 for bw in bandwidths):
        raise ValueError("MMD requires positive bandwidths and max_samples >= 2")
    _validate_pair(source, target)
    rng = np.random.default_rng(seed)
    if len(source) > max_samples:
        source = source[rng.choice(len(source), max_samples, replace=False)]
    if len(target) > max_samples:
        target = target[rng.choice(len(target), max_samples, replace=False)]

    x = torch.tensor(source, dtype=torch.float32)
    y = torch.tensor(target, dtype=torch.float32)
    value = torch.tensor(0.0)
    for bw in bandwidths:
        kxx = _rbf_kernel(x, x, bw).mean()
        kyy = _rbf_kernel(y, y, bw).mean()
        kxy = _rbf_kernel(x, y, bw).mean()
        value = value + (kxx + kyy - 2.0 * kxy)
    return float((value / len(bandwidths)).clamp_min(0.0).item())


def _validate_pair(source: np.ndarray, target: np.ndarray) -> None:
    if (source.ndim != 2 or target.ndim != 2 or source.shape[1] != target.shape[1]
            or not source.size or not target.size or not np.isfinite(source).all()
            or not np.isfinite(target).all()):
        raise ValueError("Representations must be finite, nonempty matrices with matching dimensions")


def normalize_representations(source: np.ndarray, target: np.ndarray):
    """Source-centered RMS Euclidean radius; one scalar, not feature whitening.

    RMS radius includes dimension. Invariant to common translation, uniform
    scaling and repeated coordinates (apart from the degenerate-radius floor).
    No target statistics are used to fit this normalization.
    """
    _validate_pair(source, target)
    center = source.astype(np.float64).mean(axis=0)
    radius = float(np.sqrt(np.square(source - center).sum(axis=1).mean()))
    scale = max(radius, 1e-8 * np.sqrt(source.shape[1]))
    return (source - center) / scale, (target - center) / scale, scale


def score_modules(source: ModuleRepresentations, target: ModuleRepresentations, *,
                  max_samples: int = 1024, seed: int = 0,
                  normalize: bool = True, allow_invalid_geometry: bool = False) -> Dict[str, Dict[str, float]]:
    """Selector statistics only; no gradients and no domain-alignment objective."""
    require_role(source, {SplitRole.SOURCE_TRAIN, SplitRole.SOURCE_VALIDATION}, "source module scoring")
    require_role(target, {SplitRole.TARGET_ADAPTATION}, "target module scoring")
    if set(source.features) != set(target.features) or not source.features:
        raise ValueError("Source and target module names must match")
    if target.labels.ndim != 1 or not np.isin(target.labels, [0, 1]).all():
        raise ValueError("Target discriminability requires binary labels")
    if not allow_invalid_geometry and min(np.sum(target.labels == 0), np.sum(target.labels == 1)) < 2:
        raise InsufficientDiscriminability("Module scoring requires at least two adaptation samples per class")
    scores = {}
    for name in source.features:
        src, tgt = source.features[name], target.features[name]
        _validate_pair(src, tgt)
        if len(tgt) != len(target.labels) or len(src) != len(source.labels):
            raise ValueError("Representation and label counts differ")
        normalized_source, normalized_target, scale = normalize_representations(src, tgt)
        discriminability = checked_discriminability(tgt, target.labels)
        if discriminability.value is None and not allow_invalid_geometry:
            raise InsufficientDiscriminability(f"{name}: {discriminability.status}; no mask selected")
        raw_mmd = multi_kernel_mmd(src, tgt, max_samples=max_samples, seed=seed)
        scores[name] = {
            "discriminability": discriminability.value,
            "raw_mmd": raw_mmd,
            "mmd": multi_kernel_mmd(normalized_source if normalize else src,
                                    normalized_target if normalize else tgt,
                                    max_samples=max_samples, seed=seed) if normalize else raw_mmd,
            "normalization_scale": scale if normalize else 1.0,
        }
    return scores
