import json
from pathlib import Path

import pytest
import torch

from dmv_mat_cvd.config import ExperimentConfig
from dmv_mat_cvd.data.synthetic import VIEW_DIMS, SyntheticDomainConfig, generate_domain, split_views
from dmv_mat_cvd.evaluation import extract_features, metrics
from dmv_mat_cvd.experiments.runner import loader, run_experiment, seed_everything
from dmv_mat_cvd.models.multiview_mlp import MultiViewRiskNet
from dmv_mat_cvd.safeguards import SplitRole
from dmv_mat_cvd.training import train_model
from dmv_mat_cvd.transfer.adapt import adapt_model
from dmv_mat_cvd.transfer.scores import score_modules
from dmv_mat_cvd.transfer.selector import select_adaptation_mask


@pytest.mark.parametrize("policy", ["source_fitted", "target_adaptation"])
def test_canonical_end_to_end_all_core_modes(source, target, tmp_path, policy):
    result = run_experiment(source, target, ExperimentConfig(
        epochs_source=1, epochs_target=1, device="cpu", output_dir=str(tmp_path),
        preprocessing_policy=policy, mmd_max_samples=40,
    ))
    assert len(result["module_scores"]) == 7
    assert len(result["target_metrics"]) == 8
    assert result["model_configuration"]["view_dims"]["behaviour"] == 4
    assert result["methods"]["dmv_mat"]["frozen_integrity"]["ok"]
    assert result["methods"]["dmv_mat"]["frozen_integrity"]["frozen_modules_checked"] > 0
    for mode in ("head_only", "full", "fixed_mask", "dmv_mat"):
        assert result["methods"][mode]["frozen_integrity"]["ok"]
        assert result["target_metrics"][mode]["ap"] is not None
        assert result["target_metrics"][mode]["auroc"] is not None
        assert result["target_metrics"][mode]["brier"] >= 0
    assert result["methods"]["full"]["adapted_parameter_fraction"] == 1
    assert 0 < result["methods"]["head_only"]["adapted_parameter_fraction"] < .1
    root = Path(result["output_directory"])
    saved = json.loads((root / "results.json").read_text())
    assert saved["target_metrics"] == result["target_metrics"]
    assert (root / "module_scores.csv").exists()
    assert (root / "metrics.csv").exists()
    assert "participant_id" not in (root / "results.json").read_text()


def test_legacy_synthetic_workflow_regression():
    # Original generator, network, centroid score, raw MMD and freezing flow.
    # Baseline source-only numbers were captured before the refactor on CPU.
    seed_everything(7)
    source = split_views(*generate_domain(SyntheticDomainConfig(160, "source", 7)), seed=7)
    target = split_views(*generate_domain(SyntheticDomainConfig(100, "target", 107)), seed=8,
                         roles=(SplitRole.TARGET_ADAPTATION, SplitRole.TARGET_VALIDATION, SplitRole.TARGET_TEST))
    model = MultiViewRiskNet(VIEW_DIMS)
    train_model(model, loader(source[0], shuffle=True), loader(source[1]), "cpu", epochs=1)
    source_only = metrics(model, loader(target[2]), "cpu")
    assert source_only["auroc"] == pytest.approx(.429, abs=.001)
    assert source_only["ap"] == pytest.approx(.328, abs=.001)
    scores = score_modules(extract_features(model, loader(source[1]), "cpu"),
                           extract_features(model, loader(target[0]), "cpu"), normalize=False)
    mask, _ = select_adaptation_mask(scores)
    adapted, integrity = adapt_model(model, mask, loader(target[0]), loader(target[1]), "cpu", epochs=1)
    assert integrity["ok"]
    assert metrics(adapted, loader(target[2]), "cpu")["brier"] >= 0


def test_optional_xgboost_end_to_end(source, target, tmp_path):
    try:
        import xgboost  # noqa: F401
    except Exception:
        pytest.skip("Optional XGBoost/native runtime unavailable; core suite does not require it")
    result = run_experiment(source, target, ExperimentConfig(
        epochs_source=1, epochs_target=1, device="cpu", output_dir=str(tmp_path), modes=("xgboost",),
    ))
    assert result["target_metrics"]["xgboost"]["ap"] is not None
    assert result["methods"]["xgboost"]["hyperparameters"]["missing"] == "nan"
    assert json.loads((Path(result["output_directory"]) / "results.json").read_text())["target_metrics"] == result["target_metrics"]
