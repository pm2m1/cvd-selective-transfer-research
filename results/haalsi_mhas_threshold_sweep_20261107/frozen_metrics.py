"""Supplementary statistics from retained frozen scores only. Never performs inference."""
from pathlib import Path
import math,json,sys
import numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score
from local_execution import need,sha,descriptor,load_json,write_json,cli,exclusive_output
REGISTRATION_SHA='43351eb56cd331d6729f0a1766d6ae0dce0deb41114b380a52c9ed100c090e40'
MANIFEST_SHA='b59d4d3a7bf931356ca745695a95e1612f66bdc8f6f170247c1800ac4f6ab960'
REFERENCE_SHA='e4cc0274f10af8498f63faa324b639cd7aba1a4c4d6a870a41ec88ff14730027'
PURPOSE='retained_frozen_score_supplement_only_no_inference_v1'

def validate_vectors(y,p):
    y,p=np.asarray(y),np.asarray(p)
    need(y.ndim==1 and p.ndim==1 and len(y)>0 and y.shape==p.shape,'VECTOR_SHAPE_INVALID')
    need(np.isin(y,[0,1]).all() and p.dtype.kind in 'fiu' and np.isfinite(p).all() and ((p>=0)&(p<=1)).all(),'LABEL_OR_PROBABILITY_INVALID')
    return y.astype(int),p.astype(float)
