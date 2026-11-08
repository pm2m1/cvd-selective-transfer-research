from copy import deepcopy
import json

import numpy as np
import pytest
from sklearn.metrics import average_precision_score,roc_auc_score
from phase2.phase2b_public import precision_simulation as p


def scenario(**kwargs):
    return dict(dict(id="INVENTED",n=500,prevalence=.10,auc_a=.70,auc_b=.72,
        within_class_score_correlation=.8,logit_offset_b=0.,logit_scale_b=1.,replicates=20,seed=41),**kwargs)


@pytest.mark.parametrize("seed", range(6))
def test_ap_auc_match_reference_including_ties(seed):
    rng=np.random.default_rng(seed);y=np.r_[np.ones(20),np.zeros(80)];score=rng.integers(0,5,len(y))
    ap,auc=p.discrimination(y,score)
    assert ap==pytest.approx(average_precision_score(y,score))
    assert auc==pytest.approx(roc_auc_score(y,score))


def test_identical_models_have_exactly_zero_paired_difference_and_shared_bootstrap():
    s=scenario(auc_b=.7,within_class_score_correlation=1.)
    r=p.simulate(s)
    assert r["metrics"]["paired_ap_difference"]["mean"]==0
    assert r["metrics"]["paired_ap_difference"]["sampling_width_95"]==0
    y,a,b=p.draw(s,np.random.default_rng(6));result=p.paired_bootstrap(y,a,b,replicates=50,seed=87)
    assert result["paired_ap_difference"]["sampling_width_95"]==0


def test_dgp_calibration_and_discrimination_known_large_invented_population():
    s=scenario(n=100000,prevalence=.15,logit_offset_b=.3,logit_scale_b=.8)
    y,a,b=p.draw(s,np.random.default_rng(41));ma,mb=p.metrics(y,a),p.metrics(y,b)
    assert ma["auroc"]==pytest.approx(.70,abs=.015)
    assert mb["auroc"]==pytest.approx(.72,abs=.015)
    assert ma["calibration_slope"]==pytest.approx(1.,abs=.06)
    assert mb["calibration_slope"]==pytest.approx(1.25,abs=.08)
    assert mb["calibration_intercept_joint"]==pytest.approx(-.375,abs=.10)


def test_determinism_and_no_real_performance_or_power_claim():
    a=p.simulate(scenario());b=p.simulate(scenario())
    assert a==b and a["synthetic_only"] and a["real_modeling"]=="NO_GO"
    assert a["power_guarantee"] is False and a["training_adaptation_imputation_uncertainty_included"] is False


def test_single_class_and_separation_not_converted_to_success():
    r=p.simulate(scenario(n=10,prevalence=.001))
    assert r["replicates_lacking_a_class"]>0
    assert r["metrics"]["a_ap"]["failed_replicates"]>0
    assert p.calibration_fit(np.r_[np.zeros(10),np.ones(10)],np.r_[np.full(10,-10),np.full(10,10)]) is None


@pytest.mark.parametrize("changes", [{"prevalence":0},{"prevalence":1},{"n":True},{"replicates":0},
    {"auc_a":.4},{"within_class_score_correlation":2},{"logit_scale_b":0},{"auc_b":float("nan")},{"seed":-1}])
def test_invalid_scenarios_reject(changes):
    s=scenario();s.update(changes)
    with pytest.raises(ValueError):p.simulate(s)


def test_absent_class_bootstrap_failure_tallied():
    y=np.array([1]+[0]*9);a=np.arange(10.)
    r=p.paired_bootstrap(y,a,a,replicates=200,seed=8)
    assert r["failed_single_class_resamples"]>0
    assert r["paired_ap_difference"]["failed_replicates"]==r["failed_single_class_resamples"]


def test_exclusive_output_partial_protection(tmp_path):
    path=tmp_path/"INVENTED.json";p.exclusive_json(path,{"synthetic_only":True})
    before=path.read_bytes()
    with pytest.raises(FileExistsError):p.exclusive_json(path,{"other":2})
    assert path.read_bytes()==before
