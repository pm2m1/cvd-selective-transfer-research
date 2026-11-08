"""Invented Stata tables, temporary destinations and mock authorizations ONLY."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import diagnostic_engine as engine
import frozen_decoder as decoder
import local_execution as local
import run_status_diagnostic as runner
import status_reader as reader
from verify_public import verify, install

M = local.load_json(ROOT/'references/frozen_mapping.json')
E = local.load_json(ROOT/'references/PUBLIC_EVIDENCE.json')


def raw(w, out=11, proxy=None):
    if proxy is None:
        proxy = 2 if w == 1 else 0
    return {'indoc' if w == 1 else f'w{w}indout': out, 'askpx1' if w < 3 else 'askpx': proxy}


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    # The ONLY environment-gate bypass in these tests is for invented temp fixtures.
    monkeypatch.setattr(reader, 'require_local', lambda: None)
    monkeypatch.setattr(runner, 'require_local', lambda: None)
    parent = tmp_path/'INVENTED_PRIVATE_PARENT'
    parent.mkdir(mode=0o700)
    config = local.load_json(ROOT/'config.template.json')
    config.update(source_use_review=runner.REVIEW, reviewed_scope=runner.SCOPE.copy())
    sources = {}
    for role, basename in E['required_products'].items():
        path = parent/basename
        if role == 'harmonized':
            records = [dict(idauniq=i, **{'inw'+str(w): 1 for w in range(1, 10)}) for i in (990000001, 990000002)]
        else:
            w = int(role[4:])
            records = [dict(idauniq=i, **raw(w)) for i in (990000001, 990000002)]
        for row in records:
            row['invented_unselected_health_field'] = 123
        pd.DataFrame(records).to_stata(path, write_index=False, version=118)
        sources[role] = {'path': str(path), 'sha256': local.sha(path),
            'dataset_basename': basename, 'claimed_archive_edition': 'UNRESOLVED'}
    manifest = {'schema': 'elsa-private-source-registration-v1',
        'status': 'REGISTERED_LOCAL_MEMBER_BINDINGS_ONLY_COUNT_NOT_AUTHORIZED', 'attempt_consumed': True,
        'public_contract_sha256': E['registration_public_contract_sha256'],
        'registration_protocol_sha256': E['registration_protocol_sha256'],
        'registration_code_bindings': E['registration_code_bindings'],
        'count_tool_release_sha256': E['count_tool_release_sha256'],
        'count_mapping_sha256': E['frozen_mapping_sha256'],
        'count_protocol_sha256': E['frozen_protocol_sha256'],
        'members': [{'role': k, 'materialized_file': d, 'uncompressed_member_sha256': d['sha256']} for k,d in sources.items()]}
    manifest_path = parent/'INVENTED_REGISTRATION_METADATA.json'
    local.write_json(manifest_path, manifest)
    config['source_registration'] = {'path': str(manifest_path), 'sha256': local.sha(manifest_path)}
    config['sources'] = sources
    return {'parent': parent, 'output': parent/'NEW_STATUS_OPERATION', 'config': config, 'manifest': manifest,
            'manifest_path': manifest_path}


def rebind(f, role):
    d = f['config']['sources'][role]
    d['sha256'] = local.sha(d['path'])
    for member in f['manifest']['members']:
        if member['role'] == role:
            member['materialized_file'] = copy.deepcopy(d)
            member['uncompressed_member_sha256'] = d['sha256']
    f['manifest_path'].write_text(json.dumps(f['manifest']))
    f['config']['source_registration']['sha256'] = local.sha(f['manifest_path'])


def modify_table(f, role, transform):
    path = Path(f['config']['sources'][role]['path'])
    frame = pd.read_stata(path, convert_categoricals=False)
    frame = transform(frame)
    frame.to_stata(path, write_index=False, version=118)
    rebind(f, role)


def execute(f):
    with local.exclusive_output(f['output']) as out:
        runner.execute(f['config'], out)


@pytest.mark.parametrize('out,px,kind', [(11,0,'CORE_PERSONAL_INTERVIEW'), (13,1,'CORE_PROXY_INTERVIEW'),
    (21,0,'CORE_PARTIAL_INTERVIEW'), (24,0,'CORE_INSTITUTIONAL_INTERVIEW')])
def test_consistent_types(out, px, kind):
    r = engine.classify(6, 1, raw(6,out,px), M)
    assert r['core'] == kind and r['interpretation'] == 'CONSISTENT'
    assert r['frozen_target_check'] == 'NO_TARGET_REJECTION'


@pytest.mark.parametrize('flag,part,disposition,check', [
    (0,'PARTICIPATION_ZERO','KNOWN_DISAGREEMENT','WOULD_REJECT_KNOWN_ZERO'),
    (None,'PARTICIPATION_MISSING','INSUFFICIENT_EVIDENCE','WOULD_REJECT_MISSING'),
    ('.a','PARTICIPATION_MISSING','INSUFFICIENT_EVIDENCE','WOULD_REJECT_MISSING'),
    (2,'PARTICIPATION_OTHER_OR_INVALID','INSUFFICIENT_EVIDENCE','EARLIER_PARTICIPATION_DOMAIN_REJECTION')])
def test_zero_missing_invalid_separate(flag, part, disposition, check):
    r = engine.classify(6,flag,raw(6),M)
    assert (r['participation'],r['interpretation'],r['frozen_target_check']) == (part,disposition,check)


@pytest.mark.parametrize('flag',[0,1,None,'.a'])
@pytest.mark.parametrize('outcome',[None,-1,31,95])
def test_askpx_fallback_always_ambiguous(flag,outcome):
    r = engine.classify(6,flag,raw(6,outcome,1),M)
    assert r['decoder_kind'] == 'proxy' and r['decoder_basis'] == 'ASKPX_FALLBACK'
    assert r['interpretation'] == 'UNRESOLVED_DECODER_AMBIGUITY'


def test_explicit_proxy_flag_disagreement_is_not_repaired():
    r=engine.classify(6,1,raw(6,13,0),M)
    assert r['decoder_kind']=='proxy' and r['interpretation']=='UNRESOLVED_DECODER_AMBIGUITY'


def test_wave_one_and_wave_four_specific_domains():
    assert engine.classify(1,1,raw(1),M)['core']=='CORE_PERSONAL_INTERVIEW'
    assert engine.classify(1,1,raw(1,11,0),M)['input_domain_error']
    assert engine.classify(3,1,raw(3,26,0),M)['core']=='CORE_PARTIAL_INTERVIEW'
    assert engine.classify(4,1,raw(4,26,0),M)['input_domain_error']


def test_missing_core_and_missed_wave_reentry():
    h={1:{'inw'+str(w):int(w!=5) for w in range(1,10)}}
    cores={w:({} if w==5 else {1:raw(w)}) for w in range(1,10)}
    result=engine.summarize(h,cores,M)
    assert result['first_detected_target_conflict'] is None
    assert result['waves']['5']['missing_core_records']==1
    assert engine.classify(5,0,None,M)['interpretation']=='CONSISTENT'
    assert engine.classify(5,1,None,M)['interpretation']=='INSUFFICIENT_EVIDENCE'


def test_no_interview_and_ambiguous_evidence_differ():
    assert engine.classify(6,0,raw(6,43,-1),M)['core']=='NO_CORE_INTERVIEW_EVIDENCE'
    assert engine.classify(6,0,raw(6,None,-1),M)['core']=='CORE_AMBIGUOUS'
    assert engine.classify(6,0,raw(6,95,-1),M)['core']=='CORE_DEATH_STATUS_NO_INTERVIEW_EVIDENCE'


def test_first_conflict_and_all_conflicts_counted_no_ids():
    h={987654321:{'inw'+str(w):(None if w==4 else 0 if w==6 else 1) for w in range(1,10)}}
    cores={w:{987654321:raw(w)} for w in range(1,10)}
    r=engine.summarize(h,cores,M)
    assert r['first_detected_target_conflict']['wave']==4
    assert sum(r['zero_and_missing_conflicts_separate'].values())==2
    assert '987654321' not in json.dumps(r)


def test_actual_minimal_selected_columns_and_no_ids_returned_in_report(fixture):
    f=fixture
    rows,q=reader.read_status(f['config']['sources']['harmonized']['path'],'harmonized')
    assert set(next(iter(rows.values())))=={'inw'+str(w) for w in range(1,10)}
    rows,q=reader.read_status(f['config']['sources']['core6']['path'],'core6')
    assert set(next(iter(rows.values())))=={'w6indout','askpx'} and not any(q.values())
    execute(f)
    report=local.load_json(f['output']/'status_diagnostic.private.json')
    text=json.dumps(report)
    assert '990000001' not in text and '990000002' not in text
    assert 'invented_unselected_health_field' not in text
    assert report['eligibility_decisions_changed'] is False
    assert local.load_json(f['output']/'completion.private.json')['attempt_consumed'] is True
    assert (f['output']/'operational_summary.json').is_file()


def test_selected_reader_preserves_tagged_missing(fixture):
    p=fixture['parent']/'INVENTED_TAG.dta'
    # Plain Stata missing is returned as '.' by convert_missing=True, never zero.
    pd.DataFrame({'idauniq':[990000001],'w6indout':[11.0],'askpx':[float('nan')]}).to_stata(p,write_index=False,version=118)
    rows,_=reader.read_status(p,'core6')
    assert rows[990000001]['askpx']=='.'


@pytest.mark.parametrize('problem',['missing','invalid','duplicate'])
def test_invalid_linkage_private_summary_then_failure(fixture, problem):
    f=fixture
    def change(frame):
        if problem=='missing':frame.loc[0,'idauniq']=float('nan')
        elif problem=='invalid':frame.loc[0,'idauniq']=-1
        else:frame.loc[1,'idauniq']=frame.loc[0,'idauniq']
        return frame
    modify_table(f,'core6',change)
    with pytest.raises(local.Rejected,match='INVALID_OR_DUPLICATE_STATUS_LINKAGE_NO_RETRY'):
        execute(f)
    q=local.load_json(f['output']/'input_validation.private.json')['linkage_quality']['core6']
    assert sum(q.values())==1
    assert not (f['output']/'status_diagnostic.private.json').exists()
    assert local.load_json(f['output']/'completion.private.json')['status']=='FAILED_NO_RETRY'


def test_unmatched_core_linkage_is_private_not_added_to_universe(fixture):
    f=fixture
    modify_table(f,'core6',lambda frame:frame.assign(idauniq=[990000001,990000099]))
    execute(f)
    r=local.load_json(f['output']/'status_diagnostic.private.json')
    assert r['waves']['6']['unmatched_core_records']==1 and r['waves']['6']['missing_core_records']==1
    assert '990000099' not in json.dumps(r)


@pytest.mark.parametrize('problem',['missing_field','corrupt'])
def test_incompatible_sources_fail_closed(fixture,problem):
    f=fixture
    if problem=='missing_field':modify_table(f,'core6',lambda frame:frame.drop(columns=['askpx']))
    else:
        Path(f['config']['sources']['core6']['path']).write_bytes(b'INVENTED_CORRUPT_STATA')
        rebind(f,'core6')
    with pytest.raises(local.Rejected):execute(f)
    assert (f['output']/'input_validation.private.json').is_file()
    assert not (f['output']/'operational_summary.json').exists()


def test_invalid_participation_class_preserved_but_operation_fails(fixture):
    f=fixture
    modify_table(f,'harmonized',lambda frame:frame.assign(inw6=[2,1]))
    with pytest.raises(local.Rejected,match='STATUS_DOMAIN_INCOMPATIBILITY_DIAGNOSTIC_PRESERVED'):
        execute(f)
    r=local.load_json(f['output']/'status_diagnostic.private.json')
    assert any('PARTICIPATION_OTHER_OR_INVALID' in key for key in r['waves']['6']['classification_matrix'])
    assert not (f['output']/'operational_summary.json').exists()


def test_source_integrity_mismatch_before_reading(fixture,monkeypatch):
    f=fixture
    Path(f['config']['sources']['core6']['path']).write_bytes(b'INVENTED_TAMPER')
    monkeypatch.setattr(runner,'read_status',lambda *_:pytest.fail('Source read before all hashes verified'))
    with pytest.raises(local.Rejected,match='FILE_BINDING_MISMATCH'):execute(f)


def test_source_not_registered_refused(fixture):
    f=fixture
    f['config']['sources']['core6']['sha256']='0'*64
    with pytest.raises(local.Rejected,match='SOURCE_NOT_EXACTLY_REGISTERED'):execute(f)


def test_registration_binding_mismatch(fixture):
    f=fixture
    f['manifest']['registration_code_bindings']={}
    f['manifest_path'].write_text(json.dumps(f['manifest']))
    f['config']['source_registration']['sha256']=local.sha(f['manifest_path'])
    with pytest.raises(local.Rejected,match='SOURCE_REGISTRATION_PUBLIC_BINDING_MISMATCH'):execute(f)


@pytest.mark.parametrize('field,value',[('source_use_review','UNRESOLVED_NOT_AUTHORIZED'),('reviewed_scope',[]),
    ('no_models',False),('no_event_counts',False),('mapping_sha256','0'*64),('protocol_sha256','0'*64)])
def test_permission_and_contract_fields_required_before_sources(fixture,monkeypatch,field,value):
    f=fixture;f['config'][field]=value
    monkeypatch.setattr(runner,'verify_registration',lambda *_:pytest.fail('Private metadata read before config gate'))
    with pytest.raises(local.Rejected):execute(f)


def test_output_exclusivity_and_private_modes(fixture):
    f=fixture;execute(f)
    before={p.name:p.read_bytes() for p in f['output'].iterdir()}
    with pytest.raises(local.Rejected,match='OUTPUT_ALREADY_EXISTS_NO_RETRY'):execute(f)
    assert before=={p.name:p.read_bytes() for p in f['output'].iterdir()}
    assert stat.S_IMODE(f['output'].stat().st_mode)==0o700
    assert all(stat.S_IMODE(p.stat().st_mode)==0o600 for p in f['output'].iterdir())


def test_interrupted_attempt_consumed(fixture,monkeypatch):
    f=fixture
    def interrupt(*_):raise KeyboardInterrupt()
    monkeypatch.setattr(runner,'read_status',interrupt)
    with pytest.raises(KeyboardInterrupt):execute(f)
    assert local.load_json(f['output']/'completion.private.json')['status']=='INTERRUPTED_NO_RETRY'
    with pytest.raises(local.Rejected,match='OUTPUT_ALREADY_EXISTS_NO_RETRY'):execute(f)


def test_operational_summary_identical_despite_private_disagreement(fixture):
    f=fixture;execute(f)
    summary=(f['output']/'operational_summary.json').read_bytes()
    f['output']=f['parent']/'SECOND_INVENTED_TEST_OPERATION'
    modify_table(f,'harmonized',lambda frame:frame.assign(inw6=[0,1]))
    execute(f)
    assert summary==(f['output']/'operational_summary.json').read_bytes()


@pytest.mark.parametrize('mode',['--authorize-local','--execute-local'])
def test_agent_guard_before_config_or_sources(mode):
    r=subprocess.run([sys.executable,'-B',str(ROOT/'run_status_diagnostic.py'),mode,
        '--config','/INVENTED_NOT_OPENED','--authorization','/INVENTED_NOT_OPENED','--output','/INVENTED_NOT_CREATED'],
        capture_output=True,text=True,env={**os.environ,'CODEX_SESSION_ID':'INVENTED_AGENT'})
    assert r.returncode==2 and '/INVENTED' not in r.stdout+r.stderr and not r.stderr


@pytest.mark.parametrize('problem',['missing','old_purpose','changed_code','changed_config','changed_output'])
def test_missing_or_reused_authorization_never_processes(fixture,monkeypatch,capsys,problem):
    f=fixture
    cfg=f['parent']/'INVENTED_CONFIG.json';local.write_json(cfg,f['config'])
    auth=f['parent']/'INVENTED_AUTH.json'
    record={'purpose':runner.PURPOSE,'output_binding':str(f['output']), 'authorized':True,
        'scope_confirmed_by_operator':True,'operator':'INVENTED_TEST_OPERATOR',
        'config_sha256':local.sha(cfg),'code_bindings':local.code_hashes()}
    if problem=='old_purpose':record['purpose']='OLD_COUNT_PURPOSE'
    elif problem=='changed_code':record['code_bindings']={}
    elif problem=='changed_config':record['config_sha256']='0'*64
    elif problem=='changed_output':record['output_binding']=str(f['parent']/'OTHER_INVENTED_DESTINATION')
    if problem!='missing':local.write_json(auth,record)
    monkeypatch.setattr(local,'require_local',lambda:None)
    monkeypatch.setattr(sys,'argv',['invented','--execute-local','--config',str(cfg),'--authorization',str(auth),'--output',str(f['output'])])
    assert local.cli(runner.PURPOSE,lambda *_:pytest.fail('Unauthorized processing'),runner.no_demo)==2
    assert not f['output'].exists()
    captured=capsys.readouterr()
    assert captured.out=='REVIEW ISSUE=LOCAL_OPERATION_NOT_COMPLETED_INSPECT_PRIVATE_RECEIPT\n' and not captured.err


def test_new_interactive_authorization_is_not_old_authorization(fixture,monkeypatch,capsys):
    f=fixture
    cfg=f['parent']/'INVENTED_CONFIG.json';local.write_json(cfg,f['config'])
    auth=f['parent']/'INVENTED_AUTH.json'
    monkeypatch.setattr(local,'require_local',lambda:None)
    monkeypatch.setattr(sys,'argv',['invented','--authorize-local','--config',str(cfg),'--authorization',str(auth),'--output',str(f['output'])])
    replies=iter(['INVENTED_TEST_OPERATOR','AUTHORIZE LOCAL SUPPLEMENTARY OPERATION'])
    monkeypatch.setattr('builtins.input',lambda _:next(replies))
    assert local.cli(runner.PURPOSE,lambda *_:pytest.fail('Authorization performed processing'),runner.no_demo)==0
    assert local.load_json(auth)['purpose']==runner.PURPOSE and not f['output'].exists()
    assert capsys.readouterr().out=='LOCAL_AUTHORIZATION_RECORDED_NO_DATA_PROCESSING\n'


def test_frozen_decoder_extraction_exact_and_no_count_symbols():
    assert not hasattr(decoder,'analyze') and not hasattr(decoder,'history') and not hasattr(decoder,'followup')
    tree=ast.parse((ROOT/'frozen_decoder.py').read_text())
    expected={'CountError','need','num','code','scalar','interview'}
    assert {n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}==expected
    source=(ROOT/'frozen_decoder.py').read_text()
    actual={n.name:hashlib.sha256(ast.get_source_segment(source,n).encode()).hexdigest()
            for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    assert actual==E['decoder_function_sha256']
    for name in ('diagnostic_engine.py','status_reader.py','run_status_diagnostic.py'):
        t=ast.parse((ROOT/name).read_text())
        imports=set()
        for node in ast.walk(t):
            if isinstance(node,ast.Import):imports.update(a.name.split('.')[0] for a in node.names)
            if isinstance(node,ast.ImportFrom):imports.add((node.module or '').split('.')[0])
        assert not imports & {'count_engine','run_counts','read_release','torch','sklearn'}


def test_private_scalar_text_never_returned():
    r=engine.classify(6,'INVENTED_SENSITIVE_TEXT',raw(6),M)
    assert 'INVENTED_SENSITIVE_TEXT' not in json.dumps(r)
    r=engine.classify(6,1,raw(6,'INVENTED_SENSITIVE_TEXT',0),M)
    assert 'INVENTED_SENSITIVE_TEXT' not in json.dumps(r)


def test_public_install_verify_no_overwrite_and_tamper(tmp_path):
    out=tmp_path/'NEW_PUBLIC_INSTALLATION';install(out);verify(out)
    with pytest.raises(ValueError):install(out)
    (out/'diagnostic_engine.py').write_text('INVENTED_TAMPER')
    with pytest.raises(ValueError):verify(out)


def test_historical_public_fingerprints_are_in_the_portable_evidence_ledger():
    ledger=local.load_json(ROOT/'PRIOR_PUBLIC_BINDINGS.json')
    assert all(len(expected)==64 for expected in ledger.values())
    assert ledger['results/hrs_elsa_final_count_feasibility_20261105/count_engine.py']==E['frozen_count_engine_sha256']
    assert ledger['results/hrs_elsa_final_count_feasibility_20261105/official_variable_map.json']==E['frozen_mapping_sha256']


def test_invalid_cli_does_not_print_private_arguments():
    r=subprocess.run([sys.executable,'-B',str(ROOT/'run_status_diagnostic.py'),'--bogus',
        'INVENTED_SENSITIVE_LOCATION'],capture_output=True,text=True)
    assert r.returncode==2 and not r.stderr
    assert r.stdout=='STOP ISSUE=INVALID_STATUS_DIAGNOSTIC_COMMAND\n'


def test_private_unresolved_template_creation_is_exclusive(tmp_path):
    from verify_public import new_config
    tmp_path.chmod(0o700)
    path=tmp_path/'NEW_UNRESOLVED_CONFIG.json'
    new_config(path)
    c=local.load_json(path)
    assert c['source_use_review']=='UNRESOLVED_NOT_AUTHORIZED' and c['reviewed_scope']==[]
    assert stat.S_IMODE(path.stat().st_mode)==0o600
    with pytest.raises(ValueError):new_config(path)


def test_completed_status_diagnostic_does_not_rewrite_registered_sources(fixture):
    f=fixture
    before={k:Path(d['path']).read_bytes() for k,d in f['config']['sources'].items()}
    registered=f['manifest_path'].read_bytes()
    execute(f)
    assert registered==f['manifest_path'].read_bytes()
    assert before=={k:Path(d['path']).read_bytes() for k,d in f['config']['sources'].items()}


def test_missing_harmonized_stata_response_retains_missing_category(fixture):
    f=fixture
    modify_table(f,'harmonized',lambda frame:frame.assign(inw6=[float('nan'),1]))
    execute(f)
    r=local.load_json(f['output']/'status_diagnostic.private.json')
    assert r['first_detected_target_conflict']['participation']=='PARTICIPATION_MISSING'
    assert 'STATA_MISSING_PLAIN' in r['waves']['6']['participation_raw_states']


def test_core_invalid_domain_summary_is_not_success(fixture):
    f=fixture
    modify_table(f,'core4',lambda frame:frame.assign(w4indout=[26,11]))
    with pytest.raises(local.Rejected,match='STATUS_DOMAIN_INCOMPATIBILITY_DIAGNOSTIC_PRESERVED'):execute(f)
    report=local.load_json(f['output']/'status_diagnostic.private.json')
    assert report['source_domain_error_observed'] is True
    assert not (f['output']/'operational_summary.json').exists()


def test_normalized_inputs_and_frozen_interview_decisions_are_unchanged():
    h={101:{'inw'+str(w):1 for w in range(1,10)}}
    cores={w:{101:raw(w)} for w in range(1,10)}
    before=copy.deepcopy((h,cores))
    kinds=[decoder.interview({'wave':w,'raw':cores[w][101]},M) for w in range(1,10)]
    engine.summarize(h,cores,M)
    assert (h,cores)==before
    assert kinds==[decoder.interview({'wave':w,'raw':cores[w][101]},M) for w in range(1,10)]


def test_preauthorization_scope_failure_never_prompts(fixture,monkeypatch,capsys):
    f=fixture;f['config']['source_use_review']='UNRESOLVED_NOT_AUTHORIZED'
    cfg=f['parent']/'INVENTED_CONFIG.json';local.write_json(cfg,f['config'])
    monkeypatch.setattr(sys,'argv',['run_status_diagnostic.py','--authorize-local','--config',str(cfg)])
    monkeypatch.setattr(runner,'cli',lambda *_:pytest.fail('Permission failure reached authorization prompt'))
    assert runner.main()==2
    assert capsys.readouterr().out=='STOP ISSUE=STATUS_CONFIG_NOT_READY_NO_AUTHORIZATION_RECORDED\n'


def test_synthetic_full_runtime_execution_keeps_console_static(fixture,monkeypatch,capsys):
    f=fixture
    cfg=f['parent']/'INVENTED_CONFIG.json';local.write_json(cfg,f['config'])
    auth=f['parent']/'INVENTED_NEW_PURPOSE_AUTH.json'
    local.write_json(auth,{'purpose':runner.PURPOSE,'output_binding':str(f['output']),
        'authorized':True,'scope_confirmed_by_operator':True,'operator':'INVENTED_TEST_OPERATOR',
        'config_sha256':local.sha(cfg),'code_bindings':local.code_hashes()})
    monkeypatch.setattr(local,'require_local',lambda:None)
    monkeypatch.setattr(sys,'argv',['invented','--execute-local','--config',str(cfg),'--authorization',str(auth),'--output',str(f['output'])])
    assert local.cli(runner.PURPOSE,runner.execute,runner.no_demo)==0
    result=capsys.readouterr()
    assert result.out=='REVIEW ISSUE=PRIVATE_OUTPUT_REQUIRES_DISCLOSURE_REVIEW\n' and not result.err
    assert (f['output']/'runtime.private.log').is_file()


def test_invalid_or_similar_linkage_never_fuzzy_matched():
    assert reader.key_class('00123')==(None,'INVALID_LINKAGE_STORAGE')
    assert reader.key_class(1.5)==(None,'INVALID_LINKAGE_VALUE')
    assert reader.key_class(123)[0]!=reader.key_class(1234)[0]
    h={123:{'inw'+str(w):1 for w in range(1,10)}}
    cores={w:{1234:raw(w)} for w in range(1,10)}
    r=engine.summarize(h,cores,M)
    assert all(q['missing_core_records']==q['unmatched_core_records']==1 for q in r['waves'].values())


@pytest.mark.parametrize('outcome,proxy,flag,core,basis', [
    (13,1,1,'CORE_PROXY_INTERVIEW','OUTCOME_BASED'),
    (21,0,1,'CORE_PARTIAL_INTERVIEW','OUTCOME_BASED'),
    (24,0,1,'CORE_INSTITUTIONAL_INTERVIEW','OUTCOME_BASED'),
    (11,0,0,'CORE_PERSONAL_INTERVIEW','OUTCOME_BASED'),
    (-1,1,1,'CORE_PROXY_INTERVIEW','ASKPX_FALLBACK'),
    (-1,1,0,'CORE_PROXY_INTERVIEW','ASKPX_FALLBACK'),
    (-1,1,float('nan'),'CORE_PROXY_INTERVIEW','ASKPX_FALLBACK')])
def test_real_stata_roundtrip_for_invented_survey_states(fixture,outcome,proxy,flag,core,basis):
    f=fixture
    modify_table(f,'core6',lambda frame:frame.assign(w6indout=[outcome,11],askpx=[proxy,0]))
    modify_table(f,'harmonized',lambda frame:frame.assign(inw6=[flag,1]))
    execute(f)
    r=local.load_json(f['output']/'status_diagnostic.private.json')
    assert any('|'+core+'|'+basis in cell for cell in r['waves']['6']['classification_matrix'])
    if basis=='ASKPX_FALLBACK':
        assert r['waves']['6']['interpretations']['UNRESOLVED_DECODER_AMBIGUITY']==1


def test_invented_stata_missed_wave_and_reentry(fixture):
    f=fixture
    modify_table(f,'core5',lambda frame:frame.iloc[1:].copy())
    modify_table(f,'harmonized',lambda frame:frame.assign(inw5=[0,1]))
    execute(f)
    r=local.load_json(f['output']/'status_diagnostic.private.json')
    assert r['first_detected_target_conflict'] is None
    assert r['waves']['5']['missing_core_records']==1


def test_invented_stata_wave_one_proxy_domain(fixture):
    f=fixture
    modify_table(f,'core1',lambda frame:frame.assign(askpx1=[0,2]))
    with pytest.raises(local.Rejected,match='STATUS_DOMAIN_INCOMPATIBILITY_DIAGNOSTIC_PRESERVED'):execute(f)


def test_parser_warning_is_sanitized_without_scalar_leak(fixture,monkeypatch,capsys):
    import warnings
    def warning(*args,**kwargs):warnings.warn('INVENTED_PRIVATE_SCALAR',UserWarning)
    monkeypatch.setattr(pd.io.stata.StataReader,'read',warning)
    with pytest.raises(local.Rejected,match='STATUS_SOURCE_UNREADABLE_OR_CORRUPT'):
        reader.read_status(fixture['config']['sources']['core6']['path'],'core6')
    captured=capsys.readouterr()
    assert not captured.out and not captured.err
