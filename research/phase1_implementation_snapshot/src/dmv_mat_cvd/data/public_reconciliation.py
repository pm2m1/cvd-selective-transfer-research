"""Aggregate-only public-cohort reconciliation helpers; no model or split access."""
from __future__ import annotations

import pandas as pd


def parse_master_interview_date(values: pd.Series, wave: int) -> tuple[pd.Series, dict]:
    """Parse the documented day/month/year Master strings without date inference."""
    formats = {12: "%d/%m/%Y", 15: "%d/%m/%Y", 18: "%d/%m/%y"}
    if wave not in formats:
        raise ValueError("Only the prespecified 2012, 2015 and 2018 waves are audited")
    text = values.astype("string").str.strip()
    parsed = pd.to_datetime(text, format=formats[wave], errors="coerce")
    invalid = text.notna() & text.ne("") & parsed.isna()
    return parsed, {"valid": int(parsed.notna().sum()),
                    "blank": int((text.isna() | text.eq("")).sum()),
                    "invalid_nonblank": int(invalid.sum())}


def exclude_future_wave_predictors(columns: list[str] | tuple[str, ...]) -> None:
    """Master follow-up fields may be inspected as metadata, never as predictors."""
    forbidden = {"int_date_15", "int_date_18", "tipent_15", "tipent_18",
                 "tipne_15", "tipne_18", "fallecido_15", "fallecido_18",
                 "res_biomarkers_12", "UNHHIDNP"}
    if forbidden.intersection(columns):
        raise ValueError("Master follow-up/identifier fields cannot be predictors")


def sex_agreement(master_sex: pd.Series, harmonized_gender: pd.Series) -> dict:
    """Wave-specific sex versus cross-wave latest-nonmissing gender, aggregate only."""
    valid_master = master_sex.isin([1, 2])
    valid_harmonized = harmonized_gender.isin([1, 2])
    both = valid_master & valid_harmonized
    return {"both_known": int(both.sum()), "agree": int((both & master_sex.eq(harmonized_gender)).sum()),
            "contradict": int((both & master_sex.ne(harmonized_gender)).sum()),
            "master_missing_or_invalid": int((~valid_master).sum()),
            "harmonized_missing_or_invalid": int((~valid_harmonized).sum())}


def harmonized_persistence_violations(intermediate: pd.Series, final: pd.Series) -> int:
    """Diagnostic for the Version-D prior-positive carry-forward rule."""
    if not intermediate.index.equals(final.index):
        raise ValueError("Harmonized waves must be aligned")
    return int((intermediate.eq(1) & final.eq(0)).sum())


def reversal_uncertain(status: pd.Series, reversal: pd.Series,
                       reason: pd.Series) -> pd.Series:
    """Sensitivity: explicit 'never had'/'misdiagnosed' retractions become unknown.

    'No longer has' does not erase a historical event. Missing reasons remain
    uncertain in the clinical report but are not silently reclassified here.
    """
    if not status.index.equals(reversal.index) or not status.index.equals(reason.index):
        raise ValueError("Endpoint/reversal series must be aligned")
    out = status.copy()
    disputed = reason.isin(["never_had", "misdiagnosed"])
    out.loc[reversal.fillna(False) & disputed] = "unknown"
    return out


def eol_binary(values: pd.Series) -> pd.Series:
    """Preserve Version-C Stata special missing codes as unknown, never as no."""
    known_missing = {".q", ".s", ".d", ".r", ".m", ".i", ".x"}
    result = pd.Series(pd.NA, index=values.index, dtype="Int64")
    for position, value in values.items():
        if pd.isna(value) or str(value) in known_missing:
            continue
        if value in (0, 1):
            result.loc[position] = int(value)
        else:
            raise ValueError("Unmapped End-of-Life response code")
    return result


def death_before_core_interview(death_year: pd.Series, death_month: pd.Series,
                                interview: pd.Series) -> pd.Series:
    """Only certify a contradiction when death is in an earlier calendar month."""
    if not (death_year.index.equals(death_month.index) and death_year.index.equals(interview.index)):
        raise ValueError("Chronology series must be aligned")
    year, month = pd.to_numeric(death_year, errors="coerce"), pd.to_numeric(death_month, errors="coerce")
    valid = year.between(1900, 2100) & month.between(1, 12) & interview.notna()
    death_index = year * 12 + month - 1
    interview_index = interview.dt.year * 12 + interview.dt.month - 1
    return valid & death_index.lt(interview_index)


def classify_mhas_observation(status: pd.Series, interview_type_18: pd.Series,
                              died_15: pd.Series, died_18: pd.Series,
                              noninterview_15: pd.Series | None = None,
                              noninterview_18: pd.Series | None = None,
                              eol_death_by_2018: pd.Series | None = None) -> pd.Series:
    """Conservative mutually exclusive categories; zero death flag is not alive proof."""
    if not (status.index.equals(interview_type_18.index)
            and status.index.equals(died_15.index) and status.index.equals(died_18.index)):
        raise ValueError("Observation series must be aligned")
    category = pd.Series("unknown_noninterview", index=status.index, dtype="string")
    death = died_15.eq(1).fillna(False) | died_18.eq(1).fillna(False) | interview_type_18.eq(5).fillna(False)
    if noninterview_15 is not None:
        death |= noninterview_15.eq(7).fillna(False)
    if noninterview_18 is not None:
        death |= noninterview_18.eq(8).fillna(False)
    if eol_death_by_2018 is not None:
        death |= eol_death_by_2018.fillna(False)
    core = interview_type_18.isin([1, 2, 3, 4])
    category.loc[death & status.ne("positive")] = "death_without_reported_event"
    category.loc[status.eq("known_negative") & core & ~death] = "observed_event_free"
    category.loc[status.eq("known_negative") & ~core & ~death] = "ambiguous_negative_without_core"
    category.loc[status.eq("known_negative") & core & death] = "ambiguous_death_and_negative"
    category.loc[status.eq("positive")] = "reported_event"
    return category
