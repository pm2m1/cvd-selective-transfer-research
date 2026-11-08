"""Private-only summaries; repeated participants are bootstrap clusters."""
import numpy as np
from local_execution import need
from package_runtime import api


def interval(values):
    good=[x for x in values if x is not None and np.isfinite(x)]
    return {'lower':float(np.quantile(good,.025)) if good else None,
            'upper':float(np.quantile(good,.975)) if good else None,
            'defined_replicates':len(good),'undefined_replicates':len(values)-len(good)}


def participant_bootstrap(y, probabilities, baseline, repetitions, seed):
    from sklearn.metrics import average_precision_score
    rng=np.random.default_rng(seed);ap=[];difference=[]
    for _ in range(repetitions):
        ix=rng.integers(0,len(y),len(y));labels=y[ix]
        if labels.sum()==0:
            ap.append(None);difference.append(None);continue
        own=float(np.mean([average_precision_score(labels,p[ix]) for p in probabilities]))
        ap.append(own)
        difference.append(own-float(np.mean([average_precision_score(labels,p[ix]) for p in baseline])) if baseline is not None else None)
    return {'ap_interval':interval(ap),'paired_ap_minus_matched_interval':interval(difference),
        'cluster_unit':'participant_shared_across_repeat_seeds','conditional_on_fitted_models':True,
        'includes_training_or_architecture_selection_uncertainty':False}


def summarize_results(rows,records,protocol,n,synthetic):
    t=api();groups=sorted({(r['method'],r['fraction']) for r in rows},key=lambda x:(x[1],x[0]));summaries=[]
    matrices={};labels={};per_repeat={}
    for key in groups:
        rr=[r for r in rows if (r['method'],r['fraction'])==key]
        predictions=[r for r in records if (r['method'],r['fraction'])==key]
        repeat_metrics=[];matrix=[];full=True;calibration_coverage=[]
        for seed in protocol['repeat_seeds']:
            pp=sorted([p for p in predictions if p['repeat_seed']==seed],key=lambda x:x['index'])
            need(len({p['index'] for p in pp})==len(pp),'DUPLICATE_OUTER_PARTICIPANT_WITHIN_REPEAT')
            if len(pp)!=n:
                full=False;continue
            need([p['index'] for p in pp]==list(range(n)),'OUTER_COVERAGE_INVALID')
            y=np.array([p['y'] for p in pp]);p=np.array([p['p'] for p in pp]);matrix.append(p)
            if key in labels:need(np.array_equal(labels[key],y),'OUTER_LABELS_CHANGED_BETWEEN_REPEATS')
            labels[key]=y
            repeat_metrics.append(t.metrics(y,p,.5))
            calibrated=[r for r in rr if r['repeat_seed']==seed and r['training_side_threshold'] is not None]
            counts={k:sum(r['training_side_threshold'][k] for r in calibrated) for k in ['TP','TN','FP','FN']}
            tp,tn,fp,fn=[counts[k] for k in ['TP','TN','FP','FN']]
            div=lambda a,b:a/b if b else None
            fixed_counts={k:sum(r['fixed_0_50'][k] for r in calibrated) for k in ['TP','TN','FP','FN']}
            ftp,ftn,ffp,ffn=[fixed_counts[k] for k in ['TP','TN','FP','FN']]
            calibration_coverage.append({'repeat_seed':seed,'outer_n_with_supported_threshold':tp+tn+fp+fn,
                **counts,'recall':div(tp,tp+fn),'specificity':div(tn,tn+fp),'precision':div(tp,tp+fp),
                'f1':div(2*tp,2*tp+fp+fn),'positive_predictions':tp+fp if tp+tn+fp+fn else None,
                'fixed_0_50_on_same_supported_subset':{**fixed_counts,'recall':div(ftp,ftp+ffn),
                    'specificity':div(ftn,ftn+ffp),'precision':div(ftp,ftp+ffp),'f1':div(2*ftp,2*ftp+ffp+ffn),
                    'positive_predictions':ftp+ffp if ftp+ftn+ffp+ffn else None},
                'conditional_on_training_side_calibration_support':True})
        if full and len(matrix)==len(protocol['repeat_seeds']):matrices[key]=np.array(matrix)
        per_repeat[key]=repeat_metrics
        actual=[r['budget_n'] for r in rr]
        summaries.append({'method':key[0],'fraction':key[1],'budget_n_min':min(actual),'budget_n_max':max(actual),
            'coverage':'COMPLETE' if key in matrices else 'INCOMPLETE_NO_PRIMARY_AGGREGATE',
            'fixed_0_50':t.summarize(repeat_metrics) if key in matrices else None,
            'calibrated_threshold_coverage':calibration_coverage,
            'target_compute_seconds':t.summarize([{'fit_selector_seconds':r['fit_selector_seconds'],
                'prediction_seconds':r['prediction_seconds']} for r in rr if r['status']=='EVALUATED' and 'fit_selector_seconds' in r])
                if any('fit_selector_seconds' in r for r in rr) else None,
            'trainable_parameter_counts':[r['trainable_parameters'] for r in rr if 'trainable_parameters' in r],
            'calibration_supported_folds':sum(r['training_side_threshold'] is not None for r in rr),
            'evaluated_folds':sum(r['status']=='EVALUATED' for r in rr)})
    for entry in summaries:
        key=entry['method'],entry['fraction'];baseline_key='matched_control',entry['fraction']
        baseline=matrices.get(baseline_key)
        if key in matrices:
            entry['participant_cluster_bootstrap']=participant_bootstrap(labels[key],matrices[key],baseline,
                25 if synthetic else protocol['bootstrap_repetitions'],protocol['bootstrap_seed'])
            entry['paired_repeat_ap_minus_matched']=[a['ap']-b['ap'] if a['ap'] is not None and b['ap'] is not None else None
                for a,b in zip(per_repeat[key],per_repeat.get(baseline_key,[]))]
    paired=[]
    lookup={(r['repeat_seed'],r['fold'],r['fraction'],r['method']):r for r in rows}
    for r in rows:
        if r['method'] in ['source_only_zero','matched_control'] or r['status']!='EVALUATED':continue
        b=lookup.get((r['repeat_seed'],r['fold'],r['fraction'],'matched_control'))
        if b is None or b['status']!='EVALUATED':continue
        paired.append({'repeat_seed':r['repeat_seed'],'fold':r['fold'],'fraction':r['fraction'],'method':r['method'],
            **{k:(r['fixed_0_50'][k]-b['fixed_0_50'][k] if r['fixed_0_50'][k] is not None and b['fixed_0_50'][k] is not None else None)
               for k in ['ap','auroc','brier']}})
    target=protocol['performance_target_ap']
    efficiency={'status':'NO_AP_TARGET_PRESPECIFIED_NO_MINIMUM_BUDGET_ESTIMATED','target_ap':target}
    if target is not None:
        efficiency={'status':'DESCRIPTIVE_REGISTERED_TARGET_REACH_NO_EXTRAPOLATION','target_ap':target,'methods':{}}
        for method in protocol['methods']:
            supported=[s for s in summaries if s['method']==method and s['coverage']=='COMPLETE'
                       and s['fixed_0_50']['ap']['mean'] is not None and s['fixed_0_50']['ap']['mean']>=target]
            efficiency['methods'][method]=min((s['fraction'] for s in supported),default=None)
    return {'learning_curve_summaries':summaries,'paired_outer_split_differences':paired,'label_efficiency':efficiency,
            'uncertainty_is_development_conditional_not_external_confirmation':True}


