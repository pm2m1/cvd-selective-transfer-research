"""Invented historical metadata only; no genuine data/permissions/receipts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/'tests/frozen_review_tools'
sys.path.insert(0,str(ROOT))
import prepare_offline_review_config as helper


def case(tmp_path):
    original,template=helper.review_tool(TOOLS)
    private=tmp_path/'INVENTED_PRIVATE';private.mkdir(mode=0o700)
    folders={n:private/n for n in helper.HISTORICAL}
    for p in folders.values():p.mkdir(mode=0o700)
    diag=folders[helper.HISTORICAL[0]];count=folders[helper.HISTORICAL[1]];reg=folders[helper.HISTORICAL[2]]
    dout=diag/'INVENTED_status_output';dout.mkdir(mode=0o700)
    cout=count/'INVENTED_failed_output';cout.mkdir(mode=0o700)
    rout=reg/'INVENTED_registration_output';rout.mkdir(mode=0o700)
    run=private/'hrs_elsa_private_review_20261106_run';run.mkdir(mode=0o700)
    files={}
    def write(role,path,value):
        path.write_text(json.dumps(value,indent=2)+'\n');path.chmod(0o600)
        files[role]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()};return files[role]
    contract=original.public_json('references/PUBLIC_CONTRACT.json');e=contract['source_evidence']
    sources={role:{'path':'/INVENTED_NEVER_OPEN_CLINICAL/'+base,
        'sha256':hashlib.sha256(('INVENTED_SOURCE_'+role).encode()).hexdigest(),
        'dataset_basename':base,'claimed_archive_edition':'UNRESOLVED'} for role,base in e['required_products'].items()}
    registration={'schema':'elsa-private-source-registration-v1','status':'REGISTERED_LOCAL_MEMBER_BINDINGS_ONLY_COUNT_NOT_AUTHORIZED',
        'attempt_consumed':True,'members':[{'role':k,'materialized_file':v,'uncompressed_member_sha256':v['sha256']} for k,v in sources.items()]}
    for k,v in [('public_contract_sha256',e['registration_public_contract_sha256']),('registration_protocol_sha256',e['registration_protocol_sha256']),
        ('registration_code_bindings',e['registration_code_bindings']),('count_tool_release_sha256',e['count_tool_release_sha256']),
        ('count_mapping_sha256',e['frozen_mapping_sha256']),('count_protocol_sha256',e['frozen_protocol_sha256'])]:registration[k]=v
    rd=write('source_registration',rout/'source_registration.private.json',registration)
    dc={'schema':'elsa-status-diagnostic-local-config-v1','mode':'independent_local_only','no_models':True,'no_event_counts':True,
        'source_use_review':'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_STATUS_ONLY_OPERATION',
        'reviewed_scope':['READ_REGISTERED_SOURCE_AND_INTEGRITY_METADATA','HASH_REGISTERED_SOURCE_BYTES',
                          'READ_LINKAGE_AND_INTERVIEW_STATUS_COLUMNS_ONLY','WRITE_PRIVATE_AGGREGATE_STATUS_DIAGNOSTICS'],
        'protocol_sha256':contract['diagnostic_protocol_sha256'],'mapping_sha256':e['frozen_mapping_sha256'],
        'sources':sources,'source_registration':rd}
    fc={'schema':'elsa-final-count-local-config-v1','mode':'independent_local_only','no_models':True,
        'source_use_review':'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION','source_format':'registered_stata_tables_v1',
        'protocol_sha256':e['frozen_protocol_sha256'],'mapping_sha256':e['frozen_mapping_sha256'],'sources':sources}
    dcd=write('diagnostic_config',diag/'status.reviewed.json',dc)
    fcd=write('failed_count_config',count/'count.reviewed.json',fc)
    for role,folder,filename,cfg,purpose,bindings,out in [
        ('diagnostic_authorization',diag,'status.authorization.json',dcd,contract['diagnostic_purpose'],contract['diagnostic_code_bindings'],dout),
        ('failed_count_authorization',count,'count.authorization.json',fcd,contract['count_purpose'],contract['count_code_bindings'],cout)]:
        write(role,folder/filename,{'purpose':purpose,'authorized':True,'scope_confirmed_by_operator':True,
            'operator':'INVENTED_FIXTURE_NOT_AUTHORIZATION','config_sha256':cfg['sha256'],'code_bindings':bindings,'output_binding':str(out)})
    write('diagnostic_completion',dout/'completion.private.json',{'status':'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED','attempt_consumed':True})
    write('failed_count_completion',cout/'completion.private.json',{'status':'FAILED_NO_RETRY','attempt_consumed':True,
        'issue':'ELIGIBILITY_PROCESSING_PARTICIPATION_INTERVIEW_CONFLICT'})
    # Binding only: no matrices/events are needed or interpreted by this helper.
    report={'schema':'elsa-private-status-diagnostic-v1','scope':'STATUS_ONLY_NO_DISEASE_ENDPOINTS_NO_ELIGIBILITY_CHANGES',
        'participant_rows_or_keys_written':False,'bindings':{'source_registration_sha256':rd['sha256'],
            'sources':{k:{'sha256':v['sha256'],'dataset_basename':v['dataset_basename']} for k,v in sources.items()},
            'protocol_sha256':dc['protocol_sha256'],'mapping_sha256':dc['mapping_sha256'],'code_bindings':contract['diagnostic_code_bindings']}}
    rp=write('diagnostic_report',dout/'status_diagnostic.private.json',report)
    q=write('diagnostic_input_validation',dout/'input_validation.private.json',{'schema':'elsa-status-input-validation-v1',
        'participant_rows_or_keys_written':False,'linkage_quality':{k:{x:0 for x in
          ('MISSING_LINKAGE','INVALID_LINKAGE_STORAGE','INVALID_LINKAGE_VALUE','DUPLICATE_LINKAGE')} for k in sources}})
    write('diagnostic_integrity',dout/'diagnostic_integrity.private.json',{'schema':'elsa-status-result-integrity-v1','purpose':contract['diagnostic_purpose'],
        'outputs':{'status_diagnostic.private.json':rp['sha256'],'input_validation.private.json':q['sha256']}})
    config=run/'review.reviewed.json';config.write_text(json.dumps(template,indent=2)+'\n');config.chmod(0o600)
    return private,config,files
