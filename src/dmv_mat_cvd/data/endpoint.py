"""Generic fixed-horizon outcome construction from adjudicated, harmonized metadata.

No cohort codes are interpreted here. Event time denotes the first qualifying
event when event_type is mi/stroke. last_followup_days must certify endpoint
ascertainment, not merely an unrelated visit date.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

import pandas as pd

PRIMARY_HORIZON_DAYS = 1826


class EndpointStatus(str, Enum):
    POSITIVE = "positive"
    KNOWN_NEGATIVE = "known_negative"
    COMPETING_DEATH = "competing_death"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class EventMetadata:
    event_type: str | None = None  # canonical mi, stroke or nonqualifying
    event_time_days: float | None = None
    death_time_days: float | None = None
    last_followup_days: float | None = None
    death_is_nonqualifying: bool = False


@dataclass(frozen=True)
class EndpointResult:
    status: EndpointStatus
    label: int | None


def build_endpoint(event: EventMetadata, horizon_days: float = PRIMARY_HORIZON_DAYS) -> EndpointResult:
    if not math.isfinite(horizon_days) or horizon_days <= 0:
        raise ValueError("Horizon must be finite and positive")
    times = (event.event_time_days, event.death_time_days, event.last_followup_days)
    if any(t is not None and (not math.isfinite(t) or t < 0) for t in times):
        raise ValueError("Times must be finite, nonnegative days after index")
    if event.event_type not in {None, "mi", "stroke", "nonqualifying"}:
        raise ValueError("Event types require explicit harmonization before endpoint construction")
    if (event.event_type is None) != (event.event_time_days is None):
        raise ValueError("Event type and event time must be supplied together")
    if not isinstance(event.death_is_nonqualifying, bool):
        raise ValueError("Death verification must be an explicit boolean")
    if event.death_is_nonqualifying and event.death_time_days is None:
        raise ValueError("Verified death requires a death time")
    if event.event_time_days == 0:
        raise ValueError("Day-zero events are prevalent/ambiguous; resolve eligibility first")
    if event.death_time_days is not None:
        if event.event_time_days is not None and event.event_time_days > event.death_time_days:
            raise ValueError("Event cannot occur after death")
        if event.last_followup_days is not None and event.last_followup_days > event.death_time_days:
            raise ValueError("Event-free follow-up cannot extend beyond death")
    # Event/death adjudication may extend beyond a prior routine follow-up visit.
    if event.event_type in {"mi", "stroke"} and event.event_time_days <= horizon_days:
        return EndpointResult(EndpointStatus.POSITIVE, 1)
    if event.death_time_days is not None and event.death_time_days < horizon_days:
        status = EndpointStatus.COMPETING_DEATH if event.death_is_nonqualifying else EndpointStatus.UNKNOWN
        return EndpointResult(status, None)
    if event.last_followup_days is not None and event.last_followup_days >= horizon_days:
        return EndpointResult(EndpointStatus.KNOWN_NEGATIVE, 0)
    return EndpointResult(EndpointStatus.UNKNOWN, None)


def construct_endpoints(records: pd.DataFrame, horizon_days: float = PRIMARY_HORIZON_DAYS) -> pd.DataFrame:
    """Add status and nullable label without converting unresolved outcomes to zero."""
    fields = ("event_type", "event_time_days", "death_time_days", "last_followup_days")
    missing = set(fields) - set(records.columns)
    if missing:
        raise ValueError(f"Missing endpoint metadata: {sorted(missing)}")
    results = []
    for row in records.to_dict("records"):
        values = {key: None if pd.isna(row[key]) else row[key] for key in fields}
        verified = row.get("death_is_nonqualifying", False)
        values["death_is_nonqualifying"] = False if pd.isna(verified) else verified
        results.append(build_endpoint(EventMetadata(**values), horizon_days))
    output = records.copy()
    output["endpoint_status"] = [result.status.value for result in results]
    output["label"] = pd.array([result.label for result in results], dtype="Int64")
    return output
