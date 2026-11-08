"""Training-only preprocessing for the separate ten-feature public protocol."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .base import MultiViewDataset
from .public_v2 import VIEWS_TEN
from ..safeguards import LeakageError, SplitRole

CONTINUOUS = ("age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl")
CATEGORIES = {
    "sex": ("female", "male"),
    "smoking_status": ("never", "former", "current"),
    "diabetes": ("no", "yes"),
    "antihypertensive_treatment": ("no", "yes"),
}


class PublicPreprocessor:
    def __init__(self) -> None:
        self.state: dict | None = None

    def fit(self, frame: pd.DataFrame, role: SplitRole) -> "PublicPreprocessor":
        if role not in {SplitRole.SOURCE_TRAIN, SplitRole.TARGET_ADAPTATION}:
            raise LeakageError("Public preprocessing may fit only on source train or target adaptation")
        if self.state is not None:
            raise ValueError("Already fitted")
        self._validate(frame)
        stats = {}
        for name in CONTINUOUS:
            values = pd.to_numeric(frame[name], errors="raise").to_numpy(dtype=float)
            if not np.isfinite(values).any():
                raise ValueError(f"Training field {name} has no observed values")
            median = float(np.nanmedian(values))
            filled = np.where(np.isnan(values), median, values)
            scale = float(filled.std())
            stats[name] = {"median": median, "mean": float(filled.mean()),
                           "scale": scale if scale > 1e-12 else 1.0}
        self.state = {"schema_version": "cvd-public-wave-v2-ten-doctor-report",
                      "fit_role": role.value, "views": {k: list(v) for k, v in VIEWS_TEN.items()},
                      "continuous": stats,
                      "categories": {k: list(v) + ["unknown"] for k, v in CATEGORIES.items()}}
        return self

    @staticmethod
    def _validate(frame: pd.DataFrame) -> None:
        expected = {x for names in VIEWS_TEN.values() for x in names}
        if not frame.columns.is_unique or set(frame.columns) != expected | {"participant_id", "endpoint_status", "label"}:
            raise ValueError("Public feature contract mismatch or metadata in predictors")
        for name, categories in CATEGORIES.items():
            if not frame[name].dropna().isin(categories).all():
                raise ValueError(f"Unmapped public category: {name}")

    @property
    def encoded_columns(self) -> dict[str, list[str]]:
        if self.state is None:
            raise ValueError("Fit before deriving feature order")
        return {view: [column for name in fields for column in
                       ([name] if name in CONTINUOUS else
                        [f"{name}={value}" for value in self.state["categories"][name]])]
                for view, fields in VIEWS_TEN.items()}

    @property
    def view_dims(self) -> dict[str, int]:
        return {name: len(columns) for name, columns in self.encoded_columns.items()}

    def transform(self, frame: pd.DataFrame, role: SplitRole) -> MultiViewDataset:
        if role in {SplitRole.TARGET_TEST, SplitRole.SOURCE_TEST}:
            raise LeakageError("Development preprocessing cannot access a held-out test partition")
        if self.state is None:
            raise ValueError("Preprocessor must be fitted")
        self._validate(frame)
        if frame.label.isna().any() or not frame.label.isin([0, 1]).all():
            raise ValueError("Observed binary outcome required")
        encoded = {}
        for name in CONTINUOUS:
            s = self.state["continuous"][name]
            values = pd.to_numeric(frame[name], errors="raise").to_numpy(dtype=float)
            values = np.where(np.isnan(values), s["median"], values)
            encoded[name] = ((values - s["mean"]) / s["scale"])[:, None]
        for name, cats in self.state["categories"].items():
            values = frame[name].fillna("unknown").to_numpy()
            encoded[name] = np.column_stack([values == value for value in cats])
        views = {view: np.concatenate([encoded[name] for name in fields], axis=1).astype(np.float32)
                 for view, fields in VIEWS_TEN.items()}
        return MultiViewDataset(views, frame.label.to_numpy(), role)

    def save(self, path: Path) -> None:
        if self.state is None:
            raise ValueError("Cannot save unfitted preprocessor")
        path.write_text(json.dumps({**self.state, "encoded_columns": self.encoded_columns}, indent=2) + "\n")
