from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from dmv_mat_cvd.config import ExperimentConfig
from dmv_mat_cvd.data.base import CohortPartition, CohortTable
from dmv_mat_cvd.data.budgets import InsufficientBudgetData, participant_fingerprint, sample_event_budget
from dmv_mat_cvd.data.controlled import SCENARIOS, ShiftScenario, generate_controlled_cohort, teacher_components
from dmv_mat_cvd.data.preprocessing import Preprocessor
from dmv_mat_cvd.data.schema import VIEW_FEATURES
from dmv_mat_cvd.data.splitting import split_source, split_target
from dmv_mat_cvd.evaluation import ModuleRepresentations
from dmv_mat_cvd.experiments import runner
from dmv_mat_cvd.experiments.validation import (VALIDATION_METHODS, ValidationConfig, mmd_comparability_audit,
                                               run_validation, summarize_runs)
from dmv_mat_cvd.experiments.validation_metrics import (describe, mask_jaccard, pairwise_mask_jaccard,
                                                       recovery_metrics, transfer_metrics)
from dmv_mat_cvd.models.multiview_mlp import MultiViewRiskNet
from dmv_mat_cvd.safeguards import LeakageError, SplitRole
from dmv_mat_cvd.transfer.scores import checked_discriminability, score_modules, InsufficientDiscriminability
from dmv_mat_cvd.transfer.selector import random_budget_mask, select_adaptation_mask


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_controlled_ground_truth_and_unaffected_views(name):
    scenario = SCENARIOS[name]
    reference = generate_controlled_cohort(500, "target", 17, SCENARIOS["A_no_shift"])
    target = generate_controlled_cohort(500, "target", 17, scenario)
    truth = scenario.ground_truth
    assert truth["fusion1"] is None and truth["fusion2"] is None
    for view, columns in VIEW_FEATURES.items():
        if view not in scenario.shifted_views or scenario.mechanism == "concept":
            pd.testing.assert_frame_equal(reference.records[list(columns)], target.records[list(columns)])
        assert truth[f"view:{view}"] == (view in scenario.shifted_views and scenario.mechanism in {"concept", "measurement"})
    if scenario.mechanism == "concept":
        pd.testing.assert_frame_equal(reference.predictors(), target.predictors())
        assert (reference.records.label != target.records.label).any()
    else:
        np.testing.assert_array_equal(reference.records.label, target.records.label)
    if scenario.mechanism == "nuisance":
        assert not np.allclose(reference.records.dbp, target.records.dbp)
        np.testing.assert_allclose(teacher_components(reference.records, scenario, "target"),
                                   teacher_components(target.records, scenario, "target"))


@pytest.mark.parametrize("name", ["B_haemodynamic", "C_haemodynamic_metabolic", "D_behaviour", "E_broad"])
def test_measurement_inverse_recovers_teacher_risk(name):
    scenario = SCENARIOS[name]
    source = generate_controlled_cohort(100, "source", 7, scenario)
    target = generate_controlled_cohort(100, "target", 7, scenario)
    np.testing.assert_allclose(teacher_components(source.records, scenario, "source"),
                               teacher_components(target.records, scenario, "target"), atol=1e-12)
    # The source local map on target observations is specifically wrong in changed views.
    incorrect = teacher_components(target.records, scenario, "source")
    correct = teacher_components(target.records, scenario, "target")
    for index, view in enumerate(VIEW_FEATURES):
        assert bool(not np.allclose(incorrect[:, index], correct[:, index])) == (view in scenario.shifted_views)


@pytest.mark.parametrize("options", [dict(mechanism="bad"), dict(shifted_views=("not_a_view",)),
                                     dict(mechanism="measurement"), dict(magnitude=-1),
                                     dict(mechanism="measurement", shifted_views=("metabolic", "metabolic"))])
def test_invalid_scenario_configuration(options):
    with pytest.raises(ValueError):
        ShiftScenario("invalid", **options)


def test_no_shift_same_teacher_for_both_domains():
    scenario = SCENARIOS["A_no_shift"]
    source = generate_controlled_cohort(100, "source", 8, scenario)
    target = generate_controlled_cohort(100, "target", 8, scenario)
    pd.testing.assert_frame_equal(source.predictors(), target.predictors())
    np.testing.assert_array_equal(source.records.label, target.records.label)


