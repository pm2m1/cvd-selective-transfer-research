from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from ..safeguards import SplitRole
from .schema import PREDICTORS, SCHEMA_VERSION, validate_table


@dataclass
class CohortTable:
    records: pd.DataFrame
    domain: str
    schema_version: str = SCHEMA_VERSION
    onboarding: dict | None = None

    def __post_init__(self) -> None:
        self.records = self.records.copy(deep=True).reset_index(drop=True)
        validate_table(self.records)
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Unsupported schema version")

    def predictors(self) -> pd.DataFrame:
        """Allowlist selection: endpoint metadata can never leak into features."""
        return self.records.loc[:, list(PREDICTORS)].copy()

    def __len__(self) -> int:
        return len(self.records)


@dataclass
class CohortPartition:
    cohort: CohortTable
    role: SplitRole

    def __post_init__(self) -> None:
        self.role = SplitRole(self.role)

    def __len__(self) -> int:
        return len(self.cohort)

    @property
    def participant_ids(self) -> frozenset[str]:
        return frozenset(self.cohort.records.participant_id.astype(str))


class MultiViewDataset(Dataset):
    """Model tensors only; no pandas, dates, IDs or endpoint metadata retained."""

    def __init__(self, views: dict[str, np.ndarray], labels: np.ndarray,
                 role: SplitRole | None = None):
        # Validate before casting: float32 can round a nonbinary value to 0/1.
        labels = np.asarray(labels)
        if labels.ndim != 1 or not np.isin(labels, [0, 1]).all():
            raise ValueError("Only observed binary labels can enter model datasets")
        labels = labels.astype(np.float32)
        if not views or any(np.asarray(v).ndim != 2 or len(v) != len(labels) for v in views.values()):
            raise ValueError("Views must be 2D with one row per label")
        if any(not np.isfinite(v).all() for v in views.values()):
            raise ValueError("Model inputs must be finite after preprocessing")
        self.views = {k: torch.tensor(v, dtype=torch.float32) for k, v in views.items()}
        if any(not torch.isfinite(value).all() for value in self.views.values()):
            raise ValueError("Model inputs must remain finite when converted to float32")
        self.labels = torch.tensor(labels, dtype=torch.float32)
        self.names = list(views)
        self.role = SplitRole(role) if role is not None else None

    @property
    def view_dims(self) -> dict[str, int]:
        return {name: value.shape[1] for name, value in self.views.items()}

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int):
        return {k: self.views[k][idx] for k in self.names}, self.labels[idx]
