"""Provisional HAALSI/MHAS wave-data onboarding; never fits or trains a model.

Column declarations live in external JSON reviewed against the supplied audit.
The historical complete-case calculation is reproduced as a *reference audit*,
not substituted for the frozen ten-predictor/1,826-day method contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .base import CohortTable
from .schema import PREDICTORS, SCHEMA_VERSION, VIEW_FEATURES
from .wave_endpoint import chronology_invalid, cumulative_wave_endpoint, month_index, wave_disease
from ..method import METHOD_SPEC_VERSION


def _number(series: pd.Series, missing_codes: list[int]) -> pd.Series:
    value = pd.to_numeric(series, errors="coerce")
    unknown = series.notna() & value.isna()
    if unknown.any():
        raise ValueError("Unmapped nonnumeric measurement; raw values omitted")
    return value.mask(value.isin(missing_codes))


def _binary(series: pd.Series, yes: int, no: int, missing_codes: list[int]) -> pd.Series:
    value = _number(series, missing_codes)
    if not value.dropna().isin([yes, no]).all():
        raise ValueError("Unmapped binary category; raw values omitted")
    out = pd.Series(pd.NA, index=series.index, dtype="Int64")
    out.loc[value == yes] = 1
    out.loc[value == no] = 0
    return out


def _fingerprint_ids(ids: pd.Series) -> str:
    """One cohort-level digest; never write identifiers or per-person hashes."""
    content = "\n".join(sorted(ids.astype(str)))
    return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class WaveAudit:
    cohort: CohortTable
    report: dict


class WaveCohortAdapter:
    cohort_name = ""

    def __init__(self, mapping: dict):
        if mapping.get("cohort_name") != self.cohort_name:
            raise ValueError("Mapping cohort does not match adapter")
        if mapping.get("mapping_version") != "wave-onboarding-m5-v1":
            raise ValueError("Explicit M5 mapping version required")
        self.mapping = mapping

    def _required(self) -> set[str]:
        fields = self.mapping.get("fields", {})
        required = {"participant_id", "age", "sex", "sbp", "dbp", "bmi", "fasting_glucose",
                    "total_cholesterol", "hdl", "smoke_ever", "smoke_now", "antihypertensive_treatment",
                    "diabetes_reference", "baseline_heart_attack", "baseline_stroke",
                    "intermediate_heart_attack", "intermediate_stroke", "final_heart_attack", "final_stroke",
                    "index_year", "index_month", "intermediate_year", "intermediate_month", "final_year", "final_month"}
        if set(fields) != required:
            raise ValueError("Mapping must declare every canonical and audit field exactly once")
        mapped = [value for value in fields.values() if value is not None]
        if len(mapped) != len(set(mapped)):
            raise ValueError("A raw column is mapped to multiple fields")
        for name, item in fields.items():
            if item is not None and (not isinstance(item, str) or not item.strip()):
                raise ValueError(f"{name}: invalid raw column declaration")
        codes = self.mapping.get("binary_codes", {})
        sex_codes = self.mapping.get("sex_codes", {})
        if codes.get("yes") == codes.get("no") or sex_codes.get("male") == sex_codes.get("female"):
            raise ValueError("Binary/sex category codes must be distinct")
        if any(code in self.mapping.get("missing_codes", []) for code in
               (codes.get("yes"), codes.get("no"), sex_codes.get("male"), sex_codes.get("female"))):
            raise ValueError("Missing codes overlap declared categories")
        columns = {value for value in fields.values() if value is not None}
        if self.mapping.get("hypertension_field"):
            columns.add(self.mapping["hypertension_field"])
        return columns

    def load(self, root: str | Path) -> tuple[pd.DataFrame, dict]:
        """Read only declared Stata columns from the supplied local release root."""
        self._required()
        path = (Path(root) / self.mapping["files"]["main"]).resolve()
        if not path.is_relative_to(Path(root).resolve()) or not path.is_file():
            raise ValueError("Mapped release file unavailable or outside data root")
        reader = pd.read_stata(path, iterator=True, convert_categoricals=False)
        available = set(reader.variable_labels())
        columns = self._required()
        if self.mapping.get("join") == "biomarker_anchor":
            columns -= {self.mapping["fields"]["total_cholesterol"], self.mapping["fields"]["hdl"]}
            columns.add(self.mapping["join_main_id"])
        missing = columns - available
        if missing:
            raise ValueError(f"Mapped main columns unavailable: {sorted(missing)}")
        main = pd.read_stata(path, columns=sorted(columns), convert_categoricals=False)
        if self.mapping.get("join") != "biomarker_anchor":
            return main, {"raw_main_rows": len(main), "duplicate_main_ids": int(main[self.mapping["fields"]["participant_id"]].duplicated().sum())}
        bio_path = (Path(root) / self.mapping["files"]["biomarker"]).resolve()
        if not bio_path.is_relative_to(Path(root).resolve()) or not bio_path.is_file():
            raise ValueError("Mapped biomarker file unavailable or outside data root")
        bio_columns = {self.mapping["bio_household_id"], self.mapping["bio_person_number"],
                       self.mapping["fields"]["total_cholesterol"], self.mapping["fields"]["hdl"]}
        bio_available = set(pd.read_stata(bio_path, iterator=True, convert_categoricals=False).variable_labels())
        if bio_columns - bio_available:
            raise ValueError(f"Mapped biomarker columns unavailable: {sorted(bio_columns - bio_available)}")
        bio = pd.read_stata(bio_path, columns=sorted(bio_columns), convert_categoricals=False)
        household = pd.to_numeric(bio[self.mapping["bio_household_id"]], errors="coerce")
        person = pd.to_numeric(bio[self.mapping["bio_person_number"]], errors="coerce")
        if household.isna().any() or person.isna().any() or not (household == np.floor(household)).all() or not (person == np.floor(person)).all():
            raise ValueError("Biomarker join key is incomplete or nonintegral")
        # Stata stores the components in narrow integer dtypes; cast *before*
        # multiplication so the join key cannot overflow int16 arithmetic.
        bio["__join_id"] = household.astype("int64") * 100 + person.astype("int64")
        main["__join_id"] = pd.to_numeric(main[self.mapping["join_main_id"]], errors="raise").astype("int64")
        if bio["__join_id"].duplicated().any() or main["__join_id"].duplicated().any():
            raise ValueError("Duplicate participant join key; no silent deduplication")
        joined = bio.merge(main, on="__join_id", how="left", validate="one_to_one", indicator=True)
        unmatched = int(joined["_merge"].ne("both").sum())
        if unmatched:
            raise ValueError("Biomarker rows without unique main record")
        joined = joined.drop(columns=["_merge"])
        eol_relative = self.mapping["files"].get("eol")
        eol_counts = {}
        if eol_relative:
            eol_path = (Path(root) / eol_relative).resolve()
            if not eol_path.is_relative_to(Path(root).resolve()) or not eol_path.is_file():
                raise ValueError("Mapped end-of-life file unavailable or outside data root")
            eol = pd.read_stata(eol_path, columns=[self.mapping["eol_id"],
                self.mapping["eol_year"], self.mapping["eol_month"]], convert_categoricals=False)
            eol["__join_id"] = pd.to_numeric(eol[self.mapping["eol_id"]], errors="coerce")
            if eol["__join_id"].isna().any() or eol["__join_id"].duplicated().any():
                raise ValueError("End-of-life IDs missing/duplicated; no silent deduplication")
            eol = eol.rename(columns={self.mapping["eol_year"]: "__eol_year",
                                      self.mapping["eol_month"]: "__eol_month"})
            joined = joined.merge(eol[["__join_id", "__eol_year", "__eol_month"]],
                                  on="__join_id", how="left", validate="one_to_one", indicator="__eol_merge")
            joined["__has_eol"] = joined["__eol_merge"].eq("both")
            eol_counts = {"raw_eol_rows": len(eol), "biomarker_with_eol_record": int(joined["__has_eol"].sum())}
            joined = joined.drop(columns=["__eol_merge"])
        return joined, {"raw_main_rows": len(main), "raw_biomarker_rows": len(bio),
                                                 "matched_biomarker_rows": len(joined), "unmatched_biomarker_rows": unmatched,
                                                 "duplicate_main_ids": 0, "duplicate_biomarker_ids": 0, **eol_counts}


    def audit(self, raw: pd.DataFrame, *, load_accounting: dict | None = None,
              access_phase: str = "pre_split") -> WaveAudit:
        if access_phase != "pre_split":
            raise ValueError("Wave cohort audit cannot inspect a locked target-test partition")
        required = self._required()
        if not raw.columns.is_unique or required - set(raw.columns):
            raise ValueError(f"Mapped raw columns missing or duplicated: {sorted(required - set(raw.columns))}")
        f = self.mapping["fields"]
        codes = self.mapping["binary_codes"]
        missing_codes = self.mapping["missing_codes"]
        def numeric(name: str) -> pd.Series:
            return _number(raw[f[name]], missing_codes) if f[name] else pd.Series(np.nan, index=raw.index)
        def binary(name: str) -> pd.Series:
            return _binary(raw[f[name]], codes["yes"], codes["no"], missing_codes)
        ids = raw[f["participant_id"]]
        if ids.isna().any() or ids.astype(str).str.strip().eq("").any() or ids.astype(str).duplicated().any():
            raise ValueError("Participant IDs missing or duplicated; no silent deduplication")
        baseline = wave_disease(binary("baseline_heart_attack"), binary("baseline_stroke"))
        middle = wave_disease(binary("intermediate_heart_attack"), binary("intermediate_stroke"))
        final = wave_disease(binary("final_heart_attack"), binary("final_stroke"))
        status = cumulative_wave_endpoint(middle, final)
        ix = month_index(numeric("index_year"), numeric("index_month"))
        mid = month_index(numeric("intermediate_year"), numeric("intermediate_month"))
        end = month_index(numeric("final_year"), numeric("final_month"))
        invalid = chronology_invalid(ix, mid, end)
        free = baseline == 0
        sex_codes = self.mapping["sex_codes"]
        sex_raw = numeric("sex")
        if not sex_raw.dropna().isin([sex_codes["male"], sex_codes["female"]]).all():
            raise ValueError("Unmapped sex category")
        sex = pd.Series("unknown", index=raw.index)
        sex.loc[sex_raw == sex_codes["male"]] = "male"
        sex.loc[sex_raw == sex_codes["female"]] = "female"
        ever, now = binary("smoke_ever"), binary("smoke_now")
        smoking = pd.Series("unknown", index=raw.index)
        smoking.loc[ever == 0] = "never"
        smoking.loc[(ever == 1) & (now == 0)] = "former"
        smoking.loc[(ever == 1) & (now == 1)] = "current"
        smoking_contradictions = int(((ever == 0) & (now == 1)).sum())
        if f["antihypertensive_treatment"]:
            treatment = binary("antihypertensive_treatment")
        else:
            raise ValueError("Treatment mapping missing")
        if self.mapping.get("hypertension_field"):
            htn = _binary(raw[self.mapping["hypertension_field"]], codes["yes"], codes["no"], missing_codes)
            treatment = treatment.copy()
            treatment.loc[(htn == 0) & treatment.isna()] = 0
            treatment_conflicts = int(((htn == 0) & (treatment == 1)).sum())
        else:
            treatment_conflicts = 0
        medication = pd.Series("unknown", index=raw.index)
        medication.loc[treatment == 0] = "no"
        medication.loc[treatment == 1] = "yes"
        unit_factors = self.mapping["unit_factors"]
        for name in ("age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl",
                     *(("fasting_glucose",) if f["fasting_glucose"] else ())):
            factor = unit_factors.get(name)
            if not isinstance(factor, (int, float)) or not np.isfinite(factor) or factor <= 0:
                raise ValueError(f"{name}: explicit positive unit conversion factor required")
        frame = pd.DataFrame({"participant_id": self.mapping["id_namespace"] + ":" + ids.astype(str),
                              "age": numeric("age") * unit_factors["age"], "sex": sex,
                              "sbp": numeric("sbp") * unit_factors["sbp"],
                              "dbp": numeric("dbp") * unit_factors["dbp"],
                              "bmi": numeric("bmi") * unit_factors["bmi"],
                              "fasting_glucose": numeric("fasting_glucose") * unit_factors["fasting_glucose"]
                                  if f["fasting_glucose"] else numeric("fasting_glucose"),
                              "total_cholesterol": numeric("total_cholesterol") * unit_factors["total_cholesterol"],
                              "hdl": numeric("hdl") * unit_factors["hdl"],
                              "smoking_status": smoking, "antihypertensive_treatment": medication})
        # A year/month interview is never disguised as a verified day-level event date.
        frame["index_date"] = pd.NaT
        valid_index = ix.notna()
        frame.loc[valid_index, "index_date"] = pd.to_datetime(dict(year=(ix[valid_index] // 12).astype(int),
            month=(ix[valid_index] % 12 + 1).astype(int), day=1)).to_numpy()
        frame["event_type"] = pd.NA
        frame["event_time_days"] = np.nan
        frame["death_time_days"] = np.nan
        frame["last_followup_days"] = np.nan
        frame["endpoint_status"] = status
        frame.loc[invalid, "endpoint_status"] = "unknown"
        frame["label"] = pd.array(frame.endpoint_status.map({"positive": 1, "known_negative": 0}), dtype="Int64")
        candidate = frame.loc[free.fillna(False)].copy()
        cohort = CohortTable(candidate, self.cohort_name)
        # Reproduce the prior script literally as a separate audit. Its numeric
        # completeness accepted finite negative sentinel values in continuous
        # measurements; the canonical table above deliberately masks them.
        # This comparison is never used to decide canonical eligibility.
        reference_numeric = pd.DataFrame({name: pd.to_numeric(raw[f[name]], errors="coerce")
            for name in ("age", "sex", "sbp", "dbp", "bmi", "total_cholesterol", "hdl", "diabetes_reference")})
        reference_numeric["smoking"] = smoking.where(smoking != "unknown")
        reference_numeric["treatment"] = medication.where(medication != "unknown")
        complete_reference = reference_numeric.notna().all(axis=1)
        reference_mask = free.fillna(False) & complete_reference & status.ne("unknown")
        observed = status.loc[reference_mask]
        sentinel_reference = pd.DataFrame({name: pd.to_numeric(raw[f[name]], errors="coerce").isin(missing_codes)
            for name in ("age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl")}).any(axis=1)
        reference_without_sentinels = reference_mask & ~sentinel_reference
        followup = (end - ix).loc[free.fillna(False) & final.notna()].dropna()
        diagnostics = {
            "intermediate_wave_known": int((free.fillna(False) & middle.notna()).sum()),
            "final_wave_known": int((free.fillna(False) & final.notna()).sum()),
            "intermediate_positive": int((free.fillna(False) & (middle == 1)).sum()),
            "intermediate_positive_final_negative": int((free.fillna(False) & (middle == 1) & (final == 0)).sum()),
            "intermediate_positive_final_missing": int((free.fillna(False) & (middle == 1) & final.isna()).sum()),
            "intermediate_negative_final_positive": int((free.fillna(False) & (middle == 0) & (final == 1)).sum()),
            "final_wave_missing": int((free.fillna(False) & final.isna()).sum()),
            "final_wave_missing_no_prior_positive": int((free.fillna(False) & final.isna() & middle.ne(1).fillna(True)).sum()),
            "baseline_free_unknown_cumulative": int((free.fillna(False) & status.eq("unknown")).sum()),
            "invalid_chronology": int((free.fillna(False) & invalid).sum()),
            "missing_index_month": int((free.fillna(False) & ix.isna()).sum()),
            "missing_final_interview_month": int((free.fillna(False) & end.isna()).sum()),
            "final_interview_before_60_months": int((free.fillna(False) & end.notna() & ix.notna() & ((end - ix) < 60)).sum()),
            "followup_months_median": float(followup.median()) if len(followup) else None,
            "followup_months_q1": float(followup.quantile(.25)) if len(followup) else None,
            "followup_months_q3": float(followup.quantile(.75)) if len(followup) else None,
            "smoking_contradictions": smoking_contradictions,
            "treatment_hypertension_contradictions": treatment_conflicts,
            "historical_eligible_with_numeric_sentinel": int((reference_mask & sentinel_reference).sum()),
        }
        if "__eol_year" in raw:
            death_month = month_index(_number(raw["__eol_year"], missing_codes),
                                      _number(raw["__eol_month"], missing_codes))
            duration = death_month - ix
            diagnostics.update({
                "baseline_free_with_eol_record": int((free.fillna(False) & raw["__has_eol"]).sum()),
                "baseline_free_with_valid_eol_death_month": int((free.fillna(False) & death_month.notna()).sum()),
                "baseline_free_final_missing_with_eol_record": int((free.fillna(False) & final.isna() & raw["__has_eol"]).sum()),
                "baseline_free_death_month_within_60": int((free.fillna(False) & duration.between(0, 60)).sum()),
                "note": "EOL month is diagnostic only; death cause/event adjudication is not established."})
        available = {name: f[name] is not None for name in PREDICTORS if name in f}
        available["smoking_status"] = bool(f["smoke_ever"] and f["smoke_now"])
        available["antihypertensive_treatment"] = bool(f["antihypertensive_treatment"])
        gates = {
            "mapped_columns_and_unique_ids": True,
            "all_five_view_fields_available": all(available.values()),
            "baseline_predictor_timing_verified": all(self.mapping["predictor_timing"].get(p) == "baseline_verified" for p in PREDICTORS),
            "fasting_glucose_verified": f["fasting_glucose"] is not None and self.mapping.get("fasting_glucose_verified") is True,
            "exact_1826_day_first_event_ascertainment": False,
            "death_and_attrition_ascertainment_verified": False,
            "release_manifest_complete": False,
            "cohort_matches_frozen_aric_mesa_primary": False,
            "no_target_test_preprocessing": True,
        }
        counts = {"raw_rows": len(raw), "baseline_known": int(baseline.notna().sum()),
                  "baseline_free": int(free.sum()), "baseline_positive": int((baseline == 1).sum()),
                  "baseline_unknown": int(baseline.isna().sum()),
                  "complete_historical_reference_predictors": int((free.fillna(False) & complete_reference).sum()),
                  "historical_reference_eligible": int(reference_mask.sum()),
                  "historical_reference_events": int((observed == "positive").sum()),
                  "historical_reference_without_numeric_sentinel": int(reference_without_sentinels.sum()),
                  "historical_reference_without_numeric_sentinel_events": int((reference_without_sentinels & status.eq("positive")).sum()),
                  "historical_reference_prevalence": float((observed == "positive").mean()) if len(observed) else None,
                  "canonical_baseline_free": len(cohort),
                  "canonical_known_cumulative": int(cohort.records.label.notna().sum()),
                  "canonical_missing_by_predictor": {p: int(cohort.records[p].isna().sum() +
                      (cohort.records[p].eq("unknown").sum() if p in ("sex", "smoking_status", "antihypertensive_treatment") else 0)) for p in PREDICTORS},
                  "complete_canonical_predictors": int(cohort.predictors().notna().all(axis=1).sum())}
        report = {"report_version": "wave-readiness-m5-v1", "cohort_name": self.cohort_name,
                  "method_spec_version": METHOD_SPEC_VERSION, "schema_version": SCHEMA_VERSION,
                  "mapping_version": self.mapping["mapping_version"], "mapping_sha256": hashlib.sha256(json.dumps(self.mapping,sort_keys=True).encode()).hexdigest(),
                  "ready": all(gates.values()), "gates": gates, "counts": counts, "diagnostics": diagnostics,
                  "load_accounting": load_accounting or {}, "view_fields": {k: list(v) for k,v in VIEW_FEATURES.items()},
                  "participant_set_digest": _fingerprint_ids(cohort.records.participant_id),
                  "statistical_preprocessing_performed": False, "training_performed": False,
                  "endpoint_definition": "cumulative doctor-reported heart attack or stroke at intermediate/final waves; not 1826-day verified incidence",
                  "reference_count_definition": "baseline free; nine non-glucose canonical predictors plus diabetes complete; cumulative wave outcome observed",
                  "limitations": ["No exact event date or verified first event within 1826 days",
                                  "Historical reference completeness includes diabetes and omits fasting glucose",
                                  "Self-report reversals and missing final waves require sensitivity analyses",
                                  "Death, attrition and unequal follow-up are not resolved by wave-positive logic"]}
        return WaveAudit(cohort, report)


class HAALSIAdapter(WaveCohortAdapter):
    cohort_name = "HAALSI"


class MHASAdapter(WaveCohortAdapter):
    cohort_name = "MHAS"

def join_mhas_master_followup(biomarker_cohort: pd.DataFrame, master: pd.DataFrame, *,
                              additional_metadata: tuple[str, ...] = ()) -> tuple[pd.DataFrame, dict]:
    """Validate the 2024 Master join to the existing 2012 biomarker anchor.

    The Master guide uses a padded five-character household plus three-character
    person string, whereas the harmonized/EOL numeric key is household*100+person.
    This function checks both encodings and joins on the documented components.
    Follow-up columns remain audit metadata; they are never model predictors.
    """
    allowed_metadata = {"tipent_12", "tipne_12"}
    if set(additional_metadata) - allowed_metadata:
        raise ValueError("Only declared 2012 interview-status metadata may be joined")
    required = {"cunicah", "np", "UNHHIDNP", "int_date_12", "sex_12",
                "res_biomarkers_12", "tipne_15", "tipent_15", "int_date_15",
                "fallecido_15", "tipne_18", "tipent_18", "int_date_18", "fallecido_18"}
    required.update(additional_metadata)
    if required - set(master) or not master.columns.is_unique:
        raise ValueError(f"Master follow-up columns missing/duplicated: {sorted(required - set(master))}")
    if "__join_id" not in biomarker_cohort or biomarker_cohort["__join_id"].isna().any():
        raise ValueError("Biomarker anchor must have a complete validated join ID")
    household = pd.to_numeric(master["cunicah"], errors="coerce")
    person = pd.to_numeric(master["np"], errors="coerce")
    if (household.isna().any() or person.isna().any() or
            not (household == np.floor(household)).all() or
            not (person == np.floor(person)).all() or
            not household.between(0, 99999).all() or not person.between(0, 999).all()):
        raise ValueError("Master household/person components are invalid")
    household, person = household.astype("int64"), person.astype("int64")
    padded = household.astype(str).str.zfill(5) + person.astype(str).str.zfill(3)
    if not padded.eq(master["UNHHIDNP"].astype(str)).all():
        raise ValueError("Master padded string identifier conflicts with household/person components")
    followup = master.loc[:, sorted(required)].copy()
    followup["__join_id"] = household * 100 + person
    if followup["__join_id"].duplicated().any() or biomarker_cohort["__join_id"].duplicated().any():
        raise ValueError("Duplicate Master/biomarker participant join key")
    # Do not copy alternative raw ID encodings into the joined audit frame.
    followup = followup.drop(columns=["cunicah", "np", "UNHHIDNP"])
    joined = biomarker_cohort.merge(followup, on="__join_id", how="left",
                                    validate="one_to_one", indicator="__master_match")
    matched = int(joined["__master_match"].eq("both").sum())
    report = {"master_rows": len(master), "biomarker_rows": len(biomarker_cohort),
              "matched": matched, "unmatched_biomarker": len(joined) - matched,
              "master_not_in_biomarker": len(master) - matched,
              "duplicate_master_ids": 0, "duplicate_biomarker_ids": 0,
              "padded_id_conflicts": 0}
    if report["unmatched_biomarker"]:
        raise ValueError("Biomarker participants missing from Master follow-up")
    return joined.drop(columns=["__master_match"]), report

