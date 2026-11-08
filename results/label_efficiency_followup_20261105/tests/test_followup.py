"""All populations, scores and protected-style records below are invented."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_execution import Rejected,sha,write_json,exclusive_output,require_local
import package_runtime as runtime
from design import outer_splits,budget_roles,threshold_from_calibration
from learning_curves import invented_data
from experiment import TrainingAdapter,run
from results_report import participant_bootstrap
from prospective import verify_new_membership,COVERAGE,register,evaluate

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'protocol_v1.json').read_text())
T=runtime.api()


def desc(p):return {'path':str(p),'sha256':sha(p)}
def dump(p,value):p.write_text(json.dumps(value)+'\n');return desc(p)


class DesignTests(unittest.TestCase):
    def setUp(self):self.ids=np.array([f'SYNTHETIC_ID_{i:03d}' for i in range(90)])
    def test_same_seed_reproducible(self):
        a=list(outer_splits(self.ids,3,P['repeat_seeds']));b=list(outer_splits(self.ids,3,P['repeat_seeds']))
        self.assertTrue(all(np.array_equal(x['outer'],y['outer']) and np.array_equal(x['ordered_training'],y['ordered_training']) for x,y in zip(a,b)))
    def test_every_person_outer_once_per_repeat(self):
        for seed in P['repeat_seeds']:
            all_outer=np.concatenate([s['outer'] for s in outer_splits(self.ids,3,[seed])])
            self.assertEqual(sorted(all_outer.tolist()),list(range(90)))
    def test_five_fold_profile(self):self.assertEqual(len(list(outer_splits(self.ids,5,P['repeat_seeds']))),15)
    def test_nested_budget_and_roles_and_accounting(self):
        for split in outer_splits(self.ids,3,[20261105]):
            previous={key:set() for key in ['selected','fit','stop','calibration']}
            for fraction in P['budget_fractions']:
                r=budget_roles(split,fraction)
                self.assertEqual(sum(len(r[k]) for k in ['fit','stop','calibration']),r['budget_n'])
                self.assertFalse(set(r['selected']) & set(split['outer']))
                for key in previous:
                    self.assertTrue(previous[key] <= set(r[key]));previous[key]=set(r[key])
    def test_allocation_has_no_label_argument_or_outcome_stratification(self):
        import inspect
        self.assertNotIn('labels',inspect.signature(outer_splits).parameters)
        self.assertNotIn('labels',inspect.signature(budget_roles).parameters)
    def test_row_reordering_keeps_same_id_memberships(self):
        a=list(outer_splits(self.ids,3,[13])); rev=self.ids[::-1].copy();b=list(outer_splits(rev,3,[13]))
        self.assertEqual([self.ids[s['outer']].tolist() for s in a],[rev[s['outer']].tolist() for s in b])
    def test_duplicate_ids_rejected(self):
        with self.assertRaises(Rejected):list(outer_splits(np.array(['SYNTHETIC_DUP']*9),3,[1]))
    def test_unregistered_budget_rejected(self):
        with self.assertRaises(Rejected):budget_roles(next(outer_splits(self.ids,3,[1])),.99)


class ThresholdTests(unittest.TestCase):
    def test_training_side_threshold_only(self):
        y=np.r_[np.ones(5),np.zeros(5)];p=np.r_[np.linspace(.3,.7,5),np.linspace(.01,.2,5)]
        result=threshold_from_calibration(y,p,P,T.select_validation_threshold)
        self.assertAlmostEqual(result['threshold'],.3)
        a=T.metrics([1,0],[.4,.2],.5);b=T.metrics([1,0],[.4,.2],result['threshold'])
        self.assertEqual(a['recall'],0);self.assertEqual(b['recall'],1)
        self.assertEqual(a['ap'],b['ap']);self.assertEqual(a['auroc'],b['auroc'])
    def test_insufficient_calibration_never_falls_back(self):
        r=threshold_from_calibration([1,0,0],[.4,.2,.1],P,T.select_validation_threshold)
        self.assertIsNone(r['threshold']);self.assertEqual(r['status'],'INSUFFICIENT_CALIBRATION_CLASS_SUPPORT')
    def test_no_positive_predictions_reported_honestly(self):
        m=T.metrics([1,0,0],[.1,.2,.1],.5)
        self.assertEqual(m['recall'],0);self.assertIsNone(m['precision']);self.assertEqual(m['f1'],0)
    def test_no_positive_no_negative_metrics(self):
        self.assertIsNone(T.metrics([0,0],[.1,.2])['auroc']);self.assertIsNone(T.metrics([0,0],[.1,.2])['ap'])
        self.assertIsNone(T.metrics([1,1],[.1,.2])['specificity'])
    def test_outer_labels_cannot_change_model_or_threshold(self):
        data=invented_data();p=copy.deepcopy(P);p['repeat_seeds']=p['repeat_seeds'][:1]
        split=next(outer_splits(data['target_pool__ids'],3,p['repeat_seeds']));roles=budget_roles(split,.75)
        changed={k:v.copy() for k,v in data.items()};changed['target_pool__y'][split['outer']]=1-changed['target_pool__y'][split['outer']]
        a=TrainingAdapter(data,p,True).predict('head_only',roles,split['outer'],123)
        b=TrainingAdapter(changed,p,True).predict('head_only',roles,split['outer'],123)
        np.testing.assert_array_equal(a['outer_probabilities'],b['outer_probabilities'])
        np.testing.assert_array_equal(a['calibration_probabilities'],b['calibration_probabilities'])
        ca=threshold_from_calibration(data['target_pool__y'][roles['calibration']],a['calibration_probabilities'],p,T.select_validation_threshold)
        cb=threshold_from_calibration(changed['target_pool__y'][roles['calibration']],b['calibration_probabilities'],p,T.select_validation_threshold)
        self.assertEqual(ca,cb)
    def test_adapter_rejects_outer_membership_in_training(self):
        data=invented_data();split=next(outer_splits(data['target_pool__ids'],3,[1]));roles=budget_roles(split,.5)
        roles['selected']=np.r_[roles['selected'],split['outer'][0]]
        with self.assertRaises(Rejected):TrainingAdapter(data,P,True).predict('logical',roles,split['outer'],1)
    def test_adapter_rejects_role_index_not_in_declared_budget(self):
        data=invented_data();split=next(outer_splits(data['target_pool__ids'],3,[1]));roles=budget_roles(split,.5)
        roles['fit'][0]=split['outer'][0]
        with self.assertRaises(Rejected):TrainingAdapter(data,P,True).predict('head_only',roles,split['outer'],1)
    def test_calibration_labels_do_not_change_fitting_or_stopping(self):
        data=invented_data();split=next(outer_splits(data['target_pool__ids'],3,[31]));roles=budget_roles(split,.75)
        changed={k:v.copy() for k,v in data.items()};changed['target_pool__y'][roles['calibration']]=1-changed['target_pool__y'][roles['calibration']]
        a=TrainingAdapter(data,P,True).predict('matched_control',roles,split['outer'],87)
        b=TrainingAdapter(changed,P,True).predict('matched_control',roles,split['outer'],87)
        np.testing.assert_array_equal(a['outer_probabilities'],b['outer_probabilities'])
        self.assertEqual(a['training'],b['training'])


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='synthetic_followup_export_');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.payload={}
        for role,(n,e) in T.COUNTS.items():
            self.payload[role+'__ids']=np.array([f'SYNTHETIC_EXPORTED_{role}_{i}' for i in range(n)])
            self.payload[role+'__y']=np.r_[np.ones(e),np.zeros(n-e)].astype(int)
            for v,dim in T.VIEWS.items():self.payload[role+'__'+v]=np.zeros((n,dim),dtype='float32')
        for i in range(10):self.payload[f'draw_{i}']=np.r_[np.arange(25),np.arange(49,124)].astype('int64')
        self.bundle=self.root/'invented_bundle.npz';np.savez_compressed(self.bundle,**self.payload)
        self.pp=self.root/'invented_pp.json';dump(self.pp,{'fit_role':'source_train','schema_version':'cvd-public-wave-v2-ten-doctor-report'})
        mapping={f'src/dmv_mat_cvd/invented_{i}.py':str(i).zfill(64) for i in range(63)}
        mh=hashlib.sha256(json.dumps(mapping,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        pp=patch.object(runtime,'ORIGINAL_PUBLIC_MAP_SHA',mh);pp.start();self.addCleanup(pp.stop)
        self.manifest={'public_source_bindings':mapping,'source_assignments_sha256':runtime.ORIGINAL_ASSIGNMENTS_SHA,
            'preparation_script_sha256':runtime.ORIGINAL_EXPORTER_SHA,'bundle_sha256':sha(self.bundle),
            'preprocessor_sha256':sha(self.pp),'preprocessing_fit_role':'source_train','protocol':'public-haalsi-mhas-v2','test_rows_included':False}
        self.mp=self.root/'invented_manifest.json';dump(self.mp,self.manifest)
        self.receipt={'fixture_only':'NOT_A_REAL_AUTHORIZATION_OR_EXECUTION', 'status':'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED',
            'attempt_consumed':True,'stage':'NONE','issue':'NONE','real_test_evaluation':False,
            'export_manifest_sha256':sha(self.mp),'bindings':{'public_manifest_sha256':runtime.ORIGINAL_PUBLIC_MANIFEST,'helper_ledger_sha256':runtime.ORIGINAL_WORKFLOW_LEDGER}}
        self.rp=self.root/'invented_receipt.json';dump(self.rp,self.receipt)
        self.config={'inputs':{'development_bundle':desc(self.bundle),'development_manifest':desc(self.mp),
            'source_preprocessing':desc(self.pp),'completed_workflow_receipt':desc(self.rp)}}
    def refresh(self):
        self.manifest['bundle_sha256']=sha(self.bundle);dump(self.mp,self.manifest)
        self.receipt['export_manifest_sha256']=sha(self.mp);dump(self.rp,self.receipt)
        self.config['inputs'].update(development_bundle=desc(self.bundle),development_manifest=desc(self.mp),completed_workflow_receipt=desc(self.rp))
    def test_retained_bundle_accepted_without_raw_files(self):
        data,history=runtime.load_retained_export(self.config)
        self.assertEqual(len(data),21);self.assertEqual(history['previous_adaptation_fit_union_n'],100)
        self.assertFalse(history['prior_validation_outcomes_decoded']);self.assertFalse(history['original_assignments_reopened'])
    def test_old_validation_outcomes_features_not_read(self):
        original=np.load
        class Guard:
            def __init__(self,path,**kw):self.z=original(path,**kw);self.files=self.z.files
            def __enter__(self):return self
            def __exit__(self,*a):self.z.close()
            def __getitem__(self,key):
                if key.startswith('target_validation__') and key!='target_validation__ids':raise AssertionError('must not decode old validation')
                return self.z[key]
        with patch.object(np,'load',side_effect=lambda path,**kw:Guard(path,**kw)):
            runtime.load_retained_export(self.config)
    def test_original_locked_test_field_rejected_before_reading(self):
        self.payload['target_test__y']=np.array([1]);np.savez_compressed(self.bundle,**self.payload);self.refresh()
        with self.assertRaises(Rejected):runtime.load_retained_export(self.config)
    def test_hash_change_rejected(self):
        self.bundle.write_bytes(b'SYNTHETIC_TAMPER')
        with self.assertRaises(Rejected):runtime.load_retained_export(self.config)
    def test_receipt_binding_rejected(self):
        self.receipt['export_manifest_sha256']='0'*64;dump(self.rp,self.receipt)
        self.config['inputs']['completed_workflow_receipt']=desc(self.rp)
        with self.assertRaises(Rejected):runtime.load_retained_export(self.config)
    def test_duplicate_npz_header_entry_rejected(self):
        original=np.load
        class DuplicateHeader:
            def __init__(self,path,**kwargs):self.z=original(path,**kwargs);self.files=self.z.files+[self.z.files[0]]
            def __enter__(self):return self
            def __exit__(self,*args):self.z.close()
            def __getitem__(self,key):raise AssertionError('must reject before decoding')
        with patch.object(np,'load',side_effect=lambda path,**kw:DuplicateHeader(path,**kw)):
            with self.assertRaises(Rejected):runtime.load_retained_export(self.config)


class SafetyAndReportTests(unittest.TestCase):
    def test_original_agent_guard_rejects(self):
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'SYNTHETIC_TEST_MARKER'}):
            with self.assertRaises(Rejected):require_local()
    def test_consumed_output_cannot_resume(self):
        with tempfile.TemporaryDirectory(prefix='synthetic_consumed_') as tmp:
            out=Path(tmp)/'one'
            with self.assertRaises(KeyboardInterrupt):
                with exclusive_output(out,False):raise KeyboardInterrupt()
            before=(out/'completion.private.json').read_bytes()
            with self.assertRaises(Rejected):
                with exclusive_output(out,False):pass
            self.assertEqual(before,(out/'completion.private.json').read_bytes())
    def test_private_json_permissions(self):
        with tempfile.TemporaryDirectory(prefix='synthetic_private_report_') as tmp:
            p=Path(tmp)/'invented.json';write_json(p,{'scope':'SYNTHETIC_ONLY'})
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
    def test_participant_cluster_bootstrap_reproducible_and_paired(self):
        y=np.array([1,0,0,1,0]);p=np.array([[.8,.1,.2,.6,.2],[.7,.1,.3,.6,.2]])
        a=participant_bootstrap(y,p,p,20,77);b=participant_bootstrap(y,p,p,20,77)
        self.assertEqual(a,b);self.assertEqual(a['paired_ap_minus_matched_interval']['lower'],0)
        self.assertFalse(a['includes_training_or_architecture_selection_uncertainty'])
    def test_bootstrap_does_not_redraw_single_class_samples(self):
        result=participant_bootstrap(np.array([0,0]),np.array([[.1,.2]]),None,10,1)
        self.assertEqual(result['ap_interval']['undefined_replicates'],10)
    def test_public_installation_excludes_synthetic_outputs_and_refuses_overwrite(self):
        from install_public_followup import install
        with tempfile.TemporaryDirectory(prefix='synthetic_followup_install_') as tmp:
            target=Path(tmp)/'new_tools';install(target)
            self.assertFalse((target/'synthetic_only').exists())
            self.assertEqual((target/'learning_curves.py').read_bytes(),(ROOT/'learning_curves.py').read_bytes())
            self.assertEqual(target.stat().st_mode&0o777,0o700)
            with self.assertRaises(ValueError):install(target)
    def test_public_installer_cli_destination_flag(self):
        from install_public_followup import main
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory(prefix='synthetic_followup_cli_') as tmp:
            out=io.StringIO()
            with redirect_stdout(out):rc=main(['--destination',str(Path(tmp)/'new_public_tools')])
            self.assertEqual(rc,0);self.assertEqual(out.getvalue(),'PASS: PUBLIC_FOLLOWUP_INSTALLED_NO_AUTHORIZATION\n')
    def test_threshold_comparison_uses_identical_supported_outer_subset(self):
        from results_report import summarize_results
        y=np.array([1,0,0,1,0,0]);p=np.array([.4,.1,.1,.1,.9,.8]);rows=[];records=[]
        for fold,ix in enumerate([np.arange(3),np.arange(3,6)]):
            rows.append({'method':'head_only','fraction':1.,'budget_n':4,'repeat_seed':1,'fold':fold,'status':'EVALUATED',
                'fixed_0_50':T.metrics(y[ix],p[ix],.5),
                'training_side_threshold':T.metrics(y[ix],p[ix],.2) if fold==0 else None})
            records.extend({'method':'head_only','fraction':1.,'repeat_seed':1,'index':int(i),'y':int(y[i]),'p':float(p[i])} for i in ix)
        prot={**P,'repeat_seeds':[1]};r=summarize_results(rows,records,prot,6,True)
        coverage=r['learning_curve_summaries'][0]['calibrated_threshold_coverage'][0]
        self.assertEqual(coverage['outer_n_with_supported_threshold'],3)
        fixed=coverage['fixed_0_50_on_same_supported_subset']
        self.assertEqual(sum(fixed[k] for k in ['TP','TN','FP','FN']),3)
        self.assertEqual(fixed['recall'],0);self.assertEqual(coverage['recall'],1)
    def test_every_registered_condition_runs_without_favorable_stopping(self):
        class SpyAdapter:
            source_costs={}
            def __init__(self):self.calls=[]
            def zero_reference(self,outer):return np.full(len(outer),.1),0.
            def predict(self,method,roles,outer,seed):
                self.calls.append((method,roles['fraction'],seed))
                return {'outer_probabilities':np.full(len(outer),.2),
                    'calibration_probabilities':np.full(len(roles['calibration']),.2),
                    'trainable_parameters':33,'total_parameters':8033,'fit_selector_seconds':0.,'prediction_seconds':0.}
        adapter=SpyAdapter()
        with tempfile.TemporaryDirectory(prefix='synthetic_all_conditions_') as tmp:
            r=run(invented_data(),{'synthetic_only':True},P,3,Path(tmp),True,adapter)
        self.assertEqual(len(adapter.calls),180);self.assertEqual(len(r['rows']),189)
        self.assertEqual(r['scope'],'SYNTHETIC_ONLY');self.assertEqual(r['independent_test_status'],'INDEPENDENT_TEST_NOT_AVAILABLE')


class ProspectiveTests(unittest.TestCase):
    def records(self):
        token=lambda name:hashlib.sha256(('SYNTHETIC_SALT:'+name).encode()).hexdigest()
        registry={'schema':'prior-person-token-registry-v1','complete_for_all_prior_study_access':True,
            'tokenization_context_sha256':token('SYNTHETIC_TOKENIZATION_CONTEXT'),
            'identity_resolution':'cross_dataset_person_linkage_verified_by_independent_operator',
            'token_standard':'sha256_resolved_person_id_with_private_study_salt',
            'partition_tokens':{name:[token('SYNTHETIC_PRIOR_'+name)] for name in COVERAGE}}
        member={'schema':'new-cohort-membership-v1','ids':['SYNTHETIC_NEW_1','SYNTHETIC_NEW_2'],
            'tokenization_context_sha256':registry['tokenization_context_sha256'],
            'person_tokens':[token('SYNTHETIC_NEW_1'),token('SYNTHETIC_NEW_2')]}
        return member,registry
    def test_genuinely_disjoint_token_membership(self):
        m,r=self.records();verify_new_membership(m,r)
    def test_old_locked_test_overlap_rejected(self):
        m,r=self.records();r['partition_tokens']['MHAS_ORIGINAL_LOCKED_TEST']=[m['person_tokens'][0]]
        with self.assertRaises(Rejected):verify_new_membership(m,r)
    def test_missing_prior_partition_rejected(self):
        m,r=self.records();del r['partition_tokens']['MHAS_ORIGINAL_LOCKED_TEST']
        with self.assertRaises(Rejected):verify_new_membership(m,r)
    def test_namespace_alone_is_not_identity_proof(self):
        m,r=self.records();r['identity_resolution']='namespace_prefix_only'
        with self.assertRaises(Rejected):verify_new_membership(m,r)
    def test_different_tokenization_salt_context_rejected(self):
        m,r=self.records();m['tokenization_context_sha256']='0'*64
        with self.assertRaises(Rejected):verify_new_membership(m,r)
    def test_no_cohort_availability_does_not_become_external_validation(self):
        with tempfile.TemporaryDirectory(prefix='synthetic_unavailable_') as tmp:
            p=Path(tmp)/'invented.json';d=dump(p,{'schema':'genuine-independent-test-proposal-v1','availability_attested_by_independent_operator':False})
            with self.assertRaises(Rejected):register({'proposal':d},Path(tmp))
    def test_synthetic_registration_then_one_shot_prediction_before_outcomes(self):
        import torch
        import prospective
        with tempfile.TemporaryDirectory(prefix='synthetic_prospective_') as tmp:
            root=Path(tmp);member,registry=self.records()
            mdesc=dump(root/'invented_membership.json',member);rdesc=dump(root/'invented_prior_tokens.json',registry)
            T.seed(70);model=T.CompactRiskNet();cp=root/'invented_weights.pt';torch.save(model.state_dict(),cp)
            pp=dump(root/'invented_pp.json',{'fit_role':'source_train','schema_version':'cvd-public-wave-v2-ten-doctor-report'})
            hp=dump(root/'invented_hp.json',{'model_finalized_before_external_outcomes':True,'fixture_only':True})
            cal=dump(root/'invented_cal.json',{'checkpoint_sha256':sha(cp),'threshold':.3,
                'selection_data_role':'training_side_only','evaluation_outcomes_used':False,'all_target_label_cost_recorded':True})
            feature=root/'invented_features.npz';np.savez(feature,ids=np.array(member['ids']),
                **{v:np.zeros((2,d),dtype='float32') for v,d in T.VIEWS.items()})
            fm=dump(root/'invented_feature_provenance.json',{'preprocessing_sha256':pp['sha256'],'input_features_only':True,
                'no_future_information':True,'timing_and_outcome_definition_reviewed_by_operator':True,'previous_model_development_use':False})
            proposal={'schema':'genuine-independent-test-proposal-v1','fixture_only':'INVENTED_NOT_AN_APPROVAL',
                'availability_attested_by_independent_operator':True,'previously_used_in_any_model_decision':False,
                'outcomes_not_inspected_for_registration':True,'cohort_origin':'new_unaccessed_eligible_participants',
                'cohort_id':'SYNTHETIC_NEW_COHORT','predictor_schema':'cvd-public-wave-v2-ten-doctor-report',
                'scientific_contract':{k:'SYNTHETIC CONTRACT' for k in ['target_population','eligibility','outcome_definition','baseline_timing','followup_horizon','exclusion_criteria']},
                'membership':mdesc,'prior_person_token_registry':rdesc,'features':desc(feature),'feature_provenance':fm,
                'frozen_model':{'architecture':'compact','checkpoint':desc(cp),'source_preprocessing':pp,
                    'hyperparameter_record':hp,'threshold_calibration_record':cal,'numerical_threshold':.3}}
            pd=dump(root/'invented_proposal.json',proposal)
            regout=root/'invented_registration';regout.mkdir(mode=0o700)
            register({'proposal':pd},regout)
            self.assertFalse(json.loads((regout/'registered_test.private.json').read_text())['outcomes_opened'])
            started=dump(root/'invented_started.json',{'status':'STARTED_CONSUMED','fixture_only':True})
            completed=dump(root/'invented_completed.json',{'status':'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED','attempt_consumed':True,'fixture_only':True})
            outcomes=root/'invented_outcomes.npz';np.savez(outcomes,ids=np.array(member['ids']),y=np.array([1,0]))
            config={'registration':desc(regout/'registered_test.private.json'),'registration_started_receipt':started,
                'registration_completed_receipt':completed,'outcomes':desc(outcomes)}
            predicted=[];old_prob=T.prob;old_descriptor=prospective.descriptor
            def prediction(*args,**kw):
                p=old_prob(*args,**kw);predicted.append(True);return p
            def check_order(d):
                if d==config['outcomes']:self.assertTrue(predicted)
                return old_descriptor(d)
            output=root/'invented_evaluation';output.mkdir(mode=0o700)
            with patch.object(T,'prob',side_effect=prediction),patch.object(prospective,'descriptor',side_effect=check_order):
                evaluate(config,output)
            result=json.loads((output/'independent_evaluation.private.json').read_text())
            self.assertFalse(result['model_fitted']);self.assertFalse(result['threshold_retuned'])
            marker=regout/'independent_evaluation.consumed.private.json';before=marker.read_bytes()
            second=root/'invented_second_output';second.mkdir()
            with self.assertRaises(Rejected):evaluate(config,second)
            self.assertEqual(marker.read_bytes(),before)


if __name__=='__main__':unittest.main()