def test_recovery_and_jaccard_conventions():
    metric = recovery_metrics({"a": True, "b": True, "c": False, "fusion": True},
                              {"a": True, "b": False, "c": True, "fusion": None})
    assert metric["selection_precision"] == metric["selection_recall"] == metric["selection_f1"] == .5
    assert metric["exact_mask_accuracy"] == 0
    assert metric["false_adaptation_rate"] == 1
    assert metric["missed_adaptation_rate"] == .5
    assert metric["selection_jaccard"] == pytest.approx(1 / 3)
    empty = recovery_metrics({"view:a": False, "fusion": True}, {"view:a": False, "fusion": None})
    assert empty["exact_mask_accuracy"] == empty["selection_jaccard"] == empty["selection_f1"] == 1
    assert empty["selection_precision"] is None and empty["selection_recall"] is None
    assert empty["false_adaptation_rate"] == 0
    assert mask_jaccard([], []) == 1 and mask_jaccard(["a"], []) == 0
    assert pairwise_mask_jaccard([{"view:a": True}]) is None
    assert pairwise_mask_jaccard([{"view:a": True}, {"view:a": False}]) == 0
    assert pairwise_mask_jaccard([{"fusion1": True}, {"fusion1": False}], views_only=True) == 1
    with pytest.raises(ValueError):
        recovery_metrics({}, {"view:a": False})


def test_transfer_and_aggregate_metrics():
    values = transfer_metrics({"ap": .4, "auroc": .8}, {"ap": .5, "auroc": .7})
    assert values["transfer_gain_ap"] == pytest.approx(-.1)
    assert values["negative_transfer_ap"] is True and values["negative_transfer_auroc"] is False
    assert transfer_metrics({"ap": .5, "auroc": None}, {"ap": .5, "auroc": .7})["negative_transfer_ap"] is False
    assert transfer_metrics({"ap": .5, "auroc": None}, {"ap": .5, "auroc": .7})["negative_transfer_auroc"] is None
    stats = describe([.2, .4, None])
    assert stats["mean"] == pytest.approx(.3) and stats["std"] == pytest.approx(np.sqrt(.02))
    rows = [dict(scenario="A", seed=i, target_event_budget=10, method="full", status="valid",
                 ap=ap, negative_transfer_ap=negative) for i, ap, negative in [(0, .2, True), (1, .4, False)]]
    assert summarize_runs(rows, [])["groups"][0]["statistics"]["negative_transfer_ap"]["mean"] == .5


def test_nested_budget_and_role_safety():
    target = generate_controlled_cohort(1000, "target", 7, SCENARIOS["A_no_shift"])
    parts = split_target(target)
    small = sample_event_budget(parts["target_adaptation"], 10, 2)
    large = sample_event_budget(parts["target_adaptation"], 50, 2)
    assert small.participant_ids <= large.participant_ids
    assert small.cohort.records.label.sum() == 10 and large.cohort.records.label.sum() == 50
    assert participant_fingerprint(small) == participant_fingerprint(sample_event_budget(parts["target_adaptation"], 10, 2))
    assert not large.participant_ids.intersection(parts["target_test"].participant_ids)
    with pytest.raises(LeakageError):
        sample_event_budget(parts["target_test"], 10, 2)
    with pytest.raises(InsufficientBudgetData):
        sample_event_budget(parts["target_adaptation"], 10000, 2)
    with pytest.raises(ValueError):
        sample_event_budget(parts["target_adaptation"], 1, 2)
    all_positive = parts["target_adaptation"].cohort.records.copy()
    all_positive["label"], all_positive["endpoint_status"] = 1, "positive"
    with pytest.raises(InsufficientBudgetData, match="controls"):
        sample_event_budget(CohortPartition(CohortTable(all_positive, "test"), SplitRole.TARGET_ADAPTATION), 10, 2)


def test_all_adaptation_methods_receive_identical_participants(monkeypatch, tmp_path):
    source = generate_controlled_cohort(240, "source", 0, SCENARIOS["A_no_shift"])
    target = generate_controlled_cohort(400, "target", 100, SCENARIOS["A_no_shift"])
    captured = []
    actual_adapt = runner.adapt_model
    def capture(source_model, mask, train_loader, val_loader, device, **options):
        captured.append(train_loader.dataset)
        return actual_adapt(source_model, mask, train_loader, val_loader, device, **options)
    monkeypatch.setattr(runner, "adapt_model", capture)
    result = runner.run_experiment(source, target, ExperimentConfig(
        seed=0, target_event_budget=10, epochs_source=1, epochs_target=1, device="cpu",
        modes=VALIDATION_METHODS, mmd_max_samples=32, output_dir=str(tmp_path)))
    assert len(captured) == 5 and all(dataset is captured[0] for dataset in captured)
    assert captured[0].labels.sum().item() == 10
    selected = sample_event_budget(split_target(target, seed=1)["target_adaptation"], 10, 200)
    expected = Preprocessor().fit(split_source(source, seed=0)["source_train"]).transform(selected)
    assert all(torch.equal(captured[0].views[name], expected.views[name]) for name in expected.views)
    fingerprints = {result["methods"][method]["adaptation_participant_fingerprint"] for method in VALIDATION_METHODS if method != "source_only"}
    assert fingerprints == {participant_fingerprint(selected)}
    assert result["methods"]["random_mask"]["adapted_parameter_count"] == result["methods"]["dmv_mat"]["adapted_parameter_count"]


