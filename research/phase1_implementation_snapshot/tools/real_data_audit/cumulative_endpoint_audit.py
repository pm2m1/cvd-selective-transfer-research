import numpy as np
import pandas as pd
import pyreadstat


def num(s):
    return pd.to_numeric(s, errors="coerce")


def haalsi_yn(s):
    """HAALSI: 1=yes, 2=no."""
    x = num(s)
    out = pd.Series(np.nan, index=x.index)
    out[x == 1] = 1
    out[x == 2] = 0
    return out


def mhas_yn(s):
    """Gateway MHAS harmonized binary: 1=yes, 0=no."""
    x = num(s)
    out = pd.Series(np.nan, index=x.index)
    out[x == 1] = 1
    out[x == 0] = 0
    return out


def disease(a, b):
    """
    Heart attack OR stroke at one wave.
    Positive if either positive.
    Negative only if both explicitly negative.
    """
    out = pd.Series(np.nan, index=a.index)

    pos = (a == 1) | (b == 1)
    neg = (a == 0) & (b == 0)

    out[neg] = 0
    out[pos] = 1
    return out


def cumulative_endpoint(mid, final):
    """
    Event if positive at either follow-up.
    Non-event only if final follow-up explicitly negative
    and no earlier positive.
    """
    out = pd.Series(np.nan, index=final.index)

    event = (mid == 1) | (final == 1)
    nonevent = (final == 0) & (mid != 1)

    out[nonevent] = 0
    out[event] = 1

    return out


def month_index(y, m):
    y = num(y)
    m = num(m)

    ok = y.notna() & m.between(1, 12)

    out = pd.Series(np.nan, index=y.index)
    out[ok] = y[ok] * 12 + m[ok] - 1
    return out


# ============================================================
# HAALSI
# ============================================================

print("\nReading HAALSI ...")
h, _ = pyreadstat.read_dta(
    "36633-0001-Data.dta",
    apply_value_formats=False
)

h_base = disease(
    haalsi_yn(h["W1CM025"]),
    haalsi_yn(h["W1CM038"])
)

h_w2 = disease(
    haalsi_yn(h["W2CM025"]),
    haalsi_yn(h["W2CM038"])
)

h_w3 = disease(
    haalsi_yn(h["W3CM025"]),
    haalsi_yn(h["W3CM038"])
)

h_y = cumulative_endpoint(h_w2, h_w3)

h_free = h_base == 0

# predictor completeness
age = num(h["W1C_RAGE_CALC"])
sex = num(h["W2C_RSEX"])

sbp = num(h["W1C_BS_MEAN_SYS"])
dbp = num(h["W1C_BS_MEAN_DIA"])
bmi = num(h["W1C_BS_BMI"])

tc = num(h["W1C_BS_CHOL"])
hdl = num(h["W1C_BS_HDL"])

ever = haalsi_yn(h["W1CM059"])
now = haalsi_yn(h["W1CM061"])

smoking = pd.Series(np.nan, index=h.index)
smoking[ever == 0] = 0
smoking[(ever == 1) & (now == 0)] = 1
smoking[(ever == 1) & (now == 1)] = 2

diabetes = haalsi_yn(h["W1C_CM_DIABETES_SRDIAG"])

htn = haalsi_yn(h["W1CM002"])
treat = haalsi_yn(h["W1CM005"])

antihyp = pd.Series(np.nan, index=h.index)
antihyp[htn == 0] = 0
antihyp[treat == 0] = 0
antihyp[treat == 1] = 1

h_features = pd.DataFrame({
    "age": age,
    "sex": sex,
    "sbp": sbp,
    "dbp": dbp,
    "bmi": bmi,
    "tc": tc,
    "hdl": hdl,
    "smoking": smoking,
    "diabetes": diabetes,
    "antihyp": antihyp
})

h_complete = h_features.notna().all(axis=1)

h_source = h_free & h_complete & h_y.notna()

h_events = int((h_y[h_source] == 1).sum())
h_n = int(h_source.sum())

h_date1 = month_index(
    h["W1C_INT_YEAR"],
    h["W1C_INT_MONTH"]
)

h_date3 = month_index(
    h["W3C_INT_YEAR"],
    h["W3C_INT_MONTH"]
)

h_fu = (h_date3 - h_date1)[h_free & h_w3.notna()].dropna()


