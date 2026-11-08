"""Private aggregate presentation only; receives no participant records."""
from pathlib import Path
import os
EXPECTED=('calibrated_logical','head_only','full_finetune','random_calibrated_logical','source_multiview','target_logistic')
COLUMNS=('TP','TN','FP','FN','accuracy','precision','recall','specificity','f1','balanced_accuracy','auroc','ap','brier')
def number(x):return 'N/A' if x is None else f'{x:.6f}'
def render(report,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=Path(out);synthetic=report['analysis']=='SYNTHETIC_ONLY'
    lines=['# '+('SYNTHETIC EXAMPLE — NOT STUDY RESULTS' if synthetic else 'PRIVATE SUPPLEMENTARY CLASSIFICATION METRICS'),'',
      'DISCLOSURE NOT CLEARED. Counts, figures and this report must remain in the authorized environment.',
      'Rows use predicted positive when probability >= threshold. Undefined ratios are N/A.',
      f"Distinct test people: {report['distinct_test_participants']}; the ten draws share these people. No probability ensemble or 2,830-person pool is used.",'',
      '## Table 1 — Per-draw operating points','', '| Model | Policy | Draw | Threshold | '+' | '.join(COLUMNS)+' |','|---|---|---:|---:|'+ '|'.join(['---:']*len(COLUMNS))+'|']
    for mi,(name,policies) in enumerate(report['models'].items()):
        for policy,data in policies.items():
            if not isinstance(data,dict) or 'per_draw' not in data:continue
            rows=data['per_draw']
            for i,row in enumerate(rows):
                lines.append('| '+f'{name} | {policy} | {i} | {number(row["threshold"])} | '+' | '.join(number(row[k]) for k in COLUMNS)+' |')
                _figure(plt,[[row['TN'],row['FP']],[row['FN'],row['TP']]],f'{name}; {policy}; draw {i}; threshold {row["threshold"]:.4f}',out/f'model_{mi}_{policy}_draw_{i}.svg',False)
            summary=data['summary'];cm=[[summary['TN']['mean'],summary['FP']['mean']],[summary['FN']['mean'],summary['TP']['mean']]]
            _figure(plt,cm,f'{name}; {policy}; mean of {len(rows)} fits on SAME people',out/f'model_{mi}_{policy}_descriptive_mean.svg',True)
    lines+=['','## Table 2 — Descriptive method means','',
      'Means of per-draw metrics; SD is sample SD (ddof=1), not an independent-test standard error. Fractional mean confusion entries are not a single confusion matrix.',
      '| Model | Policy | Draws | Threshold mean [range] | '+' | '.join(COLUMNS)+' |', '|---|---|---:|---|'+ '|'.join(['---:']*len(COLUMNS))+'|']
    details=[]
    for name in (list(report['models']) if synthetic else EXPECTED):
        if name not in report['models']:
            lines.append('| '+name+' | NOT AVAILABLE | — | — | '+' | '.join(['NOT AVAILABLE']*len(COLUMNS))+' |');continue
        for policy,data in report['models'][name].items():
            if not isinstance(data,dict) or 'summary' not in data:continue
            s=data['summary'];t=s['threshold'];lines.append('| '+f'{name} | {policy} | {len(data["per_draw"])} | {number(t["mean"])} [{number(t["min"])}, {number(t["max"])}] | '+' | '.join(number(s[k]['mean']) for k in COLUMNS)+' |')
            details+=['',f'### {name}: {policy} variability','', '| Metric | Mean | SD | Range | Defined / undefined |','|---|---:|---:|---|---:|']
            for k in COLUMNS:
                a=s[k];details.append(f'| {k} | {number(a["mean"])} | {number(a["sd"])} | [{number(a["min"])}, {number(a["max"])}] | {a["n_defined"]} / {a["n_undefined"]} |')
    lines+=details
    lines+=['','AUROC summarizes ranking across operating points; accuracy depends on this one threshold and prevalence. AP summarizes ranked precision–recall and is not precision at 0.5. Threshold changes cannot change AP/AUROC for unchanged scores.',
      'Fixed 0.50 is a supplementary post-hoc descriptive point. Any validation-F1 point uses validation alone, with highest-threshold tie breaking; using the same 13-positive validation sample to choose and describe a threshold is optimistic and unstable.',
      'Only 21 positive test reports underpin sensitivity: one positive changes recall by 1/21. Counts and fixed-threshold summaries do not establish clinical validity, calibrated risk or selector superiority. Original registered AP/AUROC/Brier and the inconclusive paired AP interval remain unchanged.']
    fd=os.open(out/'SUPERVISOR_CLASSIFICATION_METRICS.private.md',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write('\n'.join(lines)+'\n')
def _figure(plt,cm,title,path,mean):
    fig,ax=plt.subplots(figsize=(5.4,4.5));im=ax.imshow(cm,cmap='Blues',vmin=0)
    for i in range(2):
        for j in range(2):ax.text(j,i,f'{cm[i][j]:.2f}' if mean else str(cm[i][j]),ha='center',va='center',fontsize=15)
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Predicted negative','Predicted positive'],yticklabels=['Actual negative','Actual positive'],xlabel='Predicted label',ylabel='Observed label',title=title)
    ax.set_title(title,fontsize=9);fig.tight_layout()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:fig.savefig(f,format='svg')
    fd=os.open(path.with_suffix('.png'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:fig.savefig(f,format='png',dpi=140)
    plt.close(fig)
