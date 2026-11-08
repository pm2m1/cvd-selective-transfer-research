"""Explicit provenance checks. These prevent mistakes, not malicious relabelling."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class SplitRole(str, Enum):
    SOURCE_TRAIN = "source_train"
    SOURCE_VALIDATION = "source_validation"
    SOURCE_TEST = "source_test"
    TARGET_ADAPTATION = "target_adaptation"
    TARGET_VALIDATION = "target_validation"
    TARGET_TEST = "target_test"


class LeakageError(ValueError):
    """A partition was used outside its permitted experiment stage."""


def require_role(value: object, allowed: Iterable[SplitRole], stage: str) -> SplitRole:
    # DataLoader and Subset preserve the underlying dataset's provenance.
    while hasattr(value, "dataset"):
        value = value.dataset
    role = getattr(value, "role", None)
    if role not in allowed:
        raise LeakageError(f"{stage}: split role {role!r} is not permitted")
    return SplitRole(role)


@dataclass
class AuditLog:
    entries: list[dict] = field(default_factory=list)

    def record(self, stage: str, partition: object) -> None:
        self.entries.append({"stage": stage, "role": partition.role.value,
                             "rows": len(partition)})
