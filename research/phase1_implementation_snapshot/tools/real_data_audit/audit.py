from pathlib import Path
import re
import json
import warnings

import numpy as np
import pandas as pd
import pyreadstat

warnings.filterwarnings("ignore")

ROOT = Path(".")
OUT = ROOT / "audit_outputs"
OUT.mkdir(exist_ok=True)

FILES = {
    "mhas_main": ROOT / "H_MHAS_d.dta",
    "mhas_biomarker": ROOT / "sect_l_biomarkers_2012.dta",
    "mhas_eol": ROOT / "GH_MHAS_EOL_c.dta",
    "haalsi": ROOT / "36633-0001-Data.dta",
}

for name, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(f"Missing {name}: {path}")

def read_dta(path):
    print(f"\nReading {path.name} ...")
    df, meta = pyreadstat.read_dta(
        str(path),
        apply_value_formats=False,
    )
    labels = {}
    try:
        labels = {
            str(k): ("" if v is None else str(v))
            for k, v in meta.column_names_to_labels.items()
        }
    except Exception:
        labels = {str(c): "" for c in df.columns}

    print(f"  rows={len(df):,}, columns={len(df.columns):,}")
    return df, labels

def find_col(df, *names):
    lut = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lut:
            return lut[n.lower()]
    return None

def num(s):
    return pd.to_numeric(s, errors="coerce")

def canonical_id(s):
    return num(s).round().astype("Int64")

def schema_table(df, labels, dataset):
    nonmissing = df.notna().sum()
    rows = []
    n = len(df)

    for c in df.columns:
        nn = int(nonmissing[c])
        rows.append({
            "dataset": dataset,
            "variable": c,
            "label": labels.get(c, ""),
            "dtype": str(df[c].dtype),
            "n_total": n,
            "n_nonmissing": nn,
            "n_missing": n - nn,
            "missing_pct": round(100 * (n - nn) / n, 4) if n else np.nan,
        })

    return pd.DataFrame(rows)

def candidates(df, labels, patterns, dataset):
    compiled = [re.compile(p, re.I) for p in patterns]
    rows = []

    for c in df.columns:
        label = labels.get(c, "")
        text = f"{c} {label}"

        if any(p.search(text) for p in compiled):
            s = df[c]
            vals = s.dropna().unique()[:12]

            rows.append({
                "dataset": dataset,
                "variable": c,
                "label": label,
                "n_nonmissing": int(s.notna().sum()),
                "missing_pct": round(float(s.isna().mean() * 100), 4),
                "sample_values": " | ".join(map(str, vals)),
            })

    return pd.DataFrame(rows)

def choose_candidate(df, labels, include_patterns, prefer_patterns=None,
                     reject_patterns=None):
    prefer_patterns = prefer_patterns or []
    reject_patterns = reject_patterns or []

    scored = []

    for c in df.columns:
        label = labels.get(c, "")
        text = f"{c} {label}".lower()

        if not any(re.search(p, text, re.I) for p in include_patterns):
            continue

        score = 0

        for p in include_patterns:
            if re.search(p, text, re.I):
                score += 2

        for p in prefer_patterns:
            if re.search(p, text, re.I):
                score += 8

        for p in reject_patterns:
            if re.search(p, text, re.I):
                score -= 10

        score += min(df[c].notna().sum() / max(len(df), 1), 1)

        scored.append((score, c, label))

    scored.sort(reverse=True)

    return scored[0][1] if scored else None

def save_candidates(df, labels, patterns, filename, dataset):
    x = candidates(df, labels, patterns, dataset)
    x.to_csv(OUT / filename, index=False)
    return x

def month_index(year, month):
    y = num(year)
    m = num(month)

    valid = (
        y.notna() &
        m.notna() &
        m.between(1, 12)
    )

    out = pd.Series(np.nan, index=year.index, dtype=float)
    out.loc[valid] = y.loc[valid] * 12 + (m.loc[valid] - 1)

    return out


# ============================================================
# PART A — MHAS
# ============================================================

main, main_labels = read_dta(FILES["mhas_main"])
bio, bio_labels = read_dta(FILES["mhas_biomarker"])
eol, eol_labels = read_dta(FILES["mhas_eol"])

