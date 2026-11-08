"""Invented records only. No private loaders, assignments, receipts or predictions."""
import copy
import itertools
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_core import *

PROTOCOL=json.loads((FOLLOWUP/'protocol_v1.json').read_text())


class SelectorReferenceTests(unittest.TestCase):
    def test_reference_1000_random_and_boundary_cases(self):
        rng=np.random.default_rng(17)
        pairs=[(float(r),float(u)) for r,u in rng.uniform(-2,2,(1000,2))]
        pairs += list(itertools.product([.799999,.8,.800001],[.749999,.75,.750001,.999999,1.,1.000001]))
        for r,u in pairs:
            for p in [.049999,.05,.050001]:
                e={'geometry_status':'valid','signed_retention':r,'retention_upper':u,
                   'domain_status':'valid','domain_p':p}
                self.assertEqual(t.calibrated_mask({'a':e},'calibrated_logical')[0]['a'],logical_reference(e))

    def test_abstention_does_not_fallback_full(self):
        for status in ['insufficient_class_samples','weak_source_geometry','uncertain_source_geometry']:
            e={'geometry_status':status}
            self.assertFalse(t.calibrated_mask({'a':e},'calibrated_logical')[0]['a'])

    def test_nonfinite_valid_geometry_rejected(self):
        for value in [None,np.nan,np.inf]:
            with self.assertRaises(ValueError):
                t.calibrated_mask({'a':{'geometry_status':'valid','signed_retention':value,'retention_upper':.3}},'calibrated_logical')

    def test_strong_geometry_independent_of_domain_significance(self):
        e={'geometry_status':'valid','signed_retention':-.3,'retention_upper':.6,'domain_status':'degenerate_null','domain_p':1.}
        self.assertTrue(t.calibrated_mask({'a':e},'calibrated_logical')[0]['a'])

    def test_geometry_matches_independent_numpy_reference(self):
        rng=np.random.default_rng(19); y=np.tile([0,1],60)
        s=rng.normal(size=(120,3))+y[:,None]*[4,0,0]
        for shift in [1.,-.8,.3]:
            x=rng.normal(size=(120,3))+y[:,None]*[4*shift,0,0]
            observed=relative_geometry(s,y,x,y,config=t.CalibrationConfig(permutations=9,bootstraps=39),seed=9)
            self.assertAlmostEqual(observed['signed_retention'],geometry_reference(s,y,x,y),places=12)
            self.assertEqual(observed['geometry_status'],'valid')

    def test_mmd_matches_independent_partition_reference(self):
        rng=np.random.default_rng(2);s=rng.normal(size=(11,3));x=rng.normal(.5,size=(9,3))
        got=permutation_mmd(s,x,permutations=19,seed=12)
        expected,p=mmd_reference(s,x)
        self.assertAlmostEqual(got['permutation_mmd'],expected,places=12)
        self.assertEqual(got['domain_p'],p)

    def test_same_seed_selector_reproducible(self):
        rng=np.random.default_rng(20);y=np.tile([0,1],25)
        s=rng.normal(size=(50,3))+y[:,None]*[3,0,0]
        x=rng.normal(size=(50,3))+y[:,None]*[-3,0,0]
        src=t.ModuleRepresentations({'a':s},y,t.SplitRole.SOURCE_VALIDATION)
        tgt=t.ModuleRepresentations({'a':x},y,t.SplitRole.TARGET_ADAPTATION)
        cfg=t.CalibrationConfig(permutations=19,bootstraps=39)
        a=t.calibrate_modules(src,tgt,config=cfg,seed=3)
        b=t.calibrate_modules(src,tgt,config=cfg,seed=3)
        self.assertEqual(a,b);self.assertEqual(t.calibrated_mask(a,'calibrated_logical'),t.calibrated_mask(b,'calibrated_logical'))

    def test_outer_role_rejected_by_selector(self):
        x=np.arange(40).reshape(20,2);y=np.tile([0,1],10)
        src=t.ModuleRepresentations({'a':x},y,t.SplitRole.SOURCE_VALIDATION)
        # Use enum's forbidden target-test role, not a nonexistent string alias.
        forbidden=[r for r in t.SplitRole if r not in [t.SplitRole.SOURCE_TRAIN,t.SplitRole.SOURCE_VALIDATION,t.SplitRole.TARGET_ADAPTATION]][0]
        with self.assertRaises(Exception):
            t.calibrate_modules(src,t.ModuleRepresentations({'a':x},y,forbidden),config=t.CalibrationConfig(permutations=9,bootstraps=19))


