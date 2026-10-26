"""Seeded participant splits. Target fractions are fixed without looking at labels."""
from __future__ import annotations

import numpy as np

from .base import CohortPartition, CohortTable
from ..safeguards import SplitRole


def assert_disjoint(*partitions: CohortPartition) -> None:
    seen: set[str] = set()
    for partition in partitions:
        if seen.intersection(partition.participant_ids):
            raise ValueError("Participant overlap between partitions")
        seen.update(partition.participant_ids)


def _split(cohort: CohortTable, fractions: list[float], roles: list[SplitRole],
           seed: int) -> dict[str, CohortPartition]:
    if not np.isfinite(fractions).all() or min(fractions) < 0 or not np.isclose(sum(fractions), 1):
        raise ValueError("Split fractions must be finite, nonnegative and sum to one")
    ids = np.array(sorted(set(cohort.records.participant_id.astype(str))))
    ids = np.random.default_rng(seed).permutation(ids)
    sizes = np.floor(np.array(fractions) * len(ids)).astype(int)
    # Largest remainder allocation avoids gratuitously empty small partitions.
    order = np.argsort(-(np.array(fractions) * len(ids) - sizes), kind="stable")
    for index in order[:len(ids) - sizes.sum()]:
        sizes[index] += 1
    if any(f > 0 and size == 0 for f, size in zip(fractions, sizes)):
        raise ValueError("Too few participants for the requested nonempty splits")
    out, start = {}, 0
    for role, size in zip(roles, sizes):
        selected = ids[start:start + size]
        start += size
        if size:
            frame = cohort.records.loc[cohort.records.participant_id.astype(str).isin(selected)]
            out[role.value] = CohortPartition(CohortTable(frame, cohort.domain), role)
    assert_disjoint(*out.values())
    return out


def split_source(cohort: CohortTable, train_fraction: float = 0.6,
                 validation_fraction: float = 0.2, seed: int = 0) -> dict[str, CohortPartition]:
    if train_fraction <= 0 or validation_fraction <= 0 or train_fraction + validation_fraction > 1:
        raise ValueError("Source train and validation fractions must be positive")
    return _split(cohort, [train_fraction, validation_fraction, max(0.0, 1 - train_fraction - validation_fraction)],
                  [SplitRole.SOURCE_TRAIN, SplitRole.SOURCE_VALIDATION, SplitRole.SOURCE_TEST], seed)


def split_target(cohort: CohortTable, test_fraction: float = 0.25,
                 adaptation_fraction: float = 0.8, seed: int = 0) -> dict[str, CohortPartition]:
    """adaptation_fraction is the fraction of the non-test development pool."""
    if not 0 < test_fraction < 1 or not 0 < adaptation_fraction < 1:
        raise ValueError("Target test and development adaptation fractions must lie in (0, 1)")
    # Lock test first: changing the adaptation budget cannot change test membership.
    first = _split(cohort, [1 - test_fraction, test_fraction],
                   [SplitRole.TARGET_ADAPTATION, SplitRole.TARGET_TEST], seed)
    development = first[SplitRole.TARGET_ADAPTATION.value].cohort
    out = _split(development, [adaptation_fraction, 1 - adaptation_fraction],
                 [SplitRole.TARGET_ADAPTATION, SplitRole.TARGET_VALIDATION], seed + 1)
    out[SplitRole.TARGET_TEST.value] = first[SplitRole.TARGET_TEST.value]
    assert_disjoint(*out.values())
    return out