def private_markdown(report,path):
    lines=['# PRIVATE retrospective development label curves','',report['scope'],
        'No external confirmation. Architecture selection already used development labels.',
        'Budget includes fit + inner stopping + dedicated calibration. Evaluation-label cost and history are separate and not free.',
        'Rows are mean per-repeat participant-pooled OOF metrics. Repeats share participants; SD is not an independent-study uncertainty estimate.','',
        '| Method | Budget fraction | Actual label count | OOF AP | OOF AUROC | OOF Brier | Calibrated folds |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for s in report['learning_curve_summaries']:
        m=s['fixed_0_50']
        f=lambda k:'N/A' if m is None or m[k]['mean'] is None else f"{m[k]['mean']:.5f}"
        lines.append(f"| {s['method']} | {s['fraction']:.0%} | {s['budget_n_min']}–{s['budget_n_max']} | {f('ap')} | {f('auroc')} | {f('brier')} | {s['calibration_supported_folds']} |")
    lines += ['', '## Full target-label accounting',
        'Budget percentages below are incremental conditioning budgets, not total research-label costs. Previously used labels cannot be unlearned. Comparing/selecting methods after the curves also consumes all unique outer evaluation labels. Historical and current populations overlap, so their costs must not be blindly added.', '',
        '| Budget | Fit | Stop | Calibration | Total conditioning | Outer scoring | Conditioning + scoring |',
        '|---:|---:|---:|---:|---:|---:|---:|']
    for fraction in report['protocol']['budget_fractions']:
        rr=[r for r in report['rows'] if r['fraction']==fraction and r['method']=='matched_control']
        span=lambda key:f"{min(r[key] for r in rr)}–{max(r[key] for r in rr)}"
        lines.append(f"| {fraction:.0%} | "+' | '.join(span(k) for k in ['fit_n','stop_n','calibration_n','target_labels_fit_stop_calibration','outer_evaluation_labels','total_labels_in_this_split_including_evaluation'])+' |')
    lines += ['', 'Unique current outer-scoring participants: '+str(report['unique_target_evaluation_labels'])+'. Historical exposure is recorded in the private JSON; no zero-history prospective label-efficiency claim is made.']
    lines += ['', '## Threshold comparison on identical supported participants',
        'Fixed and calibrated decision metrics below use ONLY the same outer subsets with training-side calibration support. Missing support is not imputed. Full-population fixed-0.50 metrics remain in the JSON.', '',
        '| Method | Budget | Supported outer N/repeat | Fixed recall | Calibrated recall | Fixed F1 | Calibrated F1 | Fixed positive predictions | Calibrated positive predictions |',
        '|---|---:|---|---:|---:|---:|---:|---:|---:|']
    avg=lambda values:'N/A' if not [v for v in values if v is not None] else f"{np.mean([v for v in values if v is not None]):.5f}"
    for s in report['learning_curve_summaries']:
        if s['method']=='source_only_zero':continue
        cc=s['calibrated_threshold_coverage']
        values=[avg([r['fixed_0_50_on_same_supported_subset'][metric] for r in cc]) if fixed else avg([r[metric] for r in cc])
                for metric,fixed in [('recall',True),('recall',False),('f1',True),('f1',False),('positive_predictions',True),('positive_predictions',False)]]
        lines.append('| '+s['method']+f" | {s['fraction']:.0%} | "+'/'.join(str(r['outer_n_with_supported_threshold']) for r in cc)+' | '+' | '.join(values)+' |')
    lines += ['', '## Parameter and measured compute costs',
        '| Method | Budget | Trainable parameters min–max | Mean target fit + selector seconds | Mean prediction seconds |',
        '|---|---:|---:|---:|---:|']
    for s in report['learning_curve_summaries']:
        cost=s['target_compute_seconds'];counts=s['trainable_parameter_counts']
        if cost is None:continue
        lines.append(f"| {s['method']} | {s['fraction']:.0%} | {min(counts)}–{max(counts)} | {cost['fit_selector_seconds']['mean']:.4f} | {cost['prediction_seconds']['mean']:.4f} |")
    lines += ['', 'Source pretraining is cached/shared; its measured architecture-specific cost is reported separately in JSON, not charged repeatedly to every condition.']
    lines += ['', 'Detailed fixed-0.50 and held-out threshold confusion counts, recall/F1, abstentions, parameter counts, epoch traces and measured compute seconds are in followup_results.private.json.',
        'Calibration failure remains unavailable, never replaced by a favorable redraw or silently relabeled as fixed 0.50.',
        'Participant bootstrap intervals condition on fitted models and do not include training/architecture-selection uncertainty.',
        'INDEPENDENT_TEST_NOT_AVAILABLE. Do not upload this report or participant prediction/membership files without appropriate disclosure clearance.']
    with path.open('x') as f:f.write('\n'.join(lines)+'\n')


def plot_curves(report,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for method in report['protocol']['methods']:
        ss=sorted([s for s in report['learning_curve_summaries'] if s['method']==method and s['coverage']=='COMPLETE'],key=lambda s:s['fraction'])
        for ax,metric in zip(axes,['ap','auroc','brier']):
            line=ax.plot([s['fraction']*100 for s in ss],[s['fixed_0_50'][metric]['mean'] for s in ss],marker='o',label=method)[0]
            if metric=='ap':
                good=[s for s in ss if s['participant_cluster_bootstrap']['ap_interval']['lower'] is not None]
                ax.fill_between([s['fraction']*100 for s in good],
                    [s['participant_cluster_bootstrap']['ap_interval']['lower'] for s in good],
                    [s['participant_cluster_bootstrap']['ap_interval']['upper'] for s in good],color=line.get_color(),alpha=.12)
            ax.set(xlabel='Training-side label budget (%)',ylabel=metric.upper())
    axes[0].legend(fontsize=7);fig.suptitle(report['scope']+' — not external validation');fig.tight_layout()
    for ext in ['svg','png']:
        with (out/f'label_learning_curves.private.{ext}').open('xb') as f:fig.savefig(f,format=ext,dpi=140)
    plt.close(fig)
