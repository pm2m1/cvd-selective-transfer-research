import dataclasses
from pathlib import Path

import numpy as np
import pytest
import torch
from torch.utils.data import Subset

from dmv_mat_cvd.config import ExperimentConfig
from dmv_mat_cvd.data.base import CohortTable
from dmv_mat_cvd.data.preprocessing import Preprocessor
from dmv_mat_cvd.data.splitting import split_target
from dmv_mat_cvd.evaluation import ModuleRepresentations, extract_features, select_threshold
from dmv_mat_cvd.experiments.baselines import fit_tabular
from dmv_mat_cvd.experiments.runner import loader, run_experiment
from dmv_mat_cvd.models.multiview_mlp import MultiViewRiskNet
from dmv_mat_cvd.safeguards import LeakageError, SplitRole
from dmv_mat_cvd.training import train_model
from dmv_mat_cvd.transfer.adapt import adapt_model
from dmv_mat_cvd.transfer.scores import score_modules


def test_test_partition_rejected_at_every_fit_boundary(source_parts, target_parts):
    pp = Preprocessor().fit(source_parts["source_train"])
    test = target_parts["target_test"]
    ds = pp.transform(test)
    val = loader(pp.transform(target_parts["target_validation"]))
    train = loader(pp.transform(target_parts["target_adaptation"]))
    model = MultiViewRiskNet(pp.view_dims)
    mask = dict.fromkeys(model.selectable_modules(), False)
    with pytest.raises(LeakageError):
        Preprocessor().fit(test)
    with pytest.raises(LeakageError):
        train_model(model, loader(ds), val, "cpu", epochs=1)
    with pytest.raises(LeakageError):
        train_model(model, train, loader(ds), "cpu", epochs=1)
    with pytest.raises(LeakageError):
        train_model(model, loader(Subset(ds, [0, 1])), val, "cpu", epochs=1)
    with pytest.raises(LeakageError):
        adapt_model(model, mask, loader(ds), val, "cpu", epochs=1)
    with pytest.raises(LeakageError):
        adapt_model(model, mask, train, loader(ds), "cpu", epochs=1)
    with pytest.raises(LeakageError):
        extract_features(model, loader(ds), "cpu")
    with pytest.raises(LeakageError):
        fit_tabular("logistic_regression", ds, 0)
    with pytest.raises(LeakageError):
        select_threshold(ds.labels.numpy(), np.full(len(ds), .5), test)
    features = {"layer": np.ones((4, 3))}
    labels = np.array([0, 0, 1, 1])
    src = ModuleRepresentations(features, labels, SplitRole.SOURCE_VALIDATION)
    tgt = ModuleRepresentations(features, labels, SplitRole.TARGET_TEST)
    with pytest.raises(LeakageError):
        score_modules(src, tgt)
    with pytest.raises(LeakageError):
        score_modules(dataclasses.replace(src, role=SplitRole.SOURCE_TEST),
                      dataclasses.replace(tgt, role=SplitRole.TARGET_ADAPTATION))
    with pytest.raises(LeakageError):
        score_modules(features, features)  # provenance cannot be silently dropped


@pytest.mark.parametrize("policy", ["source_fitted", "target_adaptation"])
def test_test_perturbation_cannot_change_any_fitted_decision(source, target, tmp_path, policy):
    cfg = ExperimentConfig(epochs_source=1, epochs_target=1, device="cpu", mmd_max_samples=40,
                           threshold_policy="validation_f1", output_dir=str(tmp_path), preprocessing_policy=policy,
                           modes=("source_only", "head_only", "full", "fixed_mask", "dmv_mat"))
    test_ids = split_target(target, seed=cfg.seed + 1)["target_test"].participant_ids
    changed = target.records.copy()
    selected = changed.participant_id.isin(test_ids)
    changed.loc[selected, "age"] = 1000000.0
    changed.loc[selected, "sbp"] = -1000000.0
    changed.loc[selected, "label"] = 1 - changed.loc[selected, "label"]
    changed.loc[selected, "endpoint_status"] = np.where(changed.loc[selected, "label"] == 1,
                                                         "positive", "known_negative")
    first = run_experiment(source, target, cfg)
    second = run_experiment(source, CohortTable(changed, target.domain), cfg)
    assert first["module_scores"] == second["module_scores"]
    assert first["methods"] == second["methods"]
    for name in first["target_metrics"]:
        assert first["target_metrics"][name]["threshold"] == second["target_metrics"][name]["threshold"]
        left = torch.load(Path(first["output_directory"]) / f"{name}.pt", weights_only=True)
        right = torch.load(Path(second["output_directory"]) / f"{name}.pt", weights_only=True)
        assert all(torch.equal(left[key], right[key]) for key in left)
    assert (Path(first["output_directory"]) / "preprocessing_source.json").read_text() == (
        Path(second["output_directory"]) / "preprocessing_source.json").read_text()
    if policy == "target_adaptation":
        assert (Path(first["output_directory"]) / "preprocessing_target.json").read_text() == (
            Path(second["output_directory"]) / "preprocessing_target.json").read_text()
    stages = first["audit_log"]
    boundary = next(i for i, entry in enumerate(stages) if entry["stage"] == "locked_test_evaluation_begins")
    assert all(entry.get("role") != "target_test" for entry in stages[:boundary])
    assert all("evaluation" in entry["stage"] for entry in stages[boundary:])
