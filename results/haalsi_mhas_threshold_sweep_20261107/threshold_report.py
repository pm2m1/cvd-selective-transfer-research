"""Private aggregate-only tables/figures. No participant vectors accepted."""
import csv
import os
from pathlib import Path
import numpy as np
from local_execution import need

METRICS=('TP','TN','FP','FN','accuracy','precision','recall','specificity','f1','balanced_accuracy','auroc','ap','brier')


def text_file(path):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    return os.fdopen(fd,'w',newline='')


def save(fig,path,fmt):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:fig.savefig(f,format=fmt,dpi=150,bbox_inches='tight')


def confusion(plt,row,title,path):
    cm=[[row['TN'],row['FP']],[row['FN'],row['TP']]]
    need(all(type(n) is int for line in cm for n in line),'MEAN_COUNTS_CANNOT_BE_ONE_CONFUSION_MATRIX')
    fig,ax=plt.subplots(figsize=(5.5,4.8));ax.imshow(cm,cmap='Blues',vmin=0)
    maximum=max(max(r) for r in cm)
    for i in range(2):
        for j in range(2):ax.text(j,i,str(cm[i][j]),ha='center',va='center',fontsize=17,
                                color='white' if cm[i][j] > maximum/2 else 'black')
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Predicted negative','Predicted positive'],
        yticklabels=['Observed negative','Observed positive'],xlabel='Predicted label',ylabel='Observed label')
    ax.set_title(title,fontsize=10,pad=12);fig.tight_layout();save(fig,path,'svg');plt.close(fig)


def number(value):return 'N/A' if value is None else f'{value:.6f}'


