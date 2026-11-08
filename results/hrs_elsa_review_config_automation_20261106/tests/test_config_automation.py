"""Temporary invented JSON only; all original private artifacts stay untouched."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import prepare_offline_review_config as h
from synthetic_history import case,TOOLS


@pytest.fixture(autouse=True)
def invented_boundary_only(monkeypatch):
    # Direct API calls below use only newly invented temporary records. Child
    # process tests retain the genuine independent/agent/TTY guard.
    monkeypatch.setattr(h,'independent',lambda:None)


def test_ten_descriptors_discovery_and_preservation(tmp_path,monkeypatch,capsys):
    root,cfg,files=case(tmp_path);before=cfg.read_bytes();initial=json.loads(before)
    hashes={d['path']:hashlib.sha256(Path(d['path']).read_bytes()).hexdigest() for d in files.values()}
    original_open=os.open
    def guarded(path,*a,**kw):
        assert 'INVENTED_NEVER_OPEN_CLINICAL' not in str(path)
        return original_open(path,*a,**kw)
    monkeypatch.setattr(os,'open',guarded)
    h.bind(cfg,root,TOOLS,discover_known=True);h.check(cfg,root,TOOLS)
    value=json.loads(cfg.read_text());a=h.artifacts(cfg)
    assert value['evidence']==files and value['private_root']==str(root)
    assert all(value[k]==initial[k] for k in h.DECLARATIONS)
    assert value['public_contract_sha256']==initial['public_contract_sha256']
    assert all(value[k] is True for k in ('no_raw_data','no_event_counts','no_models'))
    assert a['backup'].read_bytes()==before and not a['stage'].exists()
    assert all(p.stat().st_mode&0o777==0o600 for p in (cfg,a['backup'],a['record']))
    assert hashes=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in hashes}
    assert capsys.readouterr()==('','')
    with pytest.raises(h.Stop):h.bind(cfg,root,TOOLS,discover_known=True)


def test_explicit_paths_and_frozen_preflight_compatibility(tmp_path,monkeypatch,capsys):
    root,cfg,files=case(tmp_path)
    h.bind(cfg,root,TOOLS,locations=files)
    original,_=h.review_tool(TOOLS);monkeypatch.setattr(original.runtime,'require_local',lambda:None)
    # Match Python's normal script-directory import behavior for the actual CLI.
    monkeypatch.syspath_prepend(str(TOOLS))
    monkeypatch.setattr(sys,'argv',['offline_scientific_review.py','--preflight','--config',str(cfg)])
    assert original.main()==2 and capsys.readouterr()==('NO_EXECUTION\n','') # unresolved is intentional
    value=json.loads(cfg.read_text())
    # Represents an EXPLICIT invented human action, never performed by helper code.
    value.update(source_use_review=original.REVIEW,isolation_review=original.ISOLATION,
        reviewed_scope=original.public_json('references/REVIEW_SCOPE.json')['required_scope'])
    cfg.write_text(json.dumps(value));h.check(cfg,root,TOOLS)
    assert original.main()==0 and capsys.readouterr()==('NO_EXECUTION\n','')


@pytest.mark.parametrize('role',h.ROLES)
def test_missing_descriptor_file(tmp_path,role):
    root,cfg,files=case(tmp_path);Path(files[role]['path']).unlink()
    before=cfg.read_bytes()
    with pytest.raises((ValueError,OSError)):h.bind(cfg,root,TOOLS,locations=files)
    assert cfg.read_bytes()==before and not h.artifacts(cfg)['backup'].exists()


def test_wrong_descriptor_role_and_duplicate_path(tmp_path):
    root,cfg,files=case(tmp_path);files['diagnostic_config']=files['failed_count_config']
    with pytest.raises(ValueError):h.bind(cfg,root,TOOLS,locations=files)
    assert not h.artifacts(cfg)['backup'].exists()


def test_swapped_roles_do_not_pass_on_filenames_alone(tmp_path):
    root,cfg,files=case(tmp_path)
    files['diagnostic_config'],files['failed_count_config']=files['failed_count_config'],files['diagnostic_config']
    with pytest.raises(ValueError):h.bind(cfg,root,TOOLS,locations=files)
    assert not h.artifacts(cfg)['backup'].exists()


def test_multiple_authorization_candidates_fail_before_choice(tmp_path):
    root,cfg,files=case(tmp_path);p=Path(files['diagnostic_authorization']['path']);other=p.with_name('second.authorization.json')
    other.write_bytes(p.read_bytes());other.chmod(0o600)
    with pytest.raises(h.Stop,match='EVIDENCE_MISSING_OR_AMBIGUOUS'):h.bind(cfg,root,TOOLS,discover_known=True)


def test_public_generic_uppercase_config_and_authorization_names(tmp_path):
    root,cfg,files=case(tmp_path)
    for role in ('diagnostic_config','failed_count_config','diagnostic_authorization','failed_count_authorization'):
        p=Path(files[role]['path'])
        target=p.with_name('INVENTED_'+('STATUS' if role.startswith('diagnostic') else 'COUNT')+
                           ('_AUTHORIZATION.json' if role.endswith('authorization') else '_CONFIG.json'))
        p.rename(target)
    h.bind(cfg,root,TOOLS,discover_known=True);h.check(cfg,root,TOOLS)


def test_frozen_public_manifest_identity_required(tmp_path):
    tools=tmp_path/'INVENTED_WRONG_PUBLIC_TOOLS';tools.mkdir()
    v=json.loads((TOOLS/'RELEASE_MANIFEST.json').read_text());v['scope']='INVENTED_CHANGED'
    (tools/'RELEASE_MANIFEST.json').write_text(json.dumps(v))
    with pytest.raises(h.Stop,match='PUBLIC_REVIEW_RELEASE_MISMATCH'):h.review_tool(tools)


@pytest.mark.parametrize('entry',['bind','check'])
def test_direct_entrypoints_guard_before_private_access(entry,monkeypatch):
    def denied():raise h.Stop('INDEPENDENT_LOCAL_OPERATOR_REQUIRED')
    monkeypatch.setattr(h,'independent',denied)
    with pytest.raises(h.Stop,match='INDEPENDENT_LOCAL_OPERATOR_REQUIRED'):
        getattr(h,entry)(Path('/INVENTED_NEVER_READ.json'),Path('/INVENTED_PRIVATE'),Path('/INVENTED_TOOLS'))


@pytest.mark.parametrize('problem',['file_mode','directory_mode','symlink_file','symlink_parent','outside_root','wrong_owner','non_json'])
def test_filesystem_safety(tmp_path,problem,monkeypatch):
    root,cfg,files=case(tmp_path);p=Path(files['diagnostic_report']['path'])
    if problem=='file_mode':p.chmod(0o644)
    elif problem=='directory_mode':p.parent.chmod(0o755)
    elif problem=='symlink_file':
        link=p.with_name('INVENTED_LINK.json');link.symlink_to(p);files['diagnostic_report']['path']=str(link)
    elif problem=='symlink_parent':
        link=root/'INVENTED_LINK_PARENT';link.symlink_to(p.parent,target_is_directory=True);files['diagnostic_report']['path']=str(link/p.name)
    elif problem=='outside_root':
        q=tmp_path/'INVENTED_OUTSIDE.json';q.write_bytes(p.read_bytes());q.chmod(0o600);files['diagnostic_report']['path']=str(q)
    elif problem=='wrong_owner':monkeypatch.setattr(h.os,'getuid',lambda:99999999)
    else:
        q=p.with_suffix('.npz');q.write_bytes(p.read_bytes());q.chmod(0o600);files['diagnostic_report']['path']=str(q)
    with pytest.raises(ValueError):h.bind(cfg,root,TOOLS,locations=files)
    assert not h.artifacts(cfg)['backup'].exists()


@pytest.mark.parametrize('field,value',[('schema','WRONG'),('public_contract_sha256','0'*64),('mode','OTHER'),
    ('private_root','/INVENTED_PARTLY_PREPARED'),('source_use_review','INVENTED_APPROVED'),('no_models',False)])
def test_modified_configuration_refused(tmp_path,field,value):
    root,cfg,files=case(tmp_path);v=json.loads(cfg.read_text());v[field]=value;cfg.write_text(json.dumps(v));before=cfg.read_bytes()
    with pytest.raises(h.Stop,match='CONFIG_NOT_PRISTINE'):h.bind(cfg,root,TOOLS,locations=files)
    assert cfg.read_bytes()==before and not h.artifacts(cfg)['backup'].exists()


@pytest.mark.parametrize('kind',['authorization','output','stage','backup','record','marker','unrelated'])
def test_existing_attempt_or_preparation_refused(tmp_path,kind):
    root,cfg,files=case(tmp_path);a=h.artifacts(cfg)
    p={'authorization':cfg.parent/'review.authorization.json','output':cfg.parent/'review_output',
       'stage':a['stage'],'backup':a['backup'],'record':a['record'],'marker':cfg.parent/'operation_started.private.json',
       'unrelated':cfg.parent/'INVENTED_UNKNOWN.json'}[kind]
    if kind=='output':p.mkdir(mode=0o700)
    else:p.write_text('INVENTED_PRIOR_ARTIFACT');p.chmod(0o600)
    with pytest.raises(h.Stop,match='REVIEW_RUN_HAS_PRIOR_OR_PARTIAL_ARTIFACTS'):h.bind(cfg,root,TOOLS,locations=files)


def test_unreadable_wrong_schema_and_invalid_sha(tmp_path):
    root,cfg,files=case(tmp_path);p=Path(files['diagnostic_report']['path']);before=p.read_bytes()
    p.write_bytes(b'INVENTED_NOT_JSON')
    with pytest.raises(ValueError):h.bind(cfg,root,TOOLS,locations=files)
    p.write_bytes(before);files['diagnostic_report']['sha256']='NOT_A_HASH'
    with pytest.raises(h.Stop,match='EVIDENCE_HASH_MISMATCH'):h.bind(cfg,root,TOOLS,locations=files)


def test_duplicate_role_in_explicit_map_rejected(tmp_path):
    root,cfg,files=case(tmp_path);p=root/'INVENTED_PATH_MAP.json'
    p.write_text('{"schema":"elsa-review-evidence-paths-v1","evidence":{"diagnostic_config":{},"diagnostic_config":{}}}');p.chmod(0o600)
    with pytest.raises(h.Stop,match='DUPLICATE_JSON_FIELD'):h.explicit_map(p,root,cfg)


def test_explicit_map_input_and_missing_unexpected_role(tmp_path):
    root,cfg,files=case(tmp_path);p=root/'INVENTED_PATH_MAP.json'
    p.write_text(json.dumps({'schema':'elsa-review-evidence-paths-v1','evidence':files}));p.chmod(0o600)
    assert h.explicit_map(p,root,cfg)==files
    wrong=dict(files);wrong['unexpected_role']=wrong.pop('source_registration')
    with pytest.raises(h.Stop):h.bind(cfg,root,TOOLS,locations=wrong)


def test_historical_config_cannot_be_destination(tmp_path):
    root,cfg,files=case(tmp_path);old=Path(files['failed_count_config']['path']);before=old.read_bytes()
    with pytest.raises(h.Stop,match='HISTORICAL_RECORD_WRITE_REFUSED'):h.bind(old,root,TOOLS,locations=files)
    assert old.read_bytes()==before


def test_atomic_replace_after_exclusive_fsynced_files(tmp_path,monkeypatch):
    root,cfg,files=case(tmp_path);initial=cfg.read_bytes();real_replace=os.replace;real_fsync=os.fsync;calls=[]
    def fsync(fd):calls.append('fsync');return real_fsync(fd)
    def replace(src,dst):
        a=h.artifacts(cfg)
        assert Path(src)==a['stage'] and Path(dst)==cfg and cfg.read_bytes()==initial
        assert all(a[n].is_file() for n in ('backup','stage')) and not a['record'].exists() and calls.count('fsync')>=4
        calls.append('replace');return real_replace(src,dst)
    monkeypatch.setattr(os,'replace',replace);monkeypatch.setattr(os,'fsync',fsync)
    h.bind(cfg,root,TOOLS,locations=files)
    assert calls.count('replace')==1 and calls[-1]=='fsync'


def test_failure_retains_artifacts_and_preserves_initial_config(tmp_path,monkeypatch):
    root,cfg,files=case(tmp_path);initial=cfg.read_bytes()
    monkeypatch.setattr(os,'replace',lambda *_:(_ for _ in ()).throw(OSError('INVENTED_PRIVATE_EXCEPTION')))
    with pytest.raises(OSError):h.bind(cfg,root,TOOLS,locations=files)
    a=h.artifacts(cfg)
    assert cfg.read_bytes()==initial and a['backup'].exists() and a['stage'].exists() and not a['record'].exists()
    with pytest.raises(h.Stop):h.bind(cfg,root,TOOLS,locations=files)


def test_interrupted_staging_is_retained_not_retried(tmp_path,monkeypatch):
    root,cfg,files=case(tmp_path);initial=cfg.read_bytes();real=h.exclusive;a=h.artifacts(cfg)
    def interrupted(path,data):
        if path==a['stage']:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
            raise OSError('INVENTED_PRIVATE_FAILURE')
        return real(path,data)
    monkeypatch.setattr(h,'exclusive',interrupted)
    with pytest.raises(OSError):h.bind(cfg,root,TOOLS,locations=files)
    assert cfg.read_bytes()==initial and a['backup'].read_bytes()==initial and a['stage'].exists()
    with pytest.raises(h.Stop):h.bind(cfg,root,TOOLS,locations=files)


def test_concurrent_configuration_change_not_overwritten(tmp_path,monkeypatch):
    root,cfg,files=case(tmp_path);real=h.exclusive;a=h.artifacts(cfg)
    def changed(path,data):
        real(path,data)
        if path==a['stage']:cfg.write_text('{"INVENTED_CONCURRENT_EDIT":true}')
    monkeypatch.setattr(h,'exclusive',changed)
    with pytest.raises(h.Stop,match='CONFIG_CHANGED_DURING_PREPARATION'):h.bind(cfg,root,TOOLS,locations=files)
    assert cfg.read_text()=='{"INVENTED_CONCURRENT_EDIT":true}' and a['backup'].exists()


def test_concurrent_authorization_artifact_prevents_replace(tmp_path,monkeypatch):
    root,cfg,files=case(tmp_path);real=h.exclusive;a=h.artifacts(cfg);initial=cfg.read_bytes()
    auth=cfg.parent/'review.authorization.json'
    def appeared(path,data):
        real(path,data)
        if path==a['stage']:auth.write_text('INVENTED_CONCURRENT_AUTH_ARTIFACT')
    monkeypatch.setattr(h,'exclusive',appeared)
    with pytest.raises(h.Stop,match='REVIEW_RUN_HAS_PRIOR_OR_PARTIAL_ARTIFACTS'):h.bind(cfg,root,TOOLS,locations=files)
    assert cfg.read_bytes()==initial and auth.read_text()=='INVENTED_CONCURRENT_AUTH_ARTIFACT'


def test_changed_evidence_or_configuration_detected_by_check(tmp_path):
    root,cfg,files=case(tmp_path);h.bind(cfg,root,TOOLS,locations=files)
    v=json.loads(cfg.read_text());v['evidence']['diagnostic_report']['sha256']='0'*64;cfg.write_text(json.dumps(v))
    with pytest.raises(h.Stop,match='CONFIG_CHANGED_AFTER_BINDING'):h.check(cfg,root,TOOLS)


def test_byte_changed_metadata_detected_without_rebinding(tmp_path):
    root,cfg,files=case(tmp_path);h.bind(cfg,root,TOOLS,locations=files)
    p=Path(files['diagnostic_report']['path']);p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(h.Stop,match='EVIDENCE_HASH_MISMATCH'):h.check(cfg,root,TOOLS)


def test_missing_postreplace_record_is_not_completed_binding(tmp_path,monkeypatch):
    root,cfg,files=case(tmp_path);real=h.exclusive;a=h.artifacts(cfg)
    def interrupted(path,data):
        if path==a['record']:raise OSError('INVENTED_INTERRUPTION_AFTER_REPLACE')
        return real(path,data)
    monkeypatch.setattr(h,'exclusive',interrupted)
    with pytest.raises(OSError):h.bind(cfg,root,TOOLS,locations=files)
    assert json.loads(cfg.read_text())['private_root']==str(root) and a['backup'].exists() and not a['stage'].exists() and not a['record'].exists()
    with pytest.raises(h.Stop):h.check(cfg,root,TOOLS)
    with pytest.raises(h.Stop):h.bind(cfg,root,TOOLS,locations=files)


def test_old_review_public_tools_unchanged(tmp_path):
    before={p:p.read_bytes() for p in TOOLS.rglob('*') if p.is_file()}
    root,cfg,files=case(tmp_path);h.bind(cfg,root,TOOLS,locations=files);h.check(cfg,root,TOOLS)
    assert before=={p:p.read_bytes() for p in before}


def test_frozen_imports_never_write_bytecode(monkeypatch):
    before={p for p in TOOLS.rglob('*') if p.is_file()}
    monkeypatch.setattr(sys,'dont_write_bytecode',False)
    h.review_tool(TOOLS)
    assert sys.dont_write_bytecode is True and before=={p for p in TOOLS.rglob('*') if p.is_file()}


@pytest.mark.parametrize('mode',['--bind','--check'])
def test_agent_guard_and_no_sensitive_output(mode):
    p=subprocess.run([sys.executable,'-B',str(ROOT/'prepare_offline_review_config.py'),mode,
        '--private-root','/INVENTED_PRIVATE_NOT_READ','--config','/INVENTED_SECRET_CONFIG.json','--review-tools','/INVENTED_TOOLS'],
        env={**os.environ,'CODEX_SESSION_ID':'INVENTED_AGENT'},capture_output=True,text=True)
    assert p.returncode==2 and p.stdout=='STOP ISSUE=INDEPENDENT_LOCAL_OPERATOR_REQUIRED\n' and not p.stderr


def test_cli_binding_and_check_only_synthetic(tmp_path,monkeypatch,capsys):
    root,cfg,files=case(tmp_path);monkeypatch.setattr(h,'independent',lambda:None)
    base=['prepare_offline_review_config.py','--private-root',str(root),'--config',str(cfg),'--review-tools',str(TOOLS)]
    monkeypatch.setattr(sys,'argv',base+['--bind','--discover-known-layout']);assert h.main()==0
    assert capsys.readouterr()==('PASS ISSUE=METADATA_BOUND_SCOPE_UNCHANGED\n','')
    monkeypatch.setattr(sys,'argv',base+['--check']);assert h.main()==0
    assert capsys.readouterr()==('PASS ISSUE=METADATA_CONFIGURATION_VERIFIED_NO_AUTHORIZATION\n','')
