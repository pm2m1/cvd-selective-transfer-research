"""Fixed invented-data mechanisms. No real-input flags or authorization operations."""
import copy
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import time
import numpy as np
import torch
from scipy.stats import hypergeom
from audit_core import (ROOT,FOLLOWUP,t,population,module_counts,state_hash,GradientRecorder,
                        epoch_zero_demonstration,public_snapshot,threshold_from_calibration)

PLAN = {
    'scope':'INVENTED_SYNTHETIC_ONLY_NOT_CLINICAL_EVIDENCE',
    'seeds':[101,202,303], 'source_train_n':1536, 'source_validation_n':384,
    'evaluation_n':1536,'source_epochs':30,'target_epochs':20,'patience':5,'lr':.001,
    'selector_permutations':19,'selector_bootstraps':39,
    'selector_precision':'reduced_for_mechanism_demo_not_registered_real_run',
}

SCENARIOS = [
    {'name':'aligned','prevalence':.2,'shift':0.,'reverse':False,'fit_n':128,'stop_n':64},
    {'name':'covariate_translation','prevalence':.2,'shift':1.,'reverse':False,'fit_n':128,'stop_n':64},
    {'name':'relationship_reversal','prevalence':.2,'shift':0.,'reverse':True,'fit_n':128,'stop_n':64},
    {'name':'scarce_positives','prevalence':.01,'shift':0.,'reverse':False,'fit_n':32,'stop_n':16},
    {'name':'pure_prior_shift','prevalence':.05,'shift':0.,'reverse':False,'fit_n':128,'stop_n':64},
    {'name':'aligned_tiny_fit','prevalence':.2,'shift':0.,'reverse':False,'fit_n':16,'stop_n':8},
]


def write(path, value):
    with path.open('x') as f: json.dump(value,f,indent=2,allow_nan=False)


def score(y,p):
    m=t.metrics(y,p)
    return {k:m[k] for k in ['ap','auroc','brier','precision','recall','specificity','f1','TP','TN','FP','FN']}


def drift(model, source):
    result={}
    for name, mod in {**model.selectable_modules(),'head':model.head}.items():
        original = source.head if name=='head' else source.selectable_modules()[name]
        before=torch.cat([p.detach().flatten() for p in original.parameters()])
        after=torch.cat([p.detach().flatten() for p in mod.parameters()])
        result[name]=float(torch.linalg.vector_norm(after-before)/max(float(torch.linalg.vector_norm(before)),1e-12))
    return result


