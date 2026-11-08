"""Cumulative, wave-ascertained self-report endpoint for onboarding audits only.

This is not the frozen 1,826-day adjudicated endpoint. A positive at either
follow-up is retained even if a later response reverses; a negative requires
an explicitly negative final wave and no earlier positive.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def wave_disease(heart_attack: pd.Series, stroke: pd.Series) -> pd.Series:
    if not heart_attack.index.equals(stroke.index):
        raise ValueError("Wave outcome indexes differ")
    valid = heart_attack.isin([0, 1]) | heart_attack.isna()
    valid &= stroke.isin([0, 1]) | stroke.isna()
    if not valid.all():
        raise ValueError("Unmapped wave response; endpoint fails closed")
    result = pd.Series(pd.NA, index=heart_attack.index, dtype="Int64")
    result.loc[(heart_attack == 0) & (stroke == 0)] = 0
    result.loc[(heart_attack == 1) | (stroke == 1)] = 1
    return result


def cumulative_wave_endpoint(intermediate: pd.Series, final: pd.Series) -> pd.Series:
    if not intermediate.index.equals(final.index):
        raise ValueError("Follow-up indexes differ")
    if not (intermediate.dropna().isin([0, 1]).all() and final.dropna().isin([0, 1]).all()):
        raise ValueError("Unmapped follow-up response; endpoint fails closed")
    status = pd.Series("unknown", index=final.index, dtype="string")
    status.loc[(final == 0) & intermediate.ne(1).fillna(True)] = "known_negative"
    status.loc[(intermediate == 1) | (final == 1)] = "positive"
    return status


def month_index(year: pd.Series, month: pd.Series) -> pd.Series:
    y = pd.to_numeric(year, errors="coerce")
    m = pd.to_numeric(month, errors="coerce")
    valid = y.notna() & m.between(1, 12) & (y == np.floor(y)) & (m == np.floor(m))
    out = pd.Series(np.nan, index=year.index, dtype=float)
    out.loc[valid] = y.loc[valid] * 12 + m.loc[valid] - 1
    return out


def chronology_invalid(index: pd.Series, intermediate: pd.Series, final: pd.Series) -> pd.Series:
    """Detect known impossible order without treating an absent wave as a reversal."""
    return ((intermediate.notna() & index.notna() & (intermediate <= index)) |
            (final.notna() & index.notna() & (final <= index)) |
            (intermediate.notna() & final.notna() & (final < intermediate)))