# ============================================================
# MHAS
# ============================================================

print("Reading MHAS ...")

m, _ = pyreadstat.read_dta(
    "H_MHAS_d.dta",
    apply_value_formats=False
)

b, _ = pyreadstat.read_dta(
    "sect_l_biomarkers_2012.dta",
    apply_value_formats=False
)

if "unhhidnp" not in b.columns:
    b["unhhidnp"] = (
        num(b["cunicah"]) * 100 + num(b["np"])
    )

cols = [
    "unhhidnp",
    "r3agey", "ragender",
    "r3systo", "r3diasto", "r3mbmi",
    "r3smokev", "r3smoken",
    "r3diabe", "r3rxhibp",
    "r3hrtatte", "r3stroke",
    "r4hrtatte", "r4stroke",
    "r5hrtatte", "r5stroke",
    "r3iwy", "r3iwm",
    "r5iwy", "r5iwm",
]

x = b[
    ["unhhidnp", "chol_rev_12", "hdlc_12"]
].merge(
    m[cols],
    on="unhhidnp",
    how="left",
    validate="one_to_one"
)

m_base = disease(
    mhas_yn(x["r3stroke"]),
    mhas_yn(x["r3hrtatte"])
)

m_w4 = disease(
    mhas_yn(x["r4stroke"]),
    mhas_yn(x["r4hrtatte"])
)

m_w5 = disease(
    mhas_yn(x["r5stroke"]),
    mhas_yn(x["r5hrtatte"])
)

m_y = cumulative_endpoint(m_w4, m_w5)

m_free = m_base == 0

smokev = mhas_yn(x["r3smokev"])
smoken = mhas_yn(x["r3smoken"])

m_smoking = pd.Series(np.nan, index=x.index)
m_smoking[smokev == 0] = 0
m_smoking[(smokev == 1) & (smoken == 0)] = 1
m_smoking[(smokev == 1) & (smoken == 1)] = 2

m_features = pd.DataFrame({
    "age": num(x["r3agey"]),
    "sex": num(x["ragender"]),
    "sbp": num(x["r3systo"]),
    "dbp": num(x["r3diasto"]),
    "bmi": num(x["r3mbmi"]),
    "tc": num(x["chol_rev_12"]),
    "hdl": num(x["hdlc_12"]),
    "smoking": m_smoking,
    "diabetes": num(x["r3diabe"]),
    "antihyp": num(x["r3rxhibp"])
})

m_complete = m_features.notna().all(axis=1)

m_target = m_free & m_complete & m_y.notna()

m_events = int((m_y[m_target] == 1).sum())
m_n = int(m_target.sum())

m_date3 = month_index(
    x["r3iwy"],
    x["r3iwm"]
)

m_date5 = month_index(
    x["r5iwy"],
    x["r5iwm"]
)

m_fu = (m_date5 - m_date3)[m_free & m_w5.notna()].dropna()


# ============================================================
# RESULTS
# ============================================================

print("\n" + "=" * 72)
print("FINAL CUMULATIVE ENDPOINT AUDIT")
print("=" * 72)

print("\nHAALSI")
print("-" * 72)
print(f"Final usable source N: {h_n:,}")
print(f"Incident heart attack/stroke events: {h_events:,}")
print(f"Event rate: {100*h_events/h_n:.3f}%")
print(
    f"W1->W3 follow-up: median {h_fu.median():.1f} months "
    f"(IQR {h_fu.quantile(.25):.1f}-{h_fu.quantile(.75):.1f})"
)

print("\nMHAS")
print("-" * 72)
print(f"Final usable target N: {m_n:,}")
print(f"Incident heart attack/stroke events: {m_events:,}")
print(f"Event rate: {100*m_events/m_n:.3f}%")
print(
    f"W3->W5 follow-up: median {m_fu.median():.1f} months "
    f"(IQR {m_fu.quantile(.25):.1f}-{m_fu.quantile(.75):.1f})"
)

print("\nDOMAIN SHIFT")
print("-" * 72)
print(
    f"Source event prevalence: {100*h_events/h_n:.3f}%"
)
print(
    f"Target event prevalence: {100*m_events/m_n:.3f}%"
)
print(
    f"Target/source event-rate ratio: "
    f"{(m_events/m_n)/(h_events/h_n):.3f}"
)

print("\nDONE")
