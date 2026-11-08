"""Synthetic metadata only. Never reads clinical data or real receipts."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import offline_scientific_review as tool
import local_execution as runtime
import review_logic as logic
import conditional_paths as paths
from invented_fixture import create_case,change,invented_report,mapping,frozen_diagnostic


@pytest.mark.parametrize('wave',[1,2,3,4,5,6,7,8,9])
@pytest.mark.parametrize('flag',[0,1,None,2])
def test_reference_categories_match_frozen_diagnostic(wave,flag):
    m=mapping();fs=m['waves'][str(wave)]['fields'];outcome='indoc' if wave==1 else f'w{wave}indout';proxy='askpx1' if wave<3 else 'askpx'
    no=2 if wave==1 else 0
    states=[(11,no),(21,no),(13,1),(13,no),(-1,1),(-1,no),(None,1)]
    if '24' in fs[outcome]['values']:states.append((24,no))
    if '95' in fs[outcome]['values']:states.append((95,no))
    for a,b in states:
        r=frozen_diagnostic.classify(wave,flag,{outcome:a,proxy:b},m)
        assert logic.classify_cell(r['participation'],r['core'],r['decoder_basis'])==(r['interpretation'],r['frozen_target_check'])
    r=frozen_diagnostic.classify(wave,flag,None,m)
    assert logic.classify_cell(r['participation'],r['core'],r['decoder_basis'])==(r['interpretation'],r['frozen_target_check'])


def test_complete_private_worksheet_no_source_bytes(tmp_path,monkeypatch,capsys):
    c,config,out,_=create_case(tmp_path);monkeypatch.setattr(runtime,'require_local',lambda:None)
    originals={d['path']:hashlib.sha256(Path(d['path']).read_bytes()).hexdigest() for d in c['evidence'].values()}
    original=os.open
    def guard(path,*a,**k):
        assert 'INVENTED_CLINICAL_NEVER_OPEN' not in str(path)
        return original(path,*a,**k)
    monkeypatch.setattr(os,'open',guard)
    with runtime.exclusive_output(out):tool.execute(c,out)
    assert capsys.readouterr()==('','')
    w=json.loads((out/'scientific_evidence_worksheet.private.json').read_text())
    d=json.loads((out/'reviewer_decision.UNRESOLVED.private.json').read_text())
    assert all(v=='UNRESOLVED' for v in d['approval_and_acceptance'].values())
    assert d['recommended_scientific_action_category']=='UNRESOLVED'
    assert not d['count_execution_authorized'] and not d['training_authorized']
    assert set(w['all_waves'])==set(map(str,range(1,10)))
    assert w['all_waves']['9']['unmatched_core_records']==1
    assert w['all_waves']['7']['missing_core_records']==1
    assert 'PARTICIPATION_ZERO' in json.dumps(w) and 'PARTICIPATION_MISSING' in json.dumps(w)
    assert 'ASKPX_FALLBACK' in json.dumps(w)
    assert all('700001' not in p.read_text() for p in out.iterdir() if p.suffix=='.json')
    assert out.stat().st_mode&0o077==0
    assert all(p.stat().st_mode&0o077==0 for p in out.iterdir())
    assert originals=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in originals}
    with pytest.raises(runtime.Rejected):
        with runtime.exclusive_output(out):pass


@pytest.mark.parametrize('role',['diagnostic_config','diagnostic_authorization','diagnostic_completion','diagnostic_integrity',
    'diagnostic_report','diagnostic_input_validation','failed_count_config','failed_count_authorization','failed_count_completion','source_registration'])
def test_every_metadata_hash_checked(tmp_path,role):
    c,_,out,_=create_case(tmp_path)
    Path(c['evidence'][role]['path']).write_text('INVENTED_MODIFIED_METADATA')
    with pytest.raises(ValueError):tool.verify_existing_evidence(c,Path(c['private_root']),out)


@pytest.mark.parametrize('role,key,bad',[
    ('diagnostic_completion','status','FAILED_NO_RETRY'),('diagnostic_completion','attempt_consumed',False),
    ('failed_count_completion','issue','OTHER_INVENTED_FAILURE'),('failed_count_completion','attempt_consumed',False),
    ('diagnostic_authorization','purpose','OLD_WRONG_PURPOSE'),('diagnostic_authorization','code_bindings',{}),
    ('failed_count_authorization','config_sha256','0'*64),('failed_count_authorization','code_bindings',{}),
    ('diagnostic_integrity','purpose','WRONG'),('diagnostic_integrity','outputs',{}),
    ('failed_count_config','mapping_sha256','0'*64),('source_registration','public_contract_sha256','0'*64)])
def test_truthfully_rehashed_incompatible_evidence_rejected(tmp_path,role,key,bad):
    c,_,out,_=create_case(tmp_path);change(c,role,lambda value:value.update({key:bad}))
    with pytest.raises(ValueError):tool.verify_existing_evidence(c,Path(c['private_root']),out)


def test_source_difference_not_repaired_by_rehashing_metadata(tmp_path):
    c,_,out,_=create_case(tmp_path)
    change(c,'failed_count_config',lambda v:v['sources']['core6'].update(sha256='0'*64))
    # Repair the INVENTED historical config binding too, leaving a genuine
    # source-equivalence mismatch for the review tool to reject.
    change(c,'failed_count_authorization',lambda v:v.update(config_sha256=c['evidence']['failed_count_config']['sha256']))
    with pytest.raises(ValueError):tool.verify_existing_evidence(c,Path(c['private_root']),out)


@pytest.mark.parametrize('field,value',[('source_use_review','UNRESOLVED'),('isolation_review','UNRESOLVED'),
    ('reviewed_scope',[]),('no_raw_data',False),('no_event_counts',False),('no_models',False),
    ('public_contract_sha256','0'*64),('schema','WRONG')])
def test_scope_contract_before_any_report_read(tmp_path,field,value,monkeypatch):
    c,_,_,_=create_case(tmp_path);c[field]=value
    monkeypatch.setattr(tool,'bound_json',lambda *_:pytest.fail('Protected metadata read before scope validation'))
    with pytest.raises(ValueError):tool.validate_config(c)


def test_private_permissions_symlinks_and_root(tmp_path):
    c,_,_,_=create_case(tmp_path);d=c['evidence']['diagnostic_report'];p=Path(d['path'])
    p.chmod(0o644)
    with pytest.raises(ValueError):tool.validate_config(c)
    p.chmod(0o600);link=p.with_name('INVENTED_LINK.json');link.symlink_to(p);d['path']=str(link)
    with pytest.raises(ValueError):tool.validate_config(c)
    d['path']=str(p);Path(c['private_root']).chmod(0o755)
    with pytest.raises(ValueError):tool.validate_config(c)


@pytest.mark.parametrize('problem',['missing_wave','total','first','unknown_cell','raw_text','duplicate_field','unknown_report_field','domain_error'])
def test_incomplete_or_unsupported_aggregate_stays_unresolved(problem):
    r=invented_report();r['bindings']={}
    if problem=='missing_wave':del r['waves']['2']
    elif problem=='total':r['waves']['6']['interpretations']['CONSISTENT']=999
    elif problem=='first':r['first_detected_target_conflict']['wave']=8
    elif problem=='unknown_cell':r['waves']['5']['classification_matrix']={'UNKNOWN|UNKNOWN|UNKNOWN':3}
    elif problem=='raw_text':r['waves']['5']['proxy_raw_states']={'INVENTED_PRIVATE_TEXT':3}
    elif problem=='duplicate_field':
        with pytest.raises(ValueError):tool.strict_json('{"a":1,"a":2}')
        return
    elif problem=='unknown_report_field':r['participant_rows']=['INVENTED_DO_NOT_ACCEPT']
    else:r['source_domain_error_observed']=True
    with pytest.raises(ValueError):logic.validate_aggregate(r)


@pytest.mark.parametrize('status',['FAILED_NO_RETRY','INTERRUPTED_NO_RETRY'])
def test_failed_attempt_remains_consumed(tmp_path,status):
    out=tmp_path/'INVENTED_CONSUMED'
    with pytest.raises((ValueError,KeyboardInterrupt)):
        with runtime.exclusive_output(out,False):
            if status.startswith('INTERRUPTED'):raise KeyboardInterrupt()
            raise ValueError('INVENTED_FAILURE')
    assert json.loads((out/'completion.private.json').read_text())['status']==status
    with pytest.raises(runtime.Rejected):
        with runtime.exclusive_output(out,False):pass


def test_single_command_delegates_authorization_then_execute(tmp_path,monkeypatch,capsys):
    c,config,out,auth=create_case(tmp_path);monkeypatch.setattr(runtime,'require_local',lambda:None)
    calls=[]
    def boundary(purpose,execute,demo):
        calls.append((purpose,sys.argv[1]));return 0
    monkeypatch.setattr(runtime,'cli',boundary)
    monkeypatch.setattr(sys,'argv',['offline_scientific_review.py','--review','--config',str(config),'--authorization',str(auth),'--output',str(out)])
    assert tool.main()==0
    assert calls==[(tool.PURPOSE,'--authorize-local'),(tool.PURPOSE,'--execute-local')]
    text=capsys.readouterr();assert str(tmp_path) not in text.out+text.err
    assert not out.exists() and not auth.exists() # mocked boundary, not real authorization


def test_authorization_cancellation_never_executes(tmp_path,monkeypatch,capsys):
    c,config,out,auth=create_case(tmp_path);monkeypatch.setattr(runtime,'require_local',lambda:None)
    calls=[]
    def boundary(*_):calls.append(sys.argv[1]);return 2
    monkeypatch.setattr(runtime,'cli',boundary)
    monkeypatch.setattr(sys,'argv',['offline_scientific_review.py','--review','--config',str(config),'--authorization',str(auth),'--output',str(out)])
    assert tool.main()==2 and calls==['--authorize-local'] and not out.exists()


def test_missing_auth_existing_output_and_private_error_are_safe(tmp_path,monkeypatch,capsys):
    c,config,out,auth=create_case(tmp_path);monkeypatch.setattr(runtime,'require_local',lambda:None)
    monkeypatch.setattr(runtime,'cli',lambda *_:pytest.fail('Unsafe operation reached boundary'))
    monkeypatch.setattr(sys,'argv',['offline_scientific_review.py','--execute-local','--config',str(config),'--authorization',str(auth),'--output',str(out)])
    assert tool.main()==2 and capsys.readouterr()==('NO_EXECUTION\n','')
    out.mkdir(mode=0o700)
    monkeypatch.setattr(sys,'argv',['offline_scientific_review.py','--review','--config',str(config),'--authorization',str(auth),'--output',str(out)])
    assert tool.main()==2 and capsys.readouterr()==('NO_EXECUTION\n','')
    config.write_text('INVENTED_PRIVATE_MALFORMED_CONTENT')
    assert tool.main()==2 and capsys.readouterr()==('NO_EXECUTION\n','')


def test_invalid_linkage_not_promoted_to_success(tmp_path):
    c,_,out,_=create_case(tmp_path)
    change(c,'diagnostic_input_validation',lambda v:v['linkage_quality']['core4'].update(DUPLICATE_LINKAGE=1))
    change(c,'diagnostic_integrity',lambda v:v['outputs'].update({'input_validation.private.json':c['evidence']['diagnostic_input_validation']['sha256']}))
    with pytest.raises(ValueError):tool.verify_existing_evidence(c,Path(c['private_root']),out)


def test_readonly_config_preflight_opens_no_report(tmp_path,monkeypatch,capsys):
    c,config,out,auth=create_case(tmp_path);monkeypatch.setattr(runtime,'require_local',lambda:None)
    monkeypatch.setattr(tool,'bound_json',lambda *_:pytest.fail('Protected result read during preflight'))
    monkeypatch.setattr(sys,'argv',['offline_scientific_review.py','--preflight','--config',str(config)])
    assert tool.main()==0 and capsys.readouterr()==('NO_EXECUTION\n','')


def test_old_authorization_never_authorizes_new_purpose(tmp_path,monkeypatch,capsys):
    c,config,out,auth=create_case(tmp_path);monkeypatch.setattr(runtime,'require_local',lambda:None)
    old=Path(c['evidence']['diagnostic_authorization']['path'])
    auth.write_bytes(old.read_bytes());auth.chmod(0o600)
    monkeypatch.setattr(sys,'argv',['offline_scientific_review.py','--execute-local','--config',str(config),'--authorization',str(auth),'--output',str(out)])
    assert runtime.cli(tool.PURPOSE,lambda *_:pytest.fail('Old purpose processed protected evidence'),lambda *_:None)==2
    assert not out.exists() and 'INVENTED' not in capsys.readouterr().out


@pytest.mark.parametrize('mode',['--review','--preflight','--execute-local','--authorize-local'])
def test_agent_guard_before_private_config(mode):
    p=subprocess.run([sys.executable,'-B',str(ROOT/'offline_scientific_review.py'),mode,'--config','/INVENTED_NEVER_READ.json'],
        env={**os.environ,'CODEX_SESSION_ID':'INVENTED_AGENT'},capture_output=True,text=True)
    assert p.returncode==2 and p.stdout=='NO_EXECUTION\n' and p.stderr==''


@pytest.mark.parametrize('args',[['--unknown','INVENTED_SECRET'],['--review','--config'],['--review','--review','--config','INVENTED_SECRET']])
def test_cli_failures_never_echo_values(args):
    p=subprocess.run([sys.executable,'-B',str(ROOT/'offline_scientific_review.py'),*args],capture_output=True,text=True)
    assert p.returncode==2 and 'INVENTED_SECRET' not in p.stdout+p.stderr and not p.stderr


@pytest.mark.parametrize('history_evidence',[{'baseline_mi':'CONFIRMED_PREVALENT'}, {'baseline_stroke':'CONFIRMED_PREVALENT'},
    {'followup':'UNKNOWN'}, {'followup':'PROXY'}, {'followup':'DEATH_CENSORED'},
    {'followup':['OBSERVED_EVENT','REPEATED_REPORT']}, {'history':['MISSED_WAVE','REENTRY']}])
def test_unadopted_C_keeps_history_and_unknowns(history_evidence):
    before=copy.deepcopy(history_evidence)
    statuses=[('PARTICIPATION_ONE','CORE_PERSONAL_INTERVIEW','OUTCOME_BASED'),
              ('PARTICIPATION_MISSING','CORE_PROXY_INTERVIEW','ASKPX_FALLBACK')]
    p=paths.prospective_quarantine(statuses,disease_history=history_evidence)
    assert p['proposed_quarantine'] and p['history']==statuses and history_evidence==before==p['unchanged_history_evidence']
    assert p['disease_outcome'] is None and p['eligible_for_count'] is None and p['count_execution']=='NO_EXECUTION'


def test_A_no_eligibility_change_and_B_no_fabricated_patch():
    a=paths.observability('PARTICIPATION_MISSING','CORE_PERSONAL_INTERVIEW','OUTCOME_BASED')
    assert a['frozen_target_check']=='WOULD_REJECT_MISSING' and not a['eligibility_decisions_changed']
    assert paths.defect_path()=={'status':'NOT_ESTABLISHED','patch_created':False,'count_execution':'NO_EXECUTION'}
    assert not paths.prospective_quarantine([('PARTICIPATION_ZERO','NO_CORE_RECORD','NO_CORE_RECORD')])['proposed_quarantine']


def test_no_runtime_loader_network_or_automatic_policy_adoption():
    forbidden={'socket','requests','urllib','http','pandas','numpy','torch','read_release','run_counts','status_reader'}
    for name in ('offline_scientific_review.py','review_logic.py','conditional_paths.py'):
        tree=ast.parse((ROOT/name).read_text())
        imported={n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module}
        imported|={a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names}
        assert not imported&forbidden
    template=json.loads((ROOT/'SCIENTIFIC_DECISION_TEMPLATE.json').read_text())
    assert all(v=='UNRESOLVED' for v in template['approval_and_acceptance'].values())
    assert paths.defect_path()['count_execution']=='NO_EXECUTION'


def test_public_install_and_unresolved_config_exclusive(tmp_path):
    import verify_public
    destination=tmp_path/'INVENTED_PUBLIC_TOOLS'
    verify_public.install(destination);verify_public.verify(destination)
    with pytest.raises(ValueError):verify_public.install(destination)
    private=tmp_path/'INVENTED_PRIVATE_RUN';private.mkdir(mode=0o700)
    config=private/'INVENTED_NEW_CONFIG.json';verify_public.new_config(config)
    assert config.stat().st_mode&0o077==0
    assert json.loads(config.read_text())['source_use_review']=='UNRESOLVED_NOT_AUTHORIZED'
    with pytest.raises(ValueError):verify_public.new_config(config)
    (destination/'review_logic.py').write_text('INVENTED_CHANGED_PUBLIC_CODE')
    with pytest.raises(ValueError):verify_public.verify(destination)


def test_sibling_private_tools_installation_supported(tmp_path,monkeypatch):
    import verify_public
    c,_,_,_=create_case(tmp_path)
    installed=Path(c['private_root'])/'INVENTED_ISOLATED_PUBLIC_TOOLS'
    verify_public.install(installed)
    monkeypatch.setattr(tool,'ROOT',installed)
    assert tool.validate_config(c)==Path(c['private_root'])


def test_direct_execution_refuses_public_or_unconsumed_output(tmp_path,monkeypatch):
    c,_,out,_=create_case(tmp_path);monkeypatch.setattr(runtime,'require_local',lambda:None)
    out.mkdir(mode=0o700)
    monkeypatch.setattr(tool,'verify_existing_evidence',lambda *_:pytest.fail('Evidence read without consumed private destination'))
    with pytest.raises(FileNotFoundError):tool.execute(c,out)