def neural_scenarios():
    rows=[]; start=time.perf_counter()
    for seed in PLAN['seeds']:
        rng=np.random.default_rng(seed)
        sx,sy=population(rng,PLAN['source_train_n']);vx,vy=population(rng,PLAN['source_validation_n'])
        # Fit each numeric column only on invented source training; frozen thereafter.
        transforms={k:(x.mean(0),np.maximum(x.std(0),1e-6)) for k,x in sx.items()}
        normalize=lambda views:{k:((x-transforms[k][0])/transforms[k][1]).astype('float32') for k,x in views.items()}
        source_train=t.Encoded(normalize(sx),sy,'source_train')
        source_val=t.Encoded(normalize(vx),vy,'source_validation')
        sources={};traces={}
        for arch in ['original','compact']:
            t.seed(seed)
            model=t.CompactRiskNet() if arch=='compact' else t.MultiViewRiskNet(t.VIEWS)
            traces[arch]=t.fit(model,source_train,source_val,PLAN['source_epochs'],PLAN['lr'])
            sources[arch]=model
        for scenario_number, scenario in enumerate(SCENARIOS):
            rng=np.random.default_rng(seed+10000*(scenario_number+1))
            parts={}
            for role,n in [('target_adaptation',scenario['fit_n']),('target_validation',scenario['stop_n']),('prediction_only',PLAN['evaluation_n'])]:
                views,y=population(rng,n,scenario['prevalence'],scenario['shift'],scenario['reverse'])
                parts[role]=t.Encoded(normalize(views),y,role)
            fit,stop,evaluation=[parts[r] for r in ['target_adaptation','target_validation','prediction_only']]
            references={}
            for arch in ['original','compact']:
                references[arch]=score(evaluation.y.numpy(),t.prob(sources[arch],evaluation))
                rows.append({'seed':seed,'scenario':scenario['name'],'method':'source_only_'+arch,
                             'metrics':references[arch],'updated_parameters':0,'architecture':arch})
            for method in ['matched_control','head_only','logical','compact_full']:
                arch='compact' if method=='compact_full' else 'original'
                source=sources[arch]; fingerprint=state_hash(source)
                model=copy.deepcopy(source);t.seed(seed+scenario_number)
                mask={k:method in ['matched_control','compact_full'] for k in model.selectable_modules()}
                evidence={};reasons={}
                if method=='logical':
                    cfg=t.CalibrationConfig(permutations=PLAN['selector_permutations'],bootstraps=PLAN['selector_bootstraps'])
                    evidence=t.calibrate_modules(t.representations(source,source_val,t.SplitRole.SOURCE_VALIDATION),
                        t.representations(source,fit,t.SplitRole.TARGET_ADAPTATION),config=cfg,seed=seed)
                    mask,reasons=t.calibrated_mask(evidence,'calibrated_logical',cfg)
                t.set_selective_trainability(model,mask);frozen=t.snapshot_frozen(model,mask)
                before_source=score(vy,t.prob(source,source_val));began=time.perf_counter()
                initial_stop=float(torch.nn.functional.binary_cross_entropy_with_logits(model(stop.views),stop.y).detach())
                with GradientRecorder(model) as recorder:
                    training=t.fit(model,fit,stop,PLAN['target_epochs'],PLAN['lr'])
                assert recorder.optimizer_ids=={id(p) for p in model.parameters() if p.requires_grad}
                assert t.frozen_unchanged(model,frozen)[0] and state_hash(source)==fingerprint
                metrics=score(evaluation.y.numpy(),t.prob(model,evaluation))
                after_source=score(vy,t.prob(model,source_val))
                rows.append({'seed':seed,'scenario':scenario['name'],'method':method,'architecture':arch,
                    'fit_positive':int(fit.y.sum()),'stopping_positive':int(stop.y.sum()),
                    'metrics':metrics,'delta_vs_same_arch_source':{k:metrics[k]-references[arch][k] for k in ['ap','auroc','brier']},
                    'delta_source_validation_ap':after_source['ap']-before_source['ap'],
                    'mask':mask,'reasons':reasons,'module_counts':module_counts(model),
                    'updated_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad),
                    'total_parameters':sum(p.numel() for p in model.parameters()),
                    'relative_layer_drift':drift(model,source),
                    'mean_gradient_norm':{k:float(np.mean([r[k] for r in recorder.records])) for k in recorder.records[0]},
                    'initial_stop_bce':initial_stop,'training':training,'source_training':traces[arch],
                    'seconds':time.perf_counter()-began,'frozen_invariant':True,'cached_source_unchanged':True})
    return {'plan':PLAN,'scenarios':SCENARIOS,'rows':rows,'seconds':time.perf_counter()-start}


