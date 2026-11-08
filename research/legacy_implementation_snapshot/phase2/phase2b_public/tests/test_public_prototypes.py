"""Invented-feature tests; no private-path discovery or real-data access."""

import json
from pathlib import Path

import numpy as np
import pytest

from phase2.phase2b_public.contracts import FEATURES, VIEWS, FeatureBatch, Role, TrainingOnlyStandardizer
from phase2.phase2b_public.source_shrinkage import fit_fixed_penalty, global_source_penalties
from phase2.phase2b_public.baseline_models import fit_elastic_net, fit_boosted_tree


def invented(seed=41):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(80, len(FEATURES)))
    y = (rng.uniform(size=80) < (1 / (1 + np.exp(-(0.6 * x[:, 0] - 0.4 * x[:, 4]))))).astype(int)
    assert set(y) == {0, 1}
    return x, y


def batch(x, role):
    return FeatureBatch(x, FEATURES, role)


def test_schema_and_preprocessing_roles():
    x, _ = invented()
    source = FeatureBatch(x, FEATURES, Role.SOURCE_TRAIN)
    normalizer = TrainingOnlyStandardizer().fit(source)
    np.testing.assert_allclose(normalizer.transform(source).mean(axis=0), 0, atol=1e-12)
    with pytest.raises(ValueError):
        normalizer.fit(FeatureBatch(x, FEATURES, Role.TARGET_ADAPTATION))
    for role in (Role.SOURCE_VALIDATION, Role.TARGET_VALIDATION, Role.TARGET_TEST):
        with pytest.raises(PermissionError):
            TrainingOnlyStandardizer().fit(FeatureBatch(x, FEATURES, role))
    with pytest.raises(PermissionError):
        normalizer.transform(FeatureBatch(x, FEATURES, Role.TARGET_TEST))
    with pytest.raises(ValueError):
        normalizer.transform(FeatureBatch(x, tuple(reversed(FEATURES)), Role.TARGET_VALIDATION))


def test_fixed_penalty_source_and_target_prototypes_are_deterministic():
    x, y = invented()
    source_a = fit_fixed_penalty(batch(x, Role.SOURCE_TRAIN), y, l2=0.5)
    source_b = fit_fixed_penalty(batch(x, Role.SOURCE_TRAIN), y, l2=0.5)
    np.testing.assert_array_equal(source_a.coefficients, source_b.coefficients)
    target_x, target_y = invented(43)
    global_fit = fit_fixed_penalty(batch(target_x, Role.TARGET_ADAPTATION), target_y, center=source_a,
                                   view_penalties=global_source_penalties(2.0))
    selective_fit = fit_fixed_penalty(batch(target_x, Role.TARGET_ADAPTATION), target_y, center=source_a,
                                      view_penalties={name: (3.0 if name == "background" else 0.5)
                                                      for name in VIEWS})
    assert global_fit.coefficients.shape == (8,)
    assert np.isfinite(global_fit.probability(target_x)).all()
    assert ((global_fit.probability(target_x) >= 0) & (global_fit.probability(target_x) <= 1)).all()
    assert not np.array_equal(global_fit.coefficients, selective_fit.coefficients)
    np.testing.assert_array_equal(source_a.coefficients, source_b.coefficients)
    with pytest.raises(ValueError):
        source_a.coefficients[0] = 99


def test_bad_labels_and_unfixed_penalties_are_rejected():
    x, y = invented()
    with pytest.raises(ValueError):
        fit_fixed_penalty(batch(x, Role.SOURCE_TRAIN), np.zeros(len(x)))
    with pytest.raises(ValueError):
        fit_fixed_penalty(batch(x, Role.SOURCE_TRAIN), y, view_penalties=global_source_penalties(1.0))
    source = fit_fixed_penalty(batch(x, Role.SOURCE_TRAIN), y)
    with pytest.raises(ValueError):
        fit_fixed_penalty(batch(x, Role.TARGET_ADAPTATION), y, center=source, view_penalties={"background": 1.0})
    with pytest.raises(ValueError):
        fit_fixed_penalty(batch(x, Role.TARGET_ADAPTATION), y, center=source, view_penalties=global_source_penalties(-1.0))


def test_no_validation_or_test_fitting_and_no_source_centered_source_refit():
    x, y = invented()
    source = fit_fixed_penalty(batch(x, Role.SOURCE_TRAIN), y)
    for role in (Role.SOURCE_VALIDATION, Role.TARGET_VALIDATION, Role.TARGET_TEST):
        with pytest.raises(PermissionError):
            fit_fixed_penalty(batch(x, role), y)
    with pytest.raises(PermissionError):
        fit_fixed_penalty(batch(x, Role.SOURCE_TRAIN), y, center=source,
                          view_penalties=global_source_penalties(1.0))


def test_registration_remains_pending():
    path = Path(__file__).parents[1] / "experiment_registration.template.json"
    registration = json.loads(path.read_text())
    assert registration["human_scientific_approval"] is False
    assert registration["external_test_partition"] == "NOT_CREATED"
    assert registration["real_data_paths"] is None
    assert tuple(registration["feature_order"]) == FEATURES


def test_declared_classical_baselines_use_only_training_roles_and_invented_data():
    x, y = invented()
    training = batch(x, Role.SOURCE_TRAIN)
    for fit in (
        lambda data: fit_elastic_net(data, y, c=1.0, l1_ratio=0.5, seed=7),
        lambda data: fit_boosted_tree(data, y, iterations=12, learning_rate=0.1, seed=7),
    ):
        first, second = fit(training), fit(training)
        np.testing.assert_allclose(first.probability(batch(x, Role.SOURCE_VALIDATION)),
                                   second.probability(batch(x, Role.SOURCE_VALIDATION)), atol=1e-10)
        for role in (Role.TARGET_VALIDATION, Role.TARGET_TEST):
            with pytest.raises(PermissionError):
                fit(batch(x, role))
        with pytest.raises(PermissionError):
            first.probability(batch(x, Role.TARGET_TEST))
