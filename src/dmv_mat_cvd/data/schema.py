"""Locked raw predictor contract, independent of any cohort release."""
from __future__ import annotations

import numpy as np
import pandas as pd

SCHEMA_VERSION = "cvd-primary-v1"
VIEW_FEATURES = {
    "background": ("age", "sex"),
    "haemodynamic": ("sbp", "dbp"),
    "metabolic": ("bmi", "fasting_glucose", "total_cholesterol", "hdl"),
    "behaviour": ("smoking_status",),
    "comorbidity_medication": ("antihypertensive_treatment",),
}
PREDICTORS = tuple(column for columns in VIEW_FEATURES.values() for column in columns)
CONTINUOUS = ("age", "sbp", "dbp", "bmi", "fasting_glucose", "total_cholesterol", "hdl")
# These are analysis categories, not guesses about raw ARIC/MESA coding.
# Recorded sex: female / male, with explicit unknown for missing/unmapped values.
CATEGORIES = {
    "sex": ("female", "male"),
    "smoking_status": ("never", "former", "current"),
    "antihypertensive_treatment": ("no", "yes"),
}
CANONICAL_UNITS = {"age": "years", "sbp": "mmHg", "dbp": "mmHg", "bmi": "kg/m^2",
                   "fasting_glucose": "mg/dL", "total_cholesterol": "mg/dL", "hdl": "mg/dL"}
ENDPOINT_FIELDS = ("index_date", "event_type", "event_time_days", "death_time_days",
                   "last_followup_days", "endpoint_status", "followup_state",
                   "death_is_nonqualifying", "label")


def validate_table(table: pd.DataFrame) -> None:
    if not table.columns.is_unique:
        raise ValueError("Duplicate column names are not permitted")
    missing = set(("participant_id", *PREDICTORS)) - set(table.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if table.empty or table.participant_id.isna().any():
        raise ValueError("Cohort must be nonempty with nonmissing participant_id")
    if table.participant_id.astype(str).str.strip().eq("").any():
        raise ValueError("participant_id must not be blank")
    for name in CONTINUOUS:
        try:
            values = pd.to_numeric(table[name], errors="raise").to_numpy(dtype=float)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{name} must be numeric in canonical units") from exc
        if np.isinf(values).any():
            raise ValueError(f"{name} contains infinite values")
    for name, categories in CATEGORIES.items():
        valid = table[name].isna() | table[name].isin((*categories, "unknown"))
        if not valid.all():
            raise ValueError(f"{name}: supply explicit canonical category mapping")
    if "label" in table:
        labels = table.label.dropna()
        if not labels.isin([0, 1]).all():
            raise ValueError("Observed labels must be binary 0/1")
    if "endpoint_status" in table:
        states = {"positive", "known_negative", "competing_death", "unknown"}
        if not table.endpoint_status.dropna().isin(states).all():
            raise ValueError("Invalid endpoint_status")
        if "label" in table:
            for status, label in zip(table.endpoint_status, table.label):
                if pd.isna(status):
                    continue
                expected = {"positive": 1, "known_negative": 0}.get(status)
                if (expected is None and pd.notna(label)) or (
                    expected is not None and (pd.isna(label) or label != expected)
                ):
                    raise ValueError("label disagrees with endpoint_status")
