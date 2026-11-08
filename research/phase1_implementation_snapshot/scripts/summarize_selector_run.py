"""Verify and summarize a completed frozen selector run; does not tune policies."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def summarize(path: Path):
    protocol = json.loads((path / 'selector_config.json').read_text())
    held_summary = json.loads((path / 'heldout_summary.json').read_text())
    cfg = protocol['configuration']
    rows = pd.read_csv(path / 'per_run.csv')
    scores = pd.read_csv(path / 'module_scores.csv')
    identity = ['phase', 'scenario', 'scope', 'seed', 'target_event_budget']
    assert not rows.duplicated(identity + ['method']).any()
    assert (rows.status == 'valid').all(), 'Inspect invalid cells rather than omitting them'
    expected_cells = (len(protocol['development_conditions']) * len(cfg['development_seeds'])
                      + len(protocol['heldout_conditions']) * len(cfg['heldout_seeds'])) * len(cfg['event_budgets']) * len(cfg['scopes'])
    assert len(rows) == expected_cells * 10
    assert len(scores) == expected_cells * 7 * 3
    adapted = rows[rows.method != 'source_only']
    assert adapted.groupby(identity).adaptation_fingerprint.nunique().eq(1).all()
    assert (rows.adaptation_events == rows.target_event_budget).all()
    assert rows.frozen_integrity.all()
    # Selector scope/budget must not alter source-only pretraining or test split.
    source = rows[rows.method == 'source_only']
    assert source.groupby(['phase', 'scenario', 'seed']).ap.nunique().eq(1).all()
    assert scores[scores.module.str.startswith('fusion')].ground_truth.isna().all()
    assert protocol['freeze_sha256'] == held_summary['freeze_sha256']
    assert (path / 'selector_config.json').read_bytes() == (path / 'frozen_selector_config.json').read_bytes()
    manifest = json.loads((path / 'legacy_artifact_manifest.json').read_text())
    assert all(hashlib.sha256((Path(manifest['directory']) / name).read_bytes()).hexdigest() == digest
               for name, digest in manifest['sha256'].items())
    metrics = ['selection_precision', 'selection_recall', 'selection_f1', 'exact_mask_accuracy',
               'selection_jaccard', 'false_adaptation_rate', 'missed_adaptation_rate', 'ap', 'auroc', 'brier',
               'negative_transfer_ap', 'negative_transfer_auroc', 'transfer_gain_ap', 'transfer_gain_auroc',
               'adapted_module_count', 'adapted_parameter_fraction']
    held = rows[rows.phase == 'HELD_OUT']
    held.groupby(['scope', 'method'])[metrics].mean().to_csv(path / 'heldout_pooled.csv')
    held.groupby(['family', 'scope', 'method'])[metrics].mean().to_csv(path / 'heldout_by_family.csv')
    held.groupby(['family', 'level', 'scope', 'target_event_budget', 'method'])[metrics].mean().to_csv(path / 'heldout_curves.csv')
    scores.groupby(['phase', 'scenario', 'level', 'scope', 'target_event_budget', 'selector', 'module']).selected.mean().to_csv(path / 'module_selection_frequency.csv')
    random = held[held.method.str.startswith('random_')]
    diagnostics = random.groupby(['scope', 'method']).agg(
        mean_candidates=('candidate_count', 'mean'), min_candidates=('candidate_count', 'min'),
        max_candidates=('candidate_count', 'max'), exact_candidates=('exact_candidate_count', 'mean'),
        expected_equality=('equality_probability', 'mean'), empirical_equality=('same_as_adaptive', 'mean'),
        mean_parameter_error=('parameter_budget_error', 'mean'), max_parameter_error=('parameter_budget_error', 'max'))
    diagnostics.to_csv(path / 'random_control_summary.csv')
    random.groupby(['scope', 'method', 'adapted_parameter_count', 'candidate_count', 'exact_candidate_count']).agg(
        cells=('seed', 'size'), empirical_equality=('same_as_adaptive', 'mean'),
        expected_equality=('equality_probability', 'mean')).to_csv(path / 'random_budget_counts.csv')
    result = dict(cells=expected_cells, method_rows=len(rows), module_rows=len(scores),
                  development_rows=int((rows.phase == 'DEVELOPMENT').sum()), heldout_rows=len(held),
                  unique_fingerprints_per_cell=1, frozen_integrity_all=True, legacy_artifacts_unchanged=True,
                  chosen_policy=held_summary['selected_policy'], protocol_digest=protocol['freeze_sha256'])
    (path / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    print('\nHELD OUT POOLED\n', held.groupby(['scope', 'method'])[metrics].mean().round(4).to_string())
    print('\nRANDOM CONTROL\n', diagnostics.round(4).to_string())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    summarize(parser.parse_args().directory)
