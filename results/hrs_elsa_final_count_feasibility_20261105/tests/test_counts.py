"""Synthetic only. No clinical file, private config or historical output reads."""
import copy,json,os,sys,subprocess,tempfile,math
from pathlib import Path
import pytest
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from count_engine import *
from synthetic_fixture import person,raw_visit,features,invented_people
from precision import *
M=json.loads((R/'official_variable_map.json').read_text());P=json.loads((R/'PROTOCOL.json').read_text())
def v(p,w):return next(x for x in p['visits'] if x['wave']==w)

@pytest.mark.parametrize('start',[1,3,4,6])
def test_continuing_and_first_interview_negative_proofs(start):
    p=person(M,start=start)
    assert history(p,6,'mi',M)=='VERIFIED_ABSENT'
    assert history(p,6,'stroke',M)=='VERIFIED_ABSENT'

@pytest.mark.parametrize('w',[3,4,5,6,7,8,9])
def test_nonendpoint_conditions_do_not_require_global_none(w):
    p=person(M,start=w);raw=v(p,w)['raw'];raw['hedim96']=0;raw['hedimbp']=1;raw['hedimdi']=1
    assert history(p,w,'mi',M)=='VERIFIED_ABSENT'
    assert history(p,w,'stroke',M)=='VERIFIED_ABSENT'

def test_wave1_proxy_no_uses_2_not_0():
    p=person(M);assert interview(v(p,1),M)=='personal'
    v(p,1)['raw']['askpx1']=0
    with pytest.raises(CountError):interview(v(p,1),M)

def test_w4_EUL_name_is_w4indout():
    fs=M['waves']['4']['fields'];assert 'w4indout' in fs and 'outindw4' not in fs

def test_w9_confirmation_absence_not_fabricated():
    assert 'hedacmi' not in M['waves']['9']['fields']
    p=person(M);assert observation(v(p,9),'mi',M)=='negative_response'
    v(p,9)['raw']['hedacmi']=-1
    with pytest.raises(CountError):analyze([p],M,P)

@pytest.mark.parametrize('w',[2,3,4,6,7,9])
def test_positional_feedforward_target_in_other_slot(w):
    p=person(M);r=v(p,w)['raw'];fs=M['waves'][str(w)]['fields']
    slots=[n for n in fs if n.startswith('hedaw') or (w==2 and n.startswith('hediaw'))]
    r[slots[0]]=8
    assert observation(v(p,w),'stroke',M)=='historical_unconfirmed'
    assert history(p,w,'stroke',M)!='VERIFIED_ABSENT'

def test_unknown_feedforward_never_absence():
    p=person(M);v(p,6)['raw']['hedawot']=-8
    assert history(p,6,'mi',M)=='UNKNOWN'

@pytest.mark.parametrize('missing',[None,'.','.a','.z',-1,-8,-9,float('nan')])
def test_missing_merged_response_not_nonevent(missing):
    p=person(M);v(p,6)['raw']['hedimmi']=missing
    assert history(p,6,'mi',M)!='VERIFIED_ABSENT'

def test_none_and_positive_contradiction_unknown():
    p=person(M);v(p,6)['raw']['hedimmi']=1
    assert observation(v(p,6),'mi',M)=='unknown'

def test_documented_nonendpoint_valvular_or_ischaemic_response_allowed():
    p=person(M,start=4);r=v(p,4)['raw'];r['hedim96']=0;r['hedizm51']=1
    assert history(p,4,'mi',M)=='VERIFIED_ABSENT'
    assert history(p,4,'stroke',M)=='VERIFIED_ABSENT'

def test_screen_zero_not_negative_proof():
    p=person(M,start=6);p['participation']['1']=1;p['screening_history']={'6':{'mi':0}}
    assert history(p,6,'mi',M)=='UNKNOWN'

def test_screen_positive_blocks_absence():
    p=person(M);p['screening_history']={'6':{'mi':1}}
    assert history(p,6,'mi',M)=='PRIOR_RECORD_UNCONFIRMED'

