"""Aggregate, pre-split decision screens for the proposed HAALSI/MHAS study.

This command does not change canonical mappings, fit statistics, split people,
or write participant records. It reuses the Milestone-5 cohort audit.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

import pandas as pd

from .data.public_cohorts import audit_public_cohort
from .data.public_reconciliation import classify_mhas_observation, parse_master_interview_date
from .data.real_cohorts import HAALSIAdapter, MHASAdapter, join_mhas_master_followup
from .public_evidence_reconciliation import MASTER_COLUMNS, _status
from .data.releases import file_sha256


def _screen(mask: pd.Series, event: pd.Series) -> dict[str, int]:
    return {"n": int(mask.sum()), "events": int((mask & event).sum())}


def timing_screens(candidate: pd.Series, event: pd.Series, interview: pd.Series,
                   examination: pd.Series) -> dict:
    """Mutually interpretable landmark screens; no participant split occurs."""
    exam = examination.where(examination.dt.year.between(2012, 2013))
    days = (exam - interview).dt.days
    valid = candidate & days.notna()
    return {
        "all_provisional": _screen(candidate, event),
        "missing_interview": _screen(candidate & interview.isna(), event),
        "missing_or_implausible_exam": _screen(candidate & exam.isna(), event),
        "valid_paired_dates": _screen(valid, event),
        "exam_before_interview": _screen(candidate & days.lt(0), event),
        "exam_same_day": _screen(candidate & days.eq(0), event),
        "exam_after_interview": _screen(candidate & days.gt(0), event),
        "interview_day_all_measures_available": _screen(candidate & days.le(0), event),
        "examination_0_to_14_days": _screen(candidate & days.between(0, 14), event),
        "examination_0_to_30_days": _screen(candidate & days.between(0, 30), event),
        "examination_15_to_30_days": _screen(candidate & days.between(15, 30), event),
        "examination_after_30_days": _screen(candidate & days.gt(30), event),
        "examination_minus_30_to_minus_1_days": _screen(candidate & days.between(-30, -1), event),
        "examination_before_minus_30_days": _screen(candidate & days.lt(-30), event),
        "examination_plus_minus_30_days": _screen(candidate & days.between(-30, 30), event),
        "days_valid_pair_median": float(days.loc[valid].median()) if valid.any() else None,
    }


def reversal_screens(raw: pd.DataFrame, mapping: dict, candidate: pd.Series,
                     event: pd.Series, free: pd.Series) -> dict:
    """Person-level sensitivity screens, never reinterpret a retraction as negative."""
    f = mapping["fields"]
    yes, no = mapping["binary_codes"]["yes"], mapping["binary_codes"]["no"]
    h2 = pd.to_numeric(raw[f["intermediate_heart_attack"]], errors="coerce")
    s2 = pd.to_numeric(raw[f["intermediate_stroke"]], errors="coerce")
    h3 = pd.to_numeric(raw[f["final_heart_attack"]], errors="coerce")
    s3 = pd.to_numeric(raw[f["final_stroke"]], errors="coerce")
    hr = pd.to_numeric(raw["W3CM324"], errors="coerce")
    sr = pd.to_numeric(raw["W3CM321"], errors="coerce")
    rev_h = h2.eq(yes) & h3.eq(no)
    rev_s = s2.eq(yes) & s3.eq(no)
    reversal = rev_h | rev_s
    explicit_h, explicit_s = rev_h & hr.isin((1, 3)), rev_s & sr.isin((1, 3))
    unexplained_h, unexplained_s = rev_h & hr.isna(), rev_s & sr.isna()
    no_longer = (rev_h & hr.eq(2)) | (rev_s & sr.eq(2))
    explicit = explicit_h | explicit_s
    unexplained = unexplained_h | unexplained_s
    # Preserve a separately observed positive for the other disease. In the
    # local screen this exception is absent, but it matters to the policy.
    valid_h_positive = h3.eq(yes) | (h2.eq(yes) & ~(explicit_h | unexplained_h))
    valid_s_positive = s3.eq(yes) | (s2.eq(yes) & ~(explicit_s | unexplained_s))
    other_positive = ((explicit_h | unexplained_h) & valid_s_positive) | (
        (explicit_s | unexplained_s) & valid_h_positive)
    uncertain_explicit = explicit & ~other_positive
    uncertain_all = (explicit | unexplained) & ~other_positive
    mid_positive_final_missing = ((h2.eq(yes) & h3.isna()) | (s2.eq(yes) & s3.isna()))
    return {
        "baseline_free_reversals": int((free & reversal).sum()),
        "baseline_free_intermediate_positive_final_missing": int((free & mid_positive_final_missing).sum()),
        "candidate_reversals": int((candidate & reversal).sum()),
        "candidate_explicit_never_or_misdiagnosed": int((candidate & explicit).sum()),
        "candidate_no_longer_has": int((candidate & no_longer).sum()),
        "candidate_unexplained": int((candidate & unexplained).sum()),
        "candidate_intermediate_positive_final_missing": int((candidate & mid_positive_final_missing).sum()),
        "candidate_other_disease_positive_despite_retraction": int((candidate & other_positive).sum()),
        "retain_all_reports": _screen(candidate, event),
        "exclude_explicit_retractions_as_uncertain": _screen(candidate & ~uncertain_explicit, event),
        "exclude_explicit_and_unexplained_as_uncertain": _screen(candidate & ~uncertain_all, event),
        "excluded_explicit": _screen(candidate & uncertain_explicit, event),
        "excluded_explicit_or_unexplained": _screen(candidate & uncertain_all, event),
    }


def _mapped_screen(raw: pd.DataFrame, mapping: dict, labels: dict, *,
                   field: str | None = None, value: str | None = None,
                   disable_hypertension_route: bool = False) -> dict[str, int]:
    altered = deepcopy(mapping)
    altered_raw = raw.copy(deep=False)
    if field and value:
        altered["fields"][field] = value
    if disable_hypertension_route:
        altered["hypertension_field"] = None
    result = audit_public_cohort(altered_raw, altered, value_labels=labels).canonical
    return {"n": len(result), "events": int(result.label.sum())}


def _nine_feature_screen(raw: pd.DataFrame, mapping: dict, labels: dict) -> dict[str, int]:
    # Constant is a completeness-screen placeholder only. It is never saved
    # as a predictor, trained on, or proposed as a clinical diabetes value.
    altered = raw.assign(__diabetes_omitted_for_completeness_screen=1)
    return _mapped_screen(altered, mapping, labels, field="diabetes_reference",
                          value="__diabetes_omitted_for_completeness_screen")


def _planning(events: int) -> dict:
    """Arithmetic illustration only; no actual participant allocation."""
    test_expected = events * .25
    validation_expected = (events - test_expected) * .20
    adaptation_expected = events - test_expected - validation_expected
    return {"total_reported_events": events, "test_25pct_expected_events": round(test_expected, 2),
            "validation_20pct_of_development_expected_events": round(validation_expected, 2),
            "adaptation_60pct_expected_events": round(adaptation_expected, 2),
            "budgets": {str(b): "expected feasible, not guaranteed" if adaptation_expected >= b
                        else "not feasible under illustrative reserves" for b in (10, 25, 50)}}


def _source_planning(events: int) -> dict:
    """Expected source train/validation/test events at existing .6/.2/.2 fractions."""
    return {"total_reported_events": events, "train_60pct_expected_events": round(events * .6, 2),
            "validation_20pct_expected_events": round(events * .2, 2),
            "optional_test_20pct_expected_events": round(events * .2, 2)}


def run(data_root: Path, master_file: Path, output_root: Path) -> Path:
    if not master_file.is_file():
        raise FileNotFoundError(master_file)
    mapping_h = json.loads(Path("configs/mappings/haalsi_wave_m5.provisional.json").read_text())
    mapping_m = json.loads(Path("configs/mappings/mhas_wave_m5.provisional.json").read_text())
    raw_h, _ = HAALSIAdapter(mapping_h).load(data_root)
    raw_m, _ = MHASAdapter(mapping_m).load(data_root)
    main_h = data_root / mapping_h["files"]["main"]
    main_m = data_root / mapping_m["files"]["main"]
    bio = data_root / mapping_m["files"]["biomarker"]
    labels_h = pd.read_stata(main_h, iterator=True, convert_categoricals=False).value_labels()
    labels_m = pd.read_stata(main_m, iterator=True, convert_categoricals=False).value_labels()
    labels_m.update(pd.read_stata(bio, iterator=True, convert_categoricals=False).value_labels())
    raw_h = pd.concat([raw_h, pd.read_stata(main_h, columns=["W3CM321", "W3CM324",
        "W1C_CM_DIABETES_SRTRT"], convert_categoricals=False)], axis=1)
    bio_extra = pd.read_stata(bio, columns=["cunicah", "np", "date_12", "sex_12"],
                             convert_categoricals=False)
    bio_extra["__join_id"] = bio_extra.cunicah.astype("int64") * 100 + bio_extra.np.astype("int64")
    bio_extra = bio_extra.rename(columns={"sex_12": "sex_12_bio"})
    raw_m = raw_m.merge(bio_extra[["__join_id", "date_12", "sex_12_bio"]],
                        on="__join_id", how="left", validate="one_to_one")
    master = pd.read_stata(master_file, columns=list(MASTER_COLUMNS), convert_categoricals=False)
    joined, join_report = join_mhas_master_followup(raw_m, master)
    h = audit_public_cohort(raw_h, mapping_h, value_labels=labels_h)
    m = audit_public_cohort(joined, mapping_m, value_labels=labels_m)
    h_id = mapping_h["id_namespace"] + ":" + raw_h[mapping_h["fields"]["participant_id"]].astype(str)
    m_id = mapping_m["id_namespace"] + ":" + joined[mapping_m["fields"]["participant_id"]].astype(str)
    h_candidate = h_id.isin(h.canonical.participant_id)
    m_candidate = m_id.isin(m.canonical.participant_id)
    h_event = h_id.map(h.canonical.set_index("participant_id").label).eq(1).fillna(False)
    m_event = m_id.map(m.canonical.set_index("participant_id").label).eq(1).fillna(False)
    h_base, _, _, _ = _status(raw_h, mapping_h)
    _, _, _, m_status = _status(joined, mapping_m)
    m_category = classify_mhas_observation(
        m_status, joined.tipent_18, joined.fallecido_15, joined.fallecido_18,
        joined.tipne_15, joined.tipne_18,
        pd.to_numeric(joined.__eol_year, errors="coerce").between(2012, 2018))
    interview, _ = parse_master_interview_date(joined.int_date_12, 12)
    examination = pd.to_datetime(joined.date_12, errors="coerce")
    timing = timing_screens(m_candidate, m_event, interview, examination)
    days = (examination.where(examination.dt.year.between(2012, 2013)) - interview).dt.days
    death_conflict = m_category.eq("ambiguous_death_and_negative")
    timing["death_negative_conflict_current"] = _screen(m_candidate & death_conflict, m_event)
    timing["death_negative_conflict_exam_0_to_14"] = _screen(
        m_candidate & days.between(0, 14) & death_conflict, m_event)
    timing["death_negative_conflict_exam_0_to_30"] = _screen(
        m_candidate & days.between(0, 30) & death_conflict, m_event)
    followup_date, _ = parse_master_interview_date(joined.int_date_18, 18)
    for name, window in (("exam_0_to_14", days.between(0, 14)),
                         ("exam_0_to_30", days.between(0, 30))):
        months = ((followup_date - examination).dt.days / 30.4375).loc[m_candidate & window].dropna()
        timing[f"{name}_observed_final_followup"] = {
            "dated_n": int(len(months)), "median_months": float(months.median()) if len(months) else None,
            "under_60_months": int(months.lt(60).sum())}
    reversal = reversal_screens(raw_h, mapping_h, h_candidate, h_event, h_base.eq(0))
    m_sex = _mapped_screen(joined, mapping_m, labels_m, field="sex", value="sex_12")
    sex_mapping = deepcopy(mapping_m)
    sex_mapping["fields"]["sex"] = "sex_12"
    sex_alt = audit_public_cohort(joined, sex_mapping, value_labels=labels_m).canonical
    m_sex["membership_symmetric_difference"] = len(
        set(sex_alt.participant_id) ^ set(m.canonical.participant_id))
    h_treatment_unrouted = _mapped_screen(raw_h, mapping_h, labels_h,
                                           disable_hypertension_route=True)
    h_diabetes_narrow = _mapped_screen(raw_h, mapping_h, labels_h,
        field="diabetes_reference", value="W1C_CM_DIABETES_SRTRT")
    report = {
        "milestone": "5F", "created_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_status": "PROPOSAL_BLOCKED_PENDING_APPROVAL", "canonical_mappings_changed": False,
        "training_performed": False, "statistical_preprocessing_performed": False,
        "publication_test_split_created": False,
        "source_checksums": {"haalsi": file_sha256(main_h), "mhas": file_sha256(main_m),
                             "biomarker": file_sha256(bio), "master": file_sha256(master_file)},
        "master_join": join_report,
        "current_candidates": {"HAALSI": _screen(h_candidate, h_event),
                               "MHAS": _screen(m_candidate, m_event)},
        "mhas_landmark_screens": timing,
        "haalsi_reversal_screens": reversal,
        "published_audit_sensitivities": {"HAALSI": h.report["endpoint_variants"],
                                           "MHAS": m.report["endpoint_variants"]},
        "predictor_comparability_screens": {
            "mhas_sex_12": m_sex, "haalsi_treatment_without_routing": h_treatment_unrouted,
            "haalsi_treatment_derived_diabetes": h_diabetes_narrow,
            "haalsi_other_nine_predictors_complete": _nine_feature_screen(raw_h, mapping_h, labels_h),
            "mhas_other_nine_predictors_complete": _nine_feature_screen(joined, mapping_m, labels_m)},
        "event_budget_arithmetic": {
            "haalsi_proposed_corrected_source": _source_planning(
                reversal["exclude_explicit_and_unexplained_as_uncertain"]["events"]),
            "mhas_current": _planning(int(m_event.sum())),
            "mhas_exam_0_to_14": _planning(timing["examination_0_to_14_days"]["events"]),
            "mhas_exam_0_to_30": _planning(timing["examination_0_to_30_days"]["events"])},
        "warning": "Aggregate screens only. No policy approved, no actual split, no event date inferred."
    }
    output = output_root / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    (output / "aggregate_feasibility.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--master-file", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("results/public_study_feasibility"))
    args = parser.parse_args()
    print(f"Aggregate-only screens: {run(args.data_root, args.master_file, args.output_root)}")


if __name__ == "__main__":
    main()
