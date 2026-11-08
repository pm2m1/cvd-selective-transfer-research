import numpy as np
import pytest
from phase2.phase2b_public.contracts import FEATURES,Role
from phase2.phase2b_public.missing_predictor_candidate import MixedTrainingImputer


LEVELS={"sex":[0,1],"smoking":[0,1,2],"diabetes":[0,1],"bp_treatment":[0,1]}


def data():return np.array([[60,0,120,75,25,0,0,1],[70,1,140,85,30,2,1,0],[np.nan,0,np.nan,80,27,np.nan,0,1]],float)


def kwargs(x):return dict(measurement_eligibility_verified=True,structural_missing=np.zeros_like(x,dtype=bool))


def test_training_only_fill_missing_indicators_and_inputs_preserved():
    x=data();original=x.copy();i=MixedTrainingImputer(LEVELS).fit(x,FEATURES,Role.SOURCE_TRAIN,**kwargs(x))
    y=i.transform(x,FEATURES,Role.SOURCE_VALIDATION,**kwargs(x))
    assert y.shape==(3,16) and np.isfinite(y).all()
    assert y[2,0]==65 and y[2,2]==130 and y[2,5]==0
    assert y[2,8]==y[2,10]==y[2,13]==1
    np.testing.assert_equal(x,original)


@pytest.mark.parametrize("role", [Role.SOURCE_VALIDATION,Role.TARGET_VALIDATION,Role.TARGET_TEST])
def test_no_validation_or_test_fitting(role):
    x=data()
    with pytest.raises(PermissionError):MixedTrainingImputer(LEVELS).fit(x,FEATURES,role,**kwargs(x))


def test_future_validation_values_never_change_training_fills():
    x=data();i=MixedTrainingImputer(LEVELS).fit(x,FEATURES,Role.SOURCE_TRAIN,**kwargs(x));before=i.fill_.copy()
    v=x.copy();v[0,0]=900
    i.transform(v,FEATURES,Role.TARGET_VALIDATION,**kwargs(v))
    np.testing.assert_array_equal(i.fill_,before)
    with pytest.raises(PermissionError):i.transform(v,FEATURES,Role.TARGET_TEST,**kwargs(v))


@pytest.mark.parametrize("kind", ["allmissing","string","extended_missing_object","unknown_category","infinite","structural","eligibility"])
def test_unidentified_or_unreviewed_values_reject_without_coercion(kind):
    x=data();kw=kwargs(x)
    if kind=="allmissing":x[:,0]=np.nan
    elif kind in {"string","extended_missing_object"}:x=x.astype(object);x[0,0]="60" if kind=="string" else ".y"
    elif kind=="unknown_category":x[0,1]=9
    elif kind=="infinite":x[0,0]=np.inf
    elif kind=="structural":kw["structural_missing"][0,0]=True
    else:kw["measurement_eligibility_verified"]=False
    with pytest.raises(ValueError):MixedTrainingImputer(LEVELS).fit(x,FEATURES,Role.SOURCE_TRAIN,**kw)