def test_derived_history_zero_not_proof_positive_never_ignored():
    p=person(M);v(p,4)['raw']['hediagmi']=3
    assert history(p,4,'mi',M)=='PRIOR_RECORD_UNCONFIRMED'
    v(p,4)['raw']['hediagmi']=0;p['participation']['1']=None
    # An earlier observed lifetime personal Wave1 still proves history here.
    # Remove it to show that the derived zero cannot supply the missing anchor.
    p['visits']=[x for x in p['visits'] if x['wave']!=1]
    assert history(p,4,'mi',M)=='UNKNOWN'

def test_minimal_reader_columns_no_fabricated_w9_confirmation():
    from read_release import count_fields
    fields=count_fields(9,M['waves']['9']['fields'])
    assert 'hedacmi' not in fields and 'heagb' not in fields and 'henmmi' not in fields
    assert 'hedimst' in fields and 'hedaw95' in fields

def test_prior_MI_exclusion_and_stroke_distinction():
    p=person(M,event_wave=3)
    assert history(p,6,'mi',M)=='CONFIRMED_PRIOR_REPORT'
    assert history(p,6,'stroke',M)=='VERIFIED_ABSENT'
    r=analyze([p],M,P)['designs']['W6_W9']['flow_ordered'];assert r['excluded_prior_MI_first']==1

def test_prior_stroke_exclusion():
    p=person(M,event_wave=3,component='stroke')
    r=analyze([p],M,P)['designs']['W6_W9']['flow_ordered'];assert r['excluded_prior_stroke_after_MI']==1

def test_missing_participation_does_not_supply_lifetime_context():
    p=person(M,start=4);p['participation']['1']=None
    assert history(p,4,'mi',M)=='UNKNOWN'

def test_undocumented_prior_interview_breaks_chain():
    p=person(M);p['visits']=[x for x in p['visits'] if x['wave']!=5]
    assert history(p,6,'mi',M)=='UNKNOWN'

def test_documented_missed_wave_can_be_covered_by_since_last_interview():
    p=person(M);p['visits']=[x for x in p['visits'] if x['wave']!=5];p['participation']['5']=0
    assert history(p,6,'mi',M)=='VERIFIED_ABSENT'

def test_new_positive_does_not_require_imputed_intervening_negatives():
    p=person(M,event_wave=8);v(p,7)['raw']['hedimmi']=-8
    assert followup(p,6,9,'mi',M,'wave_window')=='INCIDENT_REPORT'
    v(p,8)['raw']['hedimmi']=0;v(p,8)['raw']['hedim96']=1
    assert followup(p,6,9,'mi',M,'wave_window')!='OBSERVED_NONEVENT'

def test_unresolved_historical_appearance_not_repaired_by_later_new_list():
    p=person(M,event_wave=8);v(p,7)['raw']['hedawot']=3
    assert followup(p,6,9,'mi',M,'wave_window')=='UNKNOWN_EVENT_OR_TIMING'

def test_disputed_diagnosis_never_reset_negative():
    p=person(M,event_wave=3);v(p,4)['raw']['hedacmi']=2;v(p,4)['raw']['hedanmi']=1
    assert history(p,6,'mi',M)=='DISPUTED'

def test_proxy_lifetime_yes_cannot_be_personal_negative():
    p=person(M,event_wave=3);v(p,3)['raw']['w3indout']=13;v(p,3)['raw']['askpx']=1
    assert history(p,6,'mi',M)!='VERIFIED_ABSENT'

def test_case_and_repeated_reports_count_person_once():
    p=person(M,event_wave=8)
    r=analyze([p],M,P)['designs']['W6_W9']['outcomes']['wave_window']['summary']
    assert r['unique_composite_incident_reports']==1 and r['incident_MI_reports']==1