schema_table(main, main_labels, "MHAS_MAIN").to_csv(
    OUT / "mhas_main_schema.csv", index=False
)
schema_table(bio, bio_labels, "MHAS_BIOMARKER").to_csv(
    OUT / "mhas_biomarker_schema.csv", index=False
)
schema_table(eol, eol_labels, "MHAS_EOL").to_csv(
    OUT / "mhas_eol_schema.csv", index=False
)

mhas_patterns = [
    r"\bage\b",
    r"gender|sex",
    r"systol",
    r"diastol",
    r"\bbmi\b|body mass index",
    r"cholesterol|\bhdl\b",
    r"hba1c|a1c|glycat|glycosyl",
    r"smok",
    r"diabet",
    r"hypertens",
    r"blood pressure",
    r"heart attack",
    r"myocard",
    r"stroke",
    r"death",
    r"cause",
    r"interview.*month",
    r"interview.*year",
]

save_candidates(
    main, main_labels, mhas_patterns,
    "mhas_main_candidates.csv", "MHAS_MAIN"
)
save_candidates(
    bio, bio_labels, mhas_patterns,
    "mhas_biomarker_candidates.csv", "MHAS_BIOMARKER"
)
save_candidates(
    eol, eol_labels, mhas_patterns,
    "mhas_eol_candidates.csv", "MHAS_EOL"
)

# ------------------------------------------------------------
# Construct / validate person IDs
# ------------------------------------------------------------

main_id = find_col(main, "unhhidnp")
eol_id = find_col(eol, "unhhidnp")
bio_id = find_col(bio, "unhhidnp")

if main_id is None:
    raise RuntimeError("MHAS main file has no unhhidnp.")
if eol_id is None:
    raise RuntimeError("MHAS EOL file has no unhhidnp.")

main["_audit_id"] = canonical_id(main[main_id])
eol["_audit_id"] = canonical_id(eol[eol_id])

if bio_id is not None:
    bio["_audit_id"] = canonical_id(bio[bio_id])
else:
    cunicah = find_col(bio, "cunicah", "unhhid")
    np_col = find_col(bio, "np")

    if cunicah is None or np_col is None:
        raise RuntimeError(
            "Could not build MHAS biomarker ID: "
            "neither unhhidnp nor cunicah+np found."
        )

    bio["_audit_id"] = (
        num(bio[cunicah]) * 100 +
        num(bio[np_col])
    ).round().astype("Int64")

id_audit = pd.DataFrame([
    {
        "dataset": "MHAS biomarker",
        "rows": len(bio),
        "nonmissing_ids": int(bio["_audit_id"].notna().sum()),
        "unique_ids": int(bio["_audit_id"].nunique(dropna=True)),
        "duplicate_id_rows": int(bio["_audit_id"].duplicated(keep=False).sum()),
    },
    {
        "dataset": "MHAS main",
        "rows": len(main),
        "nonmissing_ids": int(main["_audit_id"].notna().sum()),
        "unique_ids": int(main["_audit_id"].nunique(dropna=True)),
        "duplicate_id_rows": int(main["_audit_id"].duplicated(keep=False).sum()),
    },
    {
        "dataset": "MHAS EOL",
        "rows": len(eol),
        "nonmissing_ids": int(eol["_audit_id"].notna().sum()),
        "unique_ids": int(eol["_audit_id"].nunique(dropna=True)),
        "duplicate_id_rows": int(eol["_audit_id"].duplicated(keep=False).sum()),
    },
])
id_audit.to_csv(OUT / "mhas_id_audit.csv", index=False)

# ------------------------------------------------------------
# Main harmonized variables we expect from the official codebook
# ------------------------------------------------------------

expected_main = [
    "r3agey",
    "ragender",
    "r3systo",
    "r3diasto",
    "r3mbmi",
    "r3smokev",
    "r3smoken",
    "r3diabe",
    "r3rxhibp",
    "r3hrtatte",
    "r3stroke",
    "r3iwm",
    "r3iwy",
    "r4hrtatte",
    "r4stroke",
    "r4iwm",
    "r4iwy",
    "r5hrtatte",
    "r5stroke",
    "r5iwm",
    "r5iwy",
    "r6iwm",
    "r6iwy",
]

