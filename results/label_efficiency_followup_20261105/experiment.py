"""Retrospective development-only label curves with disjoint stopping/calibration."""
import copy
import time
from pathlib import Path
import numpy as np
import torch
from local_execution import need, write_json
from package_runtime import api
from design import outer_splits, budget_roles, threshold_from_calibration


def sliced(t,data,indices,role):
    return t.Encoded({v:data['target_pool__'+v][indices] for v in t.VIEWS},
                     data['target_pool__y'][indices],role)


class TrainingAdapter:
    def __init__(self,data,protocol,synthetic=False,checkpoint_dir=None):
        self.t=api(); self.data=data; self.p=protocol; self.synthetic=synthetic; self.cache={};self.source_costs={}
        self.checkpoint_dir=checkpoint_dir
        torch.set_num_threads(1)

    def source(self,architecture):
        t=self.t
        if architecture not in self.cache:
            t.seed(self.p['source_seed']); start=time.perf_counter()
            model=t.CompactRiskNet() if architecture=='compact' else t.MultiViewRiskNet(t.VIEWS)
            trace=t.fit(model,t.ds(self.data,'source_train'),t.ds(self.data,'source_validation'),
                2 if self.synthetic else self.p['source_epochs'],self.p['source_lr'],patience=self.p['patience'])
            self.cache[architecture]=model
            self.source_costs[architecture]={'seconds':time.perf_counter()-start,'training':trace,
                'seed':self.p['source_seed'],'parameters':sum(p.numel() for p in model.parameters())}
            if self.checkpoint_dir is not None:
                with (self.checkpoint_dir/f'source_{architecture}.pt').open('xb') as stream:torch.save(model.state_dict(),stream)
        return self.cache[architecture]

    def predict(self,method,roles,outer,seed):
        t=self.t
        selected=set(roles['selected'].tolist()); held=set(outer.tolist())
        role_union=set(roles['fit'])|set(roles['stop'])|set(roles['calibration'])
        need(role_union==selected and sum(len(roles[k]) for k in ['fit','stop','calibration'])==len(selected)
             and selected<=set(range(len(self.data['target_pool__y'])))
             and not selected & held and not set(roles['fit']) & set(roles['stop'])
             and not set(roles['calibration']) & (set(roles['fit'])|set(roles['stop'])), 'ADAPTER_ROLE_LEAKAGE')
        need(method in self.p['methods'], 'METHOD_NOT_REGISTERED')
        architecture='compact' if method=='compact_full' else 'original'
        source=self.source(architecture);t.seed(seed);model=copy.deepcopy(source);start=time.perf_counter()
        fit=sliced(t,self.data,roles['fit'],'target_adaptation')
        stop=sliced(t,self.data,roles['stop'],'target_validation')  # Frozen-helper tag; inner stopping ONLY.
        mask={name:method in ('matched_control','compact_full') for name in model.selectable_modules()}
        selection={}
        if method=='logical':
            cfg=t.CalibrationConfig(permutations=9 if self.synthetic else self.p['selector_permutations'],
                                    bootstraps=19 if self.synthetic else self.p['selector_bootstraps'])
            ev=t.calibrate_modules(t.representations(source,t.ds(self.data,'source_validation'),t.SplitRole.SOURCE_VALIDATION),
                t.representations(source,fit,t.SplitRole.TARGET_ADAPTATION),config=cfg,max_samples=128,seed=seed)
            mask,reasons=t.calibrated_mask(ev,'calibrated_logical',cfg);selection={'evidence':ev,'reasons':reasons}
        t.set_selective_trainability(model,mask);frozen=t.snapshot_frozen(model,mask)
        trace=t.fit(model,fit,stop,2 if self.synthetic else self.p['target_epochs'],self.p['target_lr'],
                    loss=self.p['loss'],patience=self.p['patience'])
        need(t.frozen_unchanged(model,frozen)[0],'FROZEN_MODULE_CHANGED')
        fit_seconds=time.perf_counter()-start;prediction_start=time.perf_counter()
        # Dummy labels make it impossible for prediction code to consume outer/calibration outcomes.
        def predict_indices(ix):
            ds=t.Encoded({v:self.data['target_pool__'+v][ix] for v in t.VIEWS},np.zeros(len(ix)), 'prediction_only')
            return t.prob(model,ds) if len(ix) else np.array([],dtype=float)
        calibration=predict_indices(roles['calibration']); predictions=predict_indices(outer)
        prediction_seconds=time.perf_counter()-prediction_start
        checkpoint=None
        if self.checkpoint_dir is not None:
            checkpoint=f'{method}_seed{seed}_n{roles["budget_n"]}.pt'
            with (self.checkpoint_dir/checkpoint).open('xb') as stream:torch.save(model.state_dict(),stream)
        return {'outer_probabilities':predictions,'calibration_probabilities':calibration,'checkpoint':checkpoint,
                'training':trace,'mask':mask,'selector':selection,'fit_selector_seconds':fit_seconds,
                'prediction_seconds':prediction_seconds,
                'trainable_parameters':sum(p.numel() for p in model.parameters() if p.requires_grad),
                'total_parameters':sum(p.numel() for p in model.parameters())}

    def zero_reference(self,outer):
        t=self.t;model=self.source('original')
        part=t.Encoded({v:self.data['target_pool__'+v][outer] for v in t.VIEWS},np.zeros(len(outer)),'prediction_only')
        start=time.perf_counter();p=t.prob(model,part)
        return p,time.perf_counter()-start


