"""Internal, exploratory selector evidence; never an optimizer loss.

Permutation calibration uses a label-blind pooled RMS kernel so its transform
is identical under every domain relabelling. Source-RMS MMD remains an ablation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..evaluation import ModuleRepresentations
from ..safeguards import SplitRole, require_role
from .scores import _validate_pair, checked_discriminability


@dataclass(frozen=True)
class CalibrationConfig:
    permutations: int = 199
    bootstraps: int = 199
    alpha: float = .05
    min_class_count: int = 5
    min_source_discriminability: float = .1
    strong_retention: float = .5
    moderate_retention: float = .8
    confidence_retention: float = .75

    def __post_init__(self):
        if type(self.permutations) is not int or self.permutations < 9:
            raise ValueError("At least 9 integer permutations required")
        if type(self.bootstraps) is not int or self.bootstraps < 19:
            raise ValueError("At least 19 integer bootstraps required")
        if self.min_class_count < 2 or not 0 < self.alpha < .5:
            raise ValueError("Invalid class count or calibration alpha")
        if not 0 < self.min_source_discriminability or not np.isfinite(self.min_source_discriminability):
            raise ValueError("Source geometry floor must be finite and positive")
        if not 0 < self.strong_retention < self.moderate_retention < 1:
            raise ValueError("Retention thresholds must be ordered inside (0, 1)")
        if not 0 < self.confidence_retention < 1:
            raise ValueError("Confidence retention threshold must be inside (0, 1)")


def permutation_mmd(source: np.ndarray, target: np.ndarray, *, permutations: int = 199,
                    max_samples: int = 128, seed: int = 0) -> dict:
    """Biased four-kernel MMD², conditional Monte Carlo domain-label null.

    P=(1 + number(null >= observed))/(B+1). Null variance zero gives an explicit
    status and no z statistic. Fixed pooled RMS avoids freezing a transform
    fitted to the original domain labels while permuting those same labels.
    """
    _validate_pair(source, target)
    if type(permutations) is not int or permutations < 9 or max_samples < 2:
        raise ValueError("Require >=9 permutations and >=2 maximum samples")
    rng = np.random.default_rng(seed)
    x = source[rng.choice(len(source), min(len(source), max_samples), replace=False)].astype(float)
    y = target[rng.choice(len(target), min(len(target), max_samples), replace=False)].astype(float)
    n, m = len(x), len(y)
    if min(n, m) < 2:
        raise ValueError("Require at least two representations in each domain")
    pooled = np.vstack((x, y))
    pooled -= pooled.mean(axis=0)
    radius = float(np.sqrt(np.square(pooled).sum(axis=1).mean()))
    pooled /= max(radius, 1e-8 * np.sqrt(pooled.shape[1]))
    norm = np.square(pooled).sum(axis=1)
    distance = np.maximum(norm[:, None] + norm[None, :] - 2 * pooled @ pooled.T, 0)
    kernel = sum(np.exp(-distance / (2 * b * b)) for b in (.5, 1., 2., 4.)) / 4
    weights = np.full((permutations + 1, n + m), -1 / m)
    weights[0, :n] = 1 / n
    for i in range(1, permutations + 1):
        weights[i, rng.permutation(n + m)[:n]] = 1 / n
    values = np.maximum(np.einsum('ij,ij->i', weights @ kernel, weights), 0)
    observed, null = float(values[0]), values[1:]
    mean, std = float(null.mean()), float(null.std(ddof=1))
    return {"permutation_mmd": observed, "null_mean": mean, "null_std": std,
            "mmd_z": (observed - mean) / std if std > 1e-12 else None,
            "domain_p": float((1 + np.sum(null >= observed - 1e-12)) / (permutations + 1)),
            "domain_status": "valid" if std > 1e-12 else "degenerate_null",
            "permutations": permutations, "calibration_source_n": n, "calibration_target_n": m,
            "calibration_scaling": "pooled_label_blind_rms", "pooled_radius": radius}


def relative_geometry(source: np.ndarray, source_labels: np.ndarray, target: np.ndarray,
                      target_labels: np.ndarray, *, config: CalibrationConfig | None = None,
                      seed: int = 0) -> dict:
    """Source-anchored signed centroid separation relative to source separation.

    R = cos(d_s,d_t) D_t / D_s. A reversal has R < 0 even if D_t == D_s.
    Stratified bootstraps quantify class-mean uncertainty conditional on the
    fitted source direction and plug-in within-class radii; not clinical CIs.
    """
    cfg = config or CalibrationConfig()
    _validate_pair(source, target)
    src = checked_discriminability(source, source_labels)
    tgt = checked_discriminability(target, target_labels)
    result = {"source_discriminability": src.value, "target_discriminability": tgt.value,
              "source_class_counts": list(src.class_counts), "target_class_counts": list(tgt.class_counts),
              "geometry_status": "valid", "discriminability_ratio": None,
              "orientation_cosine": None, "signed_retention": None,
              "retention_lower": None, "retention_upper": None, "bootstrap_valid_fraction": None}
    if src.value is None or tgt.value is None:
        result["geometry_status"] = f"source:{src.status};target:{tgt.status}"
        return result
    if min(*src.class_counts, *tgt.class_counts) < cfg.min_class_count:
        result["geometry_status"] = "insufficient_class_samples"
        return result
    if src.value < cfg.min_source_discriminability:
        result["geometry_status"] = "weak_source_geometry"
        return result
    s, t = source.astype(float), target.astype(float)
    ds = s[source_labels == 1].mean(0) - s[source_labels == 0].mean(0)
    dt = t[target_labels == 1].mean(0) - t[target_labels == 0].mean(0)
    direction = ds / np.linalg.norm(ds)
    scatter = lambda x, y: sum(np.linalg.norm(x[y == c] - x[y == c].mean(0), axis=1).mean() for c in (0, 1)) / 2
    ss, st = scatter(s, source_labels), scatter(t, target_labels)
    cosine = float(np.dot(direction, dt) / np.linalg.norm(dt)) if np.linalg.norm(dt) > 1e-12 else None
    retention = float((dt @ direction / st) / (ds @ direction / ss))
    result.update(discriminability_ratio=tgt.value / src.value, orientation_cosine=cosine,
                  signed_retention=retention)
    rng = np.random.default_rng(seed)
    def bootstrap_contrast(x, labels):
        projected = x @ direction
        means = []
        for c in (0, 1):
            group = projected[labels == c]
            indices = rng.integers(len(group), size=(cfg.bootstraps, len(group)))
            means.append(group[indices].mean(axis=1))
        return means[1] - means[0]
    bs = bootstrap_contrast(s, source_labels) / ss
    bt = bootstrap_contrast(t, target_labels) / st
    valid = bs > .02
    result["bootstrap_valid_fraction"] = float(valid.mean())
    if valid.mean() < 1 - cfg.alpha:
        result["geometry_status"] = "uncertain_source_geometry"
        return result
    ratios = bt[valid] / bs[valid]
    result["retention_lower"] = float(np.quantile(ratios, cfg.alpha))
    result["retention_upper"] = float(np.quantile(ratios, 1 - cfg.alpha))
    return result


def calibrate_modules(source: ModuleRepresentations, target: ModuleRepresentations, *,
                      config: CalibrationConfig | None = None, max_samples: int = 128,
                      seed: int = 0) -> dict[str, dict]:
    require_role(source, {SplitRole.SOURCE_TRAIN, SplitRole.SOURCE_VALIDATION}, "source selector calibration")
    require_role(target, {SplitRole.TARGET_ADAPTATION}, "target selector calibration")
    if not source.features or set(source.features) != set(target.features):
        raise ValueError("Matching nonempty module sets required")
    cfg = config or CalibrationConfig()
    return {name: {**permutation_mmd(source.features[name], target.features[name],
                                     permutations=cfg.permutations, max_samples=max_samples, seed=seed + i),
                   **relative_geometry(source.features[name], source.labels, target.features[name], target.labels,
                                       config=cfg, seed=seed + 1000 + i)}
            for i, name in enumerate(sorted(source.features))}


def calibrated_mask(evidence: dict[str, dict], policy: str,
                    config: CalibrationConfig | None = None) -> tuple[dict[str, bool], dict[str, str]]:
    """Two frozen interpretable candidates. Invalid evidence abstains to SHARE."""
    cfg = config or CalibrationConfig()
    if policy not in {"calibrated_threshold", "calibrated_logical"} or not evidence:
        raise ValueError("Choose a known calibrated policy and nonempty evidence")
    mask, reasons = {}, {}
    for name, e in evidence.items():
        if e["geometry_status"] != "valid":
            mask[name], reasons[name] = False, "ABSTAIN:" + e["geometry_status"]
            continue
        r, upper = e["signed_retention"], e["retention_upper"]
        if r is None or upper is None or not np.isfinite([r, upper]).all():
            raise ValueError("Valid geometry requires finite retention and uncertainty")
        domain = e["domain_status"] == "valid" and e["domain_p"] <= cfg.alpha
        # B: independent point thresholds, with an uncertainty guard against R=1.
        strong = r < cfg.strong_retention and upper < 1
        # C: require the upper uncertainty bound itself to show material degradation.
        if policy == "calibrated_logical":
            strong = upper < cfg.confidence_retention
        corroborated = domain and r < cfg.moderate_retention and upper < 1
        mask[name] = bool(strong or corroborated)
        reasons[name] = "predictive_degradation" if strong else "domain_and_geometry" if corroborated else "insufficient_shift_evidence"
    return mask, reasons