class ParameterTests(unittest.TestCase):
    def test_exact_architecture_counts(self):
        model=t.MultiViewRiskNet(t.VIEWS)
        self.assertEqual(module_counts(model),{'view:background':112,'view:haemodynamic':80,
            'view:metabolic':96,'view:behaviour':112,'view:comorbidity_medication':144,'fusion1':5312,'fusion2':2144})
        self.assertEqual(sum(p.numel() for p in model.parameters()),8033)
        self.assertEqual(sum(p.numel() for p in t.CompactRiskNet().parameters()),2225)

    def test_all_128_masks_counts_optimizer_and_bitwise_frozen(self):
        t.seed(30);base=t.MultiViewRiskNet(t.VIEWS);counts=module_counts(base)
        rng=np.random.default_rng(30);views,y=population(rng,24)
        ds=t.Encoded(views,y,'target_adaptation')
        for bits in itertools.product([False,True],repeat=7):
            mask=dict(zip(base.selectable_modules(),bits));model=copy.deepcopy(base)
            self.assertFalse({id(p) for p in model.parameters()} & {id(p) for p in base.parameters()})
            t.set_selective_trainability(model,mask);frozen=t.snapshot_frozen(model,mask)
            expected=33+sum(counts[k] for k,enabled in mask.items() if enabled)
            self.assertEqual(sum(p.numel() for p in model.parameters() if p.requires_grad),expected)
            with GradientRecorder(model) as recorder:
                optimizer=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=.001,weight_decay=1e-4)
                optimizer.zero_grad();value=t.loss_value(model(ds.views),ds.y,'bce');value.backward();optimizer.step()
            self.assertEqual(recorder.optimizer_ids,{id(p) for p in model.parameters() if p.requires_grad})
            self.assertTrue(t.frozen_unchanged(model,frozen)[0])
            self.assertTrue(all(recorder.records[0][k]==0 for k,enabled in mask.items() if not enabled))

    def test_unknown_mask_and_nonbool_rejected(self):
        for mask in [{'unknown':True},{'fusion1':1}]:
            with self.assertRaises(ValueError):t.set_selective_trainability(t.MultiViewRiskNet(t.VIEWS),mask)

    def test_incomplete_mask_defaults_share_head_always_trainable(self):
        model=t.MultiViewRiskNet(t.VIEWS);t.set_selective_trainability(model,{})
        self.assertEqual(sum(p.numel() for p in model.parameters() if p.requires_grad),33)


