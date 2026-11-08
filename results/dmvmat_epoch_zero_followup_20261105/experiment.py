"""Three arms, one isolated checkpoint-eligibility change. No data at import."""
import copy
import time
import numpy as np
import torch
from local_execution import need,write_json
from retained_runtime import api
from design import outer_splits,budget_roles,threshold_from_calibration
from checkpoints import state_hash,paired_fit


def source_fit(data,p):
    t=api();t.seed(p['source_seed']);torch.set_num_threads(1)
    model=t.MultiViewRiskNet(t.VIEWS)
    trace=t.fit(model,t.ds(data,'source_train'),t.ds(data,'source_validation'),
                p['source_epochs'],p['source_lr'],patience=p['patience'])
    return model,trace


def inference(model,data,indices):
    t=api()
    dummy=t.Encoded({v:data['target_pool__'+v][indices] for v in t.VIEWS},
                    np.zeros(len(indices)),'prediction_only')
    return t.prob(model,dummy) if len(indices) else np.array([],float)


def validate_roles(data,roles,outer):
    sets=[set(roles[k].tolist()) for k in ['fit','stop','calibration']]
    selected=set(roles['selected'].tolist());held=set(outer.tolist())
    need(set.union(*sets)==selected and sum(map(len,sets))==len(selected)==roles['budget_n']
         and selected<=set(range(len(data['target_pool__y']))) and not selected&held,
         'PAIRED_ROLE_OR_BUDGET_LEAKAGE')


def predict_condition(source,data,roles,outer,seed,p):
    """No outer or calibration outcomes are passed to checkpoint selection."""
    t=api();validate_roles(data,roles,outer)
    part=lambda ix,role:t.Encoded({v:data['target_pool__'+v][ix] for v in t.VIEWS},data['target_pool__y'][ix],role)
    fit=part(roles['fit'],'target_adaptation');stop=part(roles['stop'],'target_validation')
    models,traces,verification=paired_fit(source,fit,stop,seed,p)
    outer_probs={a:inference(models[a],data,outer) for a in ['A','B']}
    cal_probs={a:inference(models[a],data,roles['calibration']) for a in ['A','B']}
    c=inference(source,data,outer)
    if traces['B']['selected_epoch']==0:
        need(np.array_equal(outer_probs['B'],c),'SOURCE_VS_EPOCH_ZERO_PREDICTION_MISMATCH')
    return models,traces,verification,outer_probs,cal_probs,c


def condition_plan(p):
    return {f'{seed}_{fold}_{fraction}':'NOT_RUN' for seed in p['repeat_seeds']
            for fold in range(p['primary_outer_folds']) for fraction in p['budget_fractions']}


