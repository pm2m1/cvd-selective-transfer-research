"""All arrays, identifiers and metadata below are invented synthetic fixtures."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import threshold_sweep as tool
import sweep_analysis as analysis
import frozen_metrics as frozen
import local_execution as local
from invented import fixture,validation,pin_invented,write,descriptor


@pytest.fixture(autouse=True)
def invented_local_boundary(monkeypatch):
    # Direct calls are only against temporary invented files. Child processes
    # retain the real guard; no production artifact or permission is substituted.
    monkeypatch.setattr(local,'require_local',lambda:None)


def test_complete_grid_ten_draws_shared_population(tmp_path):
    c,y,models,refs=fixture(tmp_path)
    result=analysis.analyze(y,models,{k:None for k in models},refs,c['models'],True)
    assert result['threshold_grid']==[.05,.10,.15,.20,.25,.30,.35,.40,.45,.50]
    assert result['distinct_test_participants']==283 and result['positive_reports']==21 and result['negative_observations']==262
    assert result['test_threshold_selected'] is False and result['validation_status']==analysis.UNESTABLISHED
    for name,item in result['models'].items():
        assert item['draw_count']==(1 if name=='source_multiview' else 10)
        for condition in item['fixed_test_thresholds']:
            for row in condition['per_draw']:
                assert row['TP']+row['FN']==21 and row['TN']+row['FP']==262
                assert all(type(row[k]) is int for k in ('TP','TN','FP','FN'))
                i=0 if row['draw_id']=='source' else row['draw_id']
                for k in ('ap','auroc','brier'):assert row[k]==refs['models'][name][k]['per_draw'][i]
        fixed=item['fixed_test_thresholds'][-1]
        for r,p in zip(fixed['per_draw'],models[name]):
            assert {k:v for k,v in r.items() if k!='draw_id'}==frozen.metrics(y,p,.5)


@pytest.mark.parametrize('metric',['ap','auroc','brier'])
@pytest.mark.parametrize('part',['mean','per_draw'])
def test_reconciliation_failure_before_report(metric,part,tmp_path):
    c,y,m,refs=fixture(tmp_path)
    if part=='mean':refs['models']['calibrated_logical'][metric]['mean']+=.01
    else:refs['models']['calibrated_logical'][metric]['per_draw'][0]+=.01
    with pytest.raises(local.Rejected,match='FROZEN_METRIC_RECONCILIATION_FAILED'):
        analysis.analyze(y,m,{},refs,c['models'],True)


def test_real_loader_rejects_invented_bindings(tmp_path):
    c,*_=fixture(tmp_path)
    with pytest.raises(local.Rejected,match='FROZEN_EVIDENCE_BINDING_MISMATCH'):tool.load_frozen(c)


def test_primary_score_reference_cannot_certify_a_secondary_budget(tmp_path):
    c,*_=fixture(tmp_path);c['models'][0]['budget']='low_label_10_30'
    with pytest.raises(local.Rejected,match='PRIMARY_REFERENCE_BUDGET_OR_DRAW_MISMATCH'):tool.load_frozen(c)


def test_no_test_threshold_optimizer_and_no_pooled_population(tmp_path,monkeypatch):
    c,y,m,refs=fixture(tmp_path)
    monkeypatch.setattr(frozen,'select_validation_threshold',lambda *_:pytest.fail('Test labels used for selection'))
    r=analysis.analyze(y,m,{},refs,c['models'],True)
    assert r['distinct_test_participants']==283 and r['test_threshold_selected'] is False
    assert r['models']['calibrated_logical']['draw_count']==10 and r['models']['source_multiview']['draw_count']==1
    rows=r['models']['calibrated_logical']['fixed_test_thresholds'][0]
    assert rows['summary']['f1']['sd']==pytest.approx(np.std([p['f1'] for p in rows['per_draw']],ddof=1))


def test_reordered_draw_scores_fail_full_precision_reconciliation(tmp_path):
    c,y,m,refs=fixture(tmp_path);m['calibrated_logical']=m['calibrated_logical'][::-1]
    with pytest.raises(local.Rejected,match='FROZEN_METRIC_RECONCILIATION_FAILED'):analysis.analyze(y,m,{},refs,c['models'],True)


def test_bound_test_loader_order_and_no_ensembling(tmp_path,monkeypatch):
    c,y,m,_=fixture(tmp_path);pin_invented(c,monkeypatch)
    loaded,models,ts,refs=tool.load_frozen(c)
    assert np.array_equal(y,loaded) and all(np.array_equal(m[k],models[k]) for k in m)
    assert all(v is None for v in ts.values())
    before=c['predictions']['path'];assert models['calibrated_logical'].shape==(10,283)
    assert frozen.sha(before)==json.loads(Path(c['completed_manifest']['path']).read_text())['private_prediction_bundle_sha256']


def test_metadata_preflight_never_reads_or_hashes_scores_or_ids(tmp_path,monkeypatch):
    c,*_=fixture(tmp_path);validation(tmp_path,c);original_sha=local.sha
    blocked={c['predictions']['path'],c['ids']['path'],c['validation_threshold']['payload']['path']}
    def sha(path):
        assert str(path) not in blocked,'Preflight read participant input bytes'
        return original_sha(path)
    monkeypatch.setattr(local,'sha',sha);monkeypatch.setattr(np,'load',lambda *_a,**_k:pytest.fail('Preflight opened arrays'))
    tool.metadata_preflight(c)


@pytest.mark.parametrize('problem',['ids_duplicate','wrong_positive_count','missing_draw','invalid_probability','wrong_width','wrong_checkpoint'])
def test_alignment_and_provenance_fail_closed(tmp_path,monkeypatch,problem):
    c,y,m,refs=fixture(tmp_path)
    if problem=='ids_duplicate':
        ip=Path(c['ids']['path']);v=json.loads(ip.read_text());v['ordered_participant_ids'][0]=v['ordered_participant_ids'][1];write(ip,v)
    elif problem=='wrong_checkpoint':c['models'][0]['checkpoint_sha256_by_draw']['0']='0'*64
    else:
        if problem=='wrong_positive_count':y[0]=0
        elif problem=='missing_draw':m['calibrated_logical']=m['calibrated_logical'][:9]
        elif problem=='invalid_probability':m['calibrated_logical'][0,0]=np.nan
        else:m['calibrated_logical']=m['calibrated_logical'][:,:282]
        with Path(c['predictions']['path']).open('wb') as f:np.savez_compressed(f,observed_labels=y,**{'primary_25_75__'+k:v for k,v in m.items()})
    mp=Path(c['completed_manifest']['path']);v=json.loads(mp.read_text());v.update(private_prediction_bundle_sha256=frozen.sha(c['predictions']['path']),private_ids_sha256=frozen.sha(c['ids']['path']));c['completed_manifest']=write(mp,v)
    pin_invented(c,monkeypatch)
    with pytest.raises((local.Rejected,ValueError)):tool.load_frozen(c)


def test_validation_selection_precedes_any_test_probability_read(tmp_path,monkeypatch):
    c,*_=fixture(tmp_path);validation(tmp_path,c);pin_invented(c,monkeypatch);before=copy.deepcopy(c)
    original_load=np.load;original_select=frozen.select_validation_threshold;events=[]
    def load(path,*args,**kw):
        if str(path)==c['predictions']['path']:
            assert len(events)==11 # ten adapted + one source selection before test load
        return original_load(path,*args,**kw)
    def select(y,p):
        assert len(y)==171 and int(y.sum())==13
        events.append('validation_only');return original_select(y,p)
    monkeypatch.setattr(np,'load',load);monkeypatch.setattr(frozen,'select_validation_threshold',select)
    y,m,ts,refs=tool.load_frozen(c)
    assert c==before and len(ts['calibrated_logical'])==10 and len(ts['source_multiview'])==1
    result=analysis.analyze(y,m,ts,refs,c['models'],True)
    assert result['models']['calibrated_logical']['validation_selected'] is not None


@pytest.mark.parametrize('problem',['overlap','wrong_role','wrong_origin','wrong_checkpoint','duplicate_ids','wrong_events','payload_hash'])
def test_untrusted_or_misaligned_validation_rejected(tmp_path,monkeypatch,problem):
    c,*_=fixture(tmp_path);validation(tmp_path,c,overlap=problem=='overlap');v=c['validation_threshold']
    vm_path=Path(v['provenance']['path']);vm=json.loads(vm_path.read_text())
    if problem=='wrong_role':vm['role']='target_test'
    elif problem=='wrong_origin':vm['origin']='new_model_predictions'
    elif problem=='wrong_checkpoint':vm['checkpoints']['calibrated_logical']['0']='0'*64
    elif problem=='payload_hash':v['payload']['sha256']='0'*64
    elif problem in ('duplicate_ids','wrong_events'):
        vp=Path(v['payload']['path'])
        with np.load(vp,allow_pickle=False) as z:arrays={k:z[k] for k in z.files if k!='UNSELECTED_OBJECT_ARRAY'}
        if problem=='duplicate_ids':arrays['original_ids'][0]=arrays['original_ids'][1]
        else:arrays['original_labels'][0]=0
        with vp.open('wb') as f:np.savez_compressed(f,**arrays)
        v['payload']=descriptor(vp);vm['payload_sha256']=v['payload']['sha256']
    v['provenance']=write(vm_path,vm);pin_invented(c,monkeypatch)
    with pytest.raises((local.Rejected,ValueError)):tool.load_frozen(c)


def test_partial_validation_explicitly_unavailable_for_other_models(tmp_path,monkeypatch):
    c,*_=fixture(tmp_path);validation(tmp_path,c,partial=True);pin_invented(c,monkeypatch)
    y,m,ts,refs=tool.load_frozen(c);r=analysis.analyze(y,m,ts,refs,c['models'],True)
    assert r['models']['source_multiview']['validation_status']==analysis.UNESTABLISHED
    assert r['models']['calibrated_logical']['validation_selected'] is not None


def test_f1_tie_highest_and_no_positive_predictions():
    assert frozen.select_validation_threshold([1,0],[.4,.1])==.4
    row=frozen.metrics([1,0],[.01,.02],.5)
    assert row['precision'] is None and row['recall']==0 and row['f1']==0 and row['balanced_accuracy']==.5
    assert frozen.metrics([1,0],[.05,.04],.05)['TP']==1


def test_prepare_reuses_recorded_configuration_without_score_reads(tmp_path,monkeypatch):
    tmp_path.chmod(0o700)
    original=json.loads((ROOT/'ORIGINAL_CONFIG_SCHEMA_REFERENCE.json').read_text())
    for k in ('registration','completed_manifest','predictions','ids'):original[k]['path']='/INVENTED_NOT_READ/'+k
    old=tmp_path/'INVENTED_ORIGINAL_050_OUTPUT';old.mkdir(mode=0o700)
    p=old/'provenance.private.json';write(p,{'config':original,'script_sha256':tool.LEGACY_SHA,'no_inference_performed':True,'no_new_fitting_performed':True})
    write(old/'completion.private.json',{'status':'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED','attempt_consumed':True})
    monkeypatch.setattr(np,'load',lambda *_a,**_k:pytest.fail('Preparation opened scores'))
    new=tmp_path/'INVENTED_NEW_RUN';new.mkdir(mode=0o700)
    out=new/'new_threshold_config.json';before=p.read_bytes()
    tool.prepare(p,'completed_metrics_provenance',out)
    c=json.loads(out.read_text());assert c['source_use_review']=='UNRESOLVED_NOT_AUTHORIZED' and c['reviewed_scope']==[] and c['original_validation'] is None
    assert p.read_bytes()==before and out.stat().st_mode&0o077==0
    with pytest.raises(local.Rejected):tool.validate_outer(c)
    c.update(source_use_review=tool.REVIEW,reviewed_scope=tool.SCOPE)
    used=tool.validate_outer(c);assert used['predictions']==original['predictions'] and used['ids']==original['ids'] and used['models']==original['models']
    with pytest.raises(local.Rejected):tool.prepare(p,'completed_metrics_provenance',out)
    with pytest.raises(local.Rejected,match='HISTORICAL_OUTPUT_MODIFICATION_REFUSED'):
        tool.prepare(p,'completed_metrics_provenance',old/'BAD_OLD_OUTPUT_CONFIG.json')


@pytest.mark.parametrize('change',[{'thresholds':[.1,.2]},{'no_inference':False},{'reviewed_scope':[]},{'validation_policy':'TEST_F1_MAX'}])
def test_protocol_changes_rejected(change):
    c=json.loads((ROOT/'threshold_config.template.json').read_text());c.update(change)
    with pytest.raises(local.Rejected):tool.validate_outer(c)


def test_render_only_integer_per_draw_matrices_and_private_files(tmp_path):
    from threshold_report import render,confusion
    import matplotlib.pyplot as plt
    c,y,m,refs=fixture(tmp_path/'inputs');name='source_multiview'
    r=analysis.analyze(y,{name:m[name]},{name:None},{'models':{name:refs['models'][name]}},[x for x in c['models'] if x['model_id']==name],True)
    out=tmp_path/'new_report';out.mkdir(mode=0o700);render(r,out)
    assert len(list((out/'confusion_matrices').rglob('*.svg')))==10
    assert len(list((out/'summary_plots').glob('*.png')))==2
    body=(out/'SUPERVISOR_THRESHOLD_COMPARISON.private.md').read_text()
    assert 'SYNTHETIC DATA ONLY' in body and analysis.UNESTABLISHED in body and 'not one realized matrix' in body
    assert 'INVENTED_MHAS_TEST_' not in body
    assert all(p.stat().st_mode&0o077==0 for p in out.rglob('*'))
    with pytest.raises(local.Rejected):confusion(plt,{'TN':1.5,'FP':0.5,'FN':1.5,'TP':0.5},'not allowed',out/'BAD.svg')


def test_existing_and_interrupted_outputs_are_consumed(tmp_path):
    out=tmp_path/'INVENTED_USED'
    with pytest.raises(KeyboardInterrupt):
        with local.exclusive_output(out,False):raise KeyboardInterrupt()
    assert json.loads((out/'completion.private.json').read_text())['status']=='INTERRUPTED_NO_RETRY'
    with pytest.raises(local.Rejected):
        with local.exclusive_output(out,False):pass


def test_old_authorization_cannot_start_new_analysis(tmp_path,monkeypatch,capsys):
    cfg=tmp_path/'INVENTED_CONFIG.json';write(cfg,{'mode':'independent_local_only'})
    auth=tmp_path/'INVENTED_OLD_AUTH.json';write(auth,{'purpose':frozen.PURPOSE,'authorized':True})
    out=tmp_path/'INVENTED_NEVER_CREATED'
    monkeypatch.setattr(sys,'argv',['threshold_sweep.py','--execute-local','--config',str(cfg),'--authorization',str(auth),'--output',str(out)])
    assert local.cli(tool.PURPOSE,lambda *_:pytest.fail('Old authorization reached data'),lambda *_:None)==2
    assert not out.exists() and 'INVENTED' not in capsys.readouterr().out


def test_all_negative_fixed_predictions_and_constant_scores_are_honest():
    y=np.r_[np.ones(21),np.zeros(262)];p=np.full(283,.04);row=frozen.metrics(y,p,.05)
    assert row['TP']==0 and row['FN']==21 and row['FP']==0 and row['TN']==262
    assert row['precision'] is None and row['f1']==0 and row['recall']==0 and row['accuracy']==pytest.approx(262/283)
    assert row['ap']==pytest.approx(21/283) and row['auroc']==.5


@pytest.mark.parametrize('mode',['--preflight','--execute-local','--authorize-local'])
def test_agent_guard_and_no_private_values(mode):
    p=subprocess.run([sys.executable,'-B',str(ROOT/'threshold_sweep.py'),mode,'--config','/INVENTED_SECRET_CONFIG.json'],
        env={**os.environ,'CODEX_THREAD_ID':'INVENTED_AGENT'},capture_output=True,text=True)
    assert p.returncode==2 and 'INVENTED_SECRET' not in p.stdout+p.stderr and not p.stderr
