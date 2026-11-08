"""Invented arrays only. No clinical data, old predictions or private files."""
import copy,json,os,sys,subprocess
from pathlib import Path
import numpy as np
import pytest
import torch
ROOT=Path(__file__).resolve().parents[1]
for folder in (ROOT,ROOT/'src',ROOT/'vendor'):sys.path.insert(0,str(folder))
from fasttrack.synthetic import fixtures,demo
from fasttrack.contracts import validate,DEV_ROLES,membership,split_indices
from fasttrack.preprocessing import BaselinePreprocessor
from fasttrack.metrics import metrics,OperatingPoint,paired_bootstrap
from fasttrack.models import fit,device_checked,weight_hash,set_selective_trainability,snapshot_frozen,frozen_unchanged
from fasttrack.pipeline import development,evaluation
from fasttrack import runtime
from dmv_mat_cvd.models.multiview_mlp import MultiViewRiskNet
import local_execution as local
from release import verify,install

@pytest.fixture
def invented():
    data,manifests,flows=fixtures()
    dev={k:v for k,v in data.items() if not k.startswith('target_test__')}
    test={k:v for k,v in data.items() if k.startswith('target_test__')}
    return dev,test,manifests,flows

def test_valid_contract_and_outcome_blind_splits(invented):
    dev,test,m,_=invented
    assert validate(dev,DEV_ROLES,m['development'])
    ids=np.array(['ELSA_INVENTED_'+str(i) for i in range(50)])
    a=split_indices(ids,{'fit':.7,'test':.3});b=split_indices(ids,{'fit':.7,'test':.3})
    assert np.array_equal(a['fit'],b['fit']) and not set(a['fit'])&set(a['test'])
    assert set(dev).isdisjoint(test)

@pytest.mark.parametrize('problem',['extra_test','duplicate','unknown_outcome','future','category','feature_order','endpoint','membership'])
def test_invalid_inputs_fail_closed(invented,problem):
    dev,test,m,_=invented;dev=copy.deepcopy(dev);manifest=copy.deepcopy(m['development'])
    if problem=='extra_test':dev['target_test__y']=test['target_test__y']
    elif problem=='duplicate':dev['target_fit__ids'][0]=dev['target_stop__ids'][0]
    elif problem=='unknown_outcome':dev['target_fit__y'][0]=-1
    elif problem=='future':dev['target_fit__availability'][0,0]=False
    elif problem=='category':dev['target_fit__x'][0,5]=3
    elif problem=='feature_order':manifest['feature_names']=list(reversed(manifest['feature_names']))
    elif problem=='endpoint':manifest['source_endpoint']='STRICT_NEGATIVES_INVENTED'
    else:manifest['roles']['target_fit']['membership_sha256']='0'*64
    with pytest.raises(ValueError):validate(dev,DEV_ROLES,manifest)

def test_source_only_preprocessing_and_wholly_missing(invented):
    dev,_,_,_=invented
    pre=BaselinePreprocessor().fit(dev['source_train__x'],'source_train')
    saved=pre.fill.copy();pre.transform(dev['target_validation__x']*2)
    assert np.array_equal(saved,pre.fill)
    assert [v.shape[1] for v in pre.transform(dev['source_train__x']).values()]==[4,4,2,4,4]
    with pytest.raises(ValueError):pre.fit(dev['target_validation__x'],'target_validation')
    missing=dev['source_train__x'].copy();missing[:,2]=np.nan
    with pytest.raises(ValueError):BaselinePreprocessor().fit(missing,'source_train')

def test_metric_counts_and_single_class():
    y=np.array([1,1,0,0]);p=np.array([.8,.1,.7,.2]);m=metrics(y,p)
    assert [m[k] for k in ('tp','tn','fp','fn')]==[1,1,1,1]
    assert m['f1']==m['recall']==m['precision']==m['specificity']==.5
    zeros=metrics(y,np.zeros(4));assert zeros['recall']==0 and zeros['precision'] is None
    assert metrics(np.zeros(4),p)['ap'] is None and metrics(np.ones(4),p)['auroc'] is None

def test_calibration_roles_and_support():
    y=np.array([0,0,0,1]);p=np.array([.1,.2,.3,.4])
    with pytest.raises(ValueError):OperatingPoint().fit(y,p,'target_test')
    point=OperatingPoint().fit(y,p,'target_calibration')
    assert point.threshold is None and point.report(y,p)['metrics'] is None
    y=np.r_[np.zeros(20),np.ones(20)];p=np.linspace(.1,.9,40)
    point=OperatingPoint().fit(y,p,'target_calibration');t=point.threshold
    point.report(1-y,p);assert point.threshold==t

