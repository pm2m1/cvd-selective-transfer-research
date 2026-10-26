"""Split-aware median imputation, standardization and fixed category encoding."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..safeguards import SplitRole, require_role
from .base import CohortPartition, MultiViewDataset
from .schema import CATEGORIES, CONTINUOUS, SCHEMA_VERSION, VIEW_FEATURES


class Preprocessor:
    def __init__(self) -> None:
        self.state: dict | None = None

    def fit(self, partition: CohortPartition) -> Preprocessor:
        role = require_role(partition, {SplitRole.SOURCE_TRAIN, SplitRole.TARGET_ADAPTATION},
                            "preprocessing fit")
        if self.state is not None:
            raise ValueError("Preprocessor is already fitted; create a new instance to refit")
        frame = partition.cohort.predictors()
        statistics = {}
        for name in CONTINUOUS:
            values = pd.to_numeric(frame[name]).to_numpy(dtype=float)
            all_missing = bool(np.isnan(values).all())
            median = 0.0 if all_missing else float(np.nanmedian(values))
            filled = np.where(np.isnan(values), median, values)
            scale = float(filled.std())
            statistics[name] = {"median": median, "mean": float(filled.mean()),
                                "scale": scale if scale > 1e-12 else 1.0,
                                "all_missing": all_missing}
        self.state = {"schema_version": SCHEMA_VERSION, "fit_role": role.value,
                      "continuous": statistics,
                      "categories": {k: [*v, "unknown"] for k, v in CATEGORIES.items()}}
        return self

    @property
    def encoded_columns(self) -> dict[str, list[str]]:
        if self.state is None:
            raise ValueError("Fit preprocessing before deriving model dimensions")
        return {view: [column for name in names for column in
                       ([name] if name in CONTINUOUS else
                        [f"{name}={category}" for category in self.state["categories"][name]])]
                for view, names in VIEW_FEATURES.items()}

    @property
    def view_dims(self) -> dict[str, int]:
        return {view: len(columns) for view, columns in self.encoded_columns.items()}

    def transform(self, partition: CohortPartition) -> MultiViewDataset:
        if self.state is None:
            raise ValueError("Preprocessor is not fitted")
        frame = partition.cohort.predictors()
        encoded = {}
        for name in CONTINUOUS:
            stats = self.state["continuous"][name]
            values = pd.to_numeric(frame[name]).to_numpy(dtype=float)
            values = np.where(np.isnan(values), stats["median"], values)
            encoded[name] = ((values - stats["mean"]) / stats["scale"])[:, None]
        for name, categories in self.state["categories"].items():
            values = frame[name].fillna("unknown").to_numpy()
            encoded[name] = np.column_stack([values == category for category in categories])
        if "label" not in partition.cohort.records or partition.cohort.records.label.isna().any():
            raise ValueError("Resolve observation status and select observed labels before tensor conversion")
        views = {view: np.concatenate([encoded[name] for name in names], axis=1).astype(np.float32)
                 for view, names in VIEW_FEATURES.items()}
        return MultiViewDataset(views, partition.cohort.records.label.to_numpy(), partition.role)

    def save(self, path: str | Path) -> None:
        if self.state is None:
            raise ValueError("Preprocessor is not fitted")
        Path(path).write_text(json.dumps(self.state, indent=2, allow_nan=False) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> Preprocessor:
        state = json.loads(Path(path).read_text())
        if state["schema_version"] != SCHEMA_VERSION:
            raise ValueError("Incompatible preprocessing schema")
        if state["fit_role"] not in {SplitRole.SOURCE_TRAIN.value, SplitRole.TARGET_ADAPTATION.value}:
            raise ValueError("Invalid preprocessing fit provenance")
        if state["categories"] != {k: [*v, "unknown"] for k, v in CATEGORIES.items()}:
            raise ValueError("Incompatible categorical encoding")
        for name in CONTINUOUS:
            stats = state["continuous"][name]
            if not all(np.isfinite(stats[key]) for key in ("median", "mean", "scale")) or stats["scale"] <= 0:
                raise ValueError("Invalid fitted continuous statistics")
        out = cls()
        out.state = state
        return out