class SplitIsolationTests(unittest.TestCase):
    def setUp(self):
        self.data=invented_adapter_data()
        self.protocol=copy.deepcopy(PROTOCOL)
        self.split=next(outer_splits(self.data['target_pool__ids'],3,[65]))
        self.roles=budget_roles(self.split,.75)

    def test_nested_disjoint_role_counts(self):
        previous=set()
        for fraction in PROTOCOL['budget_fractions']:
            roles=budget_roles(self.split,fraction)
            self.assertLessEqual(previous,set(roles['selected']));previous=set(roles['selected'])
            self.assertEqual(sum(len(roles[k]) for k in ['fit','stop','calibration']),roles['budget_n'])
            self.assertFalse(previous & set(self.split['outer']))

    def test_outcome_blind_splits(self):
        # Split API receives IDs only, no labels.
        a=list(outer_splits(self.data['target_pool__ids'],3,[65]))
        self.data['target_pool__y']=1-self.data['target_pool__y']
        b=list(outer_splits(self.data['target_pool__ids'],3,[65]))
        for x,y in zip(a,b):np.testing.assert_array_equal(x['outer'],y['outer'])

    def test_outer_and_calibration_label_flips_cannot_change_predictions(self):
        adapter=TrainingAdapter(self.data,self.protocol,synthetic=True)
        source=adapter.source('original');before=state_hash(source)
        result=adapter.predict('logical',self.roles,self.split['outer'],73)
        changed=copy.deepcopy(self.data)
        ix=np.r_[self.split['outer'],self.roles['calibration']]
        changed['target_pool__y'][ix]=1-changed['target_pool__y'][ix]
        second=TrainingAdapter(changed,self.protocol,synthetic=True)
        result2=second.predict('logical',self.roles,self.split['outer'],73)
        np.testing.assert_array_equal(result['outer_probabilities'],result2['outer_probabilities'])
        self.assertEqual(result['mask'],result2['mask']);self.assertEqual(result['training'],result2['training'])
        self.assertEqual(state_hash(source),before)

    def test_fold_cache_and_model_state_independent(self):
        adapter=TrainingAdapter(self.data,self.protocol,synthetic=True)
        before=state_hash(adapter.source('original'))
        first=adapter.predict('head_only',self.roles,self.split['outer'],73)
        adapter.predict('matched_control',self.roles,self.split['outer'],21)
        again=adapter.predict('head_only',self.roles,self.split['outer'],73)
        np.testing.assert_array_equal(first['outer_probabilities'],again['outer_probabilities'])
        self.assertEqual(before,state_hash(adapter.source('original')))
        self.assertEqual(first['trainable_parameters'],33)

    def test_outer_overlap_rejected(self):
        bad=copy.deepcopy(self.roles);bad['fit'][0]=self.split['outer'][0]
        with self.assertRaises(Exception):TrainingAdapter(self.data,self.protocol,True).predict('logical',bad,self.split['outer'],1)