def test_primary_wave_window_and_strict_calendar_results_remain_distinct():
    p=person(M,event_wave=9)
    assert followup(p,6,9,'mi',M,'wave_window')=='INCIDENT_REPORT'
    assert followup(p,6,9,'mi',M,'fixed_six_year')=='UNKNOWN_EVENT_OR_TIMING'

def test_absent_followup_not_negative_and_early_case_retained():
    p=person(M);p['visits']=[x for x in p['visits'] if x['wave']!=9]
    assert followup(p,6,9,'mi',M,'wave_window')!='OBSERVED_NONEVENT'
    p=person(M,event_wave=7);p['visits']=[x for x in p['visits'] if x['wave']!=9]
    assert followup(p,6,9,'mi',M,'wave_window')=='INCIDENT_REPORT'

def test_proxy_followup_not_negative():
    p=person(M);v(p,9)['raw']['w9indout']=13;v(p,9)['raw']['askpx']=1
    assert followup(p,6,9,'mi',M,'wave_window')=='UNKNOWN_PROXY'

def test_death_status_censored_not_nonevent():
    p=person(M);v(p,9)['raw']['w9indout']=95
    assert followup(p,6,9,'mi',M,'wave_window')=='CENSORED_DEATH_STATUS'
    p=person(M,event_wave=7);v(p,9)['raw']['w9indout']=95
    assert followup(p,6,9,'mi',M,'wave_window')=='INCIDENT_REPORT'

def test_personal_after_death_rejected():
    p=person(M);v(p,8)['raw']['w8indout']=95
    with pytest.raises(CountError):followup(p,6,9,'mi',M,'wave_window')

def test_unavailable_unrecognized_TIA_code_never_stroke():
    p=person(M);v(p,8)['raw']['hedimst']=2
    with pytest.raises(CountError):followup(p,6,9,'stroke',M,'wave_window')

def test_horizon_outside_tolerance_not_negative():
    p=person(M);v(p,9)['raw']['iintdaty']=2020
    assert followup(p,6,9,'mi',M,'wave_window')!='OBSERVED_NONEVENT'

def test_unrecognized_timing_policy_never_silently_substituted():
    with pytest.raises(CountError):followup(person(M),6,9,'mi',M,'UNREGISTERED_TIMING')

def test_zero_eligible_no_model_approval():
    p=person(M);v(p,4)['raw']['indager']=49;v(p,6)['raw']['indager']=-8
    r=analyze([p],M,P);assert not r['training_authorized']
    assert all(d['outcomes']['wave_window']['summary']['eligible_baseline']==0 for d in r['designs'].values())

def test_duplicate_person_and_wave_fail():
    p=person(M)
    with pytest.raises(CountError):analyze([p,p],M,P)
    p['visits'].append(copy.deepcopy(p['visits'][-1]))
    with pytest.raises(CountError):analyze([p],M,P)

def test_composite_union_not_sum_when_both_events():
    p=person(M,event_wave=7);v(p,8)['raw']['hedimst']=1;v(p,8)['raw']['hedim96']=0
    r=analyze([p],M,P)['designs']['W6_W9']['outcomes']['wave_window']['summary']
    assert r['incident_MI_reports']==1 and r['incident_stroke_reports']==1 and r['unique_composite_incident_reports']==1

def test_no_future_wave_in_earlier_design():
    p=person(M,event_wave=8)
    assert analyze([p],M,P)['designs']['W4_W7']['outcomes']['wave_window']['summary']['unique_composite_incident_reports']==0

def test_temporal_predictor_rules():
    p=person(M);assert feature_status(p,6,M)[0]=='COMPLETE_TIMELY'
    p['features']['6']['sbp']['available_upper']='2012-07-01'
    assert feature_status(p,6,M)[0]=='INCOMPLETE_OR_UNTIMELY'
    p['features']['6']['sbp']['source_wave']=8
    with pytest.raises(CountError):feature_status(p,6,M)

