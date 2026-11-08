"""Private paired estimands and participant-cluster conditional uncertainty."""
import numpy as np
from sklearn.metrics import average_precision_score
from local_execution import need
from retained_runtime import api


def primary_stat(cells,indices=None):
    """Equal fold weights within repeat, equal repeat weights; requires all cells."""
    t=api();values=[]
    for cell in cells:
        y=np.asarray(cell['y']);a=np.asarray(cell['probabilities']['A']);b=np.asarray(cell['probabilities']['B'])
        if indices is not None:
            # Same global participant bootstrap weights for every repeat, fold and arm.
            counts=np.bincount(indices,minlength=cell['population_n'])
            local=np.repeat(np.arange(len(y)),counts[np.asarray(cell['outer_indices'])])
            if not len(local):return None
            y,a,b=y[local],a[local],b[local]
        if not y.sum():return None
        values.append(float(average_precision_score(y,b)-average_precision_score(y,a)))
    return float(np.mean(values)) if len(values)==9 else None


def summarize(cells,protocol):
    t=api();groups=[]
    for fraction in protocol['budget_fractions']:
        cc=[c for c in cells if c['fraction']==fraction];evaluated=[c for c in cc if c['status']=='EVALUATED']
        paired=[]
        for c in evaluated:
            own={}
            for contrast,base in [('B_minus_A','A'),('B_minus_C','C'),('A_minus_C','C')]:
                arm='A' if contrast=='A_minus_C' else 'B'
                own[contrast]={k:c['metrics'][arm]['fixed_0_50'][k]-c['metrics'][base]['fixed_0_50'][k]
                               if c['metrics'][arm]['fixed_0_50'][k] is not None and c['metrics'][base]['fixed_0_50'][k] is not None else None
                               for k in ['ap','auroc','brier']}
            paired.append({'repeat_seed':c['repeat_seed'],'fold':c['fold'],**own})
        delta=primary_stat(evaluated)
        defined=[r['B_minus_A']['ap'] for r in paired if r['B_minus_A']['ap'] is not None]
        secondary_means={}
        for metric in ['auroc','brier']:
            values=[r['B_minus_A'][metric] for r in paired]
            secondary_means[metric]=float(np.mean(values)) if len(values)==9 and all(v is not None for v in values) else None
        n=cc[0]['population_n'];reps=[]
        rng=np.random.default_rng(protocol['bootstrap_seed'])
        for _ in range(protocol['bootstrap_repetitions']):
            ix=rng.integers(0,n,n)
            value=primary_stat(evaluated,ix) if len(evaluated)==9 else None
            reps.append(value)
        valid=[x for x in reps if x is not None]
        enough=len(valid)>=int(np.ceil(.95*len(reps))) and delta is not None
        uncertainty={'method':'global_participant_cluster_percentile_recompute_equal_fold_AP_difference',
            'defined_replicates':len(valid),'undefined_replicates':len(reps)-len(valid),
            'conditional_on_fitted_models':True,'includes_retraining_uncertainty':False,
            'status':'DESCRIPTIVE_CONDITIONAL' if enough else 'INSUFFICIENT_BOOTSTRAP_SUPPORT',
            'interval_95':np.quantile(valid,[.025,.975]).tolist() if enough else None,
            'family_five_budget_interval_99':np.quantile(valid,[.005,.995]).tolist() if enough else None,
            'family_interval_is_descriptive_not_confirmatory_familywise_certification':True}
        pooled=[]
        for seed in protocol['repeat_seeds']:
            rr=[c for c in evaluated if c['repeat_seed']==seed]
            if len(rr)!=3:pooled.append({'repeat_seed':seed,'status':'INCOMPLETE'});continue
            indices=np.concatenate([c['outer_indices'] for c in rr]);need(len(set(indices.tolist()))==n,'POOLED_PARTICIPANT_COVERAGE_INVALID')
            y=np.concatenate([c['y'] for c in rr])
            mm={a:t.metrics(y,np.concatenate([c['probabilities'][a] for c in rr])) for a in ['A','B','C']}
            pooled.append({'repeat_seed':seed,'status':'COMPLETE','metrics':mm,
                           'B_minus_A_ap':mm['B']['ap']-mm['A']['ap'] if mm['A']['ap'] is not None else None})
        ops={}
        for arm in ['A','B','C']:
            supported=[c for c in evaluated if c['metrics'][arm]['calibrated'] is not None]
            # A and B have identical calibration class support; C intentionally not calibrated.
            ops[arm]={'supported_cells':len(supported),'calibrated':t.summarize([c['metrics'][arm]['calibrated'] for c in supported]) if supported else None,
                      'fixed_on_same_supported_cells':t.summarize([c['metrics'][arm]['fixed_0_50'] for c in supported]) if supported else None}
        groups.append({'fraction':fraction,'registered_cells':9,'evaluated_cells':len(evaluated),
            'primary_status':'COMPLETE' if delta is not None else 'UNAVAILABLE_MISSING_CELL_OR_POSITIVE_SUPPORT',
            'primary_equal_fold_B_minus_A_AP':delta,'available_fold_descriptive_mean':float(np.mean(defined)) if defined else None,
            'secondary_equal_fold_B_minus_A':secondary_means,
            'defined_AP_cells':len(defined),'paired_cells':paired,'primary_uncertainty':uncertainty,
            'secondary_pooled_OOF_per_repeat':pooled,'operating_point_support_matched':ops,
            'B_epoch_zero_selections':sum(c['training']['B']['selected_epoch']==0 for c in evaluated),
            'B_epoch_zero_selection_denominator':len(evaluated),
            'mean_selected_epoch':{a:float(np.mean([c['training'][a]['selected_epoch'] for c in evaluated])) if evaluated else None for a in ['A','B']}})
    return groups


