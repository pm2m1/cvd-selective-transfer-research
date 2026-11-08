"""Fixed-penalty logistic prototypes for invented-data checks.

No penalty-selection rule, imputation policy, cohort, split or clinical use is
approved. The caller must supply already permitted training arrays.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, log_expit

from .contracts import FEATURES, VIEWS, FeatureBatch, Role


@dataclass(frozen=True)
class LogisticWeights:
    intercept: float
    coefficients: np.ndarray

    def __post_init__(self) -> None:
        beta = np.asarray(self.coefficients, dtype=np.float64).copy()
        if beta.shape != (len(FEATURES),) or not np.isfinite(beta).all() or not np.isfinite(self.intercept):
            raise ValueError("invalid frozen logistic weights")
        beta.setflags(write=False)
        object.__setattr__(self, "coefficients", beta)

    def probability(self, x: np.ndarray) -> np.ndarray:
        x = _features(x)
        return expit(self.intercept + x @ self.coefficients)


def _features(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != len(FEATURES) or not np.isfinite(x).all():
        raise ValueError("expected finite eight-feature training matrix")
    return x


def _labels(y: np.ndarray, n: int) -> np.ndarray:
    y = np.asarray(y, dtype=np.float64)
    if y.shape != (n,) or not np.isin(y, (0.0, 1.0)).all() or np.unique(y).size != 2:
        raise ValueError("binary training labels with both classes required")
    return y


def fit_fixed_penalty(
    batch: FeatureBatch, y: np.ndarray, *, center: LogisticWeights | None = None,
    view_penalties: dict[str, float] | None = None, l2: float = 1.0,
) -> LogisticWeights:
    """Fit a specified objective; never select penalties or access validation labels.

    For target adaptation, `center` is a frozen source fit and each supplied
    view penalty acts on its coefficient group. Intercept is unpenalized.
    """
    if batch.role not in {Role.SOURCE_TRAIN, Role.TARGET_ADAPTATION}:
        raise PermissionError("fitting requires source training or target adaptation data")
    if center is not None and batch.role != Role.TARGET_ADAPTATION:
        raise PermissionError("source-centered adaptation requires target adaptation data")
    x = batch.checked()
    y = _labels(y, len(x))
    if not np.isfinite(l2) or l2 < 0:
        raise ValueError("invalid global penalty")
    if center is not None:
        if center.coefficients.shape != (len(FEATURES),) or not np.isfinite(center.coefficients).all():
            raise ValueError("invalid source center")
        if view_penalties is None or set(view_penalties) != set(VIEWS):
            raise ValueError("all five view penalties must be fixed before fitting")
        if any(not np.isfinite(value) or value < 0 for value in view_penalties.values()):
            raise ValueError("invalid view penalty")
        penalty = np.zeros(len(FEATURES))
        for view, indices in VIEWS.items():
            penalty[list(indices)] = view_penalties[view]
        center_beta = center.coefficients
    else:
        if view_penalties is not None:
            raise ValueError("view penalties require a frozen source center")
        penalty = np.full(len(FEATURES), l2)
        center_beta = np.zeros(len(FEATURES))

    def objective(theta: np.ndarray) -> tuple[float, np.ndarray]:
        z = theta[0] + x @ theta[1:]
        loss = -np.mean(y * log_expit(z) + (1 - y) * log_expit(-z))
        delta = theta[1:] - center_beta
        loss += 0.5 * np.dot(penalty, delta * delta)
        residual = expit(z) - y
        gradient = np.empty_like(theta)
        gradient[0] = residual.mean()
        gradient[1:] = x.T @ residual / len(x) + penalty * delta
        return float(loss), gradient

    start = np.r_[float(np.log(y.mean() / (1 - y.mean()))),
                  center_beta if center is not None else np.zeros(len(FEATURES))]
    result = minimize(objective, start, jac=True, method="L-BFGS-B",
                      options={"maxiter": 400, "ftol": 1e-11})
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError("fixed-penalty logistic optimization failed")
    return LogisticWeights(float(result.x[0]), result.x[1:])


def global_source_penalties(value: float) -> dict[str, float]:
    """A prescribed global-shrinkage control under the same feature groups."""
    if not np.isfinite(value) or value < 0:
        raise ValueError("invalid global source penalty")
    return {view: float(value) for view in VIEWS}