resolved = {}
for v in expected_main:
    resolved[v] = find_col(main, v)

expected_status = pd.DataFrame([
    {
        "requested_variable": k,
        "actual_variable": v,
        "found": v is not None,
        "label": main_labels.get(v, "") if v else "",
    }
    for k, v in resolved.items()
])
expected_status.to_csv(
    OUT / "mhas_expected_variable_status.csv",
    index=False
)

# ------------------------------------------------------------
# Identify objective biomarker variables
# ------------------------------------------------------------

tc = choose_candidate(
    bio, bio_labels,
    include_patterns=[r"cholesterol"],
    prefer_patterns=[
        r"chol[_ ]?rev",
        r"revised.*cholesterol",
        r"total cholesterol",
    ],
    reject_patterns=[
        r"hdl",
        r"test",
        r"flag",
        r"reason",
        r"sample",
        r"selected",
        r"refus",
    ]
)

hdl = choose_candidate(
    bio, bio_labels,
    include_patterns=[r"\bhdl\b|high.?density lipoprotein"],
    prefer_patterns=[
        r"hdl.*mg",
        r"high.?density lipoprotein.*cholesterol",
    ],
    reject_patterns=[
        r"flag",
        r"reason",
        r"sample",
        r"selected",
        r"refus",
    ]
)

hba1c = choose_candidate(
    bio, bio_labels,
    include_patterns=[
        r"hba1c",
        r"\ba1c\b",
        r"glycat",
        r"glycosyl",
    ],
    prefer_patterns=[
        r"hba1c",
        r"a1c",
    ],
    reject_patterns=[
        r"flag",
        r"reason",
        r"sample",
        r"selected",
        r"refus",
    ]
)

selected_biomarkers = pd.DataFrame([
    {
        "concept": "total_cholesterol",
        "selected_variable": tc,
        "label": bio_labels.get(tc, "") if tc else "",
        "n_nonmissing": int(bio[tc].notna().sum()) if tc else np.nan,
    },
    {
        "concept": "hdl",
        "selected_variable": hdl,
        "label": bio_labels.get(hdl, "") if hdl else "",
        "n_nonmissing": int(bio[hdl].notna().sum()) if hdl else np.nan,
    },
    {
        "concept": "hba1c",
        "selected_variable": hba1c,
        "label": bio_labels.get(hba1c, "") if hba1c else "",
        "n_nonmissing": int(bio[hba1c].notna().sum()) if hba1c else np.nan,
    },
])
selected_biomarkers.to_csv(
    OUT / "mhas_selected_biomarkers.csv",
    index=False
)

# ------------------------------------------------------------
# Build MHAS analysis cohort
# ------------------------------------------------------------

main_keep = ["_audit_id"] + [
    v for v in resolved.values()
    if v is not None
]

main_small = main[main_keep].copy()

bio_small = bio.copy()

if tc is not None:
    bio_small["_tc"] = num(bio_small[tc])
if hdl is not None:
    bio_small["_hdl"] = num(bio_small[hdl])
if hba1c is not None:
    bio_small["_hba1c"] = num(bio_small[hba1c])

# Ensure unique main person row
if main_small["_audit_id"].duplicated().any():
    print("WARNING: duplicate IDs in main file; retaining first row.")
    main_small = main_small.drop_duplicates("_audit_id", keep="first")

cohort = bio_small.merge(
    main_small,
    on="_audit_id",
    how="left",
    indicator="_merge_main",
    validate="many_to_one",
)

# Merge EOL fields
eol_vars = ["_audit_id"]
for name in ["raxyear", "raxmonth", "ragcod", "racod_m"]:
    c = find_col(eol, name)
    if c is not None:
        eol_vars.append(c)

eol_small = eol[eol_vars].copy()

if eol_small["_audit_id"].duplicated().any():
    print("WARNING: duplicate IDs in EOL file; retaining first row.")
    eol_small = eol_small.drop_duplicates("_audit_id", keep="first")

cohort = cohort.merge(
    eol_small,
    on="_audit_id",
    how="left",
    indicator="_merge_eol",
    validate="many_to_one",
)