def private_markdown(report,path):
    lines=['# PRIVATE epoch-zero development comparison','',report['scope'],
           'INDEPENDENT_TEST_NOT_AVAILABLE. Counts, scores, decisions and participant-derived fingerprints require disclosure review.',
           'A/B share source weights, fitting/stopping/calibration participants and random update prefixes. B may stop earlier under the same patience rule.',
           'Primary: mean of nine paired outer-fold AP differences (equal fold/repeat weight), separately at every budget.',
           'Pooled OOF is secondary and is a different estimand. Intervals condition on fitted models; repeats are correlated.',
           'No superiority or clinical acceptance is assigned automatically.','',
           '| Budget | B−A fold AP | B−A fold Brier | Conditional AP 95% interval | Descriptive five-budget AP 99% interval | Epoch0 selections | Status |',
           '|---|---:|---:|---|---|---:|---|']
    for g in report['comparison']:
        lines.append(f"| {g['fraction']:.0%} | {g['primary_equal_fold_B_minus_A_AP']} | {g['secondary_equal_fold_B_minus_A']['brier']} | {g['primary_uncertainty']['interval_95']} | {g['primary_uncertainty']['family_five_budget_interval_99']} | {g['B_epoch_zero_selections']}/{g['evaluated_cells']} | {g['primary_status']} |")
    lines += ['', 'Higher AP and lower Brier are favorable. Positive AP change with positive Brier change is a ranking/calibration trade-off; negative AP with lower Brier is the opposite trade-off. Neither sign alone establishes superiority. Selected stopping BCE is distinct from outer Brier and AP.',
              '', '## Cell metrics','',
              '| Seed / fold / budget | Arm | AP | AUROC | Brier | TP/TN/FP/FN at .50 | Recall / F1 | Selected / stopped epoch | Calibration |',
              '|---|---|---:|---:|---:|---|---|---|---|']
    for c in report['cells']:
        if c['status']!='EVALUATED':
            lines.append(f"| {c['repeat_seed']}/{c['fold']}/{c['fraction']} | ALL | N/A | N/A | N/A | N/A | N/A | N/A | {c['status']} |");continue
        for a in ['A','B','C']:
            m=c['metrics'][a]['fixed_0_50'];tr=c['training'].get(a)
            lines.append(f"| {c['repeat_seed']}/{c['fold']}/{c['fraction']} | {a} | {m['ap']} | {m['auroc']} | {m['brier']} | {m['TP']}/{m['TN']}/{m['FP']}/{m['FN']} | {m['recall']} / {m['f1']} | {str(tr['selected_epoch'])+'/'+str(tr['stopped_epoch']) if tr else '0/0'} | {c['calibration'][a]['status']} |")
    lines += ['', 'Calibration-selected F1/recall in the JSON are evaluated only on outer participants; the threshold itself is selected on training-side calibration labels. This is not fitted probability calibration.',
              'No calibration is applied to C, preserving its zero-target-conditioning-label meaning. If B selects epoch0, raw C/B scores must match exactly but B may still use paid calibration labels for a different operating point.',
              'All registered conditions, failure status, unavailable class support, curves, drift, update-prefix verification and pooled summaries are retained in the JSON. No repeated predictions represent independent people.']
    with path.open('x') as f:f.write('\n'.join(lines)+'\n')
