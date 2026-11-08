"""New independent operations; existing human authorization runtime is reused."""
import json
from pathlib import Path
import numpy as np
from local_execution import require_local,need,descriptor,load_json,sha,Rejected
from .contracts import SOURCE_ENDPOINT,TARGET_ENDPOINT,FEATURES,DEV_ROLES,load_bundle
from .pipeline import development,evaluation,write_json,registered_artifact,algorithm_bindings,runtime_versions
from .models import METHODS,device_checked

ROOT=Path(__file__).resolve().parents[2]
GATES=('elsa_conflict_resolution_adopted','fresh_count_acceptance','hrs_source_event_support_accepted',
       'source_specific_sensitivity_claim_adopted','feature_harmonization_and_timing_accepted',
       'precision_and_untouched_test_design_accepted','independent_export_scope_established',
       'provider_and_institutional_scope_confirmed')
EVIDENCE=('elsa_resolution','fresh_counts','hrs_endpoint_and_support','statistical_feasibility',
          'harmonization_and_export','independent_membership')


def metadata_preflight(c):
    require_local()
    from release import verify
    verify()
    common={'schema','mode','phase','source_use_review','protocol_sha256','data','manifest','readiness','device'}
    need(isinstance(c,dict) and c.get('phase') in ('development','evaluation'),'PHASE_REQUIRED')
    need(set(c)==common|({'artifact','freeze'} if c['phase']=='evaluation' else set()),'CONFIG_FIELDS_INVALID')
    need(c['schema']=='hrs-elsa-fasttrack-local-operation-v1' and c['mode']=='independent_local_only','CONFIG_MODE_INVALID')
    need(c['source_use_review']=='INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION','NEW_OPERATION_SCOPE_REQUIRED')
    need(c['protocol_sha256']==sha(ROOT/'configs/training_protocol.json') and c['device'] in ('cpu','mps'),'PROTOCOL_OR_DEVICE_MISMATCH')
    device_checked(c['device'])  # Public hardware readiness before authorization/data access.
    # Only evidence/config metadata is opened. Do NOT hash/open participant arrays here.
    ready=load_json(descriptor(c['readiness']))
    need(ready.get('schema')=='hrs-elsa-independent-readiness-v1' and all(ready.get(g) is True for g in GATES),'SCIENTIFIC_READINESS_NOT_ESTABLISHED')
    need(ready.get('source_endpoint')==SOURCE_ENDPOINT and ready.get('target_endpoint')==TARGET_ENDPOINT,'ENDPOINT_NOT_ADOPTED')
    need(set(ready.get('evidence',{}))==set(EVIDENCE),'BOUND_REVIEW_EVIDENCE_REQUIRED')
    for d in ready['evidence'].values():descriptor(d)
    manifest=load_json(descriptor(c['manifest']))
    need(manifest.get('synthetic_only') is False and manifest.get('data_sha256')==c['data']['sha256'], 'REAL_INPUT_MANIFEST_BINDING_REQUIRED')
    need(manifest.get('partition_method')=='FROZEN_OUTCOME_BLIND_HASH','UNREGISTERED_PARTITION_METHOD')
    roles=DEV_ROLES if c['phase']=='development' else ('target_test',)
    need(manifest.get('schema')=='hrs-elsa-canonical-baseline-v1' and manifest.get('feature_names')==list(FEATURES)
         and manifest.get('source_endpoint')==SOURCE_ENDPOINT and manifest.get('target_endpoint')==TARGET_ENDPOINT
         and manifest.get('source_design')=='HRS_2012_2018_SOURCE_SPECIFIC_REPORT'
         and manifest.get('target_design') in ('W6_W9','W4_W7')
         and set(manifest.get('roles',{}))==set(roles),'INPUT_METADATA_CONTRACT_MISMATCH')
    for role,m in manifest['roles'].items():
        need(isinstance(m,dict) and set(m)=={'n','positive','membership_sha256'}
             and type(m['n']) is int and m['n']>0 and type(m['positive']) is int
             and 0<=m['positive']<=m['n'] and isinstance(m['membership_sha256'],str)
             and len(m['membership_sha256'])==64,'ROLE_METADATA_INVALID')
        if role in ('source_train','target_validation','target_test'):
            need(0<m['positive']<m['n'],'BINARY_MODEL_STAGE_NOT_SUPPORTED')
    need(ready.get('approved_manifest_sha256')==c['manifest']['sha256'],'READINESS_NOT_BOUND_TO_THIS_EXPORT')
    for name in ['data']+(['artifact','freeze'] if c['phase']=='evaluation' else []):
        d=c[name]
        need(isinstance(d,dict) and set(d)=={'path','sha256'} and Path(d['path']).is_absolute()
             and isinstance(d['sha256'],str) and len(d['sha256'])==64,'EXPLICIT_INPUT_BINDING_REQUIRED')
        p=Path(d['path']);need(not p.is_symlink() and p.is_file(),'LOCAL_INPUT_LOCATION_MISSING')
    if c['phase']=='evaluation':
        frozen=load_json(descriptor(c['freeze']))
        need(frozen.get('schema')=='hrs-elsa-development-freeze-v1' and frozen.get('synthetic_only') is False
             and frozen.get('test_accessed') is False and set(frozen.get('registered_methods',[]))==set(METHODS),
             'INCOMPLETE_OR_INVALID_TEST_REGISTRATION')
        need(frozen.get('algorithm_bindings')==algorithm_bindings() and frozen.get('runtime_versions')==runtime_versions()
             and frozen.get('artifact_sha256')==c['artifact']['sha256']
             and frozen.get('target_design')==manifest['target_design'],'FROZEN_REGISTRATION_BINDING_MISMATCH')
    return manifest


def execute(c,out):
    manifest=metadata_preflight(c)
    plan=load_json(ROOT/'configs/training_protocol.json')['training']
    plan['device']=c['device']
    try:
        artifact=None;freeze=None
        if c['phase']=='evaluation':
            freeze=load_json(descriptor(c['freeze']))
            artifact=registered_artifact(descriptor(c['artifact']),freeze,False)
        data=load_bundle(descriptor(c['data']),DEV_ROLES if c['phase']=='development' else ('target_test',))
        if c['phase']=='development':development(data,manifest,plan,out,synthetic=False)
        else:
            evaluation(data,manifest,c['artifact']['path'],freeze,plan,out,synthetic=False,artifact=artifact)
        descriptor(c['data']);descriptor(c['manifest']);descriptor(c['readiness'])
    except Rejected:
        raise
    except ValueError as exc:
        # Preserve only explicit public validator identifiers; an arbitrary library
        # message (possibly containing private data) is never treated as a code.
        allowed=load_json(ROOT/'configs/validation_codes.json')['codes']
        code=str(exc) if str(exc) in allowed else 'UNCLASSIFIED_INPUT_OR_LIBRARY_ERROR'
        raise Rejected(c['phase'].upper()+'_'+code) from None
    write_json(out/'operational_summary.json',{'status':'COMPLETED_PRIVATE_SCIENTIFIC_REVIEW_REQUIRED',
               'phase':c['phase'],'model_superiority_or_clinical_acceptance':'NOT_GRANTED'})