class SmallSampleTests(unittest.TestCase):
    def test_zero_one_positive_stopping_bce_remains_defined(self):
        rng=np.random.default_rng(52);x,y=population(rng,40);train=t.Encoded(x,y,'target_adaptation')
        for npositive in [0,1]:
            stop=t.Encoded({k:v[:9] for k,v in x.items()},np.r_[np.ones(npositive),np.zeros(9-npositive)],'target_validation')
            t.seed(4);model=t.MultiViewRiskNet(t.VIEWS)
            trace=t.fit(model,train,stop,2,.001)
            self.assertTrue(np.isfinite(trace['restored_unweighted_validation_BCE']))
            if not npositive:
                self.assertIsNone(trace['curve'][0]['validation_ap'])
                self.assertIsNone(trace['curve'][0]['validation_auroc'])
            else:
                self.assertTrue(np.isfinite(trace['curve'][0]['validation_ap']))
                self.assertTrue(np.isfinite(trace['curve'][0]['validation_auroc']))

    def test_calibration_support_0_1_4_5_6(self):
        for positive in [0,1,4,5,6]:
            y=np.r_[np.ones(positive),np.zeros(10)].astype(int);p=np.linspace(.01,.4,len(y))
            r=threshold_from_calibration(y,p,PROTOCOL,t.select_validation_threshold)
            self.assertEqual(r['threshold'] is not None,positive>=5)

    def test_10_percent_calibration_support_mathematically_impossible(self):
        split=next(outer_splits(np.array([f'INVENTED_{i}' for i in range(679)]),3,[1]))
        roles=budget_roles(split,.1)
        self.assertEqual(len(roles['calibration']),9)
        for positives in range(10):
            y=np.r_[np.ones(positives),np.zeros(9-positives)]
            self.assertIsNone(threshold_from_calibration(y,np.full(9,.1),PROTOCOL,t.select_validation_threshold)['threshold'])

    def test_all_negative_predictions_explicit_undefined_precision(self):
        m=t.metrics(np.r_[1,1,np.zeros(18)],np.full(20,.1))
        self.assertIsNone(m['precision']);self.assertEqual(m['recall'],0);self.assertEqual(m['f1'],0)

    def test_single_class_metrics(self):
        a=t.metrics(np.zeros(10),np.full(10,.1));b=t.metrics(np.ones(10),np.full(10,.9))
        self.assertIsNone(a['ap']);self.assertIsNone(a['auroc']);self.assertIsNone(b['auroc']);self.assertIsNone(b['specificity'])

    def test_constant_probability_and_highest_threshold_tie(self):
        y=np.r_[np.ones(5),np.zeros(15)]
        self.assertEqual(t.select_validation_threshold(y,np.full(20,.2)),.2)
        self.assertAlmostEqual(t.metrics(y,np.full(20,.2))['ap'],.25)

    def test_near_ties_and_skewed_probabilities(self):
        y=np.array([1,1,0,0,0,1,0,0,0,0])
        for p in [np.array([.1,.1+1e-12,.1,.1-1e-12,.1,.1,.1,.1,.1,.1]),np.r_[.999999,.000001,np.full(8,.00001)]]:
            threshold=t.select_validation_threshold(y,p)
            self.assertTrue(0<=threshold<=1)
            self.assertEqual(t.metrics(y,p,.5)['ap'],t.metrics(y,p,threshold)['ap'])

    def test_forced_epoch_counterexample(self):
        result=epoch_zero_demonstration()
        self.assertGreater(result['selected_bce'],result['initial_bce'])
        self.assertGreater(result['selected_epoch'],0)
        self.assertEqual(result['proposed_epoch_zero_gate_would_choose'],0)

    def test_pooled_oof_counterexample(self):
        y=np.array([1,0,1,0]);s=np.array([.6,.4,.6,.4]);p=np.array([.9,.8,.2,.1])
        self.assertEqual(t.metrics(y,s)['ap'],1.)
        self.assertAlmostEqual(t.metrics(y,p)['ap'],5/6)
        for i in [0,2]:self.assertEqual(t.metrics(y[i:i+2],p[i:i+2])['auroc'],1.)

    def test_supported_threshold_comparison_uses_identical_subset(self):
        from results_report import summarize_results
        protocol=copy.deepcopy(PROTOCOL);protocol['repeat_seeds']=[1];protocol['bootstrap_repetitions']=9
        labels=np.array([1,0,1,0,1,0]);probs=np.array([.3,.1,.4,.2,.4,.1])
        rows=[];records=[]
        for fold,ix in enumerate([np.arange(2),np.arange(2,4),np.arange(4,6)]):
            fixed=t.metrics(labels[ix],probs[ix],.5)
            selected=t.metrics(labels[ix],probs[ix],.25) if fold==1 else None
            rows.append({'method':'matched_control','fraction':.1,'repeat_seed':1,'fold':fold,
                         'budget_n':4,'status':'EVALUATED','fixed_0_50':fixed,'training_side_threshold':selected})
            records.extend({'method':'matched_control','fraction':.1,'repeat_seed':1,
                            'index':int(i),'y':int(labels[i]),'p':float(probs[i])} for i in ix)
        report=summarize_results(rows,records,protocol,6,True)
        entry=report['learning_curve_summaries'][0]
        coverage=entry['calibrated_threshold_coverage'][0]
        self.assertEqual(coverage['outer_n_with_supported_threshold'],2)
        self.assertEqual(sum(coverage['fixed_0_50_on_same_supported_subset'][k] for k in ['TP','TN','FP','FN']),2)
        self.assertEqual(entry['calibration_supported_folds'],1)

    def test_no_all_positive_or_single_class_fabrication(self):
        y=np.zeros(10,dtype=int);p=np.full(10,.1)
        with self.assertRaises(Exception):t.select_validation_threshold(y,p)
        r=threshold_from_calibration(y,p,PROTOCOL,t.select_validation_threshold)
        self.assertEqual(r['status'],'INSUFFICIENT_CALIBRATION_CLASS_SUPPORT')

    def test_lower_threshold_changes_decisions_not_ranking_or_brier(self):
        y=np.array([0,1,0,1]);p=np.array([.01,.03,.02,.04])
        a,b=t.metrics(y,p,.5),t.metrics(y,p,.025)
        for k in ['ap','auroc','brier']:self.assertEqual(a[k],b[k])
        self.assertEqual(a['recall'],0);self.assertEqual(b['recall'],1)

    def test_probability_normalization_no_target_refit_in_adapter(self):
        data=invented_adapter_data();before={k:v.copy() for k,v in data.items()}
        split=next(outer_splits(data['target_pool__ids'],3,[7]));roles=budget_roles(split,.5)
        TrainingAdapter(data,PROTOCOL,True).predict('head_only',roles,split['outer'],55)
        for k in data:np.testing.assert_array_equal(data[k],before[k])


if __name__=='__main__':unittest.main()
