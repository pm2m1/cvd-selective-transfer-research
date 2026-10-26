import builtins

import numpy as np
import pytest

from dmv_mat_cvd.data.preprocessing import Preprocessor
from dmv_mat_cvd.evaluation import binary_metrics, select_threshold
from dmv_mat_cvd.experiments.baselines import fit_tabular


def test_metrics_explicit_threshold_and_single_class():
    values = binary_metrics(np.array([0, 0, 1, 1]), np.array([.1, .4, .6, .9]), .5)
    assert values.ap == 1 and values.auroc == 1
    assert values.brier == pytest.approx(.085)
    assert values.sensitivity == values.specificity == values.precision == values.f1 == values.mcc == 1
    assert values.prevalence == .5
    undefined = binary_metrics(np.zeros(3), np.array([.1, .2, .3]))
    assert undefined.ap is None and undefined.auroc is None and undefined.sensitivity is None
    assert undefined.specificity == 1
    with pytest.raises(ValueError):
        binary_metrics(np.array([0, 1]), np.array([.1, np.nan]))


def test_threshold_learned_on_validation(target_parts):
    threshold = select_threshold(np.array([0, 0, 1, 1]), np.array([.1, .2, .3, .4]),
                                 target_parts["target_validation"])
    assert threshold == .3


@pytest.mark.parametrize("error", [ImportError, RuntimeError])
def test_xgboost_optional_dependency_error(target_parts, monkeypatch, error):
    dataset = Preprocessor().fit(target_parts["target_adaptation"]).transform(target_parts["target_adaptation"])
    original = builtins.__import__
    def unavailable(name, *args, **kwargs):
        if name == "xgboost":
            raise error("intentionally unavailable")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", unavailable)
    with pytest.raises(ImportError, match="XGBoost is optional"):
        fit_tabular("xgboost", dataset, 7)
    model = fit_tabular("logistic_regression", dataset, 7)
    assert model.classes_.tolist() == [0, 1]


def test_estimator_nan_default_serializes_as_metadata():
    import json
    from dmv_mat_cvd.experiments.baselines import tabular_parameters
    class Estimator:
        def get_params(self):
            return {"missing": np.nan, "max_depth": 3}
    assert json.loads(json.dumps(tabular_parameters(Estimator()), allow_nan=False)) == {
        "missing": "nan", "max_depth": 3,
    }
