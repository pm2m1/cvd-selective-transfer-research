"""Nested event-budget sampling confined to the target adaptation partition."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from .base import CohortPartition, CohortTable
from ..safeguards import SplitRole, require_role


class InsufficientBudgetData(ValueError):
    pass


def participant_fingerprint(partition: CohortPartition) -> str:
    return hashlib.sha256(json.dumps(sorted(partition.participant_ids)).encode()).hexdigest()


def sample_event_budget(partition: CohortPartition, events: int, seed: int) -> CohortPartition:
    """Take a random permutation prefix ending at the requested positive event.

    No class-ratio matching or test access. Budgets share the same permutation,
    making subsets nested. Validation supervision is additional to this budget.
    """
    require_role(partition, {SplitRole.TARGET_ADAPTATION}, "event-budget selection")
    if isinstance(events, bool) or not isinstance(events, (int, np.integer)) or events < 2:
        raise ValueError("Event budget must be an integer >= 2")
    frame = partition.cohort.records
    if not frame.participant_id.is_unique:
        raise ValueError("Event-budget sampling requires one record per participant")
    if "label" not in frame or frame.label.isna().any():
        raise ValueError("Event-budget sampling requires observed binary labels")
    # Canonical sorting makes selection independent of input row order.
    order = np.argsort(frame.participant_id.astype(str).to_numpy(), kind="stable")
    order = np.random.default_rng(seed).permutation(order)
    labels = frame.label.to_numpy()[order]
    positive_indices = np.flatnonzero(labels == 1)
    if len(positive_indices) < events:
        raise InsufficientBudgetData(f"Requested {events} events; adaptation pool has {len(positive_indices)}")
    selected = order[:positive_indices[events - 1] + 1]
    if np.sum(frame.label.to_numpy()[selected] == 0) < 2:
        raise InsufficientBudgetData("Budget prefix has fewer than two controls; no mask should be selected")
    return CohortPartition(CohortTable(frame.iloc[selected], partition.cohort.domain), partition.role)
