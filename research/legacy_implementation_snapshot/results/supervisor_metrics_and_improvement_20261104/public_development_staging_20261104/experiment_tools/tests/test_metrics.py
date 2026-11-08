"""All data here are invented. Never reference a real private dataset."""
import copy,hashlib,json,os,sys,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from compute_classification_metrics import metrics,select_validation_threshold,summarize,validate_membership,load_inputs,analyze
from local_execution import Rejected,sha,write_json,exclusive_output,require_local

def fixture(tmp):
 y=np.r_[np.ones(21),np.zeros(262)].astype(int);ids=[f'SYNTHETIC_TEST_{i}' for i in range(283)];rng=np.random.default_rng(101);p=rng.uniform(0,1,(10,283))
 bp=tmp/'fake.npz';np.savez(bp,observed_labels=y,primary_25_75__calibrated_logical=p)
 ip=tmp/'ids.json';ip.write_text(json.dumps({'ordered_participant_ids':ids}))
 reg={'models':[{'method':'calibrated_logical','budget':'primary_25_75','repetition':i,'checkpoint_sha256':str(i)*64} for i in range(10)]};rp=tmp/'reg.json';rp.write_text(json.dumps(reg))
 m={'status':'RECOVERY_COMPLETE_AFTER_FAILED_ORIGINAL_ATTEMPT','registration_sha256':sha(rp),'no_fitting_performed':True,'test_participants':283,'test_positive_reports':21,'private_prediction_bundle_sha256':sha(bp),'private_ids_sha256':sha(ip)};mp=tmp/'receipt.json';mp.write_text(json.dumps(m))
 rows=[metrics(y,x) for x in p];refs={'models':{'calibrated_logical':{k:{'mean':float(np.mean([r[k] for r in rows])),'per_draw':[r[k] for r in rows]} for k in ['ap','auroc','brier']}}};fp=tmp/'refs.json';fp.write_text(json.dumps(refs))
 d=lambda x:{'path':str(x),'sha256':sha(x)}
 c={'schema':'supplementary-classification-v1','probability_ensemble':False,'ddof':1,'fixed_threshold':.5,'absolute_tolerance':1e-8,'relative_tolerance':1e-8,'registration':d(rp),'completed_manifest':d(mp),'public_references':d(fp),'predictions':{'path':str(bp),'labels_key':'observed_labels'},'ids':{'path':str(ip),'ordered_ids_key':'ordered_participant_ids'},'models':[{'model_id':'calibrated_logical','budget':'primary_25_75','array_key':'primary_25_75__calibrated_logical','draw_ids':list(range(10)),'checkpoint_sha256_by_draw':{str(i):str(i)*64 for i in range(10)}}],'validation_threshold':None}
 return c,y,p,refs

def test_hand_calculated():
 r=metrics([1,1,0,0],[.9,.4,.6,.1]);assert [r[k] for k in ['TP','TN','FP','FN']]==[1,1,1,1]
 for k in ['accuracy','precision','recall','specificity','f1','FPR','FNR','NPV','balanced_accuracy']:assert r[k]==.5
 assert r['MCC']==0 and r['auroc']==.75 and r['ap']==pytest.approx(5/6) and r['brier']==pytest.approx(.185)
@pytest.mark.parametrize('y,p', [([],[]),([1],[2]),([1],[-.1]),([1],[float('nan')]),([1],[float('inf')]),([.2],[.5]),([None],[.5]),([[1]],[[.5]]),([1,0],[.5])])
def test_invalid_vectors(y,p):
 with pytest.raises((Rejected,TypeError)):metrics(y,p)
@pytest.mark.parametrize('t',[float('nan'),float('inf'),-.1,1.1])
def test_threshold_validation(t):
 with pytest.raises(Rejected):metrics([1,0],[.5,.5],t)
def test_threshold_boundary():assert metrics([1,0],[.5,.5])['TP']==1
def test_no_predicted_positive():
 r=metrics([1,0],[.1,.2]);assert r['precision'] is None and r['f1']==0 and r['MCC'] is None and r['recall']==0
def test_no_predicted_negative():assert metrics([1,0],[.9,.8])['NPV'] is None
def test_single_class():
 r=metrics([0,0],[0,0]);assert r['ap'] is None and r['auroc'] is None and r['f1'] is None and r['recall'] is None
 assert metrics([1,1],[1,1])['specificity'] is None
def test_constant_scores_ap():assert metrics([1,0,0,0],[.2]*4)['ap']==.25
def test_monotonic_shift_changes_cm_not_ranking():
 y=[1,1,0,0];p=np.array([.4,.3,.2,.1]);a=metrics(y,p);b=metrics(y,p+.3)
 assert a['TP']!=b['TP'] and a['ap']==b['ap'] and a['auroc']==b['auroc']
def test_validation_threshold_tie_highest():assert select_validation_threshold([1,0],[.4,.1])==.4
def test_validation_single_class_rejected():
 with pytest.raises(Rejected):select_validation_threshold([0,0],[.2,.3])
