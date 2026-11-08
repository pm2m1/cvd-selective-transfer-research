"""Milestone-5E aggregate evidence audit. No training, fitting or target splitting."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

import pandas as pd

from .data.public_cohorts import audit_public_cohort, embedded_missing_codes
from .data.public_reconciliation import (classify_mhas_observation, death_before_core_interview,
    harmonized_persistence_violations, parse_master_interview_date, sex_agreement)
from .data.real_cohorts import HAALSIAdapter, MHASAdapter, join_mhas_master_followup
from .data.releases import file_sha256
from .data.wave_endpoint import cumulative_wave_endpoint, wave_disease


MASTER_COLUMNS = ("cunicah", "np", "UNHHIDNP", "int_date_12", "sex_12",
                  "res_biomarkers_12", "tipne_15", "tipent_15", "int_date_15",
                  "fallecido_15", "tipne_18", "tipent_18", "int_date_18", "fallecido_18")
EOL_COLUMNS = ("unhhidnp", "raxmonth", "raxyear", "ralstcore", "ragcod", "racod_m",
               "raxhrtatt", "raxhrtatt1y", "raxhrtatte", "raxstrok", "raxstrok1y", "raxstroke")
DOC_NAMES = {
    "harmonized_D": "Gateway_Harmonized_MHAS_D_2001-2022.pdf",
    "eol_C": "Gateway Harmonized MHAS End of Life C 2003-2022.pdf",
    "master_V1_2026": "MHAS Master Follow-Up File Descriptive Document 2001-2024.pdf",
    "section_C_2012": "Microsoft Word - Section C.doc - Section_C_Health_2012.pdf",
    "section_C_2015": "Microsoft Word - Section C.doc - Section_C_Health_2015.pdf",
    "section_C_2018": "Microsoft Word - Section C_18.doc - Section_C_Health_2018.pdf",
    "haalsi_longitudinal": "HAALSI W1-3 Longitudinal Codebook.docx",
    "haalsi_W3": "HAALSI Wave 3 Survey Text.docx",
}


def _numbers(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts(dropna=False).items()}


def _summary(series: pd.Series) -> dict:
    good = _numbers(series).dropna()
    return {"n": len(good), "median": float(good.median()) if len(good) else None,
            "q1": float(good.quantile(.25)) if len(good) else None,
            "q3": float(good.quantile(.75)) if len(good) else None}


def _status(raw: pd.DataFrame, mapping: dict) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    f = mapping["fields"]
    yes, no = mapping["binary_codes"]["yes"], mapping["binary_codes"]["no"]
    def binary(name: str) -> pd.Series:
        value = _numbers(raw[f[name]])
        invalid = value.notna() & ~value.isin([yes, no, -97, -98, -99])
        if invalid.any():
            raise ValueError("Unmapped disease code")
        return value.map({yes: 1, no: 0})
    baseline = wave_disease(binary("baseline_heart_attack"), binary("baseline_stroke"))
    mid = wave_disease(binary("intermediate_heart_attack"), binary("intermediate_stroke"))
    end = wave_disease(binary("final_heart_attack"), binary("final_stroke"))
    return baseline, mid, end, cumulative_wave_endpoint(mid, end)


def _observed_profile(raw: pd.DataFrame, mapping: dict, free: pd.Series,
                      status: pd.Series, labels: dict) -> dict:
    fields = mapping["fields"]
    codes = embedded_missing_codes(labels, fields)
    result = {}
    for group, mask in (("observed", free & status.ne("unknown")),
                        ("unresolved", free & status.eq("unknown"))):
        item = {"n": int(mask.sum())}
        for name in ("age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl"):
            value = _numbers(raw[fields[name]]).mask(lambda x: x.isin(codes.get(name, [])))
            item[name] = _summary(value.loc[mask])
        sex = _numbers(raw[fields["sex"]])
        diab = _numbers(raw[fields["diabetes_reference"]])
        item["female_n"] = int((mask & sex.eq(mapping["sex_codes"]["female"])).sum())
        item["diabetes_yes_n"] = int((mask & diab.eq(mapping["binary_codes"]["yes"])).sum())
        result[group] = item
    return result


def _haalsi_reversals(raw: pd.DataFrame, mapping: dict, canonical: pd.DataFrame,
                      free: pd.Series) -> dict:
    f = mapping["fields"]
    yes, no = mapping["binary_codes"]["yes"], mapping["binary_codes"]["no"]
    mid_heart = _numbers(raw[f["intermediate_heart_attack"]]).eq(yes)
    mid_stroke = _numbers(raw[f["intermediate_stroke"]]).eq(yes)
    final_heart = _numbers(raw[f["final_heart_attack"]]).eq(no)
    final_stroke = _numbers(raw[f["final_stroke"]]).eq(no)
    reversal = (mid_heart & final_heart) | (mid_stroke & final_stroke)
    selected = (mapping["id_namespace"] + ":" + raw[f["participant_id"]].astype(str)).isin(canonical.participant_id)
    stroke_reason = _numbers(raw["W3CM321"])
    heart_reason = _numbers(raw["W3CM324"])
    disputed = ((mid_stroke & final_stroke & stroke_reason.isin([1, 3])) |
                (mid_heart & final_heart & heart_reason.isin([1, 3])))
    no_longer = ((mid_stroke & final_stroke & stroke_reason.eq(2)) |
                 (mid_heart & final_heart & heart_reason.eq(2)))
    reason_known = ((mid_stroke & final_stroke & stroke_reason.isin([1, 2, 3, 4, 5])) |
                    (mid_heart & final_heart & heart_reason.isin([1, 2, 3, 4, 5])))
    excluded = selected & reversal & disputed
    return {"baseline_free_reversals": int((free & reversal).sum()),
            "candidate_reversals": int((selected & reversal).sum()),
            "candidate_explicit_never_or_misdiagnosed": int(excluded.sum()),
            "candidate_no_longer_has": int((selected & reversal & no_longer).sum()),
            "candidate_reason_missing": int((selected & reversal & ~reason_known).sum()),
            "sensitivity_exclude_explicit_retractions": {
                "n": len(canonical) - int(excluded.sum()),
                "events": int(canonical.label.sum()) - int(excluded.sum()),
                "unresolved_retractions_retained": int((selected & reversal & ~disputed).sum())}}


def _mhas_timing(joined: pd.DataFrame, candidate: pd.Series, event: pd.Series) -> dict:
    interview, interview_meta = parse_master_interview_date(joined.int_date_12, 12)
    follow15, meta15 = parse_master_interview_date(joined.int_date_15, 15)
    follow18, meta18 = parse_master_interview_date(joined.int_date_18, 18)
    exam = pd.to_datetime(joined.date_12, errors="coerce")
    plausible_exam = exam.where(exam.dt.year.between(2012, 2013))
    days = (plausible_exam - interview).dt.days
    months = (plausible_exam.dt.year * 12 + plausible_exam.dt.month) - (
        interview.dt.year * 12 + interview.dt.month)
    def policy(mask: pd.Series) -> dict:
        return {"screened_candidate_n": int((candidate & mask).sum()),
                "reported_events": int((event & mask).sum())}
    return {"interview_dates": interview_meta, "followup_2015_dates": meta15,
            "followup_2018_dates": meta18,
            "exam_date_recorded": int(exam.notna().sum()),
            "exam_years": _counts(exam.dt.year),
            "suspicious_pre_2012_exam_dates": int((exam.notna() & (exam.dt.year < 2012)).sum()),
            "candidate_suspicious_pre_2012_exam_dates": int((candidate & exam.notna() & (exam.dt.year < 2012)).sum()),
            "candidate_missing_interview_date": int((candidate & interview.isna()).sum()),
            "candidate_missing_exam_date": int((candidate & exam.isna()).sum()),
            "valid_plausible_pairs": int(days.notna().sum()),
            "days_exam_minus_interview": _summary(days),
            "before_interview": int((days < 0).sum()), "same_day": int((days == 0).sum()),
            "after_interview": int((days > 0).sum()),
            "candidate_month_order": {"before": int((candidate & months.lt(0)).sum()),
                                      "same": int((candidate & months.eq(0)).sum()),
                                      "after": int((candidate & months.gt(0)).sum())},
            "candidate_day_order": {"before": int((candidate & days.lt(0)).sum()),
                                    "same": int((candidate & days.eq(0)).sum()),
                                    "after": int((candidate & days.gt(0)).sum())},
            "screens_not_approved_cohorts": {
                "all_current_candidates": policy(pd.Series(True, index=joined.index)),
                "interview_index_all_predictors_available": policy(days.le(0)),
                "exam_0_to_30_days_after_interview": policy(days.between(0, 30)),
                "exam_within_plus_minus_30_days": policy(days.between(-30, 30)),
                "valid_dates_any_order": policy(days.notna())},
            "interview_after_2015": int((interview.notna() & follow15.notna() & (interview > follow15)).sum()),
            "2015_after_2018": int((follow15.notna() & follow18.notna() & (follow15 > follow18)).sum())}


def run_evidence_reconciliation(root: Path, master_file: Path, docs_dir: Path,
                                output_root: Path) -> Path:
    if not master_file.is_file():
        raise FileNotFoundError(f"Required official Master file missing: {master_file}")
    root, master_file, docs_dir = root.resolve(), master_file.resolve(), docs_dir.resolve()
    mappings = {name: json.loads(Path(f"configs/mappings/{name.lower()}_wave_m5.provisional.json").read_text())
                for name in ("HAALSI", "MHAS")}
    raw_h, load_h = HAALSIAdapter(mappings["HAALSI"]).load(root)
    raw_m, load_m = MHASAdapter(mappings["MHAS"]).load(root)
    main_h = root / mappings["HAALSI"]["files"]["main"]
    main_m = root / mappings["MHAS"]["files"]["main"]
    bio_path = root / mappings["MHAS"]["files"]["biomarker"]
    eol_path = root / mappings["MHAS"]["files"]["eol"]
    labels_h = pd.read_stata(main_h, iterator=True, convert_categoricals=False).value_labels()
    labels_m = pd.read_stata(main_m, iterator=True, convert_categoricals=False).value_labels()
    labels_m.update(pd.read_stata(bio_path, iterator=True, convert_categoricals=False).value_labels())
    haalsi_extra = pd.read_stata(main_h,
        columns=["W3CM321", "W3CM324", "W1C_CM_DIABETES_SRTRT"], convert_categoricals=False)
    raw_h = pd.concat([raw_h, haalsi_extra], axis=1)
    bio_extra = pd.read_stata(bio_path,
        columns=["cunicah", "np", "date_12", "sex_12"], convert_categoricals=False)
    bio_extra["__join_id"] = bio_extra.cunicah.astype("int64")*100 + bio_extra.np.astype("int64")
    bio_extra = bio_extra.rename(columns={"sex_12": "sex_12_bio"})
    raw_m = raw_m.merge(bio_extra[["__join_id", "date_12", "sex_12_bio"]],
                        on="__join_id", how="left", validate="one_to_one")
    master = pd.read_stata(master_file, columns=list(MASTER_COLUMNS), convert_categoricals=False)
    joined, join_report = join_mhas_master_followup(raw_m, master)
    audit_h = audit_public_cohort(raw_h, mappings["HAALSI"], value_labels=labels_h,
                                 load_accounting=load_h)
    audit_m = audit_public_cohort(joined, mappings["MHAS"], value_labels=labels_m,
                                 load_accounting=load_m)
    base_h, mid_h, end_h, stat_h = _status(raw_h, mappings["HAALSI"])
    base_m, mid_m, end_m, stat_m = _status(joined, mappings["MHAS"])
    free_h, free_m = base_h.eq(0), base_m.eq(0)
    h_selected = ("HAALSI:" + raw_h[mappings["HAALSI"]["fields"]["participant_id"]].astype(str)).isin(
        audit_h.canonical.participant_id)
    m_selected = ("MHAS:" + joined[mappings["MHAS"]["fields"]["participant_id"]].astype(str)).isin(
        audit_m.canonical.participant_id)
    sex = sex_agreement(joined.sex_12, joined.ragender)
    sex_candidate = sex_agreement(joined.loc[m_selected,"sex_12"], joined.loc[m_selected,"ragender"])
    sex_bio = sex_agreement(joined.sex_12, joined.sex_12_bio)
    # The biomarker date merge may suffix its sex column; report both raw sources.
    narrow_mapping = json.loads(json.dumps(mappings["HAALSI"]))
    narrow_mapping["fields"]["diabetes_reference"] = "W1C_CM_DIABETES_SRTRT"
    narrow = audit_public_cohort(raw_h, narrow_mapping, value_labels=labels_h)
    eol = pd.read_stata(eol_path, columns=list(EOL_COLUMNS),
                        convert_categoricals=False, convert_missing=True)
    if eol.unhhidnp.isna().any() or eol.unhhidnp.duplicated().any():
        raise ValueError("EOL unique person ID invalid")
    eol["__join_id"] = _numbers(eol.unhhidnp).astype("int64")
    eol = eol.drop(columns="unhhidnp")
    joined_eol = joined.merge(eol, on="__join_id", how="left", validate="one_to_one", indicator="__eol_match")
    eol_death_year = _numbers(joined_eol.raxyear)
    within_horizon_death = eol_death_year.between(2012, 2018)
    core_12, _ = parse_master_interview_date(joined.int_date_12, 12)
    core_15, _ = parse_master_interview_date(joined.int_date_15, 15)
    core_18, _ = parse_master_interview_date(joined.int_date_18, 18)
    last_core = core_12.copy()
    last_core.loc[joined.tipent_15.isin([1,2,3,4])] = core_15.loc[joined.tipent_15.isin([1,2,3,4])]
    last_core.loc[joined.tipent_18.isin([1,2,3,4])] = core_18.loc[joined.tipent_18.isin([1,2,3,4])]
    death_core_conflict = death_before_core_interview(joined_eol.raxyear, joined_eol.raxmonth, last_core)
    # Reproduce the existing conservative death-before-negative interview check.
    death_month = _numbers(joined.__eol_year) * 12 + _numbers(joined.__eol_month) - 1
    final_month = _numbers(joined.r5iwy) * 12 + _numbers(joined.r5iwm) - 1
    status_reviewed = stat_m.copy()
    status_reviewed.loc[(death_month < final_month) & end_m.eq(0) & mid_m.ne(1)] = "unknown"
    group = classify_mhas_observation(status_reviewed, joined.tipent_18, joined.fallecido_15,
                                       joined.fallecido_18, joined.tipne_15, joined.tipne_18,
                                       within_horizon_death)
    candidate_event = ("MHAS:" + joined[mappings["MHAS"]["fields"]["participant_id"]].astype(str)).map(
        audit_m.canonical.set_index("participant_id").label).eq(1).fillna(False)
    report = {
        "milestone": "5E", "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED", "primary_aric_mesa": "unchanged_separate_blocked",
        "public_protocol": "proposed_not_approved", "training_performed": False,
        "statistical_preprocessing_performed": False, "publication_test_split_created": False,
        "files": {p.name: {"sha256": file_sha256(p), "bytes": p.stat().st_size}
                  for p in (main_h, main_m, bio_path, eol_path, master_file)},
        "documentation": {role: ({"file": filename, "sha256": file_sha256(docs_dir / filename)}
                                 if (docs_dir / filename).is_file() else {"file": filename, "missing": True})
                          for role, filename in DOC_NAMES.items()},
        "cohorts": {"HAALSI": audit_h.report, "MHAS": audit_m.report},
        "master_join": join_report,
        "master_status_codes": {name: _counts(joined[name]) for name in
            ("res_biomarkers_12", "tipne_15", "tipent_15", "fallecido_15",
             "tipne_18", "tipent_18", "fallecido_18")},
        "mhas_timing": _mhas_timing(joined, m_selected, candidate_event),
        "mhas_sex": {"master_vs_harmonized_all": sex,
                     "master_vs_harmonized_current_candidate": sex_candidate,
                     "master_vs_biomarker_all": sex_bio,
                     "baseline_sex_replacement_candidate_n": len(audit_m.canonical)},
        "haalsi_diabetes": {"current_broad": {"n": len(audit_h.canonical),
                                             "events": int(audit_h.canonical.label.sum())},
                              "narrow_treatment_derived_sensitivity_only": {
                                  "n": len(narrow.canonical), "events": int(narrow.canonical.label.sum())}},
        "haalsi_reversals": _haalsi_reversals(raw_h, mappings["HAALSI"], audit_h.canonical, free_h),
        "observation_profiles": {
            "HAALSI": _observed_profile(raw_h, mappings["HAALSI"], free_h, stat_h, labels_h),
            "MHAS": _observed_profile(joined, mappings["MHAS"], free_m, stat_m, labels_m)},
        "mhas_attrition": {"baseline_free_categories": _counts(group.loc[free_m]),
                           "baseline_free_2018_core_interview": int((free_m & joined.tipent_18.isin([1,2,3,4])).sum()),
                           "baseline_free_2018_next_of_kin": int((free_m & joined.tipent_18.eq(5)).sum()),
                           "baseline_free_death_2012_2015": int((free_m & joined.fallecido_15.eq(1)).sum()),
                           "baseline_free_death_2015_2018": int((free_m & joined.fallecido_18.eq(1)).sum()),
                           "baseline_free_2015_deceased_without_nok": int((free_m & joined.tipne_15.eq(7)).sum()),
                           "baseline_free_2018_deceased_without_nok": int((free_m & joined.tipne_18.eq(8)).sum()),
                           "baseline_free_eol_record": int((free_m & joined_eol.__eol_match.eq("both")).sum()),
                           "baseline_free_eol_cvd_grouped_cause": int((free_m & joined_eol.ragcod.eq(2)).sum()),
                           "baseline_free_eol_stroke_cause": int((free_m & joined_eol.racod_m.eq(3)).sum()),
                           "baseline_free_eol_heart_cause": int((free_m & joined_eol.racod_m.eq(4)).sum()),
                           "baseline_free_eol_death_year_2012_2018": int((free_m & within_horizon_death).sum()),
                           "baseline_free_eol_cvd_cause_death_year_2012_2018": int((free_m & within_horizon_death & joined_eol.ragcod.eq(2)).sum()),
                           "baseline_free_eol_death_year_after_2018": int((free_m & eol_death_year.gt(2018)).sum()),
                           "baseline_free_eol_death_before_last_core_month": int((free_m & death_core_conflict).sum()),
                           "candidate_categories": _counts(group.loc[m_selected])},
        "mhas_eol": {name: _counts(joined_eol.loc[free_m, name]) for name in EOL_COLUMNS if name != "unhhidnp"},
        "harmonized_reversals": {
            disease: harmonized_persistence_violations(joined.loc[free_m, f"r4{disease}"],
                                                        joined.loc[free_m, f"r5{disease}"])
            for disease in ("hrtatte", "stroke")},
        "documentary_limits": ["Raw MHAS 2012/2015/2018 Section C respondent files are absent; codebook frequencies are not raw-answer comparisons.",
            "MHAS 2024 Master is retrospective administrative metadata, not a baseline predictor source.",
            "HAALSI linked participant death dates remain unavailable in this release.",
            "No exact first MI/stroke dates; no finalized index or clinical approval."],
    }
    destination = output_root / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "aggregate_evidence.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--master-file", type=Path, required=True)
    parser.add_argument("--docs-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("results/public_evidence_reconciliation"))
    args = parser.parse_args()
    path = run_evidence_reconciliation(args.data_root, args.master_file, args.docs_dir, args.output_root)
    print(f"Aggregate-only evidence: {path}; scientific readiness BLOCKED")


if __name__ == "__main__":
    main()