def threshold_stress():
    protocol=json.loads((FOLLOWUP/'protocol_v1.json').read_text())
    rng=np.random.default_rng(414); y=np.r_[np.ones(10),np.zeros(90)].astype(int)
    p=np.clip(.1+.1*y+rng.normal(0,.1,100),.001,.99)
    outer_y=np.r_[np.ones(100),np.zeros(900)].astype(int)
    outer_p=np.clip(.1+.1*outer_y+rng.normal(0,.1,1000),.001,.99)
    values=[];unsupported=0
    for _ in range(100):
        idx=rng.integers(0,100,100)
        result=threshold_from_calibration(y[idx],p[idx],protocol,t.select_validation_threshold)
        if result['threshold'] is None:unsupported+=1
        else:values.append({'threshold':result['threshold'],**score(outer_y,outer_p),
                            'outer_calibrated':t.metrics(outer_y,outer_p,result['threshold'])})
    return {'scope':'synthetic_threshold_bootstrap_not_clinical_precision',
            'resamples':100,'unsupported':unsupported,'supported':len(values),
            'threshold_min':min(v['threshold'] for v in values),'threshold_max':max(v['threshold'] for v in values),
            'threshold_median':float(np.median([v['threshold'] for v in values])),
            'outer_recall_range':[min(v['outer_calibrated']['recall'] for v in values),max(v['outer_calibrated']['recall'] for v in values)],
            'outer_f1_range':[min(v['outer_calibrated']['f1'] for v in values),max(v['outer_calibrated']['f1'] for v in values)],
            'fixed_0_50':t.metrics(outer_y,outer_p,.5)}


def design_arithmetic():
    from audit_core import outer_splits,budget_roles
    split=next(outer_splits(np.array([f'INVENTED_{i:04}' for i in range(679)]),3,[20261105]))
    records=[]
    for fraction in [.1,.25,.5,.75,1.]:
        role=budget_roles(split,fraction);nstop=len(role['stop']);nc=len(role['calibration'])
        # Marginal probabilities for random subsets of the historical public pool counts.
        # Not realized private fold counts, and not independent probabilities across roles.
        support=sum(hypergeom.pmf(k,679,49,nc) for k in range(5,nc-4))
        records.append({'fraction':fraction,'budget':role['budget_n'],'fit':len(role['fit']),
            'stop':nstop,'calibration':nc,'expected_stopping_positives':nstop*49/679,
            'probability_zero_stopping_positives':float(hypergeom.pmf(0,679,49,nstop)),
            'probability_calibration_5_each':float(support)})
    return {'meaning':'design arithmetic using supplied public historical counts, NOT observed private results',
            'outer_training_n':len(split['ordered_training']),'rows':records}


def main():
    # Fixed new output only; refuses overwrites and offers no private-input option.
    out=ROOT/'synthetic_results';out.mkdir(mode=0o700)
    before=public_snapshot();write(out/'PUBLIC_SOURCE_SNAPSHOT_BEFORE.json',before)
    write(out/'SYNTHETIC_PLAN.json',{'plan':PLAN,'scenarios':SCENARIOS})
    write(out/'DESIGN_ARITHMETIC.json',design_arithmetic())
    write(out/'EPOCH_ZERO_COUNTEREXAMPLE.json',epoch_zero_demonstration())
    y=np.array([1,0,1,0]);source=np.array([.6,.4,.6,.4]);adapted=np.array([.9,.8,.2,.1])
    write(out/'POOLED_OOF_COUNTEREXAMPLE.json',{'source_pooled':score(y,source),'adapted_pooled':score(y,adapted),
        'source_folds':[score(y[i:i+2],source[i:i+2]) for i in [0,2]],
        'adapted_folds':[score(y[i:i+2],adapted[i:i+2]) for i in [0,2]],
        'interpretation':'both folds perfect rankings; pooled adapted ranking lower solely from score offsets'})
    write(out/'THRESHOLD_STRESS.json',threshold_stress())
    write(out/'NEURAL_MECHANISMS.json',neural_scenarios())
    after=public_snapshot();assert before==after
    write(out/'PUBLIC_SOURCE_SNAPSHOT_AFTER.json',after)
    write(out/'ENVIRONMENT.json',{'python':platform.python_version(),**{k:importlib.metadata.version(k) for k in ['numpy','torch','scikit-learn','scipy']}})
    print('SYNTHETIC_DIAGNOSTICS_COMPLETE PUBLIC_SOURCE_UNCHANGED')


if __name__=='__main__':main()