def test_summary_undefined_not_zero():
 r=summarize([metrics([1,0],[.1,.2]),metrics([1,0],[.9,.8])]);assert r['precision']['n_undefined']==1 and r['precision']['mean']==.5
 assert r['TP']['sd']==pytest.approx(2**-.5)
def test_membership_counts():
 with pytest.raises(Rejected):validate_membership(['X']*283,np.r_[np.ones(21),np.zeros(262)])
def test_wrong_event_count():
 with pytest.raises(Rejected):validate_membership([str(i) for i in range(283)],np.zeros(283))
def test_real_bindings_reject_invented(tmp_path):
 c,*_=fixture(tmp_path)
 with pytest.raises(Rejected):load_inputs(c)
def test_valid_synthetic_bound_bundle(tmp_path):
 c,*_=fixture(tmp_path);y,models,ts,refs=load_inputs(c,True);r=analyze(y,models,ts,refs,True)
 assert r['distinct_test_participants']==283 and r['models']['calibrated_logical']['draw_count']==10
 for x in r['models']['calibrated_logical']['fixed_0_50']['per_draw']:assert x['TP']+x['FN']==21 and x['TN']+x['FP']==262
@pytest.mark.parametrize('field,value',[('ddof',0),('fixed_threshold',.3),('probability_ensemble',True),('absolute_tolerance',.1)])
def test_contract_mutations(tmp_path,field,value):
 c,*_=fixture(tmp_path);c[field]=value
 with pytest.raises(Rejected):load_inputs(c,True)
def test_payload_tamper(tmp_path):
 c,*_=fixture(tmp_path);Path(c['predictions']['path']).write_bytes(b'private sensitive failure string')
 with pytest.raises(Rejected):load_inputs(c,True)
def test_id_payload_tamper(tmp_path):
 c,*_=fixture(tmp_path);Path(c['ids']['path']).write_text('different')
 with pytest.raises(Rejected):load_inputs(c,True)
def test_checkpoint_mismatch(tmp_path):
 c,*_=fixture(tmp_path);c['models'][0]['checkpoint_sha256_by_draw']['0']='f'*64
 with pytest.raises(Rejected):load_inputs(c,True)
def test_missing_draw(tmp_path):
 c,*_=fixture(tmp_path);c['models'][0]['draw_ids'].pop()
 with pytest.raises(Rejected):load_inputs(c,True)
def test_probabilities_wrong_order_reconciliation(tmp_path):
 c,y,p,refs=fixture(tmp_path)
 with pytest.raises(Rejected):analyze(y,{'calibrated_logical':p[::-1]}, {},refs,True)
def test_mean_probabilities_not_accepted_as_ten_draws(tmp_path):
 c,y,p,refs=fixture(tmp_path);path=Path(c['predictions']['path']);np.savez(path,observed_labels=y,primary_25_75__calibrated_logical=p.mean(0))
 mp=Path(c['completed_manifest']['path']);m=json.loads(mp.read_text());m['private_prediction_bundle_sha256']=sha(path);mp.write_text(json.dumps(m));c['completed_manifest']['sha256']=sha(mp)
 with pytest.raises(Rejected):load_inputs(c,True)
def test_invalid_mean_reference_fails(tmp_path):
 c,y,p,refs=fixture(tmp_path);refs['models']['calibrated_logical']['ap']['mean']+=.01
 with pytest.raises(Rejected):analyze(y,{'calibrated_logical':p},{},refs,True)
def test_agent_environment_rejected_before_read():
 with patch.dict(os.environ,{'CODEX_THREAD_ID':'invented'}):
  with pytest.raises(Rejected):require_local()
def test_output_exclusivity_and_permissions(tmp_path):
 out=tmp_path/'new'
 with exclusive_output(out,False):write_json(out/'private.json',{'invented':True})
 assert out.stat().st_mode&0o777==0o700 and (out/'private.json').stat().st_mode&0o777==0o600
 with pytest.raises(Rejected):
  with exclusive_output(out,False):pass
def test_interruption_consumed(tmp_path):
 out=tmp_path/'interrupted'
 with pytest.raises(KeyboardInterrupt):
  with exclusive_output(out,False):raise KeyboardInterrupt()
 assert json.loads((out/'completion.private.json').read_text())['status']=='INTERRUPTED_NO_RETRY'
def test_unexpected_exception_no_sensitive_context_in_receipt(tmp_path):
 out=tmp_path/'failed'
 with pytest.raises(RuntimeError):
  with exclusive_output(out,False):raise RuntimeError('SECRET_SYNTHETIC_IDENTIFIER')
 assert 'SECRET' not in (out/'completion.private.json').read_text()
def test_report_svg_and_na(tmp_path):
 from render_metrics_report import render
 rows=[metrics([1,0],[.1,.2])]*10
 report={'analysis':'SYNTHETIC_ONLY','distinct_test_participants':2,'models':{'invented':{'fixed_0_50':{'per_draw':rows,'summary':summarize(rows)}}}}
 render(report,tmp_path);s=(tmp_path/'SUPERVISOR_CLASSIFICATION_METRICS.private.md').read_text()
 assert 'N/A' in s and 'not a single confusion matrix' in s and len(list(tmp_path.glob('*.svg')))==11