def run(data,history,p,out,scope,progress=None):
    t=api();started=time.perf_counter();cells=[];memberships=[];source_start=time.perf_counter()
    if progress is None:progress=condition_plan(p)
    write_json(out/'registered_conditions.private.json',progress)
    source,source_trace=source_fit(data,p);source_time=time.perf_counter()-source_start
    source_sha=state_hash(source)
    (out/'checkpoints').mkdir(mode=0o700)
    with (out/'checkpoints/source.pt').open('xb') as f:torch.save(source.state_dict(),f)
    for split in outer_splits(data['target_pool__ids'],p['primary_outer_folds'],p['repeat_seeds']):
        held=split['outer'];seed=split['repeat_seed'];fold=split['fold']
        # Source-only scores generated once per fold, without any target outcome use.
        c=inference(source,data,held)
        for fraction in p['budget_fractions']:
            condition=f'{seed}_{fold}_{fraction}'
            roles=budget_roles(split,fraction,p['allocation_cycle']);validate_roles(data,roles,held)
            cell={'repeat_seed':seed,'fold':fold,'fraction':fraction,'budget_n':roles['budget_n'],
                'population_n':len(data['target_pool__y']),'outer_indices':held.tolist(),
                'label_accounting':{**{k:len(roles[k]) for k in ['fit','stop','calibration']},
                    'conditioning_total':roles['budget_n'],'outer_evaluation':len(held),
                    'C_target_conditioning_labels':0,'same_roles_A_B':True}}
            memberships.append({'repeat_seed':seed,'fold':fold,'fraction':fraction,
                **{k:data['target_pool__ids'][roles[k]].tolist() for k in ['selected','fit','stop','calibration']},
                'outer':data['target_pool__ids'][held].tolist()})
            if len(roles['fit'])<2 or not len(roles['stop']):
                progress[condition]='INSUFFICIENT_TRAINING_SIDE_LABELS'
                cells.append({**cell,'status':'INSUFFICIENT_TRAINING_SIDE_LABELS'});continue
            began=time.perf_counter();target_seed=seed+1000*fold+roles['budget_n']
            try:
                models,traces,verification,probs,cal_probs,again_c=predict_condition(source,data,roles,held,target_seed,p)
                need(np.array_equal(c,again_c),'SOURCE_REFERENCE_CHANGED')
                # Select all thresholds before outer outcomes are accessed.
                thresholds={a:threshold_from_calibration(data['target_pool__y'][roles['calibration']],
                            cal_probs[a],p,t.select_validation_threshold) for a in ['A','B']}
                thresholds['C']={'status':'ZERO_TARGET_LABEL_REFERENCE_NOT_CALIBRATED','threshold':None}
                probs['C']=c
                labels=data['target_pool__y'][held]
                metrics={a:{'fixed_0_50':t.metrics(labels,probs[a],.5),
                            'calibrated':t.metrics(labels,probs[a],thresholds[a]['threshold'])
                            if thresholds[a]['threshold'] is not None else None} for a in ['A','B','C']}
                for a in ['A','B']:
                    with (out/'checkpoints'/f'{seed}_{fold}_{roles["budget_n"]}_{a}.pt').open('xb') as f:torch.save(models[a].state_dict(),f)
                cell.update(status='EVALUATED',seed=target_seed,training=traces,paired_verification=verification,
                    calibration=thresholds,metrics=metrics,probabilities={a:v.tolist() for a,v in probs.items()},
                    y=labels.astype(int).tolist(),source_state_sha256=source_sha,
                    target_trainable_parameters={'A':8033,'B':8033,'C':0},
                    class_support={k:{'n':len(roles[k]),'positive':int(data['target_pool__y'][roles[k]].sum())} for k in ['fit','stop','calibration']},
                    B_epoch_zero_matches_source_scores=True if traces['B']['selected_epoch']==0 else None,
                    seconds=time.perf_counter()-began)
                write_json(out/f'cell_{seed}_{fold}_{roles["budget_n"]}.private.json',cell)
                cells.append(cell)
                progress[condition]='EVALUATED'
            except BaseException:
                progress[condition]='FAILED_NO_RETRY'
                write_json(out/f'cell_{seed}_{fold}_{roles["budget_n"]}_failure.private.json',
                           {**cell,'status':'FAILED_NO_RETRY','remaining_conditions':'NOT_RUN_DUE_TO_CONSUMED_FAILURE'})
                # Never continue/retry after a processing/integrity failure.
                raise
    need(state_hash(source)==source_sha,'SOURCE_CACHE_CHANGED')
    write_json(out/'memberships.private.json',memberships)
    from paired_report import summarize,private_markdown
    report={'schema':'epoch-zero-private-results-v1','scope':scope,'protocol':p,'history':history,
        'source_training':source_trace,'source_training_seconds':source_time,'source_state_sha256':source_sha,
        'cells':cells,'comparison':summarize(cells,p),'total_seconds':time.perf_counter()-started,
        'prior_validation_outcomes_used':False,'frozen_test_access':False,
        'independent_test_status':'INDEPENDENT_TEST_NOT_AVAILABLE',
        'architecture_and_design_previously_development_exposed':True,
        'source_only_epoch_zero_raw_inference_equivalence':'IDENTICAL_FOR_THIS_ARCHITECTURE_WHEN_B_SELECTS_ZERO',
        'scientific_superiority_automatically_assigned':False}
    write_json(out/'epoch_zero_comparison.private.json',report)
    private_markdown(report,out/'epoch_zero_comparison.private.md')
    # Result fingerprints remain private, along with checkpoints/predictions.
    from local_execution import sha
    write_json(out/'result_integrity.private.json',{'result_sha256':sha(out/'epoch_zero_comparison.private.json'),
        'report_sha256':sha(out/'epoch_zero_comparison.private.md'),'source_state_sha256':source_sha,
        'scope':scope,'all_registered_conditions_accounted_for':len(cells)==45})
    write_json(out/'condition_dispositions.private.json',progress)
    return report
