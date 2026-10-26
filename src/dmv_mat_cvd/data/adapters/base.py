"""Local authorized data -> explicitly mapped, harmonized canonical table."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping

import pandas as pd

from ..base import CohortTable
from ..schema import CONTINUOUS, ENDPOINT_FIELDS, PREDICTORS


class CohortAdapter:
    domain = "user_supplied"
    required_mapping = ("participant_id", *PREDICTORS, "index_date", "event_type",
                        "event_time_days", "death_time_days", "last_followup_days")

    def __init__(self, mapping: Mapping[str, str] | None = None, *,
                 converters: Mapping[str, Callable[[pd.Series], pd.Series]] | None = None,
                 units: Mapping[str, str] | None = None,
                 mapping_config: dict | str | Path | None = None,
                 endpoint_crosswalk: dict | str | Path | None = None):
        """mapping is canonical -> raw; converters explicitly reconcile values/units.

        units declares the converter OUTPUT units. Supplying these is an assertion
        by the data steward, not automatic verification of release documentation.
        """
        from ..mapping import mapping_config as load_mapping
        if mapping is not None and mapping_config is not None:
            raise ValueError("Choose external configuration or the legacy explicit mapping interface")
        self.mapping_config = load_mapping(mapping_config) if mapping_config is not None else None
        self.endpoint_crosswalk = load_mapping(endpoint_crosswalk) if endpoint_crosswalk is not None else None
        self.last_audit = None
        self.mapping = dict(mapping or {})
        self.converters = dict(converters or {})
        self.units = dict(units or {})

    def from_frame(self, raw: pd.DataFrame) -> CohortTable:
        if self.mapping_config is not None:
            result = self.dry_run(raw)
            if result.cohort is None:
                raise ValueError("Cohort construction failed; inspect adapter.last_audit")
            return result.cohort
        from ..schema import CANONICAL_UNITS

        missing = set(self.required_mapping) - set(self.mapping)
        if missing:
            raise NotImplementedError(
                f"{self.domain} release-specific column mapping must be supplied after data access. "
                f"Unresolved canonical fields: {sorted(missing)}"
            )
        allowed = {"participant_id", *PREDICTORS, *ENDPOINT_FIELDS}
        if set(self.mapping) - allowed or set(self.converters) - set(self.mapping):
            raise ValueError("Mapping/converters contain unsupported canonical fields")
        if any(self.units.get(name) != CANONICAL_UNITS[name] for name in CONTINUOUS):
            raise ValueError("Explicit canonical output units are required for all continuous predictors")
        if not raw.columns.is_unique or set(self.mapping.values()) - set(raw.columns):
            raise ValueError("Raw table has missing mapped columns or duplicate column names")
        frame = pd.DataFrame({canonical: raw[column].copy() for canonical, column in self.mapping.items()})
        for name, convert in self.converters.items():
            frame[name] = convert(frame[name])
        return CohortTable(frame, self.domain)

    def load_csv(self, path: str | Path, **read_options) -> CohortTable:
        """No download or discovery; caller supplies a local authorized file."""
        return self.from_frame(pd.read_csv(path, **read_options))

    def dry_run(self, raw: pd.DataFrame, *, manifest=None, release_directory=None, policy=None, access_phase="pre_split"):
        from ..cohort_construction import construct_cohort
        if self.mapping_config is None:
            raise ValueError("Dry-run requires an external mapping configuration")
        result = construct_cohort(raw, self.mapping_config, self.endpoint_crosswalk, domain=self.domain,
                                  manifest=manifest, release_directory=release_directory,
                                  policy=policy, access_phase=access_phase)
        self.last_audit = result.report
        return result