def attach_validation(tmp,c,overlap=False):
    vy=np.r_[np.ones(13),np.zeros(158)].astype(int);vids=[f'SYNTHETIC_VALIDATION_{i}' for i in range(171)];vids[0]='SYNTHETIC_TEST_0' if overlap else vids[0]
    vp=tmp/'val.npz';np.savez(vp,labels=vy,ids=np.asarray(vids),scores=np.tile(np.linspace(.8,.1,171),(10,1)))
    vm={'role':'target_validation','origin':'retained_original_development_predictions','payload_sha256':sha(vp),'registration_sha256':c['registration']['sha256'],'checkpoints':{'calibrated_logical':c['models'][0]['checkpoint_sha256_by_draw']}}
    mp=tmp/'valmanifest.json';mp.write_text(json.dumps(vm));c['validation_threshold']={'rule':'validation_f1_highest_threshold_tie','payload':{'path':str(vp),'sha256':sha(vp)},'provenance':{'path':str(mp),'sha256':sha(mp)},'ids_key':'ids','labels_key':'labels','model_keys':{'calibrated_logical':'scores'}}
    return c

def test_validation_threshold_uses_disjoint_original_scores(tmp_path):
 c,*_=fixture(tmp_path);c=attach_validation(tmp_path,c);y,m,ts,r=load_inputs(c,True);assert len(ts['calibrated_logical'])==10
 report=analyze(y,m,ts,r,True);item=report['models']['calibrated_logical'];assert 'validation_f1' in item
 for a,b in zip(item['fixed_0_50']['per_draw'],item['validation_f1']['per_draw']):assert [a[k] for k in ['ap','auroc','brier']]==[b[k] for k in ['ap','auroc','brier']]
def test_validation_test_overlap_rejected(tmp_path):
 c,*_=fixture(tmp_path);c=attach_validation(tmp_path,c,True)
 with pytest.raises(Rejected):load_inputs(c,True)
def test_validation_wrong_role_rejected(tmp_path):
 c,*_=fixture(tmp_path);c=attach_validation(tmp_path,c);d=c['validation_threshold']['provenance'];p=Path(d['path']);j=json.loads(p.read_text());j['role']='target_test';p.write_text(json.dumps(j));d['sha256']=sha(p)
 with pytest.raises(Rejected):load_inputs(c,True)
def test_validation_checkpoint_change_rejected(tmp_path):
 c,*_=fixture(tmp_path);c=attach_validation(tmp_path,c);d=c['validation_threshold']['provenance'];p=Path(d['path']);j=json.loads(p.read_text());j['checkpoints']['calibrated_logical']['0']='bad';p.write_text(json.dumps(j));d['sha256']=sha(p)
 with pytest.raises(Rejected):load_inputs(c,True)
def test_cli_agent_refusal_discloses_no_path(tmp_path):
 import subprocess
 root=Path(__file__).resolve().parents[1]
 for script in ['compute_classification_metrics.py','train_exploratory_candidates.py','prepare_development_inputs.py']:
  e=dict(os.environ,CODEX_THREAD_ID='synthetic_agent')
  r=subprocess.run([sys.executable,'-B',str(root/script),'--execute-local','--config',str(tmp_path/'SECRET_PATH'),'--authorization',str(tmp_path/'SECRET_AUTH'),'--output',str(tmp_path/'SECRET_OUTPUT')],env=e,text=True,capture_output=True)
  assert r.returncode==2 and 'SECRET' not in r.stdout+r.stderr and not (tmp_path/'SECRET_OUTPUT').exists()
def test_symlink_input_rejected(tmp_path):
 from local_execution import descriptor
 q=tmp_path/'real';q.write_text('invented');p=tmp_path/'link';p.symlink_to(q)
 with pytest.raises(Rejected):descriptor({'path':str(p),'sha256':sha(q)})


def test_missing_retained_predictions_report_unavailable_without_loading(tmp_path):
 c,*_=fixture(tmp_path);Path(c['predictions']['path']).unlink()
 with patch('compute_classification_metrics.np.load',side_effect=AssertionError('must not load')):
  with pytest.raises(Rejected,match='RETAINED_PREDICTIONS_OR_IDS_UNAVAILABLE'):load_inputs(c,True)

def test_even_ap_auroc_and_brier_together_do_not_identify_confusion_counts():
 # Invented mathematical counterexample; no relation to real model scores.
 y=[1,0];a=metrics(y,[.6,.7]);b=metrics(y,[.4,float(np.sqrt(.29))])
 for key in ['ap','auroc','brier']:assert a[key]==pytest.approx(b[key])
 assert [a[k] for k in ['TP','TN','FP','FN']]!=[b[k] for k in ['TP','TN','FP','FN']]
