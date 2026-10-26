from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dmv_mat_cvd.config import ExperimentConfig
from dmv_mat_cvd.data.controlled import SCENARIOS, ShiftScenario, generate_controlled_cohort, teacher_components
from dmv_mat_cvd.evaluation import ModuleRepresentations
from dmv_mat_cvd.experiments import runner
from dmv_mat_cvd.experiments.selector_validation import (METHODS, Condition, SelectorValidationConfig, condition_grid,
    choose_on_development, run_selector_validation, validate_isolation, verify_frozen)
from dmv_mat_cvd.models.multiview_mlp import MultiViewRiskNet
from dmv_mat_cvd.safeguards import LeakageError, SplitRole
from dmv_mat_cvd.transfer.calibration import (CalibrationConfig, calibrated_mask, calibrate_modules,
                                              permutation_mmd, relative_geometry)
from dmv_mat_cvd.transfer.selector import legacy_topk, select_adaptation_mask, diverse_random_budget_mask

CFG = CalibrationConfig(permutations=19, bootstraps=39)


def geometry_data(n=400, seed=7):
    rng = np.random.default_rng(seed)
    y = np.tile([0, 1], n // 2)
    x = rng.normal(size=(n, 3))
    x[:, 0] += 3 * y
    return x, y


@pytest.mark.parametrize('policy', ['calibrated_threshold', 'calibrated_logical'])
@pytest.mark.parametrize('count', [0, 1, 7])
def test_variable_masks(policy, count):
    evidence = {str(i): dict(geometry_status='valid', signed_retention=-1. if i < count else 1.,
                             retention_upper=-.5 if i < count else 1.4,
                             domain_status='valid', domain_p=.9) for i in range(7)}
    mask, _ = calibrated_mask(evidence, policy, CFG)
    assert sum(mask.values()) == count


def test_legacy_snapshot_and_alias():
    snapshot = Path('docs/milestone2_selector.py.txt').read_bytes()
    assert hashlib.sha256(snapshot).hexdigest() == 'e3c0bcb05ad11bc8e20014dc23b3ce9ec65b3a1a303c7ec041637f481991a8be'
    assert legacy_topk is select_adaptation_mask
    namespace = {}
    exec(compile(snapshot, 'legacy_snapshot', 'exec'), namespace)
    rng = np.random.default_rng(22)
    for fraction in (0, .2, .5, 1):
        scores = {str(i): {'mmd': float(rng.random()), 'discriminability': float(rng.random())} for i in range(7)}
        assert legacy_topk(scores, adapt_fraction=fraction) == namespace['select_adaptation_mask'](scores, adapt_fraction=fraction)


def test_permutation_determinism_scaling_and_shift():
    rng = np.random.default_rng(7)
    x, y = rng.normal(size=(80, 4)), rng.normal(size=(90, 4))
    a = permutation_mmd(x, y, permutations=99, seed=2)
    assert a == permutation_mmd(x, y, permutations=99, seed=2)
    b = permutation_mmd(x * 10 + 3, y * 10 + 3, permutations=99, seed=2)
    assert a['domain_p'] == b['domain_p']
    assert a['permutation_mmd'] == pytest.approx(b['permutation_mmd'])
    duplicate = permutation_mmd(np.tile(x, (1, 3)), np.tile(y, (1, 3)), permutations=99, seed=2)
    assert a['domain_p'] == duplicate['domain_p']
    assert permutation_mmd(x, y + 3, permutations=99, seed=2)['domain_p'] <= .02
    assert a['calibration_source_n'] == 80 and a['calibration_target_n'] == 90


def test_mmd_null_and_degenerate_state():
    p_values = []
    for seed in range(40):
        rng = np.random.default_rng(seed)
        result = permutation_mmd(rng.normal(size=(40, 8)), rng.normal(size=(55, 8)), permutations=99, seed=seed)
        p_values.append(result['domain_p'])
        assert result['null_std'] > 0
    # Wide deterministic statistical guard, not a brittle exact rejection rate.
    assert .25 < np.mean(p_values) < .75
    assert np.mean(np.array(p_values) <= .05) <= .2
    result = permutation_mmd(np.zeros((10, 3)), np.zeros((12, 3)), permutations=19)
    assert result['domain_status'] == 'degenerate_null' and result['mmd_z'] is None
    assert result['domain_p'] == 1


def test_source_relative_geometry_preservation_and_concept_reversal():
    x, y = geometry_data()
    same = relative_geometry(x, y, x, y, config=CFG)
    flip = relative_geometry(x, y, x, 1 - y, config=CFG)
    assert same['signed_retention'] == pytest.approx(1)
    assert flip['signed_retention'] == pytest.approx(-1)
    assert flip['discriminability_ratio'] == pytest.approx(1)
    assert flip['retention_upper'] < 0
    for scaled in (x * .01, x * 100):
        value = relative_geometry(scaled, y, scaled, 1-y, config=CFG)
        assert value['signed_retention'] == pytest.approx(-1)
    evidence = {'m': {**flip, 'domain_status': 'valid', 'domain_p': .9}}
    assert all(calibrated_mask(evidence, p, CFG)[0]['m'] for p in ('calibrated_threshold', 'calibrated_logical'))


def test_nuisance_marginal_shift_does_not_force_adaptation():
    x, y = geometry_data()
    shifted = x + np.array([0., 6., 0.])
    geom = relative_geometry(x, y, shifted, y, config=CFG)
    evidence = {'m': {**geom, **permutation_mmd(x, shifted, permutations=99)}}
    assert evidence['m']['domain_p'] <= .02
    assert geom['signed_retention'] == pytest.approx(1)
    for policy in ('calibrated_threshold', 'calibrated_logical'):
        assert calibrated_mask(evidence, policy, CFG)[0] == {'m': False}


@pytest.mark.parametrize('case', ['one_class', 'small', 'zero_scatter', 'zero_source'])
def test_invalid_class_geometry_is_explicit(case):
    x, y = geometry_data(40)
    target, labels, source = x.copy(), y.copy(), x.copy()
    if case == 'one_class':
        labels[:] = 1
    elif case == 'small':
        labels[:] = 0
        labels[:3] = 1
    elif case == 'zero_scatter':
        target[:] = 1
    else:
        source = np.tile(np.arange(20)[:, None], (1, 3)).repeat(2, axis=0).astype(float)
    evidence = relative_geometry(source, y, target, labels, config=CFG)
    assert evidence['geometry_status'] != 'valid'
    assert evidence['retention_upper'] is None
    mask, reason = calibrated_mask({'m': {**evidence, 'domain_status': 'valid', 'domain_p': .01}}, 'calibrated_logical', CFG)
    assert not mask['m'] and reason['m'].startswith('ABSTAIN:')


def test_calibration_role_guard_and_determinism():
    x, y = geometry_data(40)
    source = ModuleRepresentations({'m': x}, y, SplitRole.SOURCE_VALIDATION)
    target = ModuleRepresentations({'m': x + .3}, y, SplitRole.TARGET_ADAPTATION)
    assert calibrate_modules(source, target, config=CFG) == calibrate_modules(source, target, config=CFG)
    for bad_source, bad_target in ((replace(source, role=SplitRole.SOURCE_TEST), target),
                                    (source, replace(target, role=SplitRole.TARGET_TEST)),
                                    (source, replace(target, role=SplitRole.TARGET_VALIDATION))):
        with pytest.raises(LeakageError):
            calibrate_modules(bad_source, bad_target, config=CFG)


@pytest.mark.parametrize('angle', [.4, 1., 2.2])
def test_rotation_known_mechanism_and_inverse(angle):
    scenario = ShiftScenario('rotation', 'rotation', ('haemodynamic', 'metabolic'), angle, 'saturating')
    source = generate_controlled_cohort(100, 'source', 4, scenario)
    target = generate_controlled_cohort(100, 'target', 4, scenario)
    np.testing.assert_allclose(teacher_components(source.records, scenario, 'source'),
                               teacher_components(target.records, scenario, 'target'), atol=1e-12)
    np.testing.assert_array_equal(source.records.label, target.records.label)
    assert sum(v is True for v in scenario.ground_truth.values()) == 2
    assert scenario.ground_truth['fusion1'] is None


def test_grid_isolation_and_frozen_choice_does_not_use_prediction():
    dev, held = condition_grid()
    validate_isolation(dev, held, (1,), (100,))
    with pytest.raises(ValueError):
        validate_isolation(dev, held, (1,), (1,))
    with pytest.raises(ValueError):
        validate_isolation(dev, (replace(dev[0], phase='HELD_OUT'),), (1,), (100,))
    rows = [dict(phase='DEVELOPMENT', method=p, scope='all', status='valid', family=f,
                 selection_f1=.7, false_adaptation_rate=.1, adapted_parameter_fraction=.4,
                 ap=10 if p == 'legacy_topk' else -10)
            for p in ('legacy_topk', 'calibrated_threshold', 'calibrated_logical') for f in ('no_shift', 'concept')]
    choice = choose_on_development(rows)
    for row in rows:
        row['ap'] *= -100
    assert choose_on_development(rows) == choice
    rows[0]['phase'] = 'HELD_OUT'
    with pytest.raises(ValueError):
        choose_on_development(rows)
    with pytest.raises(ValueError):
        verify_frozen({'status': 'DEVELOPMENT'}, Path('.'))


def test_random_control_diversity_and_tolerance():
    model = MultiViewRiskNet({'background': 4, 'haemodynamic': 2, 'metabolic': 4, 'behaviour': 4, 'comorbidity_medication': 3})
    reference = {name: name in {'view:haemodynamic', 'fusion1', 'fusion2'} for name in model.selectable_modules()}
    masks = set()
    for seed in range(100):
        mask, detail = diverse_random_budget_mask(model, reference, seed)
        assert detail['parameter_budget_error'] <= detail['budget_tolerance_parameters']
        assert detail['equality_probability'] == 1 / detail['candidate_count']
        masks.add(tuple(mask.values()))
    assert len(masks) >= 4
    with pytest.raises(ValueError):
        diverse_random_budget_mask(model, reference, 0, views_only=True)


@pytest.mark.parametrize("scope", ["all", "views"])
def test_same_adaptation_dataset_all_policies_and_methods(monkeypatch, tmp_path, scope):
    source = generate_controlled_cohort(240, 'source', 0, SCENARIOS['A_no_shift'])
    target = generate_controlled_cohort(400, 'target', 100, SCENARIOS['A_no_shift'])
    captured = []
    actual = runner.adapt_model
    def capture(model, mask, train, val, device, **options):
        captured.append(train.dataset)
        return actual(model, mask, train, val, device, **options)
    monkeypatch.setattr(runner, 'adapt_model', capture)
    result = runner.run_experiment(source, target, ExperimentConfig(seed=0, target_event_budget=10,
        epochs_source=1, epochs_target=1, modes=METHODS, selector_scope=scope, calibration=CFG, device='cpu',
        mmd_max_samples=16, output_dir=str(tmp_path)))
    for name, values in result['module_scores'].items():
        if scope == 'views' and name.startswith('fusion'):
            assert values['normalized_mmd'] is None and values['adapt_score'] is None
        else:
            expected = .65 * values['normalized_mmd'] + .35 * (1 - values['normalized_discriminability'])
            assert values['adapt_score'] == pytest.approx(expected)
    assert len(captured) == 9 and all(ds is captured[0] for ds in captured)
    assert captured[0].labels.sum().item() == 10
    assert len({result['methods'][m]['adaptation_participant_fingerprint'] for m in METHODS[1:]}) == 1
    assert all(result['methods'][m]['frozen_integrity']['ok'] for m in METHODS)


def test_protocol_end_to_end_and_reproducibility(monkeypatch, tmp_path):
    import dmv_mat_cvd.experiments.selector_validation as module
    dev, held = condition_grid()
    # Keep required controls and concepts, with distinct conditions in held-out.
    small = (tuple(c for c in dev if c.key in {'A_no_shift', 'F_concept'}),
             tuple(c for c in held if c.key in {'held_no_shift', 'held_concept_high'}))
    monkeypatch.setattr(module, 'condition_grid', lambda: small)
    cfg = SelectorValidationConfig(development_seeds=(0,), heldout_seeds=(100,), event_budgets=(10,),
        scopes=('all',), source_n=160, target_n=240, epochs_source=1, epochs_target=1,
        permutations=19, bootstraps=39, mmd_max_samples=16, output_dir=str(tmp_path))
    first, second = run_selector_validation(cfg), run_selector_validation(cfg)
    assert first['choice'] == second['choice']
    assert first['heldout_summary']['groups'] == second['heldout_summary']['groups']
    output = Path(first['output_directory'])
    for name in ('development_summary.json', 'heldout_summary.json', 'selector_config.json', 'per_run.csv', 'module_scores.csv', 'masks.csv'):
        assert (output / name).exists()
    protocol = json.loads((output / 'selector_config.json').read_text())
    verify_frozen(protocol, Path(module.__file__).parents[1])
    protocol['calibration']['alpha'] = .3
    with pytest.raises(ValueError, match='changed'):
        verify_frozen(protocol, Path(module.__file__).parents[1])


def test_calibrated_runner_does_not_inspect_test_and_abstains_on_one_class(tmp_path):
    from dmv_mat_cvd.data.base import CohortTable
    from dmv_mat_cvd.data.splitting import split_target
    source = generate_controlled_cohort(240, 'source', 3, SCENARIOS['A_no_shift'])
    target = generate_controlled_cohort(400, 'target', 103, SCENARIOS['A_no_shift'])
    cfg = ExperimentConfig(seed=3, target_event_budget=10, epochs_source=1, epochs_target=1,
                           modes=('dmv_mat',), selector_policy='calibrated_logical', calibration=CFG,
                           device='cpu', mmd_max_samples=16, output_dir=str(tmp_path))
    first = runner.run_experiment(source, target, cfg)
    parts = split_target(target, seed=4)
    frame = target.records.copy()
    test = frame.participant_id.isin(parts['target_test'].participant_ids)
    frame.loc[test, 'sbp'] += 1000
    second = runner.run_experiment(source, CohortTable(frame, target.domain), cfg)
    assert first['calibration_scores'] == second['calibration_scores']
    assert first['policy_masks'] == second['policy_masks']
    adaptation = frame.participant_id.isin(parts['target_adaptation'].participant_ids)
    frame.loc[adaptation, 'label'] = 1
    frame.loc[adaptation, 'endpoint_status'] = 'positive'
    frame.loc[adaptation, 'event_type'] = 'mi'
    frame.loc[adaptation, 'event_time_days'] = 500
    third = runner.run_experiment(source, CohortTable(frame, target.domain), replace(cfg, target_event_budget=None))
    assert not any(third['policy_masks']['calibrated_logical'].values())
    assert all(v['geometry_status'] != 'valid' for v in third['calibration_scores'].values())