def test_automatic_baseline_feature_adapter_no_future_diabetes():
    from baseline_features import derive
    p=person(M)
    h={f'r{w}{s}':0 for w in [4,6] for s in ['smokev','smoken','rxhibp']}
    h['r6diabe']=1  # deliberately ignored; could be retrospectively revised
    nurses={w:{'visyear':2000+2*w,'vismon':5,'sysval':120,'diaval':75,'bmival':25} for w in [4,6]}
    p['features'],qc=derive(p,h,nurses,M)
    assert p['features']['6']['diabetes']['value']==0
    assert feature_status(p,6,M)[0]=='COMPLETE_TIMELY' and not qc

def test_automatic_feature_known_diabetes_allowed_in_endpoint_cohort():
    from baseline_features import derive
    p=person(M,start=4);v(p,4)['raw'].update(hedim96=0,hedimdi=1)
    h={f'r{w}{s}':0 for w in [4,6] for s in ['smokev','smoken','rxhibp']}
    fs,qc=derive(p,h,{},M)
    assert fs['4']['diabetes']['value']==1
    assert history(p,4,'mi',M)=='VERIFIED_ABSENT'

def test_automatic_feature_later_nurse_cannot_be_backdated():
    from baseline_features import derive
    p=person(M);h={f'r{w}{s}':0 for w in [4,6] for s in ['smokev','smoken','rxhibp']}
    ns={6:{'visyear':2012,'vismon':7,'sysval':120,'diaval':75,'bmival':25}}
    p['features'],_=derive(p,h,ns,M)
    assert feature_status(p,6,M)[0]=='INCOMPLETE_OR_UNTIMELY'

def test_automatic_feature_contradictory_smoking_kept_unknown():
    from baseline_features import derive
    p=person(M);h={'r6smokev':0,'r6smoken':1,'r6rxhibp':0}
    fs,qc=derive(p,h,{},M)
    assert fs['6']['smoking']['value'] is None and 'CONTRADICTORY_SMOKING_W6' in qc

def test_diabetes_feature_does_not_read_followup_values():
    from baseline_features import derive
    p=person(M);v(p,8)['raw'].update(hedim96=0,hedimdi=1)
    fs,_=derive(p,{}, {},M)
    assert fs['6']['diabetes']['value']==0

def test_missing_predictors_not_missing_outcomes():
    p=person(M,event_wave=8);p['features']['6']['sbp']['value']=None
    r=analyze([p],M,P)['designs']['W6_W9']['outcomes']['wave_window']['summary']
    assert r['unique_composite_incident_reports']==1 and r['timely_complete_case_binary']==0

@pytest.mark.parametrize('value',[None,-1,-8,-9,0,'.a'])
def test_missing_or_invalid_BP_never_complete(value):
    p=person(M);p['features']['6']['sbp']['value']=value
    assert feature_status(p,6,M)[0]=='INCOMPLETE_OR_UNTIMELY'

def test_unknown_exposure_not_untouched_test():
    p=person(M)
    # Find an invented token assigned to evaluation; no outcome-based selection.
    for i in range(1000):
        p['token']='INVENTED_TEST_ROLE_'+str(i)
        if partition(p['token'],P)=='evaluation':break
    p['prior_model_use']='unknown';r=analyze([p],M,P)
    assert r['designs']['W6_W9']['outcomes']['wave_window']['potential_untouched_evaluation']=={}

def test_bad_partition_fractions_rejected():
    q=copy.deepcopy(P);q['partition_fractions']['evaluation']=.9
    with pytest.raises(CountError):analyze([person(M)],M,q)

def test_invalid_or_old_config_not_authorization():
    from run_counts import validate_config
    from local_execution import Rejected,sha
    config={'schema':'elsa-final-count-local-config-v1','mode':'independent_local_only','no_models':True,
            'protocol_sha256':sha(R/'PROTOCOL.json'),'mapping_sha256':sha(R/'official_variable_map.json')}
    with pytest.raises(Rejected):validate_config(config)
    config['source_use_review']='INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION'
    assert validate_config(config)
    config['mapping_sha256']='0'*64
    with pytest.raises(Rejected):validate_config(config)

