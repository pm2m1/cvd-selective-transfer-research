"""Invented installations/records only. Original authorization/execution is mocked."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import run_development_workflow as w
import review_development_results_local as review
import configure_export_local as helper


def dump(path, obj):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2)+'\n')


def invented_report():
    rows, summary = [], {}
    for name in w.CANDIDATES:
        rr = []
        for draw in range(10):
            base = {'ap': .2+draw*.001, 'auroc': .6+draw*.001, 'brier': .08+draw*.0001}
            fixed = {**base, 'threshold': .5, 'TP':4, 'FN':9, 'TN':140, 'FP':18,
                'recall':4/13, 'specificity':140/158, 'precision':4/22, 'f1':8/35}
            selected = {**base, 'threshold': .3, 'TP':6, 'FN':7, 'TN':130, 'FP':28,
                'recall':6/13, 'specificity':130/158, 'precision':6/34, 'f1':12/47}
            row = {'candidate': {'id':name, 'target_epochs':20}, 'draw':draw,
                'scope':'EXPLORATORY_TARGET_DEVELOPMENT_ONLY', 'threshold_estimate_is_resubstitution':True,
                'fixed_0_5':fixed, 'validation_selected_threshold':selected,
                'trainable_parameters':33, 'training':None if name=='target_logistic' else
                {'selected_epoch':2,'stopped_epoch':3}}
            rr.append(row); rows.append(row)
        summary[name] = {}
        for source, dest in [('fixed_0_5','fixed_0_5'),('validation_selected_threshold','validation_selected')]:
            summary[name][dest] = {}
            for key in ['ap','auroc','brier','recall','specificity','precision','f1','threshold']:
                vals = [r[source][key] for r in rr]
                summary[name][dest][key] = {'mean':statistics.mean(vals), 'sd':statistics.stdev(vals),
                    'min':min(vals), 'max':max(vals)}
    return {'fixture_origin':'COMPLETELY_INVENTED_UNIT_TEST_NOT_A_REAL_RUN',
        'status':'PRIVATE_EXPLORATORY_DEVELOPMENT_NOT_EXTERNAL_VALIDATION',
        'test_predictions_generated':False, 'adaptation_draws_are_not_independent_validations':True,
        'rows':rows, 'summary':summary, 'source_training_curves':{}}


class FakeBoundary:
    """No actual authorization, subprocess, cohort loading or training occurs."""
    def __init__(self, fail=None): self.calls=[]; self.fail=fail
    def authorize(self, script, config, auth, output):
        kind = 'export' if script.startswith('prepare') else 'training'
        self.calls.append('authorize_'+kind)
        if self.fail == 'cancel_'+kind: raise w.Stop('INDEPENDENT_AUTHORIZATION_CANCELLED_OR_FAILED')
        if self.fail != 'missing_authorization':
            w.private_json(auth, {'fixture_only':'NOT_AN_AUTHORIZATION_OR_PERMISSION'})
        if self.fail == 'change_training_config' and kind == 'training':
            changed=w.read_json(config); changed['phase']=2; dump(config,changed)
    def verify_authorization(self, purpose, config, auth, output):
        self.calls.append('verify_authorization')
        w.need(auth.is_file(), 'ORIGINAL_AUTHORIZATION_MISSING')
    def execute(self, script, config, auth, output):
        kind = 'export' if script.startswith('prepare') else 'training'; self.calls.append('execute_'+kind)
        output.mkdir(mode=0o700)
        w.private_json(output/'operation_started.private.json', {'status':'STARTED_CONSUMED','fixture_only':True})
        if self.fail == 'interrupt': raise KeyboardInterrupt()
        if self.fail == 'fail_'+kind:
            w.private_json(output/'completion.private.json', {'status':'FAILED_NO_RETRY','attempt_consumed':True})
            raise w.Stop('ORIGINAL_OPERATION_FAILED_NO_RETRY')
        w.private_json(output/'completion.private.json', {'status':w.COMPLETE,'attempt_consumed':True})
        if kind == 'export': w.private_json(output/'development_manifest.private.json', {'fixture_only':True})
        else: w.private_json(output/'exploratory_development.private.json', invented_report())
    def validate_export(self, config, output):
        self.calls.append('validate_export')
        if self.fail == 'bad_bundle': raise w.Stop('EXPORT_MANIFEST_MISMATCH')
        print('INVENTED_SENSITIVE_LOG_SENTINEL')
        return output/'invented_assignments.json'
    def training_config(self, output, assignments):
        self.calls.append('build_training_config')
        return {'schema':'exploratory-development-v1','mode':'independent_local_only',
            'phase':2 if self.fail=='tier_two' else 1, 'no_test_evaluation':True,'candidates':w.CANDIDATES[:],
            'fixture_only':True}
    def review(self, config, output, workspace, show):
        self.calls.append('review')
        return review.write_review(output/'exploratory_development.private.json',workspace/'local_review',False)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='invented_workflow_test_')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base/'invented_package'; self.root.mkdir(mode=0o700)
        m = {'public_source_files':[], 'additional_public_records':[], 'experiment_tools':[]}
        bindings = {}
        names = ['src/dmv_mat_cvd/real_baselines.py']+[f'src/dmv_mat_cvd/invented_{i}.py' for i in range(62)]
        for name in names:
            p = self.root/'public_project'/name; p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            p.write_text("from pathlib import Path\nEVIDENCE = Path('invented.evidence.json')\n" if name.endswith('real_baselines.py') else '# INVENTED PUBLIC FIXTURE\n')
            h=w.sha(p); bindings[name]=h; m['public_source_files'].append({'path':name,'expected_sha256':h})
        cfg = {'source_mapping':'configs/mappings/invented_source.json',
            'target_mapping':'configs/mappings/invented_target.json'}
        configs = {'configs/public_haalsi_mhas_v2.ready_pending_execution_m5l.json':cfg,
            cfg['source_mapping']:{'files':{'main':'invented_source.file'}},
            cfg['target_mapping']:{'files':{'main':'invented_target.file'}},
            'configs/invented_schema_one.json':{},'configs/invented_schema_two.json':{}}
        for name, value in configs.items():
            p=self.root/'public_project'/name; dump(p,value)
            m['additional_public_records'].append({'path':name,'actual_sha256':w.sha(p)})
        tool_names = ['local_execution.py']+[f'invented_tool_{i}.py' for i in range(24)]
        for name in tool_names:
            p=self.root/'experiment_tools'/name; p.parent.mkdir(mode=0o700,exist_ok=True)
            p.write_text('# INVENTED PUBLIC TOOL; NOT EXECUTED\n')
            m['experiment_tools'].append({'path':name,'source_sha256':w.sha(p)})
        mp=self.root/'PUBLIC_STAGING_MANIFEST.json'; dump(mp,m)
        hp=self.root/'helpers'; hp.mkdir(mode=0o700)
        for name in ['configure_export_local.py','run_development_workflow.py','review_development_results_local.py']:
            (hp/name).write_text('# INVENTED HELPER FILE; NOT EXECUTED\n')
        dump(hp/'WORKFLOW_PUBLIC_BINDINGS.json', {'schema':'workflow-public-helper-bindings-v1',
            'files':{n:w.sha(hp/n) for n in ['configure_export_local.py','run_development_workflow.py','review_development_results_local.py']}})
        patches = [patch.object(w,'PUBLIC_MANIFEST_SHA',w.sha(mp)),
                   patch.object(w,'CONFIG_HELPER_SHA',w.sha(hp/'configure_export_local.py')),
                   patch.object(helper,'EXPECTED_BINDINGS_SHA256', hashlib.sha256(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()).hexdigest())]
        for p in patches: p.start(); self.addCleanup(p.stop)
        self.inputs=self.base/'invented_inputs'; self.inputs.mkdir(mode=0o700)
        for name in ['invented_source.file','invented_target.file','invented_master.file','invented_questionnaire.file']:
            (self.inputs/name).write_bytes(b'INVENTED NOT CLINICAL')
        private=self.inputs/'private_locks/public-haalsi-mhas-v2'; private.mkdir(parents=True)
        for name in ['target_lock.json','participant_assignments.private.json']:
            (private/name).write_text('INVENTED METADATA PLACEHOLDER NOT A REAL LOCK')
        (self.root/'public_project/invented.evidence.json').write_text('INVENTED NOT A REAL GOVERNANCE RECORD')
        self.config_path=self.base/'invented_config.json'
        self.config={'schema':helper.SCHEMA,'mode':'independent_local_only','no_test_rows':True,
            'isolated_public_project':str(self.root/'public_project'),'public_source_bindings':bindings,
            'data_root':str(self.inputs),'master_file':str(self.inputs/'invented_master.file'),
            'questionnaire':str(self.inputs/'invented_questionnaire.file')}
        dump(self.config_path,self.config)
        self.workspace=self.base/'invented_workspace'

    def prepared(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return w.prepare(self.root,self.workspace,self.config_path,helper)

    def run_fake(self, boundary):
        state=self.prepared()
        with contextlib.redirect_stdout(io.StringIO()):
            return w.run_prepared(self.root,self.workspace,state,boundary)

    def test_fresh_public_installation_only_allowlisted_files(self):
        secret=self.root/'DO_NOT_TRANSFER.private'; secret.write_text('INVENTED EXCLUDED')
        destination=self.base/'invented_installation'
        w.install_public(self.root,destination)
        self.assertFalse((destination/secret.name).exists())
        self.assertFalse((destination/'public_project/invented.evidence.json').exists())
        self.assertEqual(len(w.public_inventory(destination)),93)
        self.assertEqual(destination.stat().st_mode & 0o777,0o700)
        self.assertEqual((destination/'experiment_tools/local_execution.py').stat().st_mode & 0o777,0o600)

    def test_existing_identical_installation_unchanged(self):
        dest=self.base/'invented_installation'; w.install_public(self.root,dest)
        p=dest/'experiment_tools/local_execution.py'; before=p.stat().st_mtime_ns
        w.install_public(self.root,dest); self.assertEqual(before,p.stat().st_mtime_ns)

    def test_additive_helper_update_without_core_overwrite(self):
        dest=self.base/'invented_installation'; w.install_public(self.root,dest)
        (dest/'helpers/run_development_workflow.py').unlink()
        p=dest/'experiment_tools/local_execution.py'; before=p.read_bytes()
        w.install_public(self.root,dest); self.assertTrue((dest/'helpers/run_development_workflow.py').is_file())
        self.assertEqual(p.read_bytes(),before)

    def test_existing_partial_installation_rejected(self):
        dest=self.base/'invented_installation'; dest.mkdir(mode=0o700)
        with self.assertRaises(w.Stop): w.install_public(self.root,dest)

    def test_existing_changed_file_not_overwritten(self):
        dest=self.base/'invented_installation'; w.install_public(self.root,dest)
        p=dest/'helpers/run_development_workflow.py'; p.write_text('INVENTED CONFLICT')
        with self.assertRaises(w.Stop): w.install_public(self.root,dest)
        self.assertEqual(p.read_text(),'INVENTED CONFLICT')

    def test_nested_installation_rejected(self):
        with self.assertRaises(w.Stop): w.install_public(self.root,self.root/'experiment_tools/unsafe')

    def test_wrong_manifest_rejected(self):
        (self.root/'PUBLIC_STAGING_MANIFEST.json').write_text('{}')
        with self.assertRaises(w.Stop): w.public_inventory(self.root)

    def test_modified_tools_rejected(self):
        (self.root/'experiment_tools/local_execution.py').write_text('# changed fixture')
        with self.assertRaises(w.Stop): w.verify_installation(self.root)

    def test_public_symlink_escape_rejected(self):
        p=self.root/'experiment_tools/local_execution.py'; outside=self.base/'invented_outside.py'
        outside.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(outside)
        with self.assertRaises(w.Stop): w.verify_installation(self.root)

    def test_missing_paths_prompted_only_once(self):
        self.config['data_root']=None; dump(self.config_path,self.config)
        with patch.object(w,'hidden',return_value=str(self.inputs)) as prompt, contextlib.redirect_stdout(io.StringIO()):
            c=w.ensure_configured(helper,self.config_path,self.root/'public_project')
            w.ensure_configured(helper,self.config_path,self.root/'public_project')
        self.assertEqual(prompt.call_count,1); self.assertEqual(c['master_file'],self.config['master_file'])

    def test_invalid_populated_path_not_replaced(self):
        self.config['master_file']='relative/invented'; dump(self.config_path,self.config)
        with patch.object(w,'hidden',side_effect=AssertionError('must not guess')):
            with self.assertRaises(Exception): self.prepared()

    def test_missing_original_evidence_stops_preparation(self):
        (self.root/'public_project/invented.evidence.json').unlink()
        with self.assertRaises(w.Stop): self.prepared()

    def test_preparation_does_not_hash_or_open_clinical_inputs(self):
        original_sha=w.sha; touched=[]
        def guard(p):
            self.assertFalse(Path(p).is_relative_to(self.inputs)); touched.append(str(p)); return original_sha(p)
        with patch.object(w,'sha',side_effect=guard):
            state=self.prepared()
        self.assertEqual(state['original_input_integrity'],'PENDING_ORIGINAL_AUTHORIZED_LOADER')
        self.assertEqual(state['provider_institutional_permission'],'NOT_ESTABLISHED_BY_PREPARATION')

    def test_end_to_end_mocked_boundaries_no_metrics_publicly_printed(self):
        boundary=FakeBoundary(); result=self.run_fake(boundary)
        self.assertEqual(result,'WORKFLOW_COMPLETE_PRIVATE_REVIEW_ONLY')
        self.assertEqual(boundary.calls,['authorize_export','verify_authorization','execute_export',
            'validate_export','build_training_config','authorize_training','verify_authorization','execute_training','review'])
        receipt=w.read_json(self.workspace/'workflow.completion.private.json')
        self.assertEqual(receipt['status'],w.COMPLETE)
        self.assertFalse(receipt['real_test_evaluation'])
        self.assertTrue((self.workspace/'local_review/development_comparison.private.md').exists())
        self.assertIn('INVENTED_SENSITIVE_LOG_SENTINEL',(self.workspace/'post_export_validation.private.log').read_text())
        self.assertEqual((self.workspace/'post_export_validation.private.log').stat().st_mode & 0o777,0o600)

    def test_one_command_entrypoint_with_entire_authorized_boundary_mocked(self):
        boundary=FakeBoundary(); out=io.StringIO()
        with patch.object(w,'HELPERS',self.root/'helpers'), patch.object(w,'independent_runtime',return_value=object()), \
             patch.object(w,'load_module',return_value=helper), patch.object(w,'FrozenBoundary',return_value=boundary), \
             contextlib.redirect_stdout(out):
            rc=w.main(['--run-authorized','--workspace',str(self.workspace),'--export-config',str(self.config_path)])
        self.assertEqual(rc,0)
        self.assertIn('WORKFLOW_COMPLETE_PRIVATE_REVIEW_ONLY',out.getvalue())
        self.assertNotIn(str(self.base),out.getvalue())
        self.assertNotIn('0.2045',out.getvalue())
        self.assertEqual(boundary.calls.count('execute_export'),1)
        self.assertEqual(boundary.calls.count('execute_training'),1)

    def test_private_failure_context_is_confined_to_new_private_log(self):
        self.workspace.mkdir(mode=0o700)
        public=io.StringIO()
        with contextlib.redirect_stdout(public):
            with self.assertRaises(RuntimeError):
                with w.private_log(self.workspace/'invented.private.log'):
                    raise RuntimeError('INVENTED_CONTEXT_NOT_FOR_PUBLIC_OUTPUT')
        self.assertNotIn('INVENTED_CONTEXT_NOT_FOR_PUBLIC_OUTPUT',public.getvalue())
        self.assertIn('INVENTED_CONTEXT_NOT_FOR_PUBLIC_OUTPUT',(self.workspace/'invented.private.log').read_text())

    def test_completed_local_review_reopens_without_execution_or_overwrite(self):
        self.run_fake(FakeBoundary()); report=self.workspace/'local_review/development_review.private.json'
        before=report.read_bytes(); out=io.StringIO()
        with patch.object(w,'HELPERS',self.root/'helpers'), patch.object(w,'independent_runtime',return_value=object()), \
             contextlib.redirect_stdout(out):
            rc=review.main(['--workspace',str(self.workspace)])
        self.assertEqual(rc,0)
        self.assertEqual(out.getvalue().strip(),'PRIVATE_REVIEW_EXISTS_NO_METRICS_DISCLOSED')
        self.assertEqual(before,report.read_bytes())

    def test_missing_authorization_stops_before_export(self):
        b=FakeBoundary('missing_authorization')
        with self.assertRaises(w.Stop): self.run_fake(b)
        self.assertNotIn('execute_export',b.calls)

    def test_export_cancellation_consumes_workflow_without_export(self):
        b=FakeBoundary('cancel_export')
        with self.assertRaises(w.Stop): self.run_fake(b)
        self.assertFalse((self.workspace/'export').exists())
        self.assertEqual(w.status(self.workspace),'FAILED_NO_RETRY')

    def test_training_cancellation_preserves_completed_export(self):
        b=FakeBoundary('cancel_training')
        with self.assertRaises(w.Stop): self.run_fake(b)
        w.operation_completed(self.workspace/'export')
        self.assertFalse((self.workspace/'training').exists())

    def test_failed_operation_no_automatic_retry(self):
        b=FakeBoundary('fail_export'); state=self.prepared()
        with self.assertRaises(w.Stop): w.run_prepared(self.root,self.workspace,state,b)
        before=list(b.calls)
        with self.assertRaises(w.Stop): w.run_prepared(self.root,self.workspace,state,b)
        self.assertEqual(b.calls,before)
        self.assertEqual(w.read_json(self.workspace/'export/completion.private.json')['status'],'FAILED_NO_RETRY')

    def test_existing_output_directory_stops_before_authorization(self):
        state=self.prepared(); (self.workspace/'export').mkdir(); b=FakeBoundary()
        with self.assertRaises(w.Stop): w.run_prepared(self.root,self.workspace,state,b)
        self.assertEqual(b.calls,[])

    def test_preexisting_authorization_not_reused(self):
        state=self.prepared(); w.private_json(self.workspace/'export.authorization.private.json',{'fixture_only':True})
        b=FakeBoundary()
        with self.assertRaises(w.Stop): w.run_prepared(self.root,self.workspace,state,b)
        self.assertEqual(b.calls,[])

    def test_invalid_export_manifest_blocks_training(self):
        b=FakeBoundary('bad_bundle')
        with self.assertRaises(w.Stop): self.run_fake(b)
        self.assertNotIn('authorize_training',b.calls)

    def test_tier_two_rejected(self):
        b=FakeBoundary('tier_two')
        with self.assertRaises(w.Stop): self.run_fake(b)
        self.assertNotIn('authorize_training',b.calls)

    def test_changed_prepared_configuration_rejected_before_authorization(self):
        state=self.prepared(); changed=w.read_json(self.config_path); changed['invented_new_field']=True
        dump(self.config_path,changed); b=FakeBoundary()
        with self.assertRaises(w.Stop): w.run_prepared(self.root,self.workspace,state,b)
        self.assertEqual(b.calls,[])

    def test_training_configuration_change_after_authorization_stops(self):
        b=FakeBoundary('change_training_config')
        with self.assertRaises(w.Stop): self.run_fake(b)
        self.assertNotIn('execute_training',b.calls)

    def test_interruption_permanently_recorded(self):
        with self.assertRaises(KeyboardInterrupt): self.run_fake(FakeBoundary('interrupt'))
        self.assertEqual(w.status(self.workspace),'INTERRUPTED_NO_RETRY')

    def test_training_configuration_fixed_plan_rejects_substitution(self):
        c=FakeBoundary().training_config(None,None); w.validate_training_plan(c)
        c['candidates']=list(reversed(c['candidates']))
        with self.assertRaises(w.Stop): w.validate_training_plan(c)

    def test_missing_dependency_stops_before_operation(self):
        with patch.object(w.importlib.util,'find_spec',return_value=None):
            with self.assertRaises(w.Stop): self.prepared()
        self.assertFalse(self.workspace.exists())

    def test_dependency_check_uses_only_fixed_module_names(self):
        with patch.object(w.importlib.util,'find_spec',return_value=object()) as check:
            w.dependency_check()
        self.assertEqual([x.args[0] for x in check.call_args_list],
            ['numpy','pandas','torch','sklearn','scipy','matplotlib','joblib'])

    def test_original_cli_boundary_inherits_terminal_and_environment(self):
        class Runtime:
            def require_local(self): pass
        b=w.FrozenBoundary(self.root,Runtime())
        result=type('Return',(),{'returncode':0})()
        with patch.object(w,'verify_installation'), patch.object(w.subprocess,'run',return_value=result) as child:
            b.command('prepare_development_inputs.py','--authorize-local',self.config_path,self.base/'invented_auth',self.base/'invented_output')
        call=child.call_args
        self.assertNotIn('env',call.kwargs); self.assertNotIn('input',call.kwargs)
        self.assertNotIn('stdin',call.kwargs); self.assertNotIn('capture_output',call.kwargs)
        self.assertEqual(call.args[0][3],'--authorize-local')

    def test_original_gate_rejection_before_private_config_read(self):
        # Import the original public boundary only; call no private operation.
        runtime=w.load_module('original_gate_for_invented_test',HERE.parent/'experiment_tools/local_execution.py')
        with patch.object(w,'independent_runtime',side_effect=lambda root: runtime.require_local()), \
                patch.object(w,'read_json',side_effect=AssertionError('must not read private config')):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                rc=w.main(['--status','--workspace',str(self.base/'INVENTED_DO_NOT_ECHO')])
        self.assertEqual(rc,2); self.assertNotIn(str(self.base),out.getvalue())


class ReviewTests(unittest.TestCase):
    def test_correct_development_only_summaries(self):
        result=review.summarize_report(invented_report())
        self.assertEqual([x['candidate'] for x in result['candidates']],w.CANDIDATES)
        self.assertAlmostEqual(result['candidates'][0]['fixed_0_50']['ap']['mean'],.2045)
        self.assertAlmostEqual(result['candidates'][0]['fixed_0_50']['recall']['mean'],4/13)
        self.assertTrue(result['validation_selected_f1_is_optimistic_same_validation_resubstitution'])
        table=review.format_table(result)
        self.assertIn('RESUBSTITUTION',table); self.assertIn('not independent',table)
        self.assertEqual(table.count('| fixed 0.50 |'),7)

    def test_test_scope_rejected(self):
        report=invented_report(); report['test_predictions_generated']=True
        with self.assertRaises(w.Stop): review.summarize_report(report)

    def test_missing_candidate_rejected(self):
        report=invented_report(); report['rows'].pop()
        with self.assertRaises(w.Stop): review.summarize_report(report)

    def test_wrong_population_rejected(self):
        report=invented_report(); report['rows'][0]['fixed_0_5']['TP']=21
        with self.assertRaises(w.Stop): review.summarize_report(report)

    def test_changed_summary_rejected(self):
        report=invented_report(); report['summary']['logical']['fixed_0_5']['ap']['mean']=.99
        with self.assertRaises(w.Stop): review.summarize_report(report)

    def test_ranking_metrics_cannot_change_with_threshold(self):
        report=invented_report(); report['rows'][0]['validation_selected_threshold']['ap']=.99
        with self.assertRaises(w.Stop): review.summarize_report(report)

    def test_private_review_exclusive_and_restrictive(self):
        with tempfile.TemporaryDirectory(prefix='invented_review_') as tmp:
            root=Path(tmp); report=root/'invented_report.json'; dump(report,invented_report())
            dest=root/'invented_review'; review.write_review(report,dest,False)
            self.assertEqual((dest/'development_review.private.json').stat().st_mode & 0o777,0o600)
            with self.assertRaises(w.Stop): review.write_review(report,dest,False)


class MembershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(HERE.parent/'experiment_tools'))
        import train_exploratory_candidates as trainer
        import numpy as np
        cls.trainer=trainer; cls.np=np
    def fixture(self):
        np=self.np; d={}; assignments={'source_partitions':{},'target_partitions':{},'adaptation_draws':{}}
        for role,(n,e) in self.trainer.COUNTS.items():
            ids=np.array([f'INVENTED_{role}_{i}' for i in range(n)])
            d[role+'__ids']=ids; d[role+'__y']=np.r_[np.ones(e),np.zeros(n-e)].astype(int)
            for v,dim in self.trainer.VIEWS.items():d[role+'__'+v]=np.zeros((n,dim),dtype='float32')
            group=assignments['source_partitions'] if role.startswith('source_') else assignments['target_partitions']
            group['target_adaptation_pool' if role=='target_pool' else role]=ids.tolist()
        for i in range(10):
            ix=np.r_[np.arange(25),np.arange(49,124)].astype('int64'); d[f'draw_{i}']=ix
            assignments['adaptation_draws'][str(i)]={'primary_25_75':d['target_pool__ids'][ix].tolist()}
        return d,assignments
    def test_exact_original_memberships_checked_not_only_counts(self):
        d,a=self.fixture(); w.verify_memberships(d,a,self.trainer)
        a['source_partitions']['source_train'][0]='INVENTED_OTHER_ID'
        with self.assertRaises(w.Stop): w.verify_memberships(d,a,self.trainer)
    def test_invalid_draw_identity_rejected(self):
        d,a=self.fixture(); a['adaptation_draws']['0']['primary_25_75'][0]='INVENTED_OTHER_ID'
        with self.assertRaises(w.Stop): w.verify_memberships(d,a,self.trainer)
    def test_extra_test_field_rejected(self):
        d,a=self.fixture(); d['target_test__y']=self.np.zeros(1)
        with self.assertRaises(Exception): w.verify_memberships(d,a,self.trainer)


if __name__ == '__main__': unittest.main()
