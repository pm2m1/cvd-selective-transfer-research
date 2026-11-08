"""Separate, pre-model HAALSI/MHAS public protocol v2 construction.

The frozen ARIC/MESA data and publication paths are not changed. Participant
tables exist only in memory; callers must publish aggregate reports only.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import re

import numpy as np
import pandas as pd

from .public_cohorts import PUBLIC_PREDICTORS, audit_public_cohort, embedded_missing_codes
from .public_reconciliation import classify_mhas_observation, parse_master_interview_date
from .wave_endpoint import cumulative_wave_endpoint, wave_disease


PUBLIC_V2_VERSION = "public-haalsi-mhas-v2"
VIEWS_TEN = {
    "background": ("age", "sex"),
    "haemodynamic": ("sbp", "dbp"),
    "metabolic": ("bmi", "total_cholesterol", "hdl"),
    "behaviour": ("smoking_status",),
    "comorbidity_medication": ("diabetes", "antihypertensive_treatment"),
}
VIEWS_NINE = {**VIEWS_TEN, "comorbidity_medication": ("antihypertensive_treatment",)}
SCHEMA_VERSIONS = {"ten_doctor_report": "cvd-public-wave-v2-ten-doctor-report",
                   "ten_broad_diagnostic": "cvd-public-wave-v2-ten-broad-diagnostic",
                   "nine_no_diabetes": "cvd-public-wave-v2-nine-no-diabetes"}


@dataclass(frozen=True)
class PublicV2Cohort:
    canonical: pd.DataFrame  # in-memory only; never serialize this table
    views: dict[str, tuple[str, ...]]
    report: dict

    def model_views(self) -> dict[str, pd.DataFrame]:
        return {view: self.canonical.loc[:, list(fields)].copy() for view, fields in self.views.items()}


def wave1_roster_sex(frame: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Find each respondent by their Wave-1 primary key in the Wave-1 roster."""
    if "PRIM_KEY" not in frame or frame.PRIM_KEY.isna().any() or frame.PRIM_KEY.duplicated().any():
        raise ValueError("Wave-1 respondent primary keys must be present and unique")
    key_slots = {int(m.group(1)): name for name in frame
                 if (m := re.fullmatch(r"W1HHMEMBERPRIMKEY_(\d+)_", name))}
    sex_slots = {int(m.group(1)): name for name in frame
                 if (m := re.fullmatch(r"W1HHMEMBERSEX_(\d+)_", name))}
    if not sex_slots or set(sex_slots) - set(key_slots):
        raise ValueError("Every Wave-1 roster sex slot needs its paired key")
    respondent = frame.PRIM_KEY.astype("string").str.strip()
    count = pd.Series(0, index=frame.index, dtype="int64")
    sex = pd.Series(pd.NA, index=frame.index, dtype="Int64")
    for slot in sorted(sex_slots):
        roster_key = frame[key_slots[slot]].astype("string").str.strip()
        match = respondent.eq(roster_key).fillna(False)
        count = count + match.astype("int64")
        value = pd.to_numeric(frame[sex_slots[slot]], errors="coerce")
        sex.loc[match] = value.loc[match].astype("Int64")
    if count.gt(1).any():
        raise ValueError("Ambiguous Wave-1 respondent roster matches")
    invalid = sex.notna() & ~sex.isin([1, 2])
    if invalid.any():
        raise ValueError("Unmapped Wave-1 respondent sex value")
    return sex, {"roster_slots": len(sex_slots), "key_only_slots": len(set(key_slots) - set(sex_slots)),
                 "unique_matches": int(count.eq(1).sum()),
                 "unmatched": int(count.eq(0).sum()), "multiple": int(count.gt(1).sum()),
                 "matched_sex_known": int(sex.isin([1, 2]).sum())}


