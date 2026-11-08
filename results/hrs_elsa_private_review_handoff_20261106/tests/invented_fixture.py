"""Entirely invented metadata and aggregates. NOT genuine authorization."""
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/reference'))
import diagnostic_engine as frozen_diagnostic


def mapping():
    c=json.loads((ROOT/'references/PUBLIC_CONTRACT.json').read_text())
    return {'waves':{w:{'fields':{d['outcome_field']:{'values':d['outcome_values']},
             d['proxy_field']:{'values':d['proxy_values']}}} for w,d in c['wave_status_domains'].items()}}


def invented_report():
    harmonized={i:{'inw'+str(w):1 for w in range(1,10)} for i in (700001,700002,700003)}
    cores={w:{i:{('indoc' if w==1 else f'w{w}indout'):11,
                  ('askpx1' if w<3 else 'askpx'):2 if w==1 else 0} for i in harmonized} for w in range(1,10)}
    harmonized[700001]['inw4']=0
    harmonized[700002]['inw6']=None
    cores[6][700002].update(w6indout=-1,askpx=1)
    del cores[7][700003];harmonized[700003]['inw7']=0
    cores[9][799999]={'w9indout':11,'askpx':0} # INVENTED unmatched linkage, not a written ID.
    return frozen_diagnostic.summarize(harmonized,cores,mapping())


def create_case(tmp_path):
    import offline_scientific_review as tool
    private=tmp_path/'INVENTED_PRIVATE';private.mkdir(mode=0o700)
    old=private/'INVENTED_HISTORICAL';old.mkdir(mode=0o700)
    dout=old/'INVENTED_DIAGNOSTIC';dout.mkdir(mode=0o700)
    cout=old/'INVENTED_FAILED_COUNT';cout.mkdir(mode=0o700)
    fresh=private/'INVENTED_NEW_REVIEW';fresh.mkdir(mode=0o700)
    files={}
    def write(role,filename,value,parent=old):
        p=parent/filename;p.write_text(json.dumps(value,indent=2)+'\n');p.chmod(0o600)
        files[role]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()};return files[role]
    contract=tool.public_json('references/PUBLIC_CONTRACT.json');e=contract['source_evidence']
    sources={role:{'path':'/INVENTED_CLINICAL_NEVER_OPEN/'+base,'sha256':hashlib.sha256(('INVENTED_'+role).encode()).hexdigest(),
        'dataset_basename':base,'claimed_archive_edition':'UNRESOLVED'} for role,base in e['required_products'].items()}
    registration={'schema':'elsa-private-source-registration-v1','status':'REGISTERED_LOCAL_MEMBER_BINDINGS_ONLY_COUNT_NOT_AUTHORIZED',
        'attempt_consumed':True,'members':[{'role':role,'materialized_file':s,'uncompressed_member_sha256':s['sha256']} for role,s in sources.items()]}
    for name, value in [('public_contract_sha256',e['registration_public_contract_sha256']),
        ('registration_protocol_sha256',e['registration_protocol_sha256']),('registration_code_bindings',e['registration_code_bindings']),
        ('count_tool_release_sha256',e['count_tool_release_sha256']),('count_mapping_sha256',e['frozen_mapping_sha256']),
        ('count_protocol_sha256',e['frozen_protocol_sha256'])]:registration[name]=value
    reg=write('source_registration','INVENTED_registration.json',registration)
    dc={'schema':'elsa-status-diagnostic-local-config-v1','mode':'independent_local_only','no_models':True,'no_event_counts':True,
        'source_use_review':'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_STATUS_ONLY_OPERATION',
        'reviewed_scope':['READ_REGISTERED_SOURCE_AND_INTEGRITY_METADATA','HASH_REGISTERED_SOURCE_BYTES',
             'READ_LINKAGE_AND_INTERVIEW_STATUS_COLUMNS_ONLY','WRITE_PRIVATE_AGGREGATE_STATUS_DIAGNOSTICS'],
        'protocol_sha256':contract['diagnostic_protocol_sha256'],'mapping_sha256':e['frozen_mapping_sha256'],
        'sources':sources,'source_registration':reg}
    fc={'schema':'elsa-final-count-local-config-v1','mode':'independent_local_only','no_models':True,
        'source_use_review':'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION','source_format':'registered_stata_tables_v1',
        'protocol_sha256':e['frozen_protocol_sha256'],'mapping_sha256':e['frozen_mapping_sha256'],'sources':copy.deepcopy(sources)}
    dcdesc=write('diagnostic_config','INVENTED_diagnostic_config.json',dc)
    fcdesc=write('failed_count_config','INVENTED_count_config.json',fc)
    for role,cfg,purpose,binding,destination in [('diagnostic_authorization',dcdesc,contract['diagnostic_purpose'],contract['diagnostic_code_bindings'],dout),
              ('failed_count_authorization',fcdesc,contract['count_purpose'],contract['count_code_bindings'],cout)]:
        write(role,'INVENTED_'+role+'.json',{'purpose':purpose,'authorized':True,'scope_confirmed_by_operator':True,
            'operator':'INVENTED_FIXTURE_NOT_A_REAL_APPROVAL','config_sha256':cfg['sha256'],'code_bindings':binding,'output_binding':str(destination)})
    write('diagnostic_completion','completion.private.json',{'status':'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED','attempt_consumed':True},dout)
    write('failed_count_completion','completion.private.json',{'status':'FAILED_NO_RETRY','attempt_consumed':True,
        'issue':'ELIGIBILITY_PROCESSING_PARTICIPATION_INTERVIEW_CONFLICT'},cout)
    report=invented_report();report['bindings']={'source_registration_sha256':reg['sha256'],
        'sources':{k:{'sha256':s['sha256'],'dataset_basename':s['dataset_basename']} for k,s in sources.items()},
        'protocol_sha256':dc['protocol_sha256'],'mapping_sha256':dc['mapping_sha256'],'code_bindings':contract['diagnostic_code_bindings']}
    write('diagnostic_report','status_diagnostic.private.json',report,dout)
    write('diagnostic_input_validation','input_validation.private.json',{'schema':'elsa-status-input-validation-v1',
        'participant_rows_or_keys_written':False,'linkage_quality':{role:{k:0 for k in
            ('MISSING_LINKAGE','INVALID_LINKAGE_STORAGE','INVALID_LINKAGE_VALUE','DUPLICATE_LINKAGE')} for role in sources}},dout)
    write('diagnostic_integrity','diagnostic_integrity.private.json',{'schema':'elsa-status-result-integrity-v1','purpose':contract['diagnostic_purpose'],
        'outputs':{'status_diagnostic.private.json':files['diagnostic_report']['sha256'],
                   'input_validation.private.json':files['diagnostic_input_validation']['sha256']}},dout)
    config=tool.public_json('review_config.template.json');config.update(source_use_review=tool.REVIEW,isolation_review=tool.ISOLATION,
        reviewed_scope=tool.public_json('references/REVIEW_SCOPE.json')['required_scope'],private_root=str(private),evidence=files)
    configpath=fresh/'INVENTED_REVIEW_CONFIG.json';configpath.write_text(json.dumps(config));configpath.chmod(0o600)
    return config,configpath,fresh/'INVENTED_NEW_OUTPUT',fresh/'INVENTED_NEW_AUTH.json'


def change(config,role,mutator):
    d=config['evidence'][role];p=Path(d['path']);v=json.loads(p.read_text());mutator(v)
    p.write_text(json.dumps(v));d['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