def test_freezing_and_optimizer_membership(invented):
    dev,_,_,_=invented;pre=BaselinePreprocessor().fit(dev['source_train__x'],'source_train')
    views=pre.transform(dev['target_fit__x']);stop=pre.transform(dev['target_stop__x'])
    model=MultiViewRiskNet({k:v.shape[1] for k,v in views.items()})
    mask={k:False for k in model.selectable_modules()};set_selective_trainability(model,mask)
    before=snapshot_frozen(model,mask)
    fit(model,views,dev['target_fit__y'],stop,dev['target_stop__y'],train_role='target_fit',stop_role='target_stop',epochs=2,lr=.001,patience=2,seed=7,device=torch.device('cpu'),epoch_zero=True)
    assert frozen_unchanged(model,before)[0]
    assert sum(p.numel() for p in model.parameters() if p.requires_grad)==33
    with pytest.raises(ValueError):fit(model,views,dev['target_fit__y'],stop,dev['target_stop__y'],train_role='target_test',stop_role='target_stop',epochs=1,lr=.001,patience=1,seed=7,device=torch.device('cpu'),epoch_zero=True)

def test_epoch_zero_restoration_with_tiny_update(invented):
    dev,_,_,_=invented;pre=BaselinePreprocessor().fit(dev['source_train__x'],'source_train')
    views=pre.transform(dev['target_fit__x']);stop=pre.transform(dev['target_stop__x'])
    model=MultiViewRiskNet({k:v.shape[1] for k,v in views.items()});before=weight_hash(model)
    tr=fit(model,views,dev['target_fit__y'],stop,dev['target_stop__y'],train_role='target_fit',stop_role='target_stop',epochs=1,lr=1e-30,patience=1,seed=7,device=torch.device('cpu'),epoch_zero=True)
    assert tr['selected_epoch']==0 and weight_hash(model)==before

def test_synthetic_end_to_end_and_deterministic_rerun(tmp_path):
    config=json.loads((ROOT/'configs/synthetic_demo.json').read_text());config.update(source_epochs=2,target_epochs=2,tree_iterations=5,bootstrap_resamples=25)
    a=demo(tmp_path/'FIRST_INVENTED',config);b=demo(tmp_path/'SECOND_INVENTED',config)
    assert a==b
    assert len(a['methods'])==7 and a['test_thresholds_changed'] is False
    d=json.loads((tmp_path/'FIRST_INVENTED/development/development.private.json').read_text())
    assert d['target_test_accessed'] is False
    assert d['total_target_labels_consumed']==sum(d['target_label_accounting'].values())
    for method in ('head','full','selective'):assert d['training_traces'][method]['shared_parameters_unchanged']
    with pytest.raises(FileExistsError):demo(tmp_path/'FIRST_INVENTED',config)

def test_test_overlap_and_artifact_mismatch_block(invented,tmp_path):
    dev,test,m,_=invented
    config=json.loads((ROOT/'configs/synthetic_demo.json').read_text());config.update(source_epochs=1,target_epochs=1,tree_iterations=3)
    out=tmp_path/'DEVELOPMENT';out.mkdir();development(dev,m['development'],config,out,True)
    frozen=json.loads((out/'freeze.private.json').read_text())
    bad=copy.deepcopy(test);bad['target_test__ids'][0]=dev['target_fit__ids'][0]
    meta=copy.deepcopy(m['evaluation']);meta['roles']['target_test']['membership_sha256']=membership(bad['target_test__ids'])
    with pytest.raises(ValueError,match='TEST_DEVELOPMENT_OVERLAP'):evaluation(bad,meta,out/'frozen_models.private.joblib',frozen,config,tmp_path,True)
    frozen['artifact_sha256']='0'*64
    with pytest.raises(ValueError):evaluation(test,m['evaluation'],out/'frozen_models.private.joblib',frozen,config,tmp_path,True)

def test_paired_bootstrap_single_class_unavailable():
    r=paired_bootstrap(np.zeros(20),{'full':np.full(20,.1),'selective':np.full(20,.2)},25,1)
    assert r['valid_resamples']==0 and r['paired_selective_minus_full_AP_95_interval'] is None

def test_real_config_templates_blocked_before_data(monkeypatch):
    monkeypatch.setattr(runtime,'require_local',lambda:None)
    c=json.loads((ROOT/'configs/development.template.json').read_text())
    monkeypatch.setattr(runtime,'descriptor',lambda _:pytest.fail('Private artifact accessed before scope gate'))
    with pytest.raises(local.Rejected,match='NEW_OPERATION_SCOPE_REQUIRED'):runtime.metadata_preflight(c)