# ------------------------------------------------------------
# Standardized feature aliases
# ------------------------------------------------------------

alias_map = {
    "_age": resolved["r3agey"],
    "_sex": resolved["ragender"],
    "_sbp": resolved["r3systo"],
    "_dbp": resolved["r3diasto"],
    "_bmi": resolved["r3mbmi"],
    "_smoke_ever": resolved["r3smokev"],
    "_smoke_now": resolved["r3smoken"],
    "_diabetes": resolved["r3diabe"],
    "_antihyp": resolved["r3rxhibp"],
    "_base_mi": resolved["r3hrtatte"],
    "_base_stroke": resolved["r3stroke"],
}

for new, old in alias_map.items():
    if old is not None:
        cohort[new] = num(cohort[old])
    else:
        cohort[new] = np.nan

# Three-category smoking:
# 0 never, 1 former, 2 current
cohort["_smoking3"] = np.nan
cohort.loc[cohort["_smoke_ever"] == 0, "_smoking3"] = 0
cohort.loc[
    (cohort["_smoke_ever"] == 1) &
    (cohort["_smoke_now"] == 0),
    "_smoking3"
] = 1
cohort.loc[cohort["_smoke_now"] == 1, "_smoking3"] = 2

# Baseline CVD-free
cohort["_baseline_cvd_known"] = (
    cohort["_base_mi"].isin([0, 1]) &
    cohort["_base_stroke"].isin([0, 1])
)

cohort["_baseline_cvd_free"] = (
    cohort["_baseline_cvd_known"] &
    (cohort["_base_mi"] == 0) &
    (cohort["_base_stroke"] == 0)
)

# ------------------------------------------------------------
# Missingness
# ------------------------------------------------------------

feature_cols = [
    "_age",
    "_sex",
    "_sbp",
    "_dbp",
    "_bmi",
    "_tc",
    "_hdl",
    "_smoking3",
    "_diabetes",
    "_antihyp",
]

feature_cols = [c for c in feature_cols if c in cohort.columns]

def missingness_for(mask, population_name):
    d = cohort.loc[mask, feature_cols]

    rows = []
    for c in feature_cols:
        rows.append({
            "population": population_name,
            "feature": c,
            "n": len(d),
            "n_nonmissing": int(d[c].notna().sum()),
            "n_missing": int(d[c].isna().sum()),
            "missing_pct": round(float(d[c].isna().mean() * 100), 4)
            if len(d) else np.nan,
        })

    return pd.DataFrame(rows)

all_mask = pd.Series(True, index=cohort.index)
free_mask = cohort["_baseline_cvd_free"]

miss = pd.concat([
    missingness_for(all_mask, "all_biomarker_rows"),
    missingness_for(free_mask, "baseline_cvd_free"),
], ignore_index=True)

miss.to_csv(OUT / "mhas_missingness.csv", index=False)

required_complete = [
    "_age",
    "_sex",
    "_sbp",
    "_dbp",
    "_bmi",
    "_tc",
    "_hdl",
    "_smoking3",
    "_diabetes",
    "_antihyp",
]

missing_required_columns = [
    c for c in required_complete
    if c not in cohort.columns
]

if not missing_required_columns:
    cohort["_complete_predictors"] = cohort[required_complete].notna().all(axis=1)
else:
    cohort["_complete_predictors"] = False

analysis_mask = (
    cohort["_baseline_cvd_free"] &
    cohort["_complete_predictors"]
)

# ------------------------------------------------------------
# Exact month-level 5-year mortality
# ------------------------------------------------------------

base_y = resolved["r3iwy"]
base_m = resolved["r3iwm"]

if base_y is not None and base_m is not None:
    cohort["_baseline_month"] = month_index(
        cohort[base_y],
        cohort[base_m],
    )
else:
    cohort["_baseline_month"] = np.nan

death_y = find_col(cohort, "raxyear")
death_m = find_col(cohort, "raxmonth")

if death_y is not None and death_m is not None:
    cohort["_death_month"] = month_index(
        cohort[death_y],
        cohort[death_m],
    )
else:
    cohort["_death_month"] = np.nan