def test_dataset_reader_agent_guard_before_dataset_open():
    from read_release import load_selected
    with pytest.raises(Exception):load_selected(Path('/INVENTED_NOT_READ'),{'idauniq'})

def test_source_hash_mismatch_fails_without_inference(tmp_path):
    from local_execution import descriptor,Rejected
    p=tmp_path/'INVENTED_SOURCE';p.write_bytes(b'INVENTED_PUBLIC_SYNTHETIC_BYTES')
    with pytest.raises(Rejected):descriptor({'path':str(p),'sha256':'0'*64})

def test_synthetic_stata_reader_only_invented_values(tmp_path,monkeypatch):
    import pandas as pd
    import read_release
    monkeypatch.setattr(read_release,'require_local',lambda:None)
    path=tmp_path/'INVENTED_NOT_CLINICAL.dta'
    pd.DataFrame({'idauniq':[101,102],'w6indout':[11,13],'unused':[99,99]}).to_stata(path,write_index=False,version=118)
    r=read_release.load_selected(path,{'idauniq','w6indout'})
    assert set(r)=={'ELSA_NUMERIC_101','ELSA_NUMERIC_102'} and all('unused' not in x for x in r.values())

def test_missing_whole_column_is_mapping_error(tmp_path,monkeypatch):
    import pandas as pd
    import read_release
    monkeypatch.setattr(read_release,'require_local',lambda:None)
    path=tmp_path/'INVENTED.dta';pd.DataFrame({'idauniq':[101]}).to_stata(path,write_index=False,version=118)
    with pytest.raises(CountError):read_release.load_selected(path,{'idauniq','hedimmi'},{'idauniq','hedimmi'})

def test_newly_present_forbidden_confirmation_rejects_revision(tmp_path,monkeypatch):
    import pandas as pd
    import read_release
    monkeypatch.setattr(read_release,'require_local',lambda:None)
    path=tmp_path/'INVENTED.dta';pd.DataFrame({'idauniq':[101],'hedacmi':[-1]}).to_stata(path,write_index=False,version=118)
    with pytest.raises(CountError):read_release.load_selected(path,{'idauniq'},forbidden={'hedacmi'})

def test_end_to_end_twelve_INVENTED_stata_tables_count_only(tmp_path,monkeypatch):
    import pandas as pd,hashlib
    import read_release
    monkeypatch.setattr(read_release,'require_local',lambda:None)
    subjects=[person(M,i=10,event_wave=8),person(M,i=11),person(M,i=12,event_wave=3)]
    ids=[900000001,900000002,900000003];sources={}
    for w in range(1,10):
        basename=M['waves'][str(w)]['dataset_basename'];path=tmp_path/basename
        pd.DataFrame([dict(idauniq=pid,**v(p,w)['raw']) for pid,p in zip(ids,subjects)]).to_stata(path,write_index=False,version=118)
        sources['core'+str(w)]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dataset_basename':basename}
    path=tmp_path/'gh_elsa_h.dta'
    pd.DataFrame([dict(idauniq=pid,**{'inw'+str(w):1 for w in range(1,10)},
        **{f'r{w}{s}':0 for w in [4,6] for s in ['hrtatte','stroke','smokev','smoken','rxhibp']}) for pid in ids]).to_stata(path,write_index=False,version=118)
    sources['harmonized']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dataset_basename':path.name}
    measurement_sources={}
    for w in [4,6]:
        basename=M['nurse'][str(w)]['dataset_basename'];path=tmp_path/basename
        pd.DataFrame([{'idauniq':pid,'visyear':2000+2*w,'vismon':5,'sysval':120,'diaval':75,'bmival':25} for pid in ids]).to_stata(path,write_index=False,version=118)
        measurement_sources[str(w)]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dataset_basename':basename}
    people,bindings,qa=read_release.load_people({'source_format':'registered_stata_tables_v1','sources':sources,'measurement_sources':measurement_sources,'feature_metadata':None},M)
    r=analyze(people,M,P)
    assert r['designs']['W6_W9']['outcomes']['wave_window']['summary']['unique_composite_incident_reports']==1
    assert r['designs']['W6_W9']['flow_ordered']['excluded_prior_MI_first']==1
    assert len(bindings)==12 and qa['automatic_baseline_feature_derivation'] and not qa['feature_metadata_supplied']
    assert r['designs']['W6_W9']['outcomes']['wave_window']['summary']['timely_complete_case_binary']==2
    assert '900000001' not in json.dumps(r)

