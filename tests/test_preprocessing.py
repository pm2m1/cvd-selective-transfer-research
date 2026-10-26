import copy

import numpy as np
import pytest
import torch

from dmv_mat_cvd.data.base import CohortPartition, CohortTable
from dmv_mat_cvd.data.preprocessing import Preprocessor
from dmv_mat_cvd.data.schema import CONTINUOUS, PREDICTORS
from dmv_mat_cvd.safeguards import LeakageError


def test_fit_uses_only_training_statistics(source_parts, target_parts, tmp_path):
    train = source_parts["source_train"]
    pp = Preprocessor().fit(train)
    assert pp.state["continuous"]["age"]["mean"] == pytest.approx(train.cohort.records.age.mean())
    before = copy.deepcopy(pp.state)
    test = target_parts["target_test"]
    first, second = pp.transform(test), pp.transform(test)
    assert pp.state == before
    assert all(torch.equal(first.views[name], second.views[name]) for name in first.views)
    assert first.view_dims == pp.view_dims
    assert pp.view_dims == {"background": 4, "haemodynamic": 2, "metabolic": 4,
                            "behaviour": 4, "comorbidity_medication": 3}
    assert not hasattr(first, "records")
    pp.save(tmp_path / "state.json")
    restored = Preprocessor.load(tmp_path / "state.json")
    assert restored.state == before
    assert all(torch.equal(first.views[k], restored.transform(test).views[k]) for k in first.views)
    with pytest.raises(ValueError, match="already fitted"):
        pp.fit(train)


@pytest.mark.parametrize("role", ["source_validation", "source_test"])
def test_source_nontraining_fit_rejected(source_parts, role):
    with pytest.raises(LeakageError):
        Preprocessor().fit(source_parts[role])


@pytest.mark.parametrize("role", ["target_validation", "target_test"])
def test_target_nontraining_fit_rejected(target_parts, role):
    with pytest.raises(LeakageError):
        Preprocessor().fit(target_parts[role])


def test_explicit_target_adaptation_fit(target_parts):
    pp = Preprocessor().fit(target_parts["target_adaptation"])
    assert pp.state["fit_role"] == "target_adaptation"


def test_missing_and_unknown_are_finite_deterministic(source_parts):
    part = source_parts["source_train"]
    frame = part.cohort.records.copy()
    for name in CONTINUOUS:
        frame[name] = np.nan
    for name in set(PREDICTORS) - set(CONTINUOUS):
        frame[name] = None
    part = CohortPartition(CohortTable(frame, "test"), part.role)
    pp = Preprocessor().fit(part)
    ds = pp.transform(part)
    assert all(stats["all_missing"] for stats in pp.state["continuous"].values())
    assert all(torch.isfinite(value).all() for value in ds.views.values())
    assert torch.all(ds.views["behaviour"][:, -1] == 1)
    assert torch.all(ds.views["background"][:, 0] == 0)


def test_unobserved_labels_not_silently_negative(source_parts):
    part = source_parts["source_train"]
    frame = part.cohort.records.copy()
    frame.loc[0, "label"] = np.nan
    frame.loc[0, "endpoint_status"] = "unknown"
    part = CohortPartition(CohortTable(frame, "test"), part.role)
    pp = Preprocessor().fit(part)
    with pytest.raises(ValueError, match="observation status"):
        pp.transform(part)
