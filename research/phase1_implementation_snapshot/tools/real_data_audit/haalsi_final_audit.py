import numpy as np
import pandas as pd
import pyreadstat

FILE = "36633-0001-Data.dta"

print("Reading HAALSI...")
df, meta = pyreadstat.read_dta(FILE, apply_value_formats=False)
print(f"N = {len(df):,}")

def n(x):
    return pd.to_numeric(x, errors="coerce")

def coded(x):
    x = n(x)
    x[x <= -90] = np.nan
    return x

def yn(x):
    """HAALSI 1=yes, 2=no -> 1/0."""
    x = coded(x)
    out = pd.Series(np.nan, index=x.index, dtype=float)
    out[x == 1] = 1
    out[x == 2] = 0
    return out

def endpoint(stroke, mi):
    """
    Event known positive if either is yes.
    Known negative only if both are explicitly no.
    """
    out = pd.Series(np.nan, index=df.index, dtype=float)

    positive = (stroke == 1) | (mi == 1)
    negative = (stroke == 0) & (mi == 0)

    out[negative] = 0
    out[positive] = 1
    return out

# ==========================================================
# BASELINE CVD
# ==========================================================

w1_stroke = yn(df["W1CM025"])
w1_mi     = yn(df["W1CM038"])

baseline_cvd = endpoint(w1_stroke, w1_mi)
baseline_free = baseline_cvd == 0

# ==========================================================
# FOLLOW-UP OUTCOMES
# ==========================================================

w2_stroke = yn(df["W2CM025"])
w2_mi     = yn(df["W2CM038"])
w2_event  = endpoint(w2_stroke, w2_mi)

w3_stroke = yn(df["W3CM025"])
w3_mi     = yn(df["W3CM038"])
w3_event  = endpoint(w3_stroke, w3_mi)

# ==========================================================
# COMMON PREDICTORS
# ==========================================================

age = coded(df["W1C_RAGE_CALC"])
sex = coded(df["W2C_RSEX"])

sbp = coded(df["W1C_BS_MEAN_SYS"])
dbp = coded(df["W1C_BS_MEAN_DIA"])
bmi = coded(df["W1C_BS_BMI"])

tc_mmol  = coded(df["W1C_BS_CHOL"])
hdl_mmol = coded(df["W1C_BS_HDL"])

# Harmonize lipids to MHAS mg/dL
tc_mgdl  = tc_mmol * 38.67
hdl_mgdl = hdl_mmol * 38.67

# Smoking
ever_smoke = yn(df["W1CM059"])
now_smoke  = yn(df["W1CM061"])

smoking3 = pd.Series(np.nan, index=df.index)

# 0 never
smoking3[ever_smoke == 0] = 0

# 1 former
smoking3[
    (ever_smoke == 1) &
    (now_smoke == 0)
] = 1

# 2 current
smoking3[
    (ever_smoke == 1) &
    (now_smoke == 1)
] = 2

# Diabetes — harmonized derived definition
diabetes = yn(df["W1C_CM_DIABETES_SRDIAG"])

# Antihypertensive treatment
htn_dx  = yn(df["W1CM002"])
htn_trt = yn(df["W1CM005"])

antihyp = pd.Series(np.nan, index=df.index)

# explicitly on treatment
antihyp[htn_trt == 1] = 1

# diagnosed but not treated
antihyp[htn_trt == 0] = 0

# not hypertensive -> not on antihypertensive treatment
antihyp[htn_dx == 0] = 0

features = pd.DataFrame({
    "age": age,
    "sex": sex,
    "sbp": sbp,
    "dbp": dbp,
    "bmi": bmi,
    "total_cholesterol_mgdl": tc_mgdl,
    "hdl_mgdl": hdl_mgdl,
    "smoking3": smoking3,
    "diabetes": diabetes,
    "antihypertensive": antihyp,
})

complete = features.notna().all(axis=1)

# ==========================================================
# FOLLOW-UP TIME
# ==========================================================

def month_index(y, m):
    y = coded(y)
    m = coded(m)

    ok = (
        y.notna() &
        m.notna() &
        m.between(1, 12)
    )

    out = pd.Series(np.nan, index=df.index)
    out[ok] = y[ok] * 12 + m[ok] - 1
    return out

w1_date = month_index(
    df["W1C_INT_YEAR"],
    df["W1C_INT_MONTH"]
)

w2_date = month_index(
    df["W2C_INT_YEAR"],
    df["W2C_INT_MONTH"]
)

