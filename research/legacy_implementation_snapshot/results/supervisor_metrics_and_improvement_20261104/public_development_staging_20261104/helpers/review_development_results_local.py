#!/usr/bin/env python3
"""Private, aggregate development review. No prediction arrays or models are read."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import sys

CANDIDATES = ['matched_control', 'head_only', 'logical', 'compact_full',
              'target_lr_1e4', 'target_lr_3e4', 'target_logistic']


def summarize_report(report):
    """Pure aggregate checks. Never accept held-out or synthetic scores as real."""
    from run_development_workflow import need
    need(report.get('status') == 'PRIVATE_EXPLORATORY_DEVELOPMENT_NOT_EXTERNAL_VALIDATION'
         and report.get('test_predictions_generated') is False
         and report.get('adaptation_draws_are_not_independent_validations') is True,
         'DEVELOPMENT_REPORT_CONTRACT_MISMATCH')
    rows = report['rows']
    need(len(rows) == 70 and set(report['summary']) == set(CANDIDATES), 'DEVELOPMENT_REPORT_PLAN_MISMATCH')
    output = []
    for name in CANDIDATES:  # Prespecified order, not an automatic winner selection.
        rr = [r for r in rows if r['candidate']['id'] == name]
        need(len(rr) == 10 and sorted(r['draw'] for r in rr) == list(range(10)), 'DEVELOPMENT_DRAW_INVENTORY_MISMATCH')
        need(all(r['scope'] == 'EXPLORATORY_TARGET_DEVELOPMENT_ONLY'
                 and r['threshold_estimate_is_resubstitution'] is True for r in rr), 'DEVELOPMENT_SCOPE_MISMATCH')
        entry = {'candidate': name, 'draws': 10, 'fixed_0_50': {}, 'validation_selected': {}}
        for source, dest in [('fixed_0_5', 'fixed_0_50'), ('validation_selected_threshold', 'validation_selected')]:
            for r in rr:
                m = r[source]
                need(all(isinstance(m[k], int) and not isinstance(m[k], bool) and m[k] >= 0 for k in ['TP','TN','FP','FN']), 'DEVELOPMENT_COUNTS_INVALID')
                need(m['TP']+m['FN'] == 13 and m['TN']+m['FP'] == 158, 'VALIDATION_POPULATION_MISMATCH')
                need(0 <= m['threshold'] <= 1 and (source != 'fixed_0_5' or m['threshold'] == .5), 'DEVELOPMENT_THRESHOLD_MISMATCH')
            for key in ['ap', 'auroc', 'brier', 'recall', 'specificity', 'precision', 'f1', 'threshold']:
                values = [r[source][key] for r in rr if r[source][key] is not None]
                need(all(isinstance(x, (int, float)) and math.isfinite(x) and 0 <= x <= 1 for x in values), 'DEVELOPMENT_METRIC_INVALID')
                need(len(values) == 10 or key in {'precision','f1'}, 'DEVELOPMENT_METRIC_MISSING')
                entry[dest][key] = {'mean': statistics.mean(values) if values else None,
                    'sd': statistics.stdev(values) if len(values)>1 else None,
                    'min': min(values) if values else None, 'max': max(values) if values else None,
                    'undefined': 10-len(values)}
                # Verify the existing aggregate summary against its per-draw rows.
                old_key = 'fixed_0_5' if dest == 'fixed_0_50' else 'validation_selected'
                old = report['summary'][name][old_key][key]
                for field in ['mean','sd','min','max']:
                    v, expected = entry[dest][key][field], old[field]
                    need((v is None and expected is None) or (v is not None and expected is not None
                         and math.isclose(v, expected, rel_tol=1e-9, abs_tol=1e-12)), 'DEVELOPMENT_SUMMARY_MISMATCH')
        need(all(r['fixed_0_5'][k] == r['validation_selected_threshold'][k] for r in rr for k in ['ap','auroc','brier']), 'THRESHOLD_CHANGED_RANKING_METRICS')
        entry['trainable_parameters_by_draw'] = [r['trainable_parameters'] for r in rr]
        entry['training_by_draw'] = []
        for r in rr:
            tr = r['training']
            if tr is not None:
                need(isinstance(tr['selected_epoch'], int) and 1 <= tr['selected_epoch'] <= tr['stopped_epoch']
                     <= r['candidate']['target_epochs'], 'DEVELOPMENT_EPOCH_INVALID')
                entry['training_by_draw'].append({'draw': r['draw'], 'selected_epoch': tr['selected_epoch'],
                    'stopped_epoch': tr['stopped_epoch'], 'max_epochs': r['candidate']['target_epochs'],
                    'early_stopped': tr['stopped_epoch'] < r['candidate']['target_epochs']})
        output.append(entry)
    return {'scope': 'PRIVATE_DEVELOPMENT_REVIEW_NOT_EXTERNAL_VALIDATION', 'candidate_order': CANDIDATES,
            'shared_validation_contract': {'n': 171, 'positive_reports': 13},
            'draws_are_not_independent_populations': True,
            'validation_selected_f1_is_optimistic_same_validation_resubstitution': True,
            'scientific_or_clinical_success_claimed': False, 'candidates': output,
            'source_training_curves': report['source_training_curves']}


def format_table(review):
    def cell(s):
        return 'N/A' if s['mean'] is None else f"{s['mean']:.4f} ± {s['sd']:.4f}" if s['sd'] is not None else f"{s['mean']:.4f}"
    lines = ['# PRIVATE exploratory development comparison', '',
        'Same 171 validation participants / 13 positive reports; ten overlapping draws are not independent evaluations.',
        'Validation-selected F1 is optimistic SAME-VALIDATION RESUBSTITUTION. No locked-test evaluation; no external winner or clinical-success claim.', '',
        '| Candidate | Operating point | AP | AUROC | Brier | Recall | Specificity | Precision | F1 |',
        '|---|---|---|---|---|---|---|---|---|']
    for entry in review['candidates']:
        for key, label in [('fixed_0_50','fixed 0.50'), ('validation_selected','validation-selected (resubstitution)')]:
            m = entry[key]
            lines.append('| '+entry['candidate']+' | '+label+' | '+' | '.join(cell(m[k]) for k in ['ap','auroc','brier','recall','specificity','precision','f1'])+' |')
        counts = entry['trainable_parameters_by_draw']
        epochs = entry['training_by_draw']
        lines += ['', entry['candidate']+': trainable parameter counts per draw: '+', '.join('N/A' if n is None else str(n) for n in counts)+'.',
            'Selected/stopped epochs per draw: '+(', '.join(f"{r['selected_epoch']}/{r['stopped_epoch']}" for r in epochs) if epochs else 'not applicable (non-epoch model)')+'.', '']
    lines += ['Mean ± sample SD across draws is descriptive. Ranges, undefined-metric counts and early-stop indicators are in the companion private JSON.',
              'Source curves and development learning-curve artifacts remain local. Do not compare these scores with frozen test scores as matched evaluations.',
              'No report is disclosure-cleared by this utility. Do not upload private reports or logs to AI services.']
    return '\n'.join(lines)+'\n'


def write_review(report_path, destination, show=False):
    from run_development_workflow import need, read_json, private_json, sha
    need(not destination.exists(), 'PRIVATE_REVIEW_ALREADY_EXISTS')
    report = read_json(report_path)
    review = summarize_report(report)
    review['training_report_sha256'] = sha(report_path)
    text = format_table(review)
    destination.mkdir(mode=0o700)
    private_json(destination/'development_review.private.json', review)
    fd = os.open(destination/'development_comparison.private.md', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream: stream.write(text)
    if show: print(text)
    return text


def main(argv=None):
    # The orchestrator enforces the original environment boundary before any read.
    from run_development_workflow import HELPERS, independent_runtime, absolute, private_workspace, read_json, need, source_state, sha, Parser, COMPLETE
    try:
        independent_runtime(HELPERS.parent)
        p = Parser(prog='review_development_results_local.py')
        p.add_argument('--workspace', required=True)
        p.add_argument('--show-local', action='store_true')
        args = p.parse_args(argv)
        workspace = private_workspace(absolute(args.workspace))
        receipt = read_json(workspace/'workflow.completion.private.json')
        state = read_json(workspace/'workflow.prepared.private.json')
        need(receipt['status'] == COMPLETE and receipt['bindings'] == state['bindings']
             == source_state(HELPERS.parent, absolute(state['export_configuration'])), 'WORKFLOW_REVIEW_BINDING_MISMATCH')
        report_path = workspace/'training/exploratory_development.private.json'
        need(sha(report_path) == receipt['training_report_sha256'], 'TRAINING_REPORT_CHANGED')
        review = read_json(workspace/'local_review/development_review.private.json')
        need(review['training_report_sha256'] == sha(report_path)
             and sha(workspace/'local_review/development_review.private.json') == receipt['private_review_sha256']
             and sha(workspace/'local_review/development_comparison.private.md') == receipt['private_review_markdown_sha256'],
             'PRIVATE_REVIEW_BINDING_MISMATCH')
        if args.show_local: print(format_table(review))
        else: print('PRIVATE_REVIEW_EXISTS_NO_METRICS_DISCLOSED')
        return 0
    except BaseException:
        print('STOP ISSUE=PRIVATE_LOCAL_REVIEW_NOT_COMPLETED')
        return 2


if __name__ == '__main__':
    sys.exit(main())