def test_old_operation_authorization_never_enters_callback(tmp_path,monkeypatch,capsys):
    import local_execution
    monkeypatch.setattr(local_execution,'require_local',lambda:None)
    out=tmp_path/'NEW_INVENTED_OUTPUT'
    monkeypatch.setattr(sys,'argv',['INVENTED','--execute-local','--config','INVENTED_CONFIG',
       '--authorization','INVENTED_AUTH','--output',str(out)])
    monkeypatch.setattr(local_execution,'load_json',lambda p:{'purpose':'OLD_CONSUMED_OPERATION','output_binding':str(out.resolve()),'authorized':True})
    called=[]
    rc=local_execution.cli('NEW_COUNT_PURPOSE',lambda c,o:called.append(True),lambda o:None)
    assert rc==2 and not called and not out.exists()
    assert 'OLD_CONSUMED_OPERATION' not in capsys.readouterr().out

def test_new_counter_errors_never_contain_sensitive_context():
    p=person(M);v(p,6)['raw']['hedimmi']='INVENTED_SENSITIVE_SCALAR'
    with pytest.raises(CountError) as e:history(p,6,'mi',M)
    assert str(e.value)=='NONNUMERIC_SOURCE_REPRESENTATION'

def test_precision_single_class_never_favorable_validation_claim():
    assert auc_se(10,0) is None and auc_se(0,10) is None
    assert both_classes_probability(10,0,5)==0

def test_source_product_not_selected_just_by_renamed_filename(monkeypatch):
    import read_release
    monkeypatch.setattr(read_release,'require_local',lambda:None)
    cfg={'source_format':'registered_stata_tables_v1','sources':{k:{'dataset_basename':'WRONG_PUBLIC_PRODUCT'} for k in ['harmonized']+['core'+str(w) for w in range(1,10)]}}
    with pytest.raises(CountError):read_release.load_people(cfg,M)

def test_public_installation_roundtrip_no_overwrite_and_hash_rejection(tmp_path):
    from verify_public import install,verify
    out=tmp_path/'NEW_PUBLIC_ONLY_INSTALLATION';install(out);verify(out)
    assert (out/'run_counts.py').is_file() and not (out/'public_documentation').exists()
    with pytest.raises(ValueError):install(out)
    (out/'official_variable_map.json').write_text('INVENTED_TAMPER')
    with pytest.raises(ValueError):verify(out)

def test_unsafe_public_manifest_cannot_traverse(tmp_path):
    from verify_public import verify
    (tmp_path/'RELEASE_MANIFEST.json').write_text(json.dumps({'files':{'../INVENTED_NEVER_OPENED':'0'*64}}))
    with pytest.raises(ValueError):verify(tmp_path)

def test_feature_units_fail_closed():
    p=person(M);p['features']['6']['sbp']['unit']='kPa'
    with pytest.raises(CountError):feature_status(p,6,M)

def test_no_features_means_not_computed_not_zero_test_support():
    p=person(M);p['features']={};r=analyze([p],M,P)
    q=summarize(r)['designs']['W6_W9'];assert q['potential_untouched_test_case_support'] is None