cohort["_months_to_death"] = (
    cohort["_death_month"] -
    cohort["_baseline_month"]
)

cohort["_death_within_5y"] = (
    cohort["_months_to_death"].between(0, 60)
)

# Determine whether we know someone survived beyond 5 years
followup_month_cols = []

for wave in [5, 6]:
    y = resolved.get(f"r{wave}iwy")
    m = resolved.get(f"r{wave}iwm")

    if y is not None and m is not None:
        cname = f"_w{wave}_month"
        cohort[cname] = month_index(cohort[y], cohort[m])
        followup_month_cols.append(cname)

if followup_month_cols:
    cohort["_latest_late_followup"] = cohort[
        followup_month_cols
    ].max(axis=1, skipna=True)
else:
    cohort["_latest_late_followup"] = np.nan

cohort["_months_to_late_followup"] = (
    cohort["_latest_late_followup"] -
    cohort["_baseline_month"]
)

cohort["_death_after_5y"] = (
    cohort["_months_to_death"] > 60
)

cohort["_observed_alive_5y"] = (
    cohort["_months_to_late_followup"] >= 60
)

cohort["_known_5y_mortality"] = (
    cohort["_death_within_5y"] |
    cohort["_death_after_5y"] |
    cohort["_observed_alive_5y"]
)

cohort["_allcause5"] = np.nan
cohort.loc[
    cohort["_known_5y_mortality"],
    "_allcause5"
] = 0
cohort.loc[
    cohort["_death_within_5y"],
    "_allcause5"
] = 1

# CVD cause
ragcod = find_col(cohort, "ragcod")
racod_m = find_col(cohort, "racod_m")

cohort["_cvd_cause"] = False
cohort["_cause_known"] = False

if ragcod is not None:
    rg = num(cohort[ragcod])
    cohort["_cvd_cause"] |= (rg == 2)
    cohort["_cause_known"] |= rg.notna()

if racod_m is not None:
    rc = num(cohort[racod_m])
    cohort["_cvd_cause"] |= rc.isin([3, 4])
    cohort["_cause_known"] |= rc.notna()

cohort["_cvddeath5"] = np.nan

# Known alive past 5 years / death after horizon = no CVD death by 5 years
non_event_known = (
    cohort["_death_after_5y"] |
    cohort["_observed_alive_5y"]
)

cohort.loc[non_event_known, "_cvddeath5"] = 0

# Death within horizon with known cause
within_and_knowncause = (
    cohort["_death_within_5y"] &
    cohort["_cause_known"]
)

cohort.loc[
    within_and_knowncause,
    "_cvddeath5"
] = 0

cohort.loc[
    cohort["_death_within_5y"] &
    cohort["_cvd_cause"],
    "_cvddeath5"
] = 1

# ------------------------------------------------------------
# Approximate incident heart attack / stroke by Wave 4 and Wave 5
# ------------------------------------------------------------

def incident_by_wave(wave):
    h = resolved.get(f"r{wave}hrtatte")
    s = resolved.get(f"r{wave}stroke")

    out = pd.Series(np.nan, index=cohort.index, dtype=float)

    if h is None or s is None:
        return out

    hv = num(cohort[h])
    sv = num(cohort[s])

    event = (hv == 1) | (sv == 1)

    # A negative can only be asserted if both are explicitly negative
    negative = (hv == 0) & (sv == 0)

    out.loc[negative] = 0
    out.loc[event] = 1

    return out

cohort["_incident_cvd_w4"] = incident_by_wave(4)
cohort["_incident_cvd_w5"] = incident_by_wave(5)

# Only baseline CVD-free participants are eligible
cohort.loc[
    ~cohort["_baseline_cvd_free"],
    ["_incident_cvd_w4", "_incident_cvd_w5"]
] = np.nan

# ------------------------------------------------------------
# Cohort accounting
# ------------------------------------------------------------

def n_event(mask, outcome):
    s = cohort.loc[mask, outcome]
    known = s.notna()

    n = int(known.sum())
    events = int((s[known] == 1).sum())

    return {
        "n_with_known_outcome": n,
        "events": events,
        "non_events": n - events,
        "event_rate_pct": round(100 * events / n, 4) if n else np.nan,
    }

