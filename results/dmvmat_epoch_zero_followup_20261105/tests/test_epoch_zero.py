"""Invented-only checkpoint, inference, partition and lifecycle tests."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from checkpoints import t,state_hash,rng_hash,stopping_bce,fit_epoch_zero,paired_fit
from experiment import source_fit,inference,predict_condition,validate_roles
from epoch_zero import invented_data,PURPOSE
from design import outer_splits,budget_roles,threshold_from_calibration
from local_execution import Rejected,exclusive_output,write_json,cli,code_hashes
from install_public_epoch_zero import install
from package_integrity import verify_package,reviewed_protocol
from paired_report import primary_stat,summarize
P=json.loads((ROOT/'EXPERIMENT_CONFIG.json').read_text())
torch.set_num_threads(1)


class OneWeight(torch.nn.Module):
    def __init__(self,w=2.):
        super().__init__();self.w=torch.nn.Parameter(torch.tensor(w))
    def forward(self,x):return x['x'].flatten()*self.w


def conflict(w=2.):
    x=np.tile(np.array([-1.,1.]),32).astype('float32');good=(x>0).astype(int)
    train=t.Encoded({'x':x[:,None]},1-good,'target_adaptation')
    stop=t.Encoded({'x':x[:,None]},good,'target_validation')
    return OneWeight(w),train,stop


class CheckpointTests(unittest.TestCase):
    def test_original_excludes_better_initial_state(self):
        model,fit,stop=conflict();zero=stopping_bce(model,stop)
        t.seed(7);trace=t.fit(model,fit,stop,10,.03)
        self.assertEqual(trace['selected_epoch'],1)
        self.assertGreater(trace['restored_unweighted_validation_BCE'],zero)

    def test_epoch_zero_wins_restores_exact_weights_and_patience(self):
        model,fit,stop=conflict();before=state_hash(model);initial=copy.deepcopy(model.state_dict())
        t.seed(7);trace=fit_epoch_zero(model,fit,stop,10,.03,patience=5)
        self.assertEqual(trace['selected_epoch'],0);self.assertEqual(trace['stopped_epoch'],5)
        self.assertEqual(state_hash(model),before)
        for name,v in model.state_dict().items():self.assertTrue(torch.equal(v,initial[name]))
        self.assertTrue(all(r['validation_bce']>trace['epoch_zero_bce'] for r in trace['curve']))

    def test_later_improvement_selected_and_original_matches(self):
        model,wrong,stop=conflict(w=-1.)
        fit=t.Encoded({k:v.numpy() for k,v in stop.views.items()},stop.y.numpy(),'target_adaptation')
        a=copy.deepcopy(model);b=copy.deepcopy(model)
        t.seed(91);ta=t.fit(a,fit,stop,10,.03)
        t.seed(91);tb=fit_epoch_zero(b,fit,stop,10,.03)
        self.assertGreater(tb['selected_epoch'],0)
        self.assertLess(tb['restored_unweighted_validation_BCE'],tb['epoch_zero_bce'])
        self.assertEqual(ta['curve'],tb['curve']);self.assertEqual(state_hash(a),state_hash(b))

    def test_better_stopping_bce_can_have_worse_outer_ap(self):
        model,fit,stop=conflict(w=.01);a=copy.deepcopy(model);b=copy.deepcopy(model)
        t.seed(5);ta=t.fit(a,fit,stop,10,.1)
        t.seed(5);tb=fit_epoch_zero(b,fit,stop,10,.1)
        self.assertEqual(tb['selected_epoch'],0)
        self.assertLess(tb['restored_unweighted_validation_BCE'],ta['restored_unweighted_validation_BCE'])
        # Invented outer relationship is opposite to stopping; no outer input to fit.
        outer_y=fit.y.numpy();pa=t.prob(a,fit);pb=t.prob(b,fit)
        self.assertLess(t.metrics(outer_y,pb)['ap'],t.metrics(outer_y,pa)['ap'])

    def test_initial_evaluation_preserves_weights_rng_and_mode(self):
        model,fit,stop=conflict();model.train();t.seed(33)
        h,r=state_hash(model),rng_hash();stopping_bce(model,stop)
        self.assertEqual(state_hash(model),h);self.assertEqual(rng_hash(),r);self.assertTrue(model.training)

    def test_min_delta_tie_keeps_zero(self):
        model,fit,stop=conflict()
        # Zero LR is an explicit synthetic tie fixture only, not a protocol option.
        trace=fit_epoch_zero(model,fit,stop,10,0.)
        self.assertEqual(trace['selected_epoch'],0);self.assertEqual(trace['stopped_epoch'],5)

    def test_role_rejection(self):
        model,fit,stop=conflict();stop.role='target_test'
        with self.assertRaises(Rejected):fit_epoch_zero(model,fit,stop,10,.001)


class PairingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=invented_data();cls.p=copy.deepcopy(P);cls.p.update(source_epochs=2,target_epochs=6)
        cls.source,_=source_fit(cls.data,cls.p)
        cls.split=next(outer_splits(cls.data['target_pool__ids'],3,P['repeat_seeds']))
        cls.roles=budget_roles(cls.split,.75)

    def test_identical_initial_optimizer_updates_scores_rng(self):
        from experiment import predict_condition
        models,traces,v,probs,cal,c=predict_condition(self.source,self.data,self.roles,self.split['outer'],7,self.p)
        self.assertEqual(traces['A']['initial_state_sha256'],traces['B']['initial_state_sha256'])
        self.assertEqual(v['initial_optimizer']['state_entries'],0)
        self.assertGreater(v['matched_update_prefix'],0);self.assertGreater(v['matched_epoch_prefix'],0)
        n=v['matched_epoch_prefix'];self.assertEqual(traces['A']['curve'][:n],traces['B']['curve'][:n])
        self.assertEqual(v['initial_state_sha256'],state_hash(self.source))

    def test_arm_a_is_exact_frozen_fit(self):
        ix=self.roles;part=lambda indices,role:t.Encoded({v:self.data['target_pool__'+v][indices] for v in t.VIEWS},self.data['target_pool__y'][indices],role)
        fit=part(ix['fit'],'target_adaptation');stop=part(ix['stop'],'target_validation')
        models,traces,_=paired_fit(self.source,fit,stop,100,self.p)
        t.seed(100);direct=copy.deepcopy(self.source)
        t.set_selective_trainability(direct,{k:True for k in direct.selectable_modules()})
        expected=t.fit(direct,fit,stop,self.p['target_epochs'],self.p['target_lr'],patience=self.p['patience'])
        self.assertEqual(expected['curve'],traces['A']['curve']);self.assertEqual(state_hash(direct),state_hash(models['A']))

    def test_outer_calibration_labels_cannot_change_fit(self):
        first=predict_condition(self.source,self.data,self.roles,self.split['outer'],15,self.p)
        changed=copy.deepcopy(self.data);ix=np.r_[self.roles['calibration'],self.split['outer']]
        changed['target_pool__y'][ix]=1-changed['target_pool__y'][ix]
        second=predict_condition(self.source,changed,self.roles,self.split['outer'],15,self.p)
        self.assertEqual(first[1],second[1]);self.assertEqual(first[2],second[2])
        for a in ['A','B']:np.testing.assert_array_equal(first[3][a],second[3][a])

    def test_source_state_and_inputs_immutable(self):
        before=state_hash(self.source);data=copy.deepcopy(self.data)
        predict_condition(self.source,self.data,self.roles,self.split['outer'],11,self.p)
        self.assertEqual(before,state_hash(self.source))
        for k in data:np.testing.assert_array_equal(data[k],self.data[k])

    def test_source_vs_epoch_zero_forward_exact(self):
        # Directly restored clone, matching the actual model/inference path.
        clone=copy.deepcopy(self.source)
        t.set_selective_trainability(clone,{k:True for k in clone.selectable_modules()})
        np.testing.assert_array_equal(inference(clone,self.data,self.split['outer']),inference(self.source,self.data,self.split['outer']))

    def test_nested_budgets_and_roles_identical_original(self):
        previous={k:set() for k in ['fit','stop','calibration','selected']}
        for fraction in P['budget_fractions']:
            roles=budget_roles(self.split,fraction);validate_roles(self.data,roles,self.split['outer'])
            self.assertEqual(sum(len(roles[k]) for k in ['fit','stop','calibration']),roles['budget_n'])
            for k in previous:self.assertLessEqual(previous[k],set(roles[k]));previous[k]=set(roles[k])

    def test_overlap_fails_closed(self):
        bad=copy.deepcopy(self.roles);bad['fit'][0]=self.split['outer'][0]
        with self.assertRaises(Rejected):predict_condition(self.source,self.data,bad,self.split['outer'],11,self.p)

    def test_no_calibration_support_no_fallback(self):
        for n in [0,1,4]:
            y=np.r_[np.ones(n),np.zeros(9-n)]
            self.assertIsNone(threshold_from_calibration(y,np.full(9,.1),P,t.select_validation_threshold)['threshold'])


def fake_cells(single_class=False):
    cells=[]
    for repeat in P['repeat_seeds']:
        for fold in range(3):
            ix=np.arange(fold*4,fold*4+4);y=[1,0,0,0] if not single_class else [0]*4
            probs={'A':[.2,.1,.15,.1],'B':[.3,.1,.1,.1],'C':[.2,.1,.15,.1]}
            cells.append({'fraction':.1,'repeat_seed':repeat,'fold':fold,'outer_indices':ix.tolist(),'population_n':12,
                'y':y,'probabilities':probs,'status':'EVALUATED',
                'metrics':{a:{'fixed_0_50':t.metrics(y,probs[a]),'calibrated':None} for a in probs},
                'training':{a:{'selected_epoch':0 if a=='B' else 1} for a in ['A','B']}})
    return cells


class StatisticsTests(unittest.TestCase):
    def test_primary_is_equal_fold_difference(self):
        cells=fake_cells()
        for c in cells:
            if c['fold']==0:
                c['probabilities']['A']=[.1,.4,.3,.2]
                c['probabilities']['B']=[.9,.4,.3,.2]
        self.assertAlmostEqual(primary_stat(cells),.25)

    def test_equal_fold_primary_and_single_class_unavailable(self):
        cells=fake_cells();self.assertEqual(primary_stat(cells),0.)
        cells[0]['y']=[0]*4;self.assertIsNone(primary_stat(cells))
        self.assertIsNone(primary_stat(cells[1:]))

    def test_shared_participant_resample_and_no_redraw(self):
        cells=fake_cells();p=copy.deepcopy(P);p.update(budget_fractions=[.1],bootstrap_repetitions=12)
        report=summarize(cells,p)[0]
        u=report['primary_uncertainty'];self.assertEqual(u['defined_replicates']+u['undefined_replicates'],12)
        self.assertTrue(u['conditional_on_fitted_models']);self.assertFalse(u['includes_retraining_uncertainty'])
        self.assertEqual(report['B_epoch_zero_selections'],9)

    def test_fold_mean_and_pooled_different_estimands(self):
        cells=fake_cells()
        for c in cells:
            f=c['fold'];c['probabilities']['A']=[.6,.4,.4,.4]
            c['probabilities']['B']=[.9,.8,.8,.8] if f==0 else [.2,.1,.1,.1]
        self.assertEqual(primary_stat(cells),0.)
        y=np.concatenate([c['y'] for c in cells[:3]])
        a=np.concatenate([c['probabilities']['A'] for c in cells[:3]])
        b=np.concatenate([c['probabilities']['B'] for c in cells[:3]])
        self.assertLess(t.metrics(y,b)['ap'],t.metrics(y,a)['ap'])

    def test_missing_positive_metrics_remain_none(self):
        p=copy.deepcopy(P);p.update(budget_fractions=[.1],bootstrap_repetitions=5)
        report=summarize(fake_cells(True),p)[0]
        self.assertIsNone(report['primary_equal_fold_B_minus_A_AP'])
        self.assertIsNone(report['primary_uncertainty']['interval_95'])


class SecurityTests(unittest.TestCase):
    def test_processing_failure_records_plan_and_never_retries(self):
        import experiment
        data=invented_data();p=copy.deepcopy(P);p.update(source_epochs=1,target_epochs=1)
        source=t.MultiViewRiskNet(t.VIEWS)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out';progress=experiment.condition_plan(p)
            with patch('experiment.source_fit',return_value=(source,{'synthetic_only':True})),\
                 patch('experiment.predict_condition',side_effect=Rejected('SYNTHETIC_FAULT')) as mocked:
                with self.assertRaises(Rejected):
                    with exclusive_output(out,False):experiment.run(data,{'synthetic_only':True},p,out,'INVENTED_SYNTHETIC_ONLY_NOT_CLINICAL_RESULTS',progress)
            self.assertEqual(mocked.call_count,1)
            self.assertEqual(len(progress),45);self.assertEqual(list(progress.values()).count('FAILED_NO_RETRY'),1)
            self.assertEqual(list(progress.values()).count('NOT_RUN'),44)
            self.assertTrue((out/'registered_conditions.private.json').is_file())
            self.assertTrue(json.loads((out/'completion.private.json').read_text())['attempt_consumed'])

    def test_public_package_verifier_rejects_changed_immutable_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'a.py').write_text('# invented\n')
            h=hashlib.sha256((root/'a.py').read_bytes()).hexdigest()
            (root/'IMMUTABLE_DEPENDENCIES.json').write_text(json.dumps({'a.py':{'sha256':h}}))
            manifest={'schema':'epoch-zero-public-package-v1','files':{'a.py':h}}
            (root/'PUBLIC_PACKAGE_MANIFEST.json').write_text(json.dumps(manifest))
            verify_package(root)
            (root/'a.py').write_text('CHANGED')
            with self.assertRaises(Rejected):verify_package(root)

    def test_authorization_cancellation_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'invented.json';auth=root/'never_created.json';out=root/'never_created'
            config.write_text(json.dumps({'mode':'independent_local_only'}))
            with patch('local_execution.require_local'),patch('builtins.input',side_effect=['SYNTHETIC_OPERATOR','CANCEL']),\
                 patch('sys.argv',['x','--authorize-local','--config',str(config),'--authorization',str(auth),'--output',str(out)]),\
                 patch('builtins.print'):
                rc=cli(PURPOSE,lambda c,o:None,lambda o:None)
            self.assertEqual(rc,2);self.assertFalse(auth.exists());self.assertFalse(out.exists())

    def test_synthetic_mode_rejects_external_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'never'
            r=subprocess.run([sys.executable,'-B',str(ROOT/'epoch_zero.py'),'--synthetic-demo',
                '--config',str(Path(tmp)/'not_read.json'),'--output',str(out)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2);self.assertFalse(out.exists());self.assertNotIn(tmp,r.stdout+r.stderr)

    def test_manifest_mismatch_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            base=Path(tmp);src=base/'public';src.mkdir()
            manifest=src/'PUBLIC_PACKAGE_MANIFEST.json'
            manifest.write_text(json.dumps({'schema':'epoch-zero-public-package-v1','files':{'../escape.py':'0'*64}}))
            h=hashlib.sha256(manifest.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):install(src,base/'installed','0'*64)
            with self.assertRaises(ValueError):install(src,base/'installed',h)
            self.assertFalse((base/'installed').exists())

    def test_expected_configuration_and_runtime_bindings(self):
        import package_integrity as integrity
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);public=root/'public';public.mkdir();protocol=public/'EXPERIMENT_CONFIG.json'
            protocol.write_text(json.dumps(P));manifest=public/'PUBLIC_PACKAGE_MANIFEST.json';manifest.write_text('{}')
            cfg={'schema':'epoch-zero-local-v1','mode':'independent_local_only','no_locked_test':True,
                'no_prior_validation_outcomes':True,'protocol':{'path':str(protocol),'sha256':hashlib.sha256(protocol.read_bytes()).hexdigest()},
                'package_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                'runtime_versions':{'synthetic_runtime':'1'},
                'inputs':{k:{} for k in ['development_manifest','completed_workflow_receipt','source_preprocessing','development_bundle']}}
            with patch.object(integrity,'ROOT',public),patch.object(integrity,'runtime',return_value={'synthetic_runtime':'1'}):
                self.assertEqual(reviewed_protocol(cfg),P)
                for key,value in [('runtime_versions',{'different':'2'}),('package_manifest_sha256','0'*64),('no_locked_test',False)]:
                    wrong=copy.deepcopy(cfg);wrong[key]=value
                    with self.assertRaises(Rejected):reviewed_protocol(wrong)

    def test_agent_guard_before_config_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Invented nonexistent config; rejection must be guard/static status.
            env=dict(os.environ,CODEX_SESSION_ID='SYNTHETIC_AGENT')
            r=subprocess.run([sys.executable,'-B',str(ROOT/'epoch_zero.py'),'--execute-local',
                              '--config',str(Path(tmp)/'invented.json')],capture_output=True,text=True,env=env)
            self.assertEqual(r.returncode,2);self.assertNotIn(tmp,r.stdout+r.stderr)
            self.assertIn('STOP ISSUE=EPOCH_ZERO_LOCAL_READINESS_NOT_ESTABLISHED',r.stdout)

    def test_failed_and_interrupted_outputs_consumed_no_retry(self):
        for error,status in [(ValueError('INVENTED_PRIVATE_CONTEXT'),'FAILED_NO_RETRY'),(KeyboardInterrupt(),'INTERRUPTED_NO_RETRY')]:
            with tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp)/'new'
                with self.assertRaises(type(error)):
                    with exclusive_output(out,False):raise error
                receipt=json.loads((out/'completion.private.json').read_text())
                self.assertEqual(receipt['status'],status);self.assertTrue(receipt['attempt_consumed'])
                self.assertNotIn('INVENTED_PRIVATE_CONTEXT',json.dumps(receipt))
                with self.assertRaises(Rejected):
                    with exclusive_output(out,False):pass

    def test_output_mode_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'
            with exclusive_output(out,False):write_json(out/'invented.json',{'scope':'SYNTHETIC_ONLY'})
            self.assertEqual(out.stat().st_mode&0o777,0o700)
            self.assertEqual((out/'invented.json').stat().st_mode&0o777,0o600)

    def test_old_authorization_purpose_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'invented-config.json';auth=root/'invented-auth.json';out=root/'unused'
            config.write_text(json.dumps({'mode':'independent_local_only'}))
            auth.write_text(json.dumps({'purpose':'retained_development_label_efficiency_followup_v1',
                'authorized':True,'scope_confirmed_by_operator':True,'operator':'SYNTHETIC_FIXTURE_NOT_A_REAL_AUTHORIZATION',
                'output_binding':str(out.resolve()),'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'code_bindings':code_hashes()}))
            invoked=[]
            with patch('local_execution.require_local'),patch('sys.argv',['x','--execute-local','--config',str(config),
                '--authorization',str(auth),'--output',str(out)]),patch('builtins.print'):
                rc=cli(PURPOSE,lambda c,o:invoked.append(True),lambda o:None)
            self.assertEqual(rc,2);self.assertFalse(invoked);self.assertFalse(out.exists())

    def test_installer_allowlist_hash_and_no_overwrite(self):
        # macOS /var is a symlink; use its actual public temporary location.
        with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
            base=Path(tmp);src=base/'public';src.mkdir();dest=base/'installed'
            (src/'file.py').write_text('# invented public file\n');(src/'unrelated.txt').write_text('DO_NOT_COPY')
            manifest={'schema':'epoch-zero-public-package-v1','files':{'file.py':hashlib.sha256((src/'file.py').read_bytes()).hexdigest()}}
            (src/'PUBLIC_PACKAGE_MANIFEST.json').write_text(json.dumps(manifest))
            h=hashlib.sha256((src/'PUBLIC_PACKAGE_MANIFEST.json').read_bytes()).hexdigest()
            self.assertEqual(install(src,dest,h),2);self.assertFalse((dest/'unrelated.txt').exists())
            with self.assertRaises(ValueError):install(src,dest,h)
            (src/'file.py').write_text('MODIFIED')
            with self.assertRaises(ValueError):install(src,base/'changed',h)
            self.assertFalse((base/'changed').exists())

    def test_package_and_config_reject_change(self):
        # Missing local config fields cannot authorize a broader experiment.
        with self.assertRaises(Rejected):reviewed_protocol({'schema':'wrong'})


if __name__=='__main__':unittest.main()