@pytest.mark.parametrize('mode',['--preflight','--authorize-local','--execute-local'])
def test_agent_guards_before_private_configuration(mode):
    r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/run_experiment.py'),mode,'--config','/INVENTED_NOT_READ'],env={**os.environ,'CODEX_SESSION_ID':'INVENTED_AGENT'},text=True,capture_output=True)
    assert r.returncode==2 and '/INVENTED' not in r.stdout+r.stderr and not r.stderr

def test_old_authorization_and_consumed_output_rejected(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(local,'require_local',lambda:None)
    auth=tmp_path/'INVENTED_AUTH';local.write_json(auth,{'purpose':'OLD_COUNT_PURPOSE'})
    out=tmp_path/'INVENTED_OUTPUT'
    monkeypatch.setattr(sys,'argv',['invented','--execute-local','--config','INVENTED_CONFIG','--authorization',str(auth),'--output',str(out)])
    assert local.cli('hrs_elsa_fasttrack_development_v1_20261106',lambda *_:pytest.fail('Old authority processed data'),lambda _:None)==2
    assert not out.exists()
    with pytest.raises(KeyboardInterrupt):
        with local.exclusive_output(out,False):raise KeyboardInterrupt()
    with pytest.raises(local.Rejected):
        with local.exclusive_output(out,False):pass

def test_public_installation_and_integrity(tmp_path):
    target=tmp_path/'NEW_PUBLIC_TOOLS';install(target);verify(target)
    with pytest.raises(ValueError):install(target)
    (target/'configs/training_protocol.json').write_text('INVENTED_TAMPER')
    with pytest.raises(ValueError):verify(target)

@pytest.mark.skipif(not torch.backends.mps.is_available(),reason='MPS not available in this session')
def test_mps_forward_backward(invented):
    dev,_,_,_=invented;p=BaselinePreprocessor().fit(dev['source_train__x'],'source_train');views=p.transform(dev['source_train__x'])
    model=MultiViewRiskNet({k:v.shape[1] for k,v in views.items()}).to('mps')
    value=model({k:torch.tensor(v[:5],device='mps') for k,v in views.items()}).sum();value.backward()
    assert model.head.weight.grad is not None

def test_unavailable_mps_fails_without_cpu_substitution():
    if not torch.backends.mps.is_available():
        with pytest.raises(ValueError,match='MPS_UNAVAILABLE'):device_checked('mps')

def test_extra_test_array_rejected_before_any_payload_read(monkeypatch):
    from fasttrack.contracts import load_bundle
    class FakeArchive:
        files=['target_test__y']
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def __getitem__(self,key):pytest.fail('Test payload was dereferenced in development')
    monkeypatch.setattr(np,'load',lambda *a,**kw:FakeArchive())
    with pytest.raises(ValueError,match='EXTRA_OR_MISSING_INPUT_ARRAYS'):load_bundle('INVENTED',DEV_ROLES)

def test_read_only_metadata_preflight_never_opens_participant_arrays(invented,tmp_path,monkeypatch):
    from fasttrack.contracts import SOURCE_ENDPOINT,TARGET_ENDPOINT
    dev,test,m,_=invented
    input_file=tmp_path/'INVENTED_NOT_OPENED.npz';input_file.write_bytes(b'INVENTED_ARRAY_SENTINEL')
    manifest=copy.deepcopy(m['development']);manifest.update(synthetic_only=False,data_sha256=local.sha(input_file))
    mf=tmp_path/'INVENTED_MANIFEST.json';local.write_json(mf,manifest)
    evidence={}
    for name in runtime.EVIDENCE:
        f=tmp_path/(name+'.json');local.write_json(f,{'scope':'INVENTED_METADATA_FIXTURE_NOT_REAL_APPROVAL'})
        evidence[name]={'path':str(f),'sha256':local.sha(f)}
    ready={'schema':'hrs-elsa-independent-readiness-v1','source_endpoint':SOURCE_ENDPOINT,'target_endpoint':TARGET_ENDPOINT,
           'approved_manifest_sha256':local.sha(mf),'evidence':evidence,**{g:True for g in runtime.GATES}}
    rp=tmp_path/'INVENTED_READINESS.json';local.write_json(rp,ready)
    c=json.loads((ROOT/'configs/development.template.json').read_text());c.update(source_use_review='INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION',
        data={'path':str(input_file),'sha256':local.sha(input_file)},manifest={'path':str(mf),'sha256':local.sha(mf)},
        readiness={'path':str(rp),'sha256':local.sha(rp)})
    monkeypatch.setattr(runtime,'require_local',lambda:None)
    original=Path.open
    def guard(p,*a,**kw):
        assert p!=input_file,'Metadata preflight read participant bytes'
        return original(p,*a,**kw)
    monkeypatch.setattr(Path,'open',guard)
    assert runtime.metadata_preflight(c)['roles']==manifest['roles']
    c['data']['sha256']='0'*64
    with pytest.raises(local.Rejected):runtime.metadata_preflight(c)

def test_preprocessing_does_not_use_target_statistics(invented):
    dev,_,_,_=invented
    pre=BaselinePreprocessor().fit(dev['source_train__x'],'source_train')
    before=(pre.fill.copy(),pre.mean.copy(),pre.scale.copy())
    extreme=dev['target_fit__x'].copy();extreme[:,0]=10000
    pre.transform(extreme)
    assert all(np.array_equal(a,b) for a,b in zip(before,(pre.fill,pre.mean,pre.scale)))

def test_unknown_classifications_never_relabelled_negative(invented):
    dev,_,m,_=invented
    dev=copy.deepcopy(dev);dev['target_calibration__y']=dev['target_calibration__y'].astype(float)
    dev['target_calibration__y'][0]=np.nan
    with pytest.raises(ValueError,match='UNKNOWN_OR_NONBINARY_OUTCOME'):validate(dev,DEV_ROLES,m['development'])

def test_source_vendor_and_frozen_runtime_bytes_preserved():
    ledger=json.loads((ROOT/'PRESERVATION_BINDINGS.json').read_text())
    for name,pin in ledger.items():
        if name.startswith('src/dmv_mat_cvd/'):
            target=ROOT/'vendor/dmv_mat_cvd'/name[len('src/dmv_mat_cvd/'):]
        else:target=ROOT/'local_execution.py'
        assert local.sha(target)==pin

def test_same_person_role_stays_fixed_when_window_population_changes():
    ids=np.array(['ELSA_INVENTED_'+str(i) for i in range(50)])
    fractions={'fit':.4,'stop':.1,'calibration':.1,'validation':.1,'test':.3}
    first=split_indices(ids,fractions)
    larger=np.r_[ids,['ELSA_INVENTED_EXTRA_'+str(i) for i in range(50)]]
    second=split_indices(larger,fractions)
    lookup=lambda values,parts:{str(values[i]):role for role,ix in parts.items() for i in ix}
    a,b=lookup(ids,first),lookup(larger,second)
    assert all(a[str(key)]==b[str(key)] for key in ids)

def test_evaluation_artifacts_verified_before_test_payload(monkeypatch,tmp_path):
    monkeypatch.setattr(runtime,'metadata_preflight',lambda _: {})
    freeze=tmp_path/'INVENTED_FREEZE.json';local.write_json(freeze,{'artifact_sha256':'0'*64})
    artifact=tmp_path/'INVENTED_ARTIFACT';artifact.write_bytes(b'INVENTED_ONLY')
    c={'phase':'evaluation','device':'cpu','freeze':{'path':str(freeze),'sha256':local.sha(freeze)},
       'artifact':{'path':str(artifact),'sha256':'0'*64}}
    monkeypatch.setattr(runtime,'load_bundle',lambda *_:pytest.fail('Test payload opened before registered artifact verified'))
    with pytest.raises(local.Rejected,match='FILE_BINDING_MISMATCH'):runtime.execute(c,tmp_path)

def test_validation_codes_are_allowlisted_not_private_error_text(monkeypatch,tmp_path):
    monkeypatch.setattr(runtime,'metadata_preflight',lambda _: {})
    data=tmp_path/'INVENTED_DATA';data.write_bytes(b'invented')
    c={'phase':'development','device':'cpu','data':{'path':str(data),'sha256':local.sha(data)}}
    def fixed(*_):raise ValueError('EXTRA_OR_MISSING_INPUT_ARRAYS')
    monkeypatch.setattr(runtime,'load_bundle',fixed)
    with pytest.raises(local.Rejected,match='DEVELOPMENT_EXTRA_OR_MISSING_INPUT_ARRAYS'):runtime.execute(c,tmp_path)
    def sensitive(*_):raise ValueError('ELSA_PRIVATE_PARTICIPANT_TEXT')
    monkeypatch.setattr(runtime,'load_bundle',sensitive)
    with pytest.raises(local.Rejected) as e:runtime.execute(c,tmp_path)
    assert e.value.code=='DEVELOPMENT_UNCLASSIFIED_INPUT_OR_LIBRARY_ERROR'
