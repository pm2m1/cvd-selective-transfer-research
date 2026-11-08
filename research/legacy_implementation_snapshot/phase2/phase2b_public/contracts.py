"""Frozen-shape public interfaces for synthetic Phase 2B development only."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


FEATURES = ("age", "sex", "sbp", "dbp", "bmi", "smoking", "diabetes", "bp_treatment")
VIEWS = {
    "background": (0, 1),
    "haemodynamic": (2, 3),
    "metabolic": (4,),
    "behaviour": (5,),
    "comorbidity_medication": (6, 7),
}


class Role(str, Enum):
    SOURCE_TRAIN = "source_train"
    SOURCE_VALIDATION = "source_validation"
    TARGET_ADAPTATION = "target_adaptation"
    TARGET_VALIDATION = "target_validation"
    TARGET_TEST = "target_test"


@dataclass(frozen=True)
class FeatureBatch:
    values: np.ndarray
    feature_names: tuple[str, ...]
    role: Role

    def checked(self) -> np.ndarray:
        if self.feature_names != FEATURES:
            raise ValueError("unapproved feature order")
        x = np.asarray(self.values, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != len(FEATURES) or not np.isfinite(x).all():
            raise ValueError("invalid eight-feature matrix")
        if self.role == Role.TARGET_TEST:
            raise PermissionError("target-test access is unavailable in development")
        return x


class TrainingOnlyStandardizer:
    """A source or target-training fit boundary; imputation policy is not set here."""

    def __init__(self) -> None:
        self.mean_: np.ndarray | None = None
        self.scale_: np.ndarray | None = None
        self.fit_role: Role | None = None

    def fit(self, batch: FeatureBatch) -> "TrainingOnlyStandardizer":
        if self.mean_ is not None:
            raise ValueError("preprocessor is already fitted")
        if batch.role not in {Role.SOURCE_TRAIN, Role.TARGET_ADAPTATION}:
            raise PermissionError("preprocessing fit requires a permitted training role")
        x = batch.checked()
        if len(x) == 0:
            raise ValueError("empty training batch")
        self.mean_ = x.mean(axis=0)
        scale = x.std(axis=0)
        self.scale_ = np.where(scale > 0, scale, 1.0)
        self.fit_role = batch.role
        return self

    def transform(self, batch: FeatureBatch) -> np.ndarray:
        if self.mean_ is None or self.scale_ is None:
            raise ValueError("preprocessor has not been fitted")
        return (batch.checked() - self.mean_) / self.scale_
