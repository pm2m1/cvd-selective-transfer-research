"""Pre-model, aggregate-only audit for the *proposed* public wave protocol.

This module does not modify the frozen ARIC/MESA schema or make a cohort ready.
Stata value labels, rather than a blanket negative-value rule, identify special
missing codes. Participant rows are returned only in memory for audit tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from .real_cohorts import HAALSIAdapter, MHASAdapter
from .wave_endpoint import chronology_invalid, cumulative_wave_endpoint, month_index, wave_disease

PUBLIC_PROTOCOL_VERSION = "public-haalsi-mhas-proposed-v1"
PUBLIC_SCHEMA_VERSION = "cvd-public-wave-proposed-v1"
PUBLIC_VIEWS = {
    "background": ("age", "sex"),
    "haemodynamic": ("sbp", "dbp"),
    "metabolic": ("bmi", "total_cholesterol", "hdl"),
    "behaviour": ("smoking_status",),
    "comorbidity_medication": ("diabetes", "antihypertensive_treatment"),
}
PUBLIC_PREDICTORS = tuple(x for view in PUBLIC_VIEWS.values() for x in view)
SPECIAL_LABELS = (".e = empty", ".d = don't know", ".r = refused")


def embedded_missing_codes(value_labels: dict, fields: dict) -> dict[str, list[int]]:
    """Use only release-embedded, explicitly labelled special codes per field."""
    result = {}
    for canonical, raw_name in fields.items():
        if raw_name is None:
            continue
        labels = value_labels.get(raw_name, {})
        result[canonical] = sorted(int(code) for code, label in labels.items()
                                   if str(label).strip().lower().startswith(SPECIAL_LABELS))
    return result


def _numeric(raw: pd.DataFrame, fields: dict, codes: dict, name: str) -> pd.Series:
    series = raw[fields[name]]
    number = pd.to_numeric(series, errors="coerce")
    if (series.notna() & number.isna()).any():
        raise ValueError(f"Unmapped nonnumeric {name}")
    return number.mask(number.isin(codes.get(name, [])))


def _binary(raw: pd.DataFrame, fields: dict, codes: dict, name: str, yes: int, no: int) -> pd.Series:
    number = _numeric(raw, fields, codes, name)
    if not number.dropna().isin((yes, no)).all():
        raise ValueError(f"Unmapped response category in {name}")
    out = pd.Series(pd.NA, index=raw.index, dtype="Int64")
    out.loc[number == yes] = 1
    out.loc[number == no] = 0
    return out


def _duration_summary(values: pd.Series) -> dict:
    good = values.dropna()
    return {"observed_n": int(len(good)), "median_months": float(good.median()) if len(good) else None,
            "q1_months": float(good.quantile(.25)) if len(good) else None,
            "q3_months": float(good.quantile(.75)) if len(good) else None,
            "under_60_months": int((good < 60).sum())}


@dataclass(frozen=True)
class PublicAudit:
    canonical: pd.DataFrame
    report: dict

    def views(self) -> dict[str, pd.DataFrame]:
        return {name: self.canonical.loc[:, list(columns)].copy()
                for name, columns in PUBLIC_VIEWS.items()}


def split_public_target(canonical: pd.DataFrame, *, seed: int, test_fraction: float = .25,
                        validation_fraction: float = .2) -> dict[str, pd.DataFrame]:
    """Prospective in-memory participant split; never invoked by the readiness audit.

    Scientific approval, a persistent publication lock and an event-budget plan
    are prerequisites to using this on the real target cohort.
    """
    if not (0 < test_fraction < 1 and 0 < validation_fraction < 1):
        raise ValueError("Split fractions must be in (0,1)")
    if "participant_id" not in canonical or canonical.participant_id.isna().any() or canonical.participant_id.duplicated().any():
        raise ValueError("Unique participant IDs required")
    n = len(canonical)
    if n < 3:
        raise ValueError("At least three participants required")
    order = np.random.default_rng(seed).permutation(n)
    n_test = max(1, int(round(n * test_fraction)))
    n_validation = max(1, int(round((n - n_test) * validation_fraction)))
    if n_test + n_validation >= n:
        raise ValueError("Split fractions leave no adaptation participants")
    positions = {"test": order[:n_test], "validation": order[n_test:n_test + n_validation],
                 "adaptation": order[n_test + n_validation:]}
    return {name: canonical.iloc[index].copy() for name, index in positions.items()}


def audit_public_cohort(raw: pd.DataFrame, mapping: dict, *, value_labels: dict,
                        load_accounting: dict | None = None,
                        corrected_intermediate_stroke: pd.Series | None = None,
                        include_diabetes: bool = True) -> PublicAudit:
    """Construct a proposed complete-case wave cohort without fitting anything."""
    cohort = mapping["cohort_name"]
    if cohort not in {"HAALSI", "MHAS"}:
        raise ValueError("Only declared HAALSI/MHAS public audits are supported")
    fields = mapping["fields"]
    codes = embedded_missing_codes(value_labels, fields)
    yes, no = mapping["binary_codes"]["yes"], mapping["binary_codes"]["no"]
    ids = raw[fields["participant_id"]]
    if ids.isna().any() or ids.astype(str).duplicated().any():
        raise ValueError("Missing/duplicate participant IDs")
    binary = lambda name: _binary(raw, fields, codes, name, yes, no)
    num = lambda name: _numeric(raw, fields, codes, name)

    baseline = wave_disease(binary("baseline_heart_attack"), binary("baseline_stroke"))
    intermediate = wave_disease(binary("intermediate_heart_attack"), binary("intermediate_stroke"))
    final = wave_disease(binary("final_heart_attack"), binary("final_stroke"))
    cumulative = cumulative_wave_endpoint(intermediate, final)
    historical_cumulative = cumulative.copy()
    final_only = pd.Series("unknown", index=raw.index, dtype="string")
    final_only.loc[final == 0] = "known_negative"
    final_only.loc[final == 1] = "positive"
    both = pd.Series("unknown", index=raw.index, dtype="string")
    both.loc[(intermediate == 0) & (final == 0)] = "known_negative"
    both.loc[intermediate.notna() & final.notna() & ((intermediate == 1) | (final == 1))] = "positive"

    index_month = month_index(num("index_year"), num("index_month"))
    mid_month = month_index(num("intermediate_year"), num("intermediate_month"))
    final_month = month_index(num("final_year"), num("final_month"))
    invalid_chronology = chronology_invalid(index_month, mid_month, final_month)
    death_before_negative_final = pd.Series(False, index=raw.index)
    if "__has_eol" in raw:
        death_month = month_index(pd.to_numeric(raw["__eol_year"], errors="coerce"),
                                  pd.to_numeric(raw["__eol_month"], errors="coerce"))
        death_before_negative_final = (death_month.notna() & final_month.notna() &
                                       (death_month < final_month) & (final == 0) &
                                       intermediate.ne(1).fillna(True))
    for status in (cumulative, final_only, both):
        status.loc[invalid_chronology] = "unknown"
        status.loc[death_before_negative_final] = "unknown"

    sex_num = num("sex")
    male, female = mapping["sex_codes"]["male"], mapping["sex_codes"]["female"]
    if not sex_num.dropna().isin((male, female)).all():
        raise ValueError("Unmapped sex category")
    sex = pd.Series(pd.NA, index=raw.index, dtype="string")
    sex.loc[sex_num == male] = "male"
    sex.loc[sex_num == female] = "female"
    ever, now = binary("smoke_ever"), binary("smoke_now")
    smoking = pd.Series(pd.NA, index=raw.index, dtype="string")
    smoking.loc[ever == 0] = "never"
    smoking.loc[(ever == 1) & (now == 0)] = "former"
    smoking.loc[(ever == 1) & (now == 1)] = "current"
    if ((ever == 0) & (now == 1)).any():
        raise ValueError("Contradictory smoking responses")
    diabetes = (binary("diabetes_reference").map({0: "no", 1: "yes"}).astype("string")
                if include_diabetes else pd.Series(pd.NA, index=raw.index, dtype="string"))
    treatment = binary("antihypertensive_treatment")
    # The historical HAALSI questionnaire route leaves medication blank when
    # hypertension is denied. This is a *proposed* derivation requiring review.
    if mapping.get("hypertension_field"):
        htn_name = mapping["hypertension_field"]
        htn_codes = {"hypertension": sorted(int(k) for k, v in value_labels.get(htn_name, {}).items()
                                           if str(v).strip().lower().startswith(SPECIAL_LABELS))}
        htn = _binary(raw, {"hypertension": htn_name}, htn_codes, "hypertension", yes, no)
        treatment.loc[(htn == 0) & treatment.isna()] = 0
    medication = treatment.map({0: "no", 1: "yes"}).astype("string")

    factors = mapping["unit_factors"]
    predictors = pd.DataFrame({
        "age": num("age") * factors["age"], "sex": sex,
        "sbp": num("sbp") * factors["sbp"], "dbp": num("dbp") * factors["dbp"],
        "bmi": num("bmi") * factors["bmi"],
        "total_cholesterol": num("total_cholesterol") * factors["total_cholesterol"],
        "hdl": num("hdl") * factors["hdl"], "smoking_status": smoking,
        "diabetes": diabetes, "antihypertensive_treatment": medication,
    })
    if set(predictors.columns) != set(PUBLIC_PREDICTORS):
        raise AssertionError("Public predictor schema drift")
    continuous = ("age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl")
    invalid_numeric = pd.Series(False, index=raw.index)
    for name in continuous:
        invalid_numeric |= predictors[name].notna() & ((predictors[name] <= 0) | ~np.isfinite(predictors[name]))
    invalid_numeric |= predictors.sbp.notna() & predictors.dbp.notna() & (predictors.sbp <= predictors.dbp)
    # No speculative upper truncation: extreme but positive values are flags.
    active_predictors = (PUBLIC_PREDICTORS if include_diabetes else
                         tuple(name for name in PUBLIC_PREDICTORS if name != "diabetes"))
    completeness = predictors.loc[:, list(active_predictors)].notna().all(axis=1) & ~invalid_numeric
    free = baseline == 0
    complete = free.fillna(False) & completeness
    selected = complete & cumulative.ne("unknown")

    canonical = predictors.loc[selected, list(active_predictors)].copy()
    canonical.insert(0, "participant_id", mapping["id_namespace"] + ":" + ids.loc[selected].astype(str))
    canonical["endpoint_status"] = cumulative.loc[selected].to_numpy()
    canonical["label"] = (cumulative.loc[selected] == "positive").astype(int).to_numpy()
    if canonical.participant_id.duplicated().any():
        raise ValueError("Nonunique canonical IDs")

    # Historical calculation is solely a reconciliation diagnostic, never
    # eligibility logic. It accepted sentinel numerics as finite values.
    old_numeric = pd.DataFrame({name: pd.to_numeric(raw[fields[name]], errors="coerce")
                                for name in continuous})
    old_complete = old_numeric.notna().all(axis=1) & sex.notna() & smoking.notna() & medication.notna()
    if include_diabetes:
        old_complete &= diabetes.notna()
    historical = free.fillna(False) & old_complete & historical_cumulative.ne("unknown")
    sentinel_any = pd.DataFrame({name: pd.to_numeric(raw[fields[name]], errors="coerce").isin(codes.get(name, []))
                                 for name in continuous}).any(axis=1)
    variants = {}
    for name, status in (("cumulative", cumulative), ("final_only", final_only), ("both_waves", both)):
        mask = complete & status.ne("unknown")
        duration = (final_month - index_month).loc[mask]
        variants[name] = {"n": int(mask.sum()), "events": int((mask & status.eq("positive")).sum()),
                          "prevalence": float((mask & status.eq("positive")).sum() / mask.sum()) if mask.sum() else None,
                          "unknown_among_complete": int((complete & status.eq("unknown")).sum()),
                          "followup": _duration_summary(duration)}
    correction = None
    if corrected_intermediate_stroke is not None:
        corrected_name = "corrected_intermediate_stroke"
        corrected = _binary(pd.DataFrame({corrected_name: corrected_intermediate_stroke}),
                            {corrected_name: corrected_name},
                            {corrected_name: sorted(int(k) for k, v in value_labels.get(corrected_name, {}).items()
                                                    if str(v).strip().lower().startswith(SPECIAL_LABELS))},
                            corrected_name, yes, no)
        corrected_mid = wave_disease(binary("intermediate_heart_attack"), corrected)
        corrected_status = cumulative_wave_endpoint(corrected_mid, final)
        corrected_status.loc[invalid_chronology] = "unknown"
        corrected_status.loc[death_before_negative_final] = "unknown"
        corrected_mask = complete & corrected_status.ne("unknown")
        correction = {"raw_vs_corrected_stroke_disagreement_when_both_known":
                      int((free.fillna(False) & binary("intermediate_stroke").notna() & corrected.notna() &
                           (binary("intermediate_stroke") != corrected)).sum()),
                      "all_raw_vs_corrected_disagreement_when_both_known":
                      int((binary("intermediate_stroke").notna() & corrected.notna() &
                           (binary("intermediate_stroke") != corrected)).sum()),
                      "corrected_cumulative_n": int(corrected_mask.sum()),
                      "corrected_cumulative_events": int((corrected_mask & corrected_status.eq("positive")).sum()),
                      "raw_missing_corrected_positive": int((free.fillna(False) & binary("intermediate_stroke").isna() & (corrected == 1)).sum()),
                      "raw_negative_corrected_positive": int((free.fillna(False) & (binary("intermediate_stroke") == 0) & (corrected == 1)).sum())}
    flags = {"age_over_100": int((selected & (predictors.age > 100)).sum()),
             "bmi_over_80": int((selected & (predictors.bmi > 80)).sum()),
             "hdl_over_200_mg_dl": int((selected & (predictors.hdl > 200)).sum()),
             "total_cholesterol_over_700_mg_dl": int((selected & (predictors.total_cholesterol > 700)).sum()),
             "missing_index_month": int((selected & index_month.isna()).sum()),
             "missing_final_month": int((selected & final_month.isna()).sum())}
    selection_diagnostics = {}
    for label, mask in (("endpoint_observed", selected),
                        ("endpoint_unknown", complete & cumulative.eq("unknown"))):
        ages = predictors.loc[mask, "age"].dropna()
        selection_diagnostics[label] = {
            "n": int(mask.sum()), "age_median": float(ages.median()) if len(ages) else None,
            "female_n": int((mask & sex.eq("female")).sum()),
            "diabetes_yes_n": int((mask & diabetes.eq("yes")).sum())}
    baseline_counts = {"raw": len(raw), "prior_cvd": int((baseline == 1).sum()),
                       "baseline_unknown": int(baseline.isna().sum()), "baseline_free": int(free.sum())}
    waterfall = {**baseline_counts, "invalid_or_missing_predictors": int((free.fillna(False) & ~completeness).sum()),
                 "complete_predictors": int(complete.sum()),
                 "unknown_endpoint_after_predictors": int((complete & cumulative.eq("unknown")).sum()),
                 "eligible": int(selected.sum()), "incident_events": int((selected & cumulative.eq("positive")).sum())}
    if waterfall["raw"] != waterfall["prior_cvd"] + waterfall["baseline_unknown"] + waterfall["baseline_free"]:
        raise AssertionError("Baseline waterfall does not reconcile")
    if waterfall["baseline_free"] != waterfall["invalid_or_missing_predictors"] + waterfall["complete_predictors"]:
        raise AssertionError("Predictor waterfall does not reconcile")
    if waterfall["complete_predictors"] != waterfall["unknown_endpoint_after_predictors"] + waterfall["eligible"]:
        raise AssertionError("Endpoint waterfall does not reconcile")
    report = {"protocol_version": PUBLIC_PROTOCOL_VERSION, "schema_version": PUBLIC_SCHEMA_VERSION,
              "cohort": cohort, "status": "PROPOSED_NOT_READY", "waterfall": waterfall,
              "historical_reference": {"n": int(historical.sum()),
                                       "events": int((historical & historical_cumulative.eq("positive")).sum()),
                                       "sentinel_affected_n": int((historical & sentinel_any).sum()),
                                       "sentinel_affected_events": int((historical & sentinel_any & historical_cumulative.eq("positive")).sum()),
                                       "sentinel_by_predictor": {
                                           name: int((historical & pd.to_numeric(raw[fields[name]], errors="coerce").isin(codes.get(name, []))).sum())
                                           for name in continuous}},
              "endpoint_variants": variants,
              "observation": {"intermediate_known": int((free.fillna(False) & intermediate.notna()).sum()),
                              "final_known": int((free.fillna(False) & final.notna()).sum()),
                              "final_missing": int((free.fillna(False) & final.isna()).sum()),
                              "cumulative_unknown": int((free.fillna(False) & cumulative.eq("unknown")).sum()),
                              "cumulative_positive": int((free.fillna(False) & cumulative.eq("positive")).sum()),
                              "cumulative_known_negative": int((free.fillna(False) & cumulative.eq("known_negative")).sum()),
                              "intermediate_positive_final_negative": int((free.fillna(False) & (intermediate == 1) & (final == 0)).sum()),
                              "intermediate_positive_final_missing": int((free.fillna(False) & (intermediate == 1) & final.isna()).sum()),
                              "invalid_chronology": int((free.fillna(False) & invalid_chronology).sum()),
                              "death_before_negative_final": int((free.fillna(False) & death_before_negative_final).sum()),
                              "followup_observed": _duration_summary((final_month - index_month).loc[free.fillna(False) & final.notna()])},
              "measurement_flags": flags, "special_missing_codes": codes,
              "selection_diagnostics": selection_diagnostics,
              "active_predictors": list(active_predictors),
              "invalid_nonpositive_or_bp_order_after_baseline": int((free.fillna(False) & invalid_numeric).sum()),
              "field_profiles": {name: {
                  "raw_null": int(raw[fields[name]].isna().sum()),
                  "special_code_counts": {str(code): int((pd.to_numeric(raw[fields[name]], errors="coerce") == code).sum())
                                          for code in codes.get(name, [])},
                  "valid_min": float(num(name).min()) if num(name).notna().any() else None,
                  "valid_max": float(num(name).max()) if num(name).notna().any() else None}
                  for name in continuous},
              "response_profiles": {name: {
                  "raw_null": int(raw[fields[name]].isna().sum()),
                  "raw_code_counts": {str(k): int(v) for k, v in raw[fields[name]].value_counts(dropna=True).items()}}
                  for name in ("sex", "smoke_ever", "smoke_now", "diabetes_reference",
                               "antihypertensive_treatment", "baseline_heart_attack", "baseline_stroke",
                               "intermediate_heart_attack", "intermediate_stroke",
                               "final_heart_attack", "final_stroke")},
              "predictor_missing_after_baseline_screen": {name: int((free.fillna(False) & predictors[name].isna()).sum()) for name in active_predictors},
              "load_accounting": load_accounting or {},
              "unit_factors": {name: factors[name] for name in continuous},
              "five_views": {name: list(cols) for name, cols in PUBLIC_VIEWS.items()},
              "training_performed": False, "statistical_preprocessing_performed": False}
    if correction is not None:
        report["stroke_correction_diagnostic"] = correction
    if "__has_eol" in raw:
        death = death_month
        report["observation"]["eol"] = {
            "baseline_free_with_eol_record": int((free.fillna(False) & raw["__has_eol"]).sum()),
            "baseline_free_valid_death_month": int((free.fillna(False) & death.notna()).sum()),
            "baseline_free_death_before_index": int((free.fillna(False) & death.notna() & index_month.notna() & (death < index_month)).sum()),
            "baseline_free_death_before_positive_final": int((free.fillna(False) & death.notna() & final_month.notna() &
                                                                 (death < final_month) & (final == 1)).sum()),
            "baseline_free_final_missing_eol": int((free.fillna(False) & final.isna() & raw["__has_eol"]).sum()),
            "complete_predictors_unknown_endpoint_eol": int((complete & cumulative.eq("unknown") & raw["__has_eol"]).sum()),
            "baseline_free_death_within_60_months": int((free.fillna(False) & (death - index_month).between(0, 60)).sum()),
            "eligible_with_eol_record": int((selected & raw["__has_eol"]).sum()),
            "eligible_death_before_final_interview": int((selected & death.notna() & final_month.notna() & (death < final_month)).sum())}
    return PublicAudit(canonical=canonical, report=report)


def audit_release(data_root: str | Path, mapping: dict, *, stroke_correction_field: str | None = None) -> PublicAudit:
    adapter = HAALSIAdapter(mapping) if mapping["cohort_name"] == "HAALSI" else MHASAdapter(mapping)
    raw, accounting = adapter.load(data_root)
    main_path = Path(data_root) / mapping["files"]["main"]
    labels = pd.read_stata(main_path, iterator=True, convert_categoricals=False).value_labels()
    if mapping.get("join") == "biomarker_anchor":
        labels.update(pd.read_stata(Path(data_root) / mapping["files"]["biomarker"],
                                    iterator=True, convert_categoricals=False).value_labels())
    corrected = None
    if stroke_correction_field:
        if mapping["cohort_name"] != "HAALSI":
            raise ValueError("Correction field must be explicitly HAALSI")
        extra = pd.read_stata(main_path, columns=[mapping["fields"]["participant_id"], stroke_correction_field],
                              convert_categoricals=False)
        if not extra[mapping["fields"]["participant_id"]].equals(raw[mapping["fields"]["participant_id"]]):
            raise ValueError("Correction field alignment failed")
        corrected = extra[stroke_correction_field]
        labels["corrected_intermediate_stroke"] = labels.get(stroke_correction_field, {})
    return audit_public_cohort(raw, mapping, value_labels=labels, load_accounting=accounting,
                               corrected_intermediate_stroke=corrected)