def metrics(y,p,threshold=.5):
    y,p=validate_vectors(y,p);need(isinstance(threshold,(int,float,np.floating)) and math.isfinite(threshold) and 0<=threshold<=1,'THRESHOLD_INVALID')
    pred=p>=threshold;tp=int(np.sum(pred&(y==1)));tn=int(np.sum(~pred&(y==0)));fp=int(np.sum(pred&(y==0)));fn=int(np.sum(~pred&(y==1)))
    div=lambda a,b:float(a/b) if b else None
    rec,spec=div(tp,tp+fn),div(tn,tn+fp);den=(tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
    return {'threshold':float(threshold),'TP':tp,'TN':tn,'FP':fp,'FN':fn,'accuracy':div(tp+tn,len(y)),'precision':div(tp,tp+fp),'recall':rec,'sensitivity':rec,'specificity':spec,'f1':div(2*tp,2*tp+fp+fn),'FPR':div(fp,fp+tn),'FNR':div(fn,fn+tp),'NPV':div(tn,tn+fn),'balanced_accuracy':(rec+spec)/2 if rec is not None and spec is not None else None,'MCC':div(tp*tn-fp*fn,math.sqrt(den)),'ap':float(average_precision_score(y,p)) if y.sum() else None,'auroc':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None,'brier':float(np.mean((p-y)**2))}
def select_validation_threshold(y,p):
    y,p=validate_vectors(y,p);need(len(np.unique(y))==2,'VALIDATION_REQUIRES_BOTH_CLASSES')
    choices=np.unique(np.r_[0.,.5,1.,p]);return float(max(choices,key=lambda t:(metrics(y,p,float(t))['f1'] or 0.,float(t))))
def summarize(rows):
    out={}
    for key in rows[0]:
        vals=np.asarray([r[key] for r in rows if r[key] is not None],dtype=float)
        out[key]={'n_defined':len(vals),'n_undefined':len(rows)-len(vals),'mean':float(vals.mean()) if len(vals) else None,'sd':float(vals.std(ddof=1)) if len(vals)>1 else None,'min':float(vals.min()) if len(vals) else None,'max':float(vals.max()) if len(vals) else None}
    return out

def validate_membership(ids,y,n=283,events=21):
    need(isinstance(ids,list) and len(ids)==n and all(isinstance(i,str) and i for i in ids) and len(set(ids))==n,'PARTICIPANT_MEMBERSHIP_INVALID')
    need(np.asarray(y).shape==(n,) and np.isin(y,[0,1]).all() and int(np.sum(y))==events,'LABEL_COUNTS_INVALID')

def load_inputs(c,synthetic=False):
    need(c['schema']=='supplementary-classification-v1' and c['probability_ensemble'] is False and c['ddof']==1 and c['fixed_threshold']==.5,'ANALYSIS_CONTRACT_MISMATCH')
    need(c['absolute_tolerance']==1e-8 and c['relative_tolerance']==1e-8,'TOLERANCE_CHANGE_REJECTED')
    rp=descriptor(c['registration']);mp=descriptor(c['completed_manifest']);refp=descriptor(c['public_references'])
    if not synthetic:need(sha(rp)==REGISTRATION_SHA and sha(mp)==MANIFEST_SHA and sha(refp)==REFERENCE_SHA,'FROZEN_EVIDENCE_BINDING_MISMATCH')
    reg,manifest,refs=load_json(rp),load_json(mp),load_json(refp)
    need(manifest['status']=='RECOVERY_COMPLETE_AFTER_FAILED_ORIGINAL_ATTEMPT' and manifest['registration_sha256']==sha(rp) and manifest['no_fitting_performed'] is True and manifest['test_participants']==283 and manifest['test_positive_reports']==21,'COMPLETED_RUN_BINDING_MISMATCH')
    need(isinstance(c['predictions']['path'],str) and isinstance(c['ids']['path'],str),'INPUT_PATH_MISSING')
    bp=Path(c['predictions']['path']).expanduser().resolve();ip=Path(c['ids']['path']).expanduser().resolve()
    need(bp.is_file() and ip.is_file(),'RETAINED_PREDICTIONS_OR_IDS_UNAVAILABLE')
    need(sha(bp)==manifest['private_prediction_bundle_sha256'] and sha(ip)==manifest['private_ids_sha256'],'RETAINED_PAYLOAD_BINDING_MISMATCH')
    ids=load_json(ip)[c['ids']['ordered_ids_key']];need(len(ids)==283 and len(set(ids))==283,'PARTICIPANT_MEMBERSHIP_INVALID')
    models=c['models'];need(bool(models) and len({m['model_id'] for m in models})==len(models),'MODEL_INVENTORY_INVALID')
    validation=None
    if c.get('validation_threshold') is not None:
        v=c['validation_threshold'];need(v['rule']=='validation_f1_highest_threshold_tie','UNRECOGNIZED_THRESHOLD_RULE')
        vp=descriptor(v['payload']);vm=load_json(descriptor(v['provenance']))
        need(vm['role']=='target_validation' and vm['origin']=='retained_original_development_predictions' and vm['payload_sha256']==sha(vp) and vm['registration_sha256']==sha(rp),'VALIDATION_PROVENANCE_INVALID')
        with np.load(vp,allow_pickle=False) as z:validation={k:z[k].copy() for k in z.files}
        vids=validation[v['ids_key']].tolist();vy=validation[v['labels_key']];validate_membership(vids,vy,171,13)
        need(not set(ids)&set(vids),'VALIDATION_TEST_MEMBERSHIP_OVERLAP')
    selected={};thresholds={}
    # Thresholds are fixed exclusively from validation before any test probability is opened.
    for m in models:
        name,budget=m['model_id'],m['budget'];draws=m['draw_ids'];source=budget=='source'
        need(draws==(['source'] if source else list(range(10))),'DRAW_INVENTORY_INVALID')
        entries=[e for e in reg['models'] if e['method']==name and e['budget']==budget]
        checkpoints={'source' if e['repetition'] is None else str(e['repetition']):e['checkpoint_sha256'] for e in entries}
        need(len(entries)==len(draws) and checkpoints==m['checkpoint_sha256_by_draw'],'CHECKPOINT_OR_DRAW_BINDING_MISMATCH')
        need(m['array_key']=='primary_25_75__'+name and name in refs['models'],'FROZEN_ARRAY_MAPPING_INVALID')
        thresholds[name]=None
        if validation is not None:
            need(vm['checkpoints'].get(name)==checkpoints,'VALIDATION_CHECKPOINT_MISMATCH')
            matrix=validation[v['model_keys'][name]];need(matrix.shape==(len(draws),171),'VALIDATION_SHAPE_INVALID')
            thresholds[name]=[select_validation_threshold(vy,p) for p in matrix]
    with np.load(bp,allow_pickle=False) as z:
        need(c['predictions']['labels_key'] in z.files and all(m['array_key'] in z.files for m in models),'RETAINED_MODEL_ARRAY_NOT_AVAILABLE')
        y=z[c['predictions']['labels_key']].copy()
        for m in models:
            name=m['model_id'];matrix=z[m['array_key']].copy();need(matrix.shape==(len(m['draw_ids']),283),'PROBABILITY_MATRIX_SHAPE_INVALID')
            for row in matrix:validate_vectors(y,row)
            selected[name]=matrix
    validate_membership(ids,y)
    need(sha(bp)==manifest['private_prediction_bundle_sha256'] and sha(ip)==manifest['private_ids_sha256'] and sha(rp)==c['registration']['sha256'] and sha(mp)==c['completed_manifest']['sha256'] and sha(refp)==c['public_references']['sha256'],'INPUT_CHANGED_DURING_READ')
    return y,selected,thresholds,refs

def analyze(y,models,thresholds,refs,synthetic=False):
    # Reproduce historical mean-of-per-draw metrics; never average probability vectors.
    report={'analysis':'SYNTHETIC_ONLY' if synthetic else 'POST_HOC_SUPPLEMENT_RETAINED_FROZEN_SCORES','distinct_test_participants':len(y),'shared_population_across_draws':True,'sd_ddof':1,'ensemble':False,'models':{}}
    for name,matrix in models.items():
        fixed=[metrics(y,p,.5) for p in matrix]
        for k in ['ap','auroc','brier']:
            want=refs['models'][name][k]
            got=[r[k] for r in fixed]
            need(np.isclose(np.mean(got),want['mean'],atol=1e-8,rtol=1e-8) and np.allclose(got,want['per_draw'],atol=1e-8,rtol=1e-8),'FROZEN_METRIC_RECONCILIATION_FAILED')
        item={'draw_count':len(fixed),'fixed_0_50':{'threshold_origin':'POST_HOC_FIXED_0_50_NOT_PREREGISTERED','per_draw':fixed,'summary':summarize(fixed)}}
        if thresholds.get(name) is not None:
            rows=[metrics(y,p,t) for p,t in zip(matrix,thresholds[name])]
            item['validation_f1']={'threshold_origin':'POST_HOC_VALIDATION_ONLY_OPTIMIZATION_NOT_INDEPENDENT','rule':'max validation F1; ties highest threshold','per_draw':rows,'summary':summarize(rows)}
        report['models'][name]=item
    return report

def execute(c,out):
    y,models,ts,refs=load_inputs(c);report=analyze(y,models,ts,refs)
    write_json(out/'classification_metrics.private.json',report)
    from render_metrics_report import render
    render(report,out)
    write_json(out/'provenance.private.json',{'config':c,'script_sha256':sha(__file__),'numpy_version':np.__version__,'no_inference_performed':True,'no_new_fitting_performed':True,'disclosure_cleared':False})
def demo(output):
    # Invented 283-person fixture; explicitly distinct from real MHAS observations.
    rng=np.random.default_rng(20261104);y=np.r_[np.ones(21),np.zeros(262)].astype(int);p=rng.uniform(0,1,(10,283));rows=[metrics(y,x) for x in p]
    refs={'models':{'synthetic_logical':{k:{'mean':float(np.mean([r[k] for r in rows])),'per_draw':[r[k] for r in rows]} for k in ['ap','auroc','brier']}}}
    report=analyze(y,{'synthetic_logical':p},{},refs,True)
    with exclusive_output(output,False) as out:
        write_json(out/'synthetic_classification_metrics.json',report)
        from render_metrics_report import render
        render(report,out)
if __name__=='__main__':sys.exit(cli(PURPOSE,execute,demo))