accounting_rows = [
    {
        "stage": "raw_biomarker_rows",
        "n": len(bio),
    },
    {
        "stage": "unique_biomarker_ids",
        "n": int(bio["_audit_id"].nunique(dropna=True)),
    },
    {
        "stage": "merged_to_main",
        "n": int((cohort["_merge_main"] == "both").sum()),
    },
    {
        "stage": "baseline_cvd_status_known",
        "n": int(cohort["_baseline_cvd_known"].sum()),
    },
    {
        "stage": "baseline_cvd_free",
        "n": int(cohort["_baseline_cvd_free"].sum()),
    },
    {
        "stage": "complete_common_predictors",
        "n": int(cohort["_complete_predictors"].sum()),
    },
    {
        "stage": "baseline_cvd_free_and_complete_predictors",
        "n": int(analysis_mask.sum()),
    },
]

pd.DataFrame(accounting_rows).to_csv(
    OUT / "mhas_cohort_accounting.csv",
    index=False
)

event_rows = []

for population_name, mask in [
    ("baseline_cvd_free", free_mask),
    ("baseline_cvd_free_complete_predictors", analysis_mask),
]:
    for outcome, label in [
        ("_allcause5", "5y_all_cause_death"),
        ("_cvddeath5", "5y_cvd_death"),
        ("_incident_cvd_w4", "incident_MI_or_stroke_by_W4_approx_3y"),
        ("_incident_cvd_w5", "incident_MI_or_stroke_by_W5_approx_6y"),
    ]:
        r = n_event(mask, outcome)
        r["population"] = population_name
        r["outcome"] = label
        event_rows.append(r)

events = pd.DataFrame(event_rows)
events.to_csv(
    OUT / "mhas_event_counts.csv",
    index=False
)

# ------------------------------------------------------------
# Merge audit
# ------------------------------------------------------------

merge_audit = pd.DataFrame([
    {
        "metric": "biomarker_rows",
        "value": len(bio),
    },
    {
        "metric": "biomarker_unique_ids",
        "value": int(bio["_audit_id"].nunique(dropna=True)),
    },
    {
        "metric": "biomarker_rows_matched_main",
        "value": int((cohort["_merge_main"] == "both").sum()),
    },
    {
        "metric": "biomarker_rows_with_EOL_record",
        "value": int((cohort["_merge_eol"] == "both").sum()),
    },
    {
        "metric": "baseline_CVD_free",
        "value": int(free_mask.sum()),
    },
    {
        "metric": "baseline_CVD_free_complete_predictors",
        "value": int(analysis_mask.sum()),
    },
])

merge_audit.to_csv(
    OUT / "mhas_merge_audit.csv",
    index=False
)

# Aggregate-only distribution checks
dist_rows = []

for c in [
    "_base_mi",
    "_base_stroke",
    "_diabetes",
    "_antihyp",
    "_smoking3",
    "_allcause5",
    "_cvddeath5",
    "_incident_cvd_w4",
    "_incident_cvd_w5",
]:
    if c not in cohort:
        continue

    vc = cohort[c].value_counts(dropna=False)

    for value, count in vc.items():
        dist_rows.append({
            "variable": c,
            "value": str(value),
            "count": int(count),
        })

pd.DataFrame(dist_rows).to_csv(
    OUT / "mhas_aggregate_distributions.csv",
    index=False
)

# ============================================================
# PART B — HAALSI
# ============================================================

print("\nMHAS calculations complete.")
print("Releasing MHAS memory before HAALSI ...")

del main, bio, eol, main_small, bio_small, eol_small

haalsi, haalsi_labels = read_dta(FILES["haalsi"])

schema_table(
    haalsi,
    haalsi_labels,
    "HAALSI"
).to_csv(
    OUT / "haalsi_schema.csv",
    index=False
)

haalsi_outcome_patterns = [
    r"heart attack",
    r"myocard",
    r"stroke",
    r"cerebro",
    r"cardiovascular",
    r"coronary",
    r"angina",
    r"heart disease",
    r"heart condition",
    r"death",
    r"deceased",
    r"\bdied\b",
    r"mortality",
    r"cause of death",
    r"verbal autopsy",
    r"vital status",
    r"date of death",
    r"year of death",
    r"month of death",
]