def wave1_medication(frame: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Derive current treatment only from explicit answers or documented skips."""
    for name in ("W1CM002", "W1CM004", "W1CM005"):
        if name not in frame:
            raise ValueError(f"Missing Wave-1 medication-route field: {name}")
    htn = pd.to_numeric(frame.W1CM002, errors="coerce")
    ever = pd.to_numeric(frame.W1CM004, errors="coerce")
    current = pd.to_numeric(frame.W1CM005, errors="coerce")
    for name, values in (("hypertension", htn), ("ever treatment", ever), ("current treatment", current)):
        if not values.dropna().isin([1, 2, -97, -98, -99]).all():
            raise ValueError(f"Unmapped {name} response")
    current = current.where(current.isin([1, 2]))
    no_htn = current.isna() & htn.eq(2)
    no_ever = current.isna() & htn.eq(1) & ever.eq(2)
    # A refused/unknown current answer is not a questionnaire skip.
    raw_current = pd.to_numeric(frame.W1CM005, errors="coerce")
    no_htn &= raw_current.isna()
    no_ever &= raw_current.isna()
    current.loc[no_htn | no_ever] = 2
    return current, {"explicit_yes": int(raw_current.eq(1).sum()),
                     "explicit_no": int(raw_current.eq(2).sum()),
                     "derived_no_hypertension": int(no_htn.sum()),
                     "derived_no_never_treated": int(no_ever.sum()),
                     "refused_or_unknown_preserved": int(raw_current.isin([-97, -98, -99]).sum()),
                     "unresolved_blank": int(current.isna().sum() - raw_current.isin([-97, -98, -99]).sum()),
                     "contradictory_explicit_yes_with_no_hypertension": int((raw_current.eq(1) & htn.eq(2)).sum())}


def wave1_doctor_diabetes(frame: pd.DataFrame, roster_sex: pd.Series,
                          labels: dict) -> tuple[pd.Series, dict]:
    """Use only the sex-routed Wave-1 doctor-told high-sugar/diabetes question."""
    names = ("W1CM007_MALES", "W1CM007_FEMALES")
    if set(names) - set(frame):
        raise ValueError("Wave-1 doctor-told diabetes responses missing")
    codes = embedded_missing_codes(labels, {"male": names[0], "female": names[1]})
    values = []
    for kind, name in zip(("male", "female"), names):
        raw = pd.to_numeric(frame[name], errors="coerce")
        clean = raw.mask(raw.isin(codes[kind]))
        if not clean.dropna().isin([1, 2]).all():
            raise ValueError("Unmapped doctor-told diabetes response")
        values.append(clean)
    selected = values[0].where(roster_sex.eq(1), values[1].where(roster_sex.eq(2)))
    off_route_answer = ((roster_sex.eq(1) & values[1].notna()) |
                        (roster_sex.eq(2) & values[0].notna()))
    # An answered opposite branch is a source inconsistency, not evidence that
    # the respondent's baseline sex should be changed. Keep diabetes unknown.
    selected.loc[off_route_answer] = np.nan
    return selected, {"known": int(selected.isin([1, 2]).sum()),
                      "yes": int(selected.eq(1).sum()), "no": int(selected.eq(2).sum()),
                      "missing": int(selected.isna().sum()),
                      "off_route_answers": int(off_route_answer.sum())}


def haalsi_endpoint_v2(frame: pd.DataFrame, fields: dict, labels: dict) -> tuple[pd.Series, dict]:
    """Composite report with disputed disease-specific reversals left unknown."""
    codes = embedded_missing_codes(labels, fields)
    def answer(name: str) -> pd.Series:
        raw = pd.to_numeric(frame[fields[name]], errors="coerce")
        clean = raw.mask(raw.isin(codes.get(name, [])))
        if not clean.dropna().isin([1, 2]).all():
            raise ValueError(f"Unmapped {name} disease response")
        return clean.map({1: 1, 2: 0})
    h2, h3 = answer("intermediate_heart_attack"), answer("final_heart_attack")
    s2, s3 = answer("intermediate_stroke"), answer("final_stroke")
    def reason(name: str) -> pd.Series:
        raw = pd.to_numeric(frame[name], errors="coerce")
        clean = raw.mask(raw.isin([-97, -98, -99]))
        if not clean.dropna().isin([1, 2, 3, 4, 5]).all():
            raise ValueError("Unmapped HAALSI reversal reason")
        return clean
    hr, sr = reason("W3CM324"), reason("W3CM321")
    rh, rs = h2.eq(1) & h3.eq(0), s2.eq(1) & s3.eq(0)
    uh = rh & (hr.isin([1, 3, 5]) | hr.isna())
    us = rs & (sr.isin([1, 3, 5]) | sr.isna())
    valid_h = h3.eq(1) | (h2.eq(1) & ~uh)
    valid_s = s3.eq(1) | (s2.eq(1) & ~us)
    original = cumulative_wave_endpoint(wave_disease(h2, s2), wave_disease(h3, s3))
    uncertain = (uh | us) & ~(valid_h | valid_s)
    status = original.copy()
    status.loc[uncertain] = "unknown"
    return status, {"reversal_heart": int(rh.sum()), "reversal_stroke": int(rs.sum()),
                    "explicit_retractions": int(((rh & hr.isin([1, 3])) | (rs & sr.isin([1, 3]))).sum()),
                    "unexplained_retractions": int(((rh & hr.isna()) | (rs & sr.isna())).sum()),
                    "no_longer_has": int(((rh & hr.eq(2)) | (rs & sr.eq(2))).sum()),
                    "other_reason_uncertain": int(((rh & hr.eq(5)) | (rs & sr.eq(5))).sum()),
                    "uncertain_composite": int(uncertain.sum()),
                    "positive_despite_other_component_retraction": int(((uh | us) & (valid_h | valid_s)).sum())}


def _finish_v2(old, raw_ids: pd.Series, status: pd.Series | None, *, schema: str,
               cohort: str, extra_mask: pd.Series | None = None,
               diagnostic: dict | None = None) -> PublicV2Cohort:
    canonical = old.canonical.copy()
    if status is not None:
        indexed = pd.Series(status.to_numpy(), index=raw_ids.to_numpy())
        corrected = canonical.participant_id.map(indexed)
        keep = corrected.ne("unknown").fillna(False)
        canonical = canonical.loc[keep].copy()
        canonical["endpoint_status"] = corrected.loc[keep].to_numpy()
        canonical["label"] = corrected.loc[keep].eq("positive").astype(int).to_numpy()
    if extra_mask is not None:
        indexed = pd.Series(extra_mask.to_numpy(), index=raw_ids.to_numpy())
        canonical = canonical.loc[canonical.participant_id.map(indexed).fillna(False)].copy()
    views = VIEWS_NINE if schema == "nine_no_diabetes" else VIEWS_TEN
    predictors = tuple(field for fields in views.values() for field in fields)
    if set(canonical.columns) != set(predictors) | {"participant_id", "endpoint_status", "label"}:
        raise AssertionError("Public v2 predictor/metadata contract drift")
    if canonical.participant_id.duplicated().any() or not canonical.label.isin([0, 1]).all():
        raise ValueError("Invalid v2 participant or endpoint contract")
    return PublicV2Cohort(canonical.reset_index(drop=True), views,
        {"cohort": cohort, "protocol_version": PUBLIC_V2_VERSION,
         "schema_version": SCHEMA_VERSIONS[schema], "before_v2_rules": old.report["waterfall"],
         "after_v2_rules": {"n": len(canonical), "events": int(canonical.label.sum()),
                             "known_negative": int((canonical.label == 0).sum())},
         "diagnostics": diagnostic or {}, "training_performed": False,
         "publication_split_created": False})


def construct_haalsi_v2(raw: pd.DataFrame, mapping: dict, labels: dict,
                         *, schema: str = "ten_doctor_report") -> PublicV2Cohort:
    if schema not in SCHEMA_VERSIONS:
        raise ValueError("Unknown public v2 schema")
    sex, sex_report = wave1_roster_sex(raw)
    medication, med_report = wave1_medication(raw)
    doctor, diabetes_report = wave1_doctor_diabetes(raw, sex, labels)
    enriched = raw.assign(__v2_w1_sex=sex, __v2_bp_medication=medication,
                          __v2_doctor_diabetes=doctor)
    adjusted = deepcopy(mapping)
    adjusted["fields"]["sex"] = "__v2_w1_sex"
    adjusted["fields"]["antihypertensive_treatment"] = "__v2_bp_medication"
    adjusted["hypertension_field"] = None
    if schema == "ten_doctor_report":
        adjusted["fields"]["diabetes_reference"] = "__v2_doctor_diabetes"
    old = audit_public_cohort(enriched, adjusted, value_labels=labels,
                              include_diabetes=schema != "nine_no_diabetes")
    status, endpoint_report = haalsi_endpoint_v2(raw, mapping["fields"], labels)
    raw_ids = mapping["id_namespace"] + ":" + raw[mapping["fields"]["participant_id"]].astype(str)
    both = sex.isin([1, 2]) & raw[mapping["fields"]["sex"]].isin([1, 2])
    sex_report.update({"combined_agree": int((both & sex.eq(raw[mapping["fields"]["sex"]])).sum()),
                       "combined_contradict": int((both & sex.ne(raw[mapping["fields"]["sex"]])).sum())})
    return _finish_v2(old, raw_ids, status, schema=schema, cohort="HAALSI Wave 1",
        diagnostic={"sex": sex_report, "medication": med_report, "diabetes": diabetes_report,
                    "endpoint": endpoint_report})


def target_landmark_mask(raw: pd.DataFrame, *, max_days: int) -> tuple[pd.Series, dict]:
    if max_days not in (14, 30):
        raise ValueError("Only prespecified 0–14 or 0–30 day windows are allowed")
    interview, parsing = parse_master_interview_date(raw.int_date_12, 12)
    exam = pd.to_datetime(raw.date_12, errors="coerce")
    plausible_exam = exam.where(exam.dt.year.eq(2012))
    days = (plausible_exam - interview).dt.days
    core = raw.tipent_12.isin([1, 2]) & raw.tipne_12.eq(1)
    processed = raw.res_biomarkers_12.eq(2)
    eligible = core & processed & days.between(0, max_days)
    return eligible, {"window_days": max_days, "interview_dates": parsing,
                      "invalid_or_missing_exam": int(plausible_exam.isna().sum()),
                      "exam_before_interview": int(days.lt(0).sum()),
                      "exam_after_window": int(days.gt(max_days).sum()),
                      "incompatible_interview_type": int((~core).sum()),
                      "biomarker_not_processed": int((~processed).sum()),
                      "eligible_before_predictor_outcome_screen": int(eligible.sum()),
                      "interval_onset_unverifiable": True}


def construct_mhas_v2(raw: pd.DataFrame, mapping: dict, labels: dict, *,
                      schema: str = "ten_doctor_report", max_days: int = 30) -> PublicV2Cohort:
    if schema not in SCHEMA_VERSIONS:
        raise ValueError("Unknown public v2 schema")
    adjusted = deepcopy(mapping)
    adjusted["fields"]["sex"] = "sex_12"
    old = audit_public_cohort(raw, adjusted, value_labels=labels,
                              include_diabetes=schema != "nine_no_diabetes")
    landmark, landmark_report = target_landmark_mask(raw, max_days=max_days)
    # A negative report cannot stand when Master/EOL signals a death or a
    # death/interview conflict. A positive report remains a positive report.
    raw_ids = mapping["id_namespace"] + ":" + raw[mapping["fields"]["participant_id"]].astype(str)
    known = raw_ids.map(old.canonical.set_index("participant_id").endpoint_status)
    category = classify_mhas_observation(known.astype("string"), raw.tipent_18,
        raw.fallecido_15, raw.fallecido_18, raw.tipne_15, raw.tipne_18,
        pd.to_numeric(raw.__eol_year, errors="coerce").between(2012, 2018))
    observation_ok = category.isin(["reported_event", "observed_event_free"])
    old_candidate = raw_ids.isin(old.canonical.participant_id)
    event = raw_ids.map(old.canonical.set_index("participant_id").label).eq(1).fillna(False)
    interview, _ = parse_master_interview_date(raw.int_date_12, 12)
    exam = pd.to_datetime(raw.date_12, errors="coerce").where(lambda x: x.dt.year.eq(2012))
    days = (exam - interview).dt.days
    core = raw.tipent_12.isin([1, 2]) & raw.tipne_12.eq(1) & raw.res_biomarkers_12.eq(2)
    steps = (
        ("candidate_after_predictor_endpoint", old_candidate),
        ("documented_core_and_processed_exam", old_candidate & core),
        ("valid_paired_dates", old_candidate & core & days.notna()),
        ("exam_not_before_interview", old_candidate & core & days.ge(0)),
        ("exam_within_window", old_candidate & landmark),
        ("observed_nonconflicting_outcome", old_candidate & landmark & observation_ok),
    )
    waterfall = {name: {"n": int(mask.sum()), "events": int((mask & event).sum())}
                 for name, mask in steps}
    return _finish_v2(old, raw_ids, None, schema=schema,
        cohort="MHAS Wave 3/2012 examination", extra_mask=landmark & observation_ok,
        diagnostic={"landmark": landmark_report,
                    "candidate_waterfall": waterfall,
                    "candidate_observation_categories": {
                        str(k): int(v) for k, v in category.loc[raw_ids.isin(old.canonical.participant_id)]
                        .value_counts(dropna=False).items()}})