def test_same_person_partition_across_windows_and_outcome_blind():
    p=person(M);a=partition(p['token'],P);p2=person(M,event_wave=8)
    assert a==partition(p2['token'],P)

def test_component_and_flow_partition_accounting_no_ID_leak():
    r=analyze(invented_people(M),M,P);s=json.dumps(r)
    assert 'INVENTED_FINAL_COUNT_PERSON_' not in s and 'token' not in s
    for d in r['designs'].values():
        for out in d['outcomes'].values():
            x=out['summary'];assert x['eligible_baseline']==x['ascertained_binary_outcomes']+x['unknown_disputed_or_censored']

def test_ordinary_runtime_agent_guard_before_config_read():
    env=dict(os.environ,CODEX_SESSION_ID='INVENTED_AGENT')
    r=subprocess.run([sys.executable,'-B',str(R/'run_counts.py'),'--execute-local',
        '--config','/INVENTED_CONFIG_NOT_READ','--authorization','/INVENTED_AUTH_NOT_READ','--output','/INVENTED_NOT_CREATED'],capture_output=True,text=True,env=env)
    assert r.returncode==2 and '/INVENTED' not in r.stdout+r.stderr

def test_authorization_agent_guard_precedes_config_read():
    env=dict(os.environ,CODEX_SESSION_ID='INVENTED_AGENT')
    r=subprocess.run([sys.executable,'-B',str(R/'run_counts.py'),'--authorize-local',
        '--config','/INVENTED_CONFIG_NEVER_OPENED'],capture_output=True,text=True,env=env)
    assert r.returncode==2 and 'NO_AUTHORIZATION_RECORDED' in r.stdout and '/INVENTED' not in r.stdout+r.stderr

def test_bad_config_rejected_before_any_authorization_prompt(monkeypatch,capsys):
    import run_counts
    monkeypatch.setattr(sys,'argv',['INVENTED','--authorize-local','--config','INVENTED_CONFIG'])
    monkeypatch.setattr(run_counts,'require_local',lambda:None)
    monkeypatch.setattr(run_counts,'load_json',lambda p:{'schema':'WRONG_INVENTED_SCHEMA'})
    called=[];monkeypatch.setattr(run_counts,'cli',lambda *args:called.append(True))
    assert run_counts.main()==2 and not called
    assert 'NO_AUTHORIZATION_RECORDED' in capsys.readouterr().out

def test_public_help_is_success_without_private_inputs():
    r=subprocess.run([sys.executable,'-B',str(R/'run_counts.py'),'--help'],capture_output=True,text=True)
    assert r.returncode==0 and '--authorize-local' in r.stdout

def test_exact_linkage_no_fuzzy_strings():
    from read_release import person_key
    assert person_key(123)==person_key(123.0)
    assert person_key(123)!=person_key(1234)
    with pytest.raises(CountError):person_key('00123')

def test_synthetic_planning_not_performance():
    assert required_cases()==62 and required_cases(.9,.05)==139
    assert auc_se(0,100) is None and wilson(0,0) is None
    assert both_classes_probability(1,1,2)==1
    assert both_classes_probability(0,10,5)==0
    assert summarize(analyze(invented_people(M),M,P))['scope']=='PLANNING_ASSUMPTIONS_NOT_OBSERVED_MODEL_METRICS'

def test_exclusive_outputs_failure_interruption_and_no_retry(tmp_path):
    from local_execution import exclusive_output,Rejected
    out=tmp_path/'INVENTED_OUTPUT'
    with pytest.raises(KeyboardInterrupt):
        with exclusive_output(out,False):raise KeyboardInterrupt()
    rec=json.loads((out/'completion.private.json').read_text())
    assert rec['attempt_consumed'] and rec['status']=='INTERRUPTED_NO_RETRY'
    assert out.stat().st_mode&0o777==0o700
    assert (out/'completion.private.json').stat().st_mode&0o777==0o600
    with pytest.raises(Rejected):
        with exclusive_output(out,False):pass