def scored(t,y,p,threshold):
    m=t.metrics(y,p,threshold)
    return {**m,'positive_predictions':m['TP']+m['FP'],'negative_predictions':m['TN']+m['FN']}


def run(data,history,protocol,folds,out,synthetic=False,adapter=None):
    t=api()
    if adapter is None:
        (out/'checkpoints').mkdir(mode=0o700)
        adapter=TrainingAdapter(data,protocol,synthetic,out/'checkpoints')
    ids=data['target_pool__ids'];y=data['target_pool__y'];rows=[];prediction_records=[];split_records=[]
    for split in outer_splits(ids,folds,protocol['repeat_seeds']):
        held=split['outer']; seed=split['repeat_seed'];fold=split['fold']
        split_records.append({'repeat_seed':seed,'fold':fold,'outer_ids':ids[held].tolist(),
                              'training_order_ids':ids[split['ordered_training']].tolist()})
        if protocol['include_source_only']:
            p,seconds=adapter.zero_reference(held)
            # Outcome access begins after prediction; it cannot affect the zero-label reference.
            m=scored(t,y[held],p,.5)
            rows.append({'method':'source_only_zero','fraction':0.,'budget_n':0,'repeat_seed':seed,'fold':fold,
                'status':'EVALUATED','fixed_0_50':m,'training_side_threshold':None,
                'prediction_seconds':seconds,'target_labels_fit_stop_calibration':0,
                'outer_evaluation_labels':len(held),'trainable_parameters':0,'total_parameters':8033})
            prediction_records.extend({'method':'source_only_zero','fraction':0.,'repeat_seed':seed,
                'index':int(i),'y':int(y[i]),'p':float(v)} for i,v in zip(held,p))
        for fraction in protocol['budget_fractions']:
            roles=budget_roles(split,fraction,protocol['allocation_cycle'])
            account={'fit_n':len(roles['fit']),'stop_n':len(roles['stop']),'calibration_n':len(roles['calibration']),
                'target_labels_fit_stop_calibration':roles['budget_n'],'outer_evaluation_labels':len(held),
                'total_labels_in_this_split_including_evaluation':roles['budget_n']+len(held),
                'outer_training_denominator':len(split['ordered_training']),
                'no_additional_target_hyperparameter_selection':True}
            need(account['fit_n']+account['stop_n']+account['calibration_n']==roles['budget_n'],'LABEL_ACCOUNTING_MISMATCH')
            for method in protocol['methods']:
                row={'method':method,'fraction':fraction,'budget_n':roles['budget_n'],
                     'repeat_seed':seed,'fold':fold,**account}
                if len(roles['fit'])<2 or not len(roles['stop']):
                    rows.append({**row,'status':'INSUFFICIENT_TRAINING_SIDE_LABELS','fixed_0_50':None,'training_side_threshold':None})
                    continue  # Registered condition retained; never enlarge/redraw its labels.
                fit_seed=seed+1000*fold+roles['budget_n']
                result=adapter.predict(method,roles,held,fit_seed)
                calibration=threshold_from_calibration(y[roles['calibration']],result['calibration_probabilities'],protocol,t.select_validation_threshold)
                # Freeze threshold before accessing outer outcomes for scoring.
                threshold=calibration['threshold'];p=result.pop('outer_probabilities');result.pop('calibration_probabilities')
                fixed=scored(t,y[held],p,.5)
                calibrated=scored(t,y[held],p,threshold) if threshold is not None else None
                rows.append({**row,**result,'status':'EVALUATED','seed':fit_seed,'fixed_0_50':fixed,
                    'training_side_threshold':calibrated,'calibration_evidence':calibration,
                    'fit_positive':int(y[roles['fit']].sum()),'stop_positive':int(y[roles['stop']].sum()),
                    'calibration_positive':int(y[roles['calibration']].sum()),
                    'threshold_selected_without_outer_labels':True})
                prediction_records.extend({'method':method,'fraction':fraction,'repeat_seed':seed,
                    'index':int(i),'y':int(y[i]),'p':float(v)} for i,v in zip(held,p))
    from results_report import summarize_results,plot_curves,private_markdown
    report={'schema':'label-efficiency-results-v1','scope':'SYNTHETIC_ONLY' if synthetic else 'RETROSPECTIVE_DEVELOPMENT_NOT_EXTERNAL_VALIDATION',
        'protocol':protocol,'outer_folds':folds,'rows':rows,'history':history,'source_training':adapter.source_costs,
        'unique_target_evaluation_labels':len(ids),'previous_validation_labels_used':False,
        'label_accounting_global':{'incremental_training_budget_includes':['fit','stop','calibration'],
            'all_current_outer_evaluation_labels_counted':len(ids),
            'unique_previous_target_development_labels_available':history.get('previous_target_development_labels_available'),
            'historical_and_current_labels_overlap_do_not_sum_costs':True,
            'selection_after_learning_curves_uses_the_entire_outer_evaluation_population':True,
            'prospective_label_acquisition_saving_demonstrated':False},
        'architecture_previously_selected_on_development':True,'independent_test_status':'INDEPENDENT_TEST_NOT_AVAILABLE'}
    report.update(summarize_results(rows,prediction_records,protocol,len(ids),synthetic))
    write_json(out/'followup_results.private.json',report)
    write_json(out/'fold_memberships.private.json',split_records)
    write_json(out/'outer_predictions.private.json',{'ids':ids.tolist(),'records':prediction_records})
    private_markdown(report,out/'label_budget_comparison.private.md')
    plot_curves(report,out)
    return report