haalsi_risk_patterns = [
    r"systol",
    r"diastol",
    r"blood pressure",
    r"\bbmi\b",
    r"body mass index",
    r"cholesterol",
    r"\bhdl\b",
    r"glucose",
    r"diabet",
    r"smok",
    r"hypertens",
    r"antihypertens",
    r"blood pressure medication",
]

hout = save_candidates(
    haalsi,
    haalsi_labels,
    haalsi_outcome_patterns,
    "haalsi_outcome_candidates.csv",
    "HAALSI",
)

hrisk = save_candidates(
    haalsi,
    haalsi_labels,
    haalsi_risk_patterns,
    "haalsi_riskfactor_candidates.csv",
    "HAALSI",
)

# Detailed aggregate distributions for outcome candidates only
candidate_dist = []

if len(hout):
    for _, row in hout.iterrows():
        c = row["variable"]
        s = haalsi[c]

        vc = s.value_counts(dropna=False).head(30)

        for value, count in vc.items():
            candidate_dist.append({
                "variable": c,
                "label": haalsi_labels.get(c, ""),
                "value": str(value),
                "count": int(count),
            })

pd.DataFrame(candidate_dist).to_csv(
    OUT / "haalsi_outcome_candidate_distributions.csv",
    index=False
)

# HAALSI ID candidates
id_patterns = [
    r"primary key",
    r"participant.*id",
    r"respondent.*id",
    r"person.*id",
    r"individual.*id",
    r"\bid\b",
]

save_candidates(
    haalsi,
    haalsi_labels,
    id_patterns,
    "haalsi_id_candidates.csv",
    "HAALSI",
)

# ============================================================
# HUMAN-READABLE SUMMARY
# ============================================================

summary = []

summary.append("DMV-MAT-CVD PUBLIC DATASET AUDIT")
summary.append("=" * 70)

summary.append("")
summary.append("MHAS COHORT ACCOUNTING")
summary.append("-" * 70)

for row in accounting_rows:
    summary.append(f"{row['stage']}: {row['n']:,}")

summary.append("")
summary.append("MHAS SELECTED BIOMARKERS")
summary.append("-" * 70)

for _, r in selected_biomarkers.iterrows():
    summary.append(
        f"{r['concept']}: {r['selected_variable']} | "
        f"{r['label']} | nonmissing={r['n_nonmissing']}"
    )

summary.append("")
summary.append("MHAS EVENT COUNTS")
summary.append("-" * 70)

for _, r in events.iterrows():
    summary.append(
        f"{r['population']} | {r['outcome']} | "
        f"N known={r['n_with_known_outcome']} | "
        f"events={r['events']} | "
        f"rate={r['event_rate_pct']}%"
    )

summary.append("")
summary.append("MHAS REQUIRED PREDICTOR COLUMNS")
summary.append("-" * 70)
summary.append(
    "Missing required derived columns: "
    + (", ".join(missing_required_columns)
       if missing_required_columns else "NONE")
)

summary.append("")
summary.append("HAALSI OUTCOME CROSSWALK")
summary.append("-" * 70)
summary.append(
    f"Outcome/mortality candidate variables found: {len(hout)}"
)
summary.append(
    f"Risk-factor candidate variables found: {len(hrisk)}"
)
summary.append(
    "See haalsi_outcome_candidates.csv and "
    "haalsi_outcome_candidate_distributions.csv for exact labels/codes."
)

summary.append("")
summary.append("IMPORTANT INTERPRETATION")
summary.append("-" * 70)
summary.append(
    "W4/W5 incident MI-or-stroke values are wave-based self-reported "
    "diagnosis endpoints, not adjudicated exact event dates."
)
summary.append(
    "Five-year mortality uses month/year timing and requires evidence "
    "of survival beyond 60 months or an observed death date."
)
summary.append(
    "No raw participant-level rows or identifiers are exported by this audit."
)

(OUT / "audit_summary.txt").write_text(
    "\n".join(summary),
    encoding="utf-8",
)

print("\n" + "\n".join(summary))
print("\nAudit complete.")
print(f"Outputs written to: {OUT.resolve()}")
