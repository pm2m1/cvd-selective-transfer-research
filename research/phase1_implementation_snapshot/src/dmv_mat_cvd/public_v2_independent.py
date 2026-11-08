"""Independent raw-field HAALSI check; no public cohort constructor is imported.

Only aggregate counts leave this module. This is an audit cross-check, not an
alternative cohort definition or a fitted preprocessing step.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

import numpy as np
import pandas as pd


def _clean(frame: pd.DataFrame, labels: dict, field: str) -> pd.Series:
    values = pd.to_numeric(frame[field], errors="coerce")
    missing = {int(code) for code, name in labels.get(field, {}).items()
               if str(name).strip().lower().startswith((".e = empty", ".d = don't know", ".r = refused"))}
    return values.mask(values.isin(missing))


def _yes(frame: pd.DataFrame, labels: dict, field: str) -> pd.Series:
    value = _clean(frame, labels, field)
    if not value.dropna().isin([1, 2]).all():
        raise ValueError(f"Unexpected HAALSI answer in {field}")
    return value.map({1: 1, 2: 0})


def _month(frame: pd.DataFrame, labels: dict, year: str, month: str) -> pd.Series:
    y, m = _clean(frame, labels, year), _clean(frame, labels, month)
    return (y * 12 + m - 1).where(y.notna() & m.between(1, 12) & y.eq(np.floor(y)) & m.eq(np.floor(m)))


def independent_haalsi_screen(frame: pd.DataFrame, labels: dict, mapping: dict) -> dict:
    """Recalculate v1/v2 masks directly and return only aggregate diagnostics."""
    f = mapping["fields"]
    if frame[f["participant_id"]].isna().any() or frame[f["participant_id"]].duplicated().any():
        raise ValueError("HAALSI respondent IDs missing or repeated")
    slots = sorted(int(m.group(1)) for name in frame
                   if (m := re.fullmatch(r"W1HHMEMBERSEX_(\d+)_", name)))
    matches = pd.Series(0, index=frame.index)
    sex = pd.Series(np.nan, index=frame.index)
    for slot in slots:
        key = f"W1HHMEMBERPRIMKEY_{slot}_"
        if key not in frame:
            raise ValueError("Wave-1 roster key/sex pair incomplete")
        hit = frame[key].astype("string").eq(frame[f["participant_id"]].astype("string")).fillna(False)
        matches += hit.astype(int)
        sex.loc[hit] = pd.to_numeric(frame.loc[hit, f"W1HHMEMBERSEX_{slot}_"], errors="coerce")
    if matches.gt(1).any() or (sex.notna() & ~sex.isin([1, 2])).any():
        raise ValueError("Ambiguous or invalid Wave-1 roster sex")
    combined = _clean(frame, labels, f["sex"])

    htn = _clean(frame, labels, "W1CM002")
    ever = _clean(frame, labels, "W1CM004")
    raw_current = pd.to_numeric(frame["W1CM005"], errors="coerce")
    current = _clean(frame, labels, "W1CM005")
    if not current.dropna().isin([1, 2]).all():
        raise ValueError("Invalid current BP treatment")
    route_no_htn = raw_current.isna() & htn.eq(2)
    route_never = raw_current.isna() & htn.eq(1) & ever.eq(2)
    treatment_old = current.copy()
    treatment_old.loc[route_no_htn] = 2
    treatment_new = treatment_old.copy()
    treatment_new.loc[route_never] = 2
    # Neither a special response code nor an unexplained blank is a no.

    male = _clean(frame, labels, "W1CM007_MALES")
    female = _clean(frame, labels, "W1CM007_FEMALES")
    if not male.dropna().isin([1, 2]).all() or not female.dropna().isin([1, 2]).all():
        raise ValueError("Invalid doctor-report diabetes answer")
    doctor = male.where(sex.eq(1), female.where(sex.eq(2)))
    off_route = (sex.eq(1) & female.notna()) | (sex.eq(2) & male.notna())
    doctor.loc[off_route] = np.nan
    broad = _clean(frame, labels, f["diabetes_reference"])

    continuous = ("age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl")
    numeric = {name: _clean(frame, labels, f[name]) * mapping["unit_factors"][name]
               for name in continuous}
    numeric_ok = pd.Series(True, index=frame.index)
    for value in numeric.values():
        numeric_ok &= value.notna() & np.isfinite(value) & value.gt(0)
    numeric_ok &= numeric["sbp"] > numeric["dbp"]
    smoke_ever = _yes(frame, labels, f["smoke_ever"])
    smoke_now = _yes(frame, labels, f["smoke_now"])
    if (smoke_ever.eq(0) & smoke_now.eq(1)).any():
        raise ValueError("Contradictory smoking answers")
    smoke_ok = smoke_ever.eq(0) | (smoke_ever.eq(1) & smoke_now.isin([0, 1]))

    bh = _yes(frame, labels, f["baseline_heart_attack"])
    bs = _yes(frame, labels, f["baseline_stroke"])
    free = bh.eq(0) & bs.eq(0)
    ih = _yes(frame, labels, f["intermediate_heart_attack"])
    fh = _yes(frame, labels, f["final_heart_attack"])
    istroke = _yes(frame, labels, f["intermediate_stroke"])
    fstroke = _yes(frame, labels, f["final_stroke"])
    mid_positive = ih.eq(1) | istroke.eq(1)
    final_positive = fh.eq(1) | fstroke.eq(1)
    final_negative = fh.eq(0) & fstroke.eq(0)
    initial_positive = mid_positive | final_positive
    initial_negative = final_negative & ~mid_positive
    index_month = _month(frame, labels, f["index_year"], f["index_month"])
    middle_month = _month(frame, labels, f["intermediate_year"], f["intermediate_month"])
    final_month = _month(frame, labels, f["final_year"], f["final_month"])
    bad_time = ((middle_month.notna() & index_month.notna() & middle_month.le(index_month)) |
                (final_month.notna() & index_month.notna() & final_month.le(index_month)) |
                (middle_month.notna() & final_month.notna() & final_month.lt(middle_month)))
    initial_observed = (initial_positive | initial_negative) & ~bad_time
    reason_h = _clean(frame, labels, "W3CM324")
    reason_s = _clean(frame, labels, "W3CM321")
    if not reason_h.dropna().isin([1, 2, 3, 4, 5]).all() or not reason_s.dropna().isin([1, 2, 3, 4, 5]).all():
        raise ValueError("Unexpected reversal reason")
    revoked_h = ih.eq(1) & fh.eq(0) & (reason_h.isin([1, 3, 5]) | reason_h.isna())
    revoked_s = istroke.eq(1) & fstroke.eq(0) & (reason_s.isin([1, 3, 5]) | reason_s.isna())
    valid_h = fh.eq(1) | (ih.eq(1) & ~revoked_h)
    valid_s = fstroke.eq(1) | (istroke.eq(1) & ~revoked_s)
    uncertain_reversal = (revoked_h | revoked_s) & ~(valid_h | valid_s)
    observed_new = initial_observed & ~uncertain_reversal
    positive_new = initial_positive & observed_new

    common = free & numeric_ok & smoke_ok & sex.isin([1, 2])
    prior_complete = common & broad.isin([1, 2]) & treatment_old.isin([1, 2])
    broad_new = common & broad.isin([1, 2]) & treatment_new.isin([1, 2])
    doctor_new = common & doctor.isin([1, 2]) & treatment_new.isin([1, 2])
    nine = common & treatment_new.isin([1, 2])
    def tally(mask: pd.Series, observed: pd.Series = observed_new) -> dict:
        selected = mask & observed
        return {"n": int(selected.sum()), "events": int((selected & positive_new).sum())}
    prior = prior_complete & observed_new
    broad_selected = broad_new & observed_new
    doctor_selected = doctor_new & observed_new
    newly_in_broad = broad_selected & ~prior
    newly_in_doctor = doctor_selected & ~broad_selected
    old_only_broad = prior & ~broad_selected
    broad_only_doctor = broad_selected & ~doctor_selected
    selected_disputed = doctor_new & initial_observed & uncertain_reversal
    def selected_reason(code: int) -> int:
        return int((selected_disputed & ((revoked_h & reason_h.eq(code)) |
                                         (revoked_s & reason_s.eq(code)))).sum())
    selected_unexplained = int((selected_disputed &
        ((revoked_h & reason_h.isna()) | (revoked_s & reason_s.isna()))).sum())
    return {
        "raw_n": int(len(frame)),
        "wave1_roster": {"unique": int(matches.eq(1).sum()), "unmatched": int(matches.eq(0).sum()),
                         "multiple": int(matches.gt(1).sum()), "known": int(sex.isin([1, 2]).sum()),
                         "agree_combined": int((sex.isin([1, 2]) & sex.eq(combined)).sum()),
                         "contradict_combined": int((sex.isin([1, 2]) & combined.isin([1, 2]) & sex.ne(combined)).sum())},
        "medication": {"explicit_yes": int(current.eq(1).sum()), "explicit_no": int(current.eq(2).sum()),
                       "blank_no_hypertension": int(route_no_htn.sum()), "blank_never_prescribed": int(route_never.sum()),
                       "special_response": int((raw_current.notna() & current.isna()).sum()),
                       "unexplained_blank": int((raw_current.isna() & ~(route_no_htn | route_never)).sum())},
        "diabetes": {"doctor_known": int(doctor.isin([1, 2]).sum()), "doctor_yes": int(doctor.eq(1).sum()),
                     "doctor_no": int(doctor.eq(2).sum()), "off_route": int(off_route.sum())},
        "waterfall": {"baseline_free": int(free.sum()), "ten_doctor_complete": int(doctor_new.sum()),
                      "ten_doctor_old_observed": int((doctor_new & initial_observed).sum()),
                      "ten_doctor_disputed_selected": int((doctor_new & initial_observed & uncertain_reversal).sum()),
                      "prior_5f": tally(prior_complete), "broader_treatment_route": tally(broad_new),
                      "doctor_diabetes": tally(doctor_new), "nine_no_diabetes": tally(nine)},
        "membership_changes": {"new_broad_vs_prior": tally(newly_in_broad),
                               "lost_broad_vs_prior": tally(old_only_broad),
                               "new_doctor_vs_broad": tally(newly_in_doctor),
                               "lost_doctor_vs_broad": tally(broad_only_doctor)},
        "reversals": {"uncertain_all": int(uncertain_reversal.sum()),
                      "independent_other_positive": int(((revoked_h | revoked_s) & (valid_h | valid_s)).sum()),
                      "selected_uncertain": int(selected_disputed.sum()),
                      "selected_heart_component_retracted": int((selected_disputed & revoked_h).sum()),
                      "selected_stroke_component_retracted": int((selected_disputed & revoked_s).sum()),
                      "selected_never_had": selected_reason(1),
                      "selected_misdiagnosed": selected_reason(3),
                      "selected_other_reason": selected_reason(5),
                      "selected_unexplained": selected_unexplained,
                      "selected_no_longer_has_retained": int((doctor_new & initial_observed &
                          ((ih.eq(1) & fh.eq(0) & reason_h.eq(2)) |
                           (istroke.eq(1) & fstroke.eq(0) & reason_s.eq(2)))).sum())},
        "no_participant_records_written": True,
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, default=Path("configs/mappings/haalsi_wave_m5.provisional.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mapping = json.loads(args.mapping.read_text())
    path = args.data_root / mapping["files"]["main"]
    reader = pd.read_stata(path, iterator=True, convert_categoricals=False)
    labels = reader.value_labels()
    columns = set(reader.variable_labels())
    needed = {value for value in mapping["fields"].values() if isinstance(value, str)}
    needed |= {"W1CM002", "W1CM004", "W1CM005", "W1CM007_MALES", "W1CM007_FEMALES", "W3CM321", "W3CM324"}
    needed |= {name for name in columns if re.fullmatch(r"W1HHMEMBER(?:PRIMKEY|SEX)_\d+_", name)}
    frame = pd.read_stata(path, columns=sorted(needed), convert_categoricals=False)
    result = independent_haalsi_screen(frame, labels, mapping)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as out:
        out.write(json.dumps(result, indent=2) + "\n")
    print("Independent HAALSI aggregate check written")


if __name__ == "__main__":
    main()
