"""Invented-score planning only: no project data input, model training or GO.

Binormal conditional score distributions give an explicit assumed AUROC. The
log density ratio yields calibrated risks at the assumed natural prevalence.
Two models share correlated errors on the SAME synthetic people. Sampling
intervals across Monte Carlo cohorts are not confidence intervals for observed
HRS/ELSA performance, and do not include training/adaptation uncertainty.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import NormalDist

import numpy as np
from scipy.special import expit

VERSION = "phase2b-invented-score-precision-v1"


def _checked(y, score):
    y, score = np.asarray(y), np.asarray(score)
    if y.ndim != 1 or score.shape != y.shape or score.dtype.kind not in "iuf" or not np.isfinite(score).all() or not np.isin(y, [0,1]).all():
        raise ValueError("SYNTHETIC_SCORE_SCHEMA_INVALID")
    if not np.any(y == 1) or not np.any(y == 0): raise ValueError("BOTH_CLASSES_REQUIRED")
    return y.astype(float), score.astype(float)


def discrimination(y, score):
    y, score = _checked(y, score)
    order = np.argsort(-score, kind="stable"); yy, ss = y[order], score[order]
    end = np.r_[np.flatnonzero(np.diff(ss)), len(ss)-1]
    tp = np.cumsum(yy)[end]; seen = end+1; fp = seen-tp
    increments = np.diff(np.r_[0., tp])
    ap = float(np.sum(increments/y.sum()*tp/seen))
    # Descending thresholds; trapezoids assign half credit to score ties.
    tpr = np.r_[0., tp/tp[-1]]; fpr = np.r_[0., fp/fp[-1]]
    auc = float(np.sum(np.diff(fpr)*(tpr[1:]+tpr[:-1])/2))
    return ap, auc


def calibration_fit(y, logits, *, offset_only=False):
    """Unpenalized binomial MLE. Separation/nonidentifiability is a failure."""
    y, logits = _checked(y, logits)
    x = np.ones((len(y),1)) if offset_only else np.column_stack((np.ones(len(y)),logits))
    offset = logits if offset_only else np.zeros(len(y))
    beta = np.zeros(x.shape[1])
    for _ in range(60):
        eta = offset+x@beta; p = expit(eta); w = p*(1-p)
        info = x.T@(w[:,None]*x); score = x.T@(y-p)
        if not np.isfinite(info).all() or np.linalg.cond(info) > 1e12: return None
        try: step = np.linalg.solve(info,score)
        except np.linalg.LinAlgError: return None
        current = float(np.sum(np.logaddexp(0,eta)-y*eta))
        scale = 1.
        while scale > 1e-8:
            proposed = offset+x@(beta+scale*step)
            if np.sum(np.logaddexp(0,proposed)-y*proposed) <= current+1e-10: break
            scale *= .5
        if scale <= 1e-8: return None
        beta += scale*step
        if not np.isfinite(beta).all() or np.max(np.abs(beta)) > 80: return None
        if np.max(np.abs(step)) < 1e-7:
            return [float(v) for v in beta]
    return None


def metrics(y, logits, *, calibration=True):
    y, logits = _checked(y, logits)
    ap, auc = discrimination(y, logits)
    result = {"ap":ap,"auroc":auc,"brier":float(np.mean((expit(logits)-y)**2))}
    if calibration:
        fit = calibration_fit(y,logits); offset = calibration_fit(y,logits,offset_only=True)
        result.update(calibration_intercept_joint=None if fit is None else fit[0],
            calibration_slope=None if fit is None else fit[1],
            calibration_in_large=None if offset is None else offset[0])
    return result


def validate_scenario(s):
    expected = {"id","n","prevalence","auc_a","auc_b","within_class_score_correlation",
        "logit_offset_b","logit_scale_b","replicates","seed"}
    if set(s) != expected or type(s["id"]) is not str or not s["id"]: raise ValueError("SCENARIO_SCHEMA_INVALID")
    for k in ("n","replicates","seed"):
        if type(s[k]) is not int or s[k] < (2 if k != "seed" else 0): raise ValueError("SCENARIO_SIZE_INVALID")
    for k in expected-{"id","n","replicates","seed"}:
        if type(s[k]) not in (float,int) or not math.isfinite(s[k]): raise ValueError("SCENARIO_PARAMETER_INVALID")
    if not (0<s["prevalence"]<1 and .5<=s["auc_a"]<1 and .5<=s["auc_b"]<1 and
        -1<=s["within_class_score_correlation"]<=1 and s["logit_scale_b"]>0): raise ValueError("SCENARIO_PARAMETER_INVALID")


def draw(s, rng):
    validate_scenario(s)
    y = rng.binomial(1,s["prevalence"],s["n"])
    da,db = (math.sqrt(2)*NormalDist().inv_cdf(s[k]) for k in ("auc_a","auc_b"))
    shared, independent = rng.standard_normal((2,s["n"]))
    rho=s["within_class_score_correlation"]
    za=shared+y*da; zb=rho*shared+math.sqrt(max(0,1-rho*rho))*independent+y*db
    prior=math.log(s["prevalence"]/(1-s["prevalence"]))
    la=prior+da*za-da*da/2
    lb=s["logit_offset_b"]+s["logit_scale_b"]*(prior+db*zb-db*db/2)
    return y,la,lb


def summarize(values, requested):
    finite=[float(v) for v in values if v is not None and math.isfinite(v)]
    if not finite: return {"valid_replicates":0,"failed_replicates":requested,"mean":None,"sampling_interval_95":None,"sampling_width_95":None}
    lo,hi=np.quantile(finite,[.025,.975]); sd=float(np.std(finite,ddof=1)) if len(finite)>1 else None
    return {"valid_replicates":len(finite),"failed_replicates":requested-len(finite),"mean":float(np.mean(finite)),
        "sd":sd,"monte_carlo_se_of_mean":sd/math.sqrt(len(finite)) if sd is not None else None,
        "sampling_interval_95":[float(lo),float(hi)],"sampling_width_95":float(hi-lo)}


def simulate(s):
    validate_scenario(s); rng=np.random.default_rng(s["seed"])
    names=("ap","auroc","brier","calibration_intercept_joint","calibration_slope","calibration_in_large")
    values={prefix+k:[] for prefix in ("a_","b_") for k in names}
    values.update({"paired_ap_difference":[],"paired_auroc_difference":[]})
    absent=0; realized_events=[]
    for _ in range(s["replicates"]):
        y,a,b=draw(s,rng); realized_events.append(int(y.sum()))
        if not np.any(y==1) or not np.any(y==0): absent+=1; continue
        ma,mb=metrics(y,a),metrics(y,b)
        for prefix,m in (("a_",ma),("b_",mb)):
            for k,v in m.items(): values[prefix+k].append(v)
        values["paired_ap_difference"].append(mb["ap"]-ma["ap"])
        values["paired_auroc_difference"].append(mb["auroc"]-ma["auroc"])
    return {"identity":VERSION,"synthetic_only":True,"scenario":s,
        "population_sampling":"IID_BERNOULLI_NATURAL_PREVALENCE_NOT_FIXED_CASE_CONTROL",
        "expected_events":s["n"]*s["prevalence"],"realized_synthetic_events_range":[min(realized_events),max(realized_events)],
        "replicates_lacking_a_class":absent,
        "true_b_calibration_intercept_joint":-s["logit_offset_b"]/s["logit_scale_b"],
        "true_b_calibration_slope":1/s["logit_scale_b"] if s["auc_b"]>.5 else None,
        "metrics":{k:summarize(v,s["replicates"]) for k,v in values.items()},
        "interval_interpretation":"MONTE_CARLO_SAMPLING_SPREAD_CONDITIONAL_ON_ESTIMABLE_REPLICATES_NOT_OBSERVED_PERFORMANCE_CI",
        "training_adaptation_imputation_uncertainty_included":False,"power_guarantee":False,"real_modeling":"NO_GO"}


def paired_bootstrap(y,a,b,*,replicates,seed):
    """Shared person resample across models; natural-prevalence ordinary bootstrap."""
    y,a=_checked(y,a); _,b=_checked(y,b)
    if type(replicates) is not int or replicates<2 or type(seed) is not int or seed<0:
        raise ValueError("BOOTSTRAP_SPEC_INVALID")
    rng=np.random.default_rng(seed); delta=[]; ap_a=[]; ap_b=[]; failed=0
    for _ in range(replicates):
        idx=rng.integers(0,len(y),len(y)); yy=y[idx]
        if yy.sum() in (0,len(yy)): failed+=1; continue
        ma,mb=metrics(yy,a[idx],calibration=False),metrics(yy,b[idx],calibration=False)
        ap_a.append(ma["ap"]);ap_b.append(mb["ap"]);delta.append(mb["ap"]-ma["ap"])
    return {"resampling":"SAME_SYNTHETIC_PEOPLE_IN_BOTH_MODELS_ORDINARY_BOOTSTRAP","requested":replicates,
        "failed_single_class_resamples":failed,"a_ap":summarize(ap_a,replicates),"b_ap":summarize(ap_b,replicates),
        "paired_ap_difference":summarize(delta,replicates),
        "interval_interpretation":"PERCENTILE_BOOTSTRAP_OF_FIXED_SYNTHETIC_PREDICTIONS_NOT_REAL_STUDY_EVIDENCE"}


def exclusive_json(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w") as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write("\n");f.flush();os.fsync(f.fileno())


def main():
    parser=argparse.ArgumentParser(description="Public synthetic precision planning; no real-data input mode")
    parser.add_argument("--synthetic",action="store_true",required=True)
    parser.add_argument("--plan",required=True);parser.add_argument("--output",required=True)
    args=parser.parse_args()
    try:
        raw=Path(args.plan).read_bytes(); plan=json.loads(raw)
        if plan.get("synthetic_only") is not True or plan.get("real_modeling")!="NO_GO": raise ValueError("PLAN_SCOPE_INVALID")
        result={"identity":VERSION+"_grid","synthetic_only":True,"real_modeling":"NO_GO",
            "plan_sha256":hashlib.sha256(raw).hexdigest(),"numpy":np.__version__,
            "scenarios":[simulate(s) for s in plan["scenarios"]]}
        example=plan["bootstrap_demonstration"];y,a,b=draw(example,np.random.default_rng(example["seed"]))
        result["paired_bootstrap_demonstration"]=paired_bootstrap(y,a,b,replicates=499,seed=93721)
        exclusive_json(Path(args.output),result)
        print("PASS ISSUE=PUBLIC_SYNTHETIC_PRECISION_GRID_WRITTEN_NO_REAL_PERFORMANCE");return 0
    except Exception:
        print("BLOCKED ISSUE=SYNTHETIC_PRECISION_PLAN_OR_DESTINATION_INVALID");return 2


if __name__=="__main__":raise SystemExit(main())