w3_date = month_index(
    df["W3C_INT_YEAR"],
    df["W3C_INT_MONTH"]
)

fu2 = w2_date - w1_date
fu3 = w3_date - w1_date

# ==========================================================
# REPORTING
# ==========================================================

def report_endpoint(name, outcome, population):
    s = outcome[population]
    known = s.notna()

    N = int(known.sum())
    E = int((s[known] == 1).sum())

    rate = 100 * E / N if N else np.nan

    print(
        f"{name}: known={N:,}, events={E:,}, "
        f"non-events={N-E:,}, rate={rate:.3f}%"
    )

def followup_report(name, months, mask):
    s = months[mask].dropna()

    if len(s) == 0:
        print(f"{name}: no valid dates")
        return

    print(
        f"{name}: N={len(s):,}, "
        f"median={s.median():.1f} months, "
        f"IQR={s.quantile(.25):.1f}-{s.quantile(.75):.1f}, "
        f"range={s.min():.1f}-{s.max():.1f}"
    )

print()
print("=" * 72)
print("HAALSI FINAL ENDPOINT AUDIT")
print("=" * 72)

print()
print("BASELINE")
print("-" * 72)
print(f"All participants: {len(df):,}")
print(f"Baseline CVD known: {int(baseline_cvd.notna().sum()):,}")
print(f"Baseline CVD-free: {int(baseline_free.sum()):,}")
print(f"Complete common predictors: {int(complete.sum()):,}")
print(
    "Baseline CVD-free + complete predictors: "
    f"{int((baseline_free & complete).sum()):,}"
)

print()
print("INCIDENT MI/STROKE — BASELINE CVD-FREE")
print("-" * 72)

report_endpoint(
    "W1 -> W2",
    w2_event,
    baseline_free
)

report_endpoint(
    "W1 -> W3",
    w3_event,
    baseline_free
)

print()
print("INCIDENT MI/STROKE — BASELINE CVD-FREE + COMPLETE PREDICTORS")
print("-" * 72)

source_mask = baseline_free & complete

report_endpoint(
    "W1 -> W2",
    w2_event,
    source_mask
)

report_endpoint(
    "W1 -> W3",
    w3_event,
    source_mask
)

print()
print("FOLLOW-UP DURATION")
print("-" * 72)

followup_report(
    "W1 -> W2",
    fu2,
    baseline_free & w2_event.notna()
)

followup_report(
    "W1 -> W3",
    fu3,
    baseline_free & w3_event.notna()
)

print()
print("ATTRITION / OUTCOME AVAILABILITY")
print("-" * 72)

for name, out in [
    ("W2", w2_event),
    ("W3", w3_event),
]:
    eligible = int(baseline_free.sum())
    known = int((baseline_free & out.notna()).sum())
    print(
        f"{name}: {known:,}/{eligible:,} "
        f"({100*known/eligible:.2f}%) baseline-CVD-free "
        "participants have usable outcome"
    )

print()
print("RESPONSE CONSISTENCY")
print("-" * 72)

both_followups = (
    baseline_free &
    w2_event.notna() &
    w3_event.notna()
)

w2_yes_w3_no = int(
    (
        both_followups &
        (w2_event == 1) &
        (w3_event == 0)
    ).sum()
)

w2_no_w3_yes = int(
    (
        both_followups &
        (w2_event == 0) &
        (w3_event == 1)
    ).sum()
)

print(
    f"W2 positive -> W3 negative reversals: "
    f"{w2_yes_w3_no}"
)

print(
    f"W2 negative -> W3 positive later cases: "
    f"{w2_no_w3_yes}"
)

# Compare raw vs corrected W2 stroke
if "W2_CM_025_COMBO" in df.columns:
    combo = yn(df["W2_CM_025_COMBO"])

    comparable = (
        baseline_free &
        combo.notna() &
        w2_stroke.notna()
    )

    disagreement = int(
        (
            comparable &
            (combo != w2_stroke)
        ).sum()
    )

    print(
        "Raw vs corrected W2 stroke disagreements "
        f"among comparable baseline-free participants: "
        f"{disagreement}"
    )

print()
print("PREDICTOR MISSINGNESS — BASELINE CVD-FREE")
print("-" * 72)

for c in features.columns:
    s = features.loc[baseline_free, c]
    print(
        f"{c:28s} "
        f"missing={s.isna().sum():4d} "
        f"({100*s.isna().mean():6.2f}%)"
    )

print()
print("DONE")