def test_checked_discriminability_and_score_determinism():
    rng = np.random.default_rng(3)
    features = rng.normal(size=(24, 5))
    labels = np.tile([0, 1], 12)
    value = checked_discriminability(features, labels)
    assert value.status == "valid"
    for scale in (.001, 10, 1000):
        assert checked_discriminability(features * scale, labels).value == pytest.approx(value.value, rel=1e-4)
    assert checked_discriminability(features, np.zeros(24)).value is None
    assert checked_discriminability(features[:3], np.array([0, 0, 1])).status == "insufficient_class_samples"
    assert checked_discriminability(np.zeros_like(features), labels).status == "degenerate_within_class_scatter"
    source = ModuleRepresentations({"module": features}, labels, SplitRole.SOURCE_VALIDATION)
    target = ModuleRepresentations({"module": features + .5}, labels, SplitRole.TARGET_ADAPTATION)
    assert score_modules(source, target, max_samples=8, seed=5) == score_modules(source, target, max_samples=8, seed=5)
    with pytest.raises(InsufficientDiscriminability):
        score_modules(source, replace(target, labels=np.zeros(24)))


def test_random_mask_exact_parameter_matching():
    model = MultiViewRiskNet({"background": 4, "haemodynamic": 2, "metabolic": 4,
                              "behaviour": 4, "comorbidity_medication": 3})
    reference = {name: name == "view:background" for name in model.selectable_modules()}
    selections = set()
    for seed in range(20):
        mask, diagnostics = random_budget_mask(model, reference, seed)
        assert diagnostics["parameter_budget_error"] == 0
        assert diagnostics["candidate_count"] == 3
        assert random_budget_mask(model, reference, seed) == (mask, diagnostics)
        selections.add(tuple(name for name, value in mask.items() if value))
    assert len(selections) == 3
    for value in (False, True):
        mask, diagnostic = random_budget_mask(model, dict.fromkeys(reference, value), 0)
        assert diagnostic["candidate_count"] == 1 and all(v == value for v in mask.values())


def test_mmd_comparability_audit_records_scale_effect():
    result = mmd_comparability_audit(replicates=2, n=16)
    assert result["maximum_radius_mmd_difference_under_rescaling"] < 1e-6
    same_dim = [row for row in result["groups"] if row["dimension"] == 16 and not row["shifted"]]
    assert max(row["raw_mmd"]["mean"] for row in same_dim) - min(row["raw_mmd"]["mean"] for row in same_dim) > .01


def test_class_centroid_magnitude_cannot_detect_label_orientation_reversal():
    features = np.random.default_rng(32).normal(size=(30, 4))
    labels = np.tile([0, 1], 15)
    assert checked_discriminability(features, labels).value == checked_discriminability(features, 1 - labels).value


def test_top_k_structurally_cannot_recover_all_share_or_all_adapt_views():
    scores = {name: {"mmd": 0.0, "discriminability": 1.0}
              for name in SCENARIOS["A_no_shift"].ground_truth}
    mask, _ = select_adaptation_mask(scores)
    assert sum(mask.values()) == 4
    assert recovery_metrics(mask, SCENARIOS["A_no_shift"].ground_truth)["exact_mask_accuracy"] == 0
    assert recovery_metrics(mask, SCENARIOS["E_broad"].ground_truth)["exact_mask_accuracy"] == 0


def test_repeated_seed_validation_reproducible(tmp_path):
    cfg = ValidationConfig(seeds=(0, 1), event_budgets=(10,), scenarios=("A_no_shift",),
                           source_n=160, target_n=240, epochs_source=1, epochs_target=1,
                           mmd_max_samples=32, output_dir=str(tmp_path))
    first = run_validation(cfg)
    second = run_validation(cfg)
    assert first["valid_cells"] == 2 and not first["invalid_cells"]
    assert first["groups"] == second["groups"]
    assert first["mask_stability"] == second["mask_stability"]
    for name in ("summary.json", "per_run.csv", "module_scores.csv", "masks.csv"):
        assert (Path(first["output_directory"]) / name).exists()
    summary = json.loads((Path(first["output_directory"]) / "summary.json").read_text())
    assert len(summary["groups"]) == 6
    assert all(group["statistics"]["exact_mask_accuracy"]["mean"] == 0 for group in summary["groups"] if group["method"] == "dmv_mat")


def test_infeasible_cells_recorded_without_fabricated_scores(tmp_path):
    cfg = ValidationConfig(seeds=(0,), event_budgets=(10000,), scenarios=("A_no_shift",),
                           source_n=80, target_n=80, epochs_source=1, epochs_target=1,
                           mmd_max_samples=16, output_dir=str(tmp_path))
    result = run_validation(cfg)
    assert result["valid_cells"] == 0 and len(result["invalid_cells"]) == 1
    assert all(group["valid_runs"] == 0 for group in result["groups"])
