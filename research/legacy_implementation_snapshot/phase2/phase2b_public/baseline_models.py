"""Registered-family prototypes for invented-data Phase 2B checks only.

Hyperparameters are caller supplied. No cohort loader, search, split creation,
private-path handling or real-data authorization is provided here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from .contracts import FeatureBatch, Role


@dataclass(frozen=True)
class FittedBaseline:
    family: Literal["elastic_net", "boosted_tree"]
    training_role: Role
    model: object

    def probability(self, batch: FeatureBatch) -> np.ndarray:
        x = batch.checked()  # Development code refuses a target-test batch.
        result = np.asarray(self.model.predict_proba(x)[:, 1], dtype=np.float64)
        if result.shape != (len(x),) or not np.isfinite(result).all() or np.any((result < 0) | (result > 1)):
            raise ValueError("invalid baseline probabilities")
        return result


def _training(batch: FeatureBatch, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if batch.role not in {Role.SOURCE_TRAIN, Role.TARGET_ADAPTATION}:
        raise PermissionError("baseline fitting requires permitted training data")
    x = batch.checked()
    y = np.asarray(labels)
    if y.shape != (len(x),) or not np.isin(y, [0, 1]).all() or len(np.unique(y)) != 2:
        raise ValueError("binary training labels with both classes are required")
    return x, y.astype(int)


def fit_elastic_net(batch: FeatureBatch, labels: np.ndarray, *, c: float, l1_ratio: float,
                    seed: int) -> FittedBaseline:
    x, y = _training(batch, labels)
    if not np.isfinite(c) or c <= 0 or not np.isfinite(l1_ratio) or not 0 <= l1_ratio <= 1:
        raise ValueError("invalid prespecified elastic-net parameters")
    model = LogisticRegression(penalty="elasticnet", solver="saga", C=c, l1_ratio=l1_ratio,
                               random_state=seed, max_iter=2000, tol=1e-6)
    model.fit(x, y)
    return FittedBaseline("elastic_net", batch.role, model)


def fit_boosted_tree(batch: FeatureBatch, labels: np.ndarray, *, iterations: int,
                     learning_rate: float, seed: int) -> FittedBaseline:
    x, y = _training(batch, labels)
    if not isinstance(iterations, int) or iterations < 1 or not np.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("invalid prespecified boosted-tree parameters")
    model = HistGradientBoostingClassifier(max_iter=iterations, learning_rate=learning_rate,
                                           random_state=seed)
    model.fit(x, y)
    return FittedBaseline("boosted_tree", batch.role, model)