def render(report,out):
    import matplotlib
    matplotlib.use('Agg',force=True)
    import matplotlib.pyplot as plt
    out=Path(out);synthetic=report['analysis']=='SYNTHETIC_ONLY';prefix='INVENTED SYNTHETIC EXAMPLE' if synthetic else 'PRIVATE POST-HOC DESCRIPTIVE ANALYSIS'
    cmroot=out/'confusion_matrices';cmroot.mkdir(mode=0o700,exist_ok=False)
    chartroot=out/'summary_plots';chartroot.mkdir(mode=0o700,exist_ok=False)
    lines=['# '+prefix+' — frozen-score threshold sweep','',
        'DISCLOSURE NOT CLEARED. Keep all counts, tables, figures and this report inside the authorized environment.',
        'SYNTHETIC DATA ONLY; NOT CLINICAL FINDINGS.' if synthetic else 'No model fitting, inference, score transformation or test-based threshold selection occurred.',
        f"Distinct test participants: {report['distinct_test_participants']}; positive reports: {report['positive_reports']}; negative observations: {report['negative_observations']}.",
        'Ten adaptation draws reuse ONE shared population. They are not ten independent cohorts or 2,830 independent participants.',
        'Predicted positive means probability >= cutoff. Undefined ratios are N/A. AP/AUROC/Brier remain unchanged for unchanged scores.',
        'The complete fixed grid is specified for this supplement, not the original preregistered primary analysis. No best test threshold is selected or highlighted.',
        '', 'Validation threshold status: **'+report['validation_status']+'**.',
        'If authentic original validation scores are unavailable, no validation-optimal threshold is established. New scores or test-selected cutoffs are not substitutes.',
        '', '## Per-draw data', '',
        'See threshold_metrics_per_draw.private.csv and threshold_sweep.private.json. Each confusion SVG represents ONE model/draw/operating point with integer counts. No fractional mean is plotted as one confusion matrix.',
        '', '## Descriptive model/threshold means', '',
        'Each row below is a mean of per-draw metrics on the same people. Mean TP/TN/FP/FN may be fractional; they are descriptive expectations across fitted draws, not one realized matrix. Source-only has one original score vector, not ten duplicated draws.',
        'Means use defined values only. The summary CSV/JSON records n_defined/n_undefined, sample SD, minimum and maximum for every metric; undefined precision is never silently replaced by zero.',
        '', '| Model | Draws | Cutoff | '+' | '.join(METRICS)+' |', '|---|---:|---:|'+ '|'.join(['---:']*len(METRICS))+'|']
    per_rows=[];sum_rows=[];all_methods=list(report['models'])
    for name,item in report['models'].items():
        folder=cmroot/name;folder.mkdir(mode=0o700)
        for condition in item['fixed_test_thresholds']:
            threshold=condition['threshold'];summary=condition['summary']
            lines.append('| '+f'{name} | {item["draw_count"]} | {threshold:.2f} | '+' | '.join(number(summary[k]['mean']) for k in METRICS)+' |')
            for row in condition['per_draw']:
                per_rows.append({'model':name,'policy':'FIXED_TEST_GRID_DESCRIPTIVE','draw_id':row['draw_id'],**{k:row[k] for k in ('threshold',*METRICS)}})
                confusion(plt,row,f'{prefix}\n{name}; draw {row["draw_id"]}; cutoff {threshold:.2f}',
                    folder/f'draw_{row["draw_id"]}__fixed_{threshold:.2f}.svg')
            for metric,stats in summary.items():sum_rows.append({'model':name,'policy':'FIXED_TEST_GRID_DESCRIPTIVE',
                'threshold':threshold,'metric':metric,**stats})
        val=item['validation_selected']
        if val is not None:
            for row in val['per_draw']:
                per_rows.append({'model':name,'policy':'ORIGINAL_VALIDATION_F1_SELECTED_POST_HOC','draw_id':row['draw_id'],**{k:row[k] for k in ('threshold',*METRICS)}})
                confusion(plt,row,f'{prefix}\n{name}; draw {row["draw_id"]}; validation cutoff {row["threshold"]:.6g}',
                    folder/f'draw_{row["draw_id"]}__original_validation_selected.svg')
            for metric,stats in val['summary'].items():sum_rows.append({'model':name,'policy':'ORIGINAL_VALIDATION_F1_SELECTED_POST_HOC',
                'threshold':'varies_by_draw','metric':metric,**stats})
        xs=[c['threshold'] for c in item['fixed_test_thresholds']]
        fig,axes=plt.subplots(2,3,figsize=(11,6.8))
        for ax,metric in zip(axes.flat,('recall','specificity','precision','f1','balanced_accuracy','positive_predictions')):
            if metric=='positive_predictions':
                values=[[r['TP']+r['FP'] for r in c['per_draw']] for c in item['fixed_test_thresholds']]
                means=np.array([np.mean(v) for v in values]);sd=np.array([np.std(v,ddof=1) if len(v)>1 else np.nan for v in values])
                upper=report['distinct_test_participants'];label='Positive predictions (count)'
            else:
                means=np.array([np.nan if c['summary'][metric]['mean'] is None else c['summary'][metric]['mean'] for c in item['fixed_test_thresholds']])
                sd=np.array([np.nan if c['summary'][metric]['sd'] is None else c['summary'][metric]['sd'] for c in item['fixed_test_thresholds']])
                upper=1;label=metric.replace('_',' ').title()
            ax.plot(xs,means,marker='o',color='#215b84',linewidth=1.7)
            ax.fill_between(xs,np.maximum(0,means-sd),np.minimum(upper,means+sd),color='#215b84',alpha=.15)
            ax.set(xlabel='Fixed probability cutoff',ylabel=label,ylim=(-.02*upper,1.03*upper),xticks=[.05,.15,.25,.35,.5])
            ax.grid(alpha=.25)
        fig.suptitle(f'{prefix}\n{name}: {item["draw_count"]} fitted score vector(s)',fontsize=12)
        fig.text(.5,.005,'Means on SAME participants; shading = descriptive ±1 sample SD, NOT a confidence interval. N/A values remain gaps.',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.03,1,.93))
        for fmt in ('svg','png'):save(fig,chartroot/(name+'_threshold_response.'+fmt),fmt)
        plt.close(fig)
    # Comparison is descriptive at EVERY grid value; no test-derived winner.
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    for ax,metric in zip(axes.flat,('recall','specificity','precision','f1')):
        for name,item in report['models'].items():
            xs=[c['threshold'] for c in item['fixed_test_thresholds']]
            ys=[np.nan if c['summary'][metric]['mean'] is None else c['summary'][metric]['mean'] for c in item['fixed_test_thresholds']]
            ax.plot(xs,ys,marker='.',label=name.replace('_',' '))
        ax.set(xlabel='Fixed probability cutoff',ylabel=metric.title(),ylim=(-.03,1.03));ax.grid(alpha=.25)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=min(3,len(all_methods)),fontsize=8)
    fig.suptitle(prefix+'\nDescriptive threshold-response comparison; no cutoff selected',fontsize=12)
    fig.tight_layout(rect=(0,.11,1,.91))
    for fmt in ('svg','png'):save(fig,chartroot/('method_comparison.'+fmt),fmt)
    plt.close(fig)
    with text_file(out/'threshold_metrics_per_draw.private.csv') as f:
        writer=csv.DictWriter(f,fieldnames=['model','policy','draw_id','threshold',*METRICS]);writer.writeheader();writer.writerows(per_rows)
    with text_file(out/'threshold_metrics_summary.private.csv') as f:
        writer=csv.DictWriter(f,fieldnames=['model','policy','threshold','metric','n_defined','n_undefined','mean','sd','min','max']);writer.writeheader();writer.writerows(sum_rows)
    lines += ['', '## Unchanged ranking metrics','', '| Model | AP mean | AUROC mean | Brier mean |','|---|---:|---:|---:|']
    for name,item in report['models'].items():
        lines.append('| '+name+' | '+' | '.join(number(item['unchanged_ranking'][k]['mean']) for k in ('ap','auroc','brier'))+' |')
    lines += ['', '## Original-validation-selected operating points','',
        '| Model | Draw | Selected cutoff | '+' | '.join(METRICS)+' |','|---|---|---:|'+ '|'.join(['---:']*len(METRICS))+'|']
    for name,item in report['models'].items():
        if item['validation_selected'] is None:
            lines.append('| '+name+' | '+item['validation_status']+' | N/A | '+' | '.join(['N/A']*len(METRICS))+' |')
        else:
            for row in item['validation_selected']['per_draw']:
                lines.append('| '+name+' | '+str(row['draw_id'])+' | '+number(row['threshold'])+' | '+' | '.join(number(row[k]) for k in METRICS)+' |')
    lines += ['', '## Interpretation limits','',
        'These test thresholds are supplementary descriptive analyses of an already examined frozen test. They cannot establish an optimized or newly confirmed operating point. A threshold chosen retrospectively from this table would require genuinely new independent evaluation.',
        'Authentic original-validation F1 selection, when supported, uses only171 validation participants/13 positive reports, with highest-threshold tie breaking before test probabilities are opened. It remains post-hoc and unstable. The validation-set optimized F1 itself would be optimistic; it is not reported here as independent performance.',
        'Across-draw sample SD/ranges describe correlated fitted models, not independent-test uncertainty. Undefined precision is N/A, not zero or successful performance. The21 test positives limit sensitivity precision; one changed case changes recall by1/21. High all-negative accuracy is not useful event detection.',
        'AP is the ranked average precision statistic, not fixed-threshold precision or trapezoidal area under these ten displayed grid points. Threshold changes cannot alter AP/AUROC/Brier without changing scores. No calibration fitting or score transformation occurs.',
        'The registered historical findings and inconclusive comparison remain unchanged. This output does not establish clinical validity, superiority, external confirmation or permission for deployment. Do not update the B.Tech report or release cells without applicable disclosure review.']
    with text_file(out/'SUPERVISOR_THRESHOLD_COMPARISON.private.md') as f:f.write('\n'.join(lines)+'\n')
