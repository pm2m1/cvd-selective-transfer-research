"""Fresh human-authorized retained-score statistics. No inference/training APIs."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import numpy as np
import frozen_metrics as frozen
import local_execution as local
from sweep_analysis import analyze,GRID,UNESTABLISHED

ROOT=Path(__file__).resolve().parent
PURPOSE='retained_frozen_mhas_threshold_sweep_v1_20261107'
LEGACY_SHA='daf996ad519450d672137f512019506e232a5dfb49e515848517ff5078ac7efc'
REVIEW='INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_THRESHOLD_SWEEP'
SCOPE=['READ_RECORDED_METRICS_CONFIGURATION_AND_COMPLETION_METADATA',
       'READ_RETAINED_FROZEN_TEST_PROBABILITIES_LABELS_AND_ORDERED_IDS',
       'READ_FROZEN_REGISTRATION_MANIFEST_AND_REFERENCE_BINDINGS',
       'RECONCILE_FROZEN_AP_AUROC_BRIER_BEFORE_REPORTING',
       'DESCRIBE_FIXED_TEST_THRESHOLDS_WITHOUT_TEST_OPTIMIZATION',
       'READ_AUTHENTIC_ORIGINAL_VALIDATION_IF_RECORDED',
       'WRITE_NEW_PRIVATE_SUPPLEMENTARY_REPORTS_AND_FIGURES']


def safe_path(value,private=False):
    local.need(isinstance(value,(str,Path)),'EXPLICIT_RECORDED_PATH_REQUIRED')
    p=Path(value)
    local.need(p.is_absolute() and '..' not in p.parts and not any(x.is_symlink() for x in (p,*p.parents)),
               'UNSAFE_OR_RELATIVE_INPUT_PATH')
    s=p.stat();local.need(stat.S_ISREG(s.st_mode),'REGULAR_RECORDED_FILE_REQUIRED')
    if private:
        local.need(s.st_uid==os.getuid() and s.st_mode&0o077==0 and p.parent.stat().st_mode&0o077==0,
                   'PRIVATE_INPUT_PERMISSIONS_REQUIRED')
    return p


def bound_json(d,private=False):
    local.need(isinstance(d,dict) and set(d)=={'path','sha256'} and isinstance(d['sha256'],str)
               and re.fullmatch('[0-9a-f]{64}',d['sha256']),'REVIEWED_DESCRIPTOR_REQUIRED')
    p=safe_path(d['path'],private);local.need(local.sha(p)==d['sha256'],'RECORDED_METADATA_BINDING_MISMATCH')
    return local.load_json(p)


def primary_inventory(c):
    allowed=set(local.load_json(ROOT/'FROZEN_PUBLIC_METRIC_REFERENCES.json')['models'])
    names=[m['model_id'] for m in c['models']]
    local.need(bool(names) and len(set(names))==len(names) and set(names)<=allowed,'MODEL_INVENTORY_INVALID')
    for m in c['models']:
        source=m['model_id']=='source_multiview'
        local.need(m['budget']==('source' if source else 'primary_25_75')
                   and m['draw_ids']==(['source'] if source else list(range(10))),'PRIMARY_REFERENCE_BUDGET_OR_DRAW_MISMATCH')


def recorded_config(c):
    local.require_local()
    source=c['metrics_source'];local.need(set(source)=={'kind','record','completion'},'METRICS_SOURCE_SCHEMA_INVALID')
    value=bound_json(source['record'],True)
    if source['kind']=='completed_metrics_provenance':
        local.need(value.get('script_sha256')==LEGACY_SHA and value.get('no_inference_performed') is True
                   and value.get('no_new_fitting_performed') is True,'ORIGINAL_METRICS_PROVENANCE_INVALID')
        completion=bound_json(source['completion'],True)
        local.need(Path(source['completion']['path'])==Path(source['record']['path']).parent/'completion.private.json'
                   and completion.get('status')=='COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED'
                   and completion.get('attempt_consumed') is True,'ORIGINAL_METRICS_NOT_COMPLETED')
        value=value['config']
    else:
        local.need(source['kind']=='reviewed_metrics_config' and source['completion'] is None,'METRICS_SOURCE_SCHEMA_INVALID')
    local.need(value.get('schema')=='supplementary-classification-v1' and value.get('mode')=='independent_local_only',
               'ORIGINAL_CONFIG_SCHEMA_INVALID')
    local.need(value.get('fixed_threshold')==.5 and value.get('ddof')==1 and value.get('probability_ensemble') is False
               and value.get('absolute_tolerance')==1e-8 and value.get('relative_tolerance')==1e-8,'ORIGINAL_ANALYSIS_CONTRACT_CHANGED')
    for name in ('registration','completed_manifest','predictions','ids'):
        local.need(isinstance(value[name]['path'],str) and Path(value[name]['path']).is_absolute(),'RECORDED_PRIVATE_PATH_NOT_ABSOLUTE')
    local.need(value['registration']['sha256']==frozen.REGISTRATION_SHA
               and value['completed_manifest']['sha256']==frozen.MANIFEST_SHA
               and value['public_references']['sha256']==frozen.REFERENCE_SHA,'FROZEN_EVIDENCE_BINDING_MISMATCH')
    local.need(value['models'] and all(re.fullmatch('[a-zA-Z0-9_]{1,60}',m['model_id']) for m in value['models']),
               'MODEL_INVENTORY_INVALID')
    primary_inventory(value)
    result=copy.deepcopy(value)
    # The public reference file is identical bytes with the original registered
    # hash. Relocate that public dependency only; never guess a private path/key.
    local.need(local.sha(ROOT/'FROZEN_PUBLIC_METRIC_REFERENCES.json')==frozen.REFERENCE_SHA,'PUBLIC_REFERENCE_CHANGED')
    result['public_references']['path']=str(ROOT/'FROZEN_PUBLIC_METRIC_REFERENCES.json')
    return result


def validate_outer(c,require_scope=True):
    local.need(isinstance(c,dict) and set(c)=={'schema','mode','source_use_review','reviewed_scope',
        'metrics_source','thresholds','validation_policy','original_validation','no_inference','no_training','no_score_changes','private_output_only'},
        'SWEEP_CONFIG_SCHEMA_INVALID')
    local.need(c['schema']=='frozen-mhas-threshold-sweep-v1' and c['mode']=='independent_local_only'
               and c['thresholds']==list(GRID),'THRESHOLD_GRID_OR_MODE_CHANGED')
    local.need(c['validation_policy']=='AUTHENTIC_ORIGINAL_VALIDATION_ONLY_OR_NOT_ESTABLISHED'
               and all(c[k] is True for k in ('no_inference','no_training','no_score_changes','private_output_only')),
               'READ_ONLY_SUPPLEMENT_CONTRACT_REQUIRED')
    if require_scope:local.need(c['source_use_review']==REVIEW and c['reviewed_scope']==SCOPE,'NEW_THRESHOLD_SCOPE_NOT_ESTABLISHED')
    recorded=recorded_config(c)
    v=c['original_validation']
    if v is not None:
        local.need(isinstance(v,dict) and set(v)=={'rule','payload','provenance','ids_key','labels_key','model_keys'},
                   'ORIGINAL_VALIDATION_DESCRIPTOR_INVALID')
        local.need(recorded.get('validation_threshold') in (None,v),'CONFLICTING_ORIGINAL_VALIDATION_DESCRIPTORS')
        recorded['validation_threshold']=copy.deepcopy(v) # New analysis only; old record is read-only.
    v=recorded.get('validation_threshold')
    if v is not None:
        local.need(isinstance(v,dict) and set(v)=={'rule','payload','provenance','ids_key','labels_key','model_keys'}
                   and v['rule']=='validation_f1_highest_threshold_tie','ORIGINAL_VALIDATION_DESCRIPTOR_INVALID')
        for name in ('payload','provenance'):
            d=v[name];local.need(isinstance(d,dict) and set(d)=={'path','sha256'} and isinstance(d['path'],str)
                and Path(d['path']).is_absolute() and isinstance(d['sha256'],str) and re.fullmatch('[0-9a-f]{64}',d['sha256']),
                'ORIGINAL_VALIDATION_DESCRIPTOR_INVALID')
        local.need(isinstance(v['model_keys'],dict) and bool(v['model_keys']) and all(isinstance(k,str) and k for k in
            (v['ids_key'],v['labels_key'],*v['model_keys'].values())),'VALIDATION_EXPLICIT_KEYS_INVALID')
    return recorded


def validation_thresholds(c):
    """Select from ORIGINAL validation only, BEFORE reading any test score/label.

    Unlike the old optional branch, dereference only the explicitly selected
    validation arrays. Unselected arrays are never copied/read.
    """
    local.require_local()
    v=c.get('validation_threshold')
    if v is None:return {m['model_id']:None for m in c['models']}
    local.need(v['rule']=='validation_f1_highest_threshold_tie','UNRECOGNIZED_THRESHOLD_RULE')
    reg=bound_json(c['registration']);manifest=bound_json(c['completed_manifest'])
    local.need(manifest['registration_sha256']==c['registration']['sha256'],'COMPLETED_RUN_BINDING_MISMATCH')
    ids_path=safe_path(c['ids']['path'],True)
    local.need(local.sha(ids_path)==manifest['private_ids_sha256'],'RETAINED_PAYLOAD_BINDING_MISMATCH')
    test_ids=local.load_json(ids_path)[c['ids']['ordered_ids_key']]
    local.need(len(test_ids)==283 and len(set(test_ids))==283 and all(isinstance(i,str) and i for i in test_ids),
               'PARTICIPANT_MEMBERSHIP_INVALID')
    vp=safe_path(v['payload']['path'],True);vm=bound_json(v['provenance'],True)
    local.need(local.sha(vp)==v['payload']['sha256'] and vm['payload_sha256']==v['payload']['sha256']
               and vm['registration_sha256']==c['registration']['sha256'] and vm['role']=='target_validation'
               and vm['origin']=='retained_original_development_predictions','VALIDATION_PROVENANCE_INVALID')
    selected={m['model_id']:None for m in c['models']}
    local.need(isinstance(v['model_keys'],dict) and bool(v['model_keys'])
               and set(v['model_keys'])<=set(selected),'VALIDATION_EXPLICIT_KEYS_INVALID')
    with np.load(vp,allow_pickle=False) as z:
        local.need(v['ids_key']!=v['labels_key'] and v['ids_key'] in z.files and v['labels_key'] in z.files,
                   'VALIDATION_EXPLICIT_KEYS_INVALID')
        vids=z[v['ids_key']].tolist();vy=z[v['labels_key']].copy()
        frozen.validate_membership(vids,vy,171,13)
        local.need(not set(vids)&set(test_ids),'VALIDATION_TEST_MEMBERSHIP_OVERLAP')
        keys=[]
        for m in c['models']:
            if m['model_id'] not in v['model_keys']:continue # Explicitly unavailable, never a test fallback.
            name=m['model_id'];draws=m['draw_ids'];entries=[e for e in reg['models'] if e['method']==name and e['budget']==m['budget']]
            checkpoints={'source' if e['repetition'] is None else str(e['repetition']):e['checkpoint_sha256'] for e in entries}
            local.need(checkpoints==m['checkpoint_sha256_by_draw'] and vm['checkpoints'].get(name)==checkpoints,
                       'VALIDATION_CHECKPOINT_MISMATCH')
            key=v['model_keys'][name];local.need(key not in (v['ids_key'],v['labels_key']) and key in z.files and key not in keys,
                                             'VALIDATION_EXPLICIT_KEYS_INVALID');keys.append(key)
            matrix=z[key];local.need(matrix.shape==(len(draws),171),'VALIDATION_SHAPE_INVALID')
            selected[name]=[frozen.select_validation_threshold(vy,p) for p in matrix]
    local.need(local.sha(vp)==v['payload']['sha256'] and local.sha(v['provenance']['path'])==v['provenance']['sha256']
               and local.sha(ids_path)==manifest['private_ids_sha256'],'INPUT_CHANGED_DURING_VALIDATION_SELECTION')
    return selected


def load_frozen(c):
    local.require_local()
    primary_inventory(c)
    for name in ('predictions','ids','completed_manifest'):safe_path(c[name]['path'],True)
    safe_path(c['registration']['path'])
    ts=validation_thresholds(c) # Test probabilities/labels have not been opened.
    test_config=copy.deepcopy(c);test_config['validation_threshold']=None
    y,models,_,refs=frozen.load_inputs(test_config) # Original strict frozen test reader, unchanged.
    return y,models,ts,refs


def metadata_preflight(c):
    """Exists/type/permission checks only for participant files; no score/ID bytes."""
    for name in ('predictions','ids'):safe_path(c[name]['path'],True)
    for name in ('registration','completed_manifest','public_references'):
        safe_path(c[name]['path'],name=='completed_manifest');local.descriptor(c[name])
    v=c.get('validation_threshold')
    if v is not None:
        safe_path(v['payload']['path'],True)
        safe_path(v['provenance']['path'],True);local.descriptor(v['provenance'])


def execute(c,out):
    local.require_local()
    from verify_release import verify
    verify(ROOT)
    original=validate_outer(c)
    y,models,ts,refs=load_frozen(original)
    result=analyze(y,models,ts,refs,original['models'])
    # Recheck every read-only input before any new metric table or plot is written.
    descriptors=[c['metrics_source']['record'],original['registration'],original['completed_manifest'],original['public_references']]
    if c['metrics_source']['completion'] is not None:descriptors.append(c['metrics_source']['completion'])
    if original.get('validation_threshold') is not None:descriptors += [original['validation_threshold'][k] for k in ('payload','provenance')]
    for d in descriptors:local.descriptor(d)
    manifest=bound_json(original['completed_manifest'])
    local.need(local.sha(original['predictions']['path'])==manifest['private_prediction_bundle_sha256']
               and local.sha(original['ids']['path'])==manifest['private_ids_sha256'],'INPUT_CHANGED_DURING_SWEEP')
    from threshold_report import render
    local.write_json(out/'threshold_sweep.private.json',result);render(result,out)
    from importlib.metadata import version
    local.write_json(out/'provenance.private.json',{'purpose':PURPOSE,'metrics_source':c['metrics_source'],
        'original_prediction_and_id_descriptors_reused':True,'retained_prediction_sha256':manifest['private_prediction_bundle_sha256'],
        'retained_ordered_ids_sha256':manifest['private_ids_sha256'],'code_bindings':local.code_hashes(),
        'legacy_metric_code_sha256':local.sha(ROOT/'frozen_metrics.py'),'thresholds':list(GRID),
        'python':sys.version,'runtime_versions':{n:version(n) for n in ('numpy','scikit-learn','matplotlib')},
        'new_inference_or_training':False,'test_threshold_optimized':False,'disclosure_cleared':False})
    for d in descriptors:local.descriptor(d)
    local.need(local.sha(original['predictions']['path'])==manifest['private_prediction_bundle_sha256']
               and local.sha(original['ids']['path'])==manifest['private_ids_sha256'],'INPUT_CHANGED_DURING_RENDERING')
    local.write_json(out/'result_integrity.private.json',{'purpose':PURPOSE,'files':{
        p.relative_to(out).as_posix():local.sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name not in
        ('runtime.private.log','operation_started.private.json','completion.private.json')}})


def prepare(record,kind,destination):
    local.require_local()
    from verify_release import verify
    verify(ROOT)
    p=safe_path(record,True);out=Path(destination)
    local.need(out.is_absolute() and not out.exists() and not out.is_relative_to(ROOT)
               and not any(q.is_symlink() for q in (out,*out.parents)) and out.parent.is_dir()
               and out.parent.stat().st_mode&0o077==0 and out.parent.stat().st_uid==os.getuid(),'NEW_PRIVATE_CONFIG_DESTINATION_REQUIRED')
    source={'kind':kind,'record':{'path':str(p),'sha256':local.sha(p)},'completion':None}
    if kind=='completed_metrics_provenance':
        completion=safe_path(p.parent/'completion.private.json',True)
        source['completion']={'path':str(completion),'sha256':local.sha(completion)}
    c={'schema':'frozen-mhas-threshold-sweep-v1','mode':'independent_local_only','source_use_review':'UNRESOLVED_NOT_AUTHORIZED',
       'reviewed_scope':[],'metrics_source':source,'thresholds':list(GRID),
       'validation_policy':'AUTHENTIC_ORIGINAL_VALIDATION_ONLY_OR_NOT_ESTABLISHED',
       'original_validation':None,
       'no_inference':True,'no_training':True,'no_score_changes':True,'private_output_only':True}
    recorded=validate_outer(c,require_scope=False) # Metadata only; no prediction/label/ID arrays read.
    protected={Path(recorded[k]['path']).parent for k in ('predictions','ids')}
    if kind=='completed_metrics_provenance':protected.add(p.parent)
    local.need(not any(out.is_relative_to(folder) for folder in protected),'HISTORICAL_OUTPUT_MODIFICATION_REFUSED')
    local.write_json(out,c)


def demo(output):
    rng=np.random.default_rng(20261107);y=np.r_[np.ones(21),np.zeros(262)].astype(int)
    matrix=rng.uniform(0,.6,(10,283));name='INVENTED_LOGICAL';base=[frozen.metrics(y,p) for p in matrix]
    refs={'models':{name:{k:{'per_draw':[r[k] for r in base],'mean':float(np.mean([r[k] for r in base]))} for k in ('ap','auroc','brier')}}}
    result=analyze(y,{name:matrix},{name:None},refs,[{'model_id':name,'draw_ids':list(range(10))}],True)
    with local.exclusive_output(output,False) as out:
        from threshold_report import render
        local.write_json(out/'SYNTHETIC_threshold_sweep.json',result);render(result,out)


class Parser(argparse.ArgumentParser):
    def error(self,message):raise local.Rejected('INVALID_THRESHOLD_SWEEP_COMMAND')


def execution_destinations(args,original,c):
    local.need(args.authorization is not None and args.output is not None,'NEW_AUTHORIZATION_AND_OUTPUT_REQUIRED')
    for p in (args.authorization,args.output):
        local.need(p.is_absolute() and '..' not in p.parts and not any(q.is_symlink() for q in (p,*p.parents))
            and not p.is_relative_to(ROOT) and p.parent.is_dir() and p.parent.stat().st_mode&0o077==0
            and p.parent.stat().st_uid==os.getuid(),'NEW_PRIVATE_DESTINATION_REQUIRED')
    protected_dirs={Path(original[k]['path']).parent for k in ('predictions','ids')}
    if c['metrics_source']['kind']=='completed_metrics_provenance':protected_dirs.add(Path(c['metrics_source']['record']['path']).parent)
    local.need(not any(args.output.is_relative_to(p) for p in protected_dirs) and args.authorization!=args.config
               and not args.output.exists(),'ORIGINAL_OR_CONSUMED_DESTINATION_REFUSED')
    if args.authorize_local:local.need(not args.authorization.exists(),'AUTHORIZATION_ALREADY_EXISTS')
    else:safe_path(args.authorization,True)


def main():
    try:
        p=Parser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
        for mode in ('preflight','authorize-local','execute-local','synthetic-demo'):g.add_argument('--'+mode,action='store_true')
        g.add_argument('--prepare-from-metrics-provenance',type=Path);g.add_argument('--prepare-from-metrics-config',type=Path)
        p.add_argument('--new-config',type=Path);p.add_argument('--config',type=Path)
        p.add_argument('--authorization',type=Path);p.add_argument('--output',type=Path)
        args=p.parse_args()
        from verify_release import verify
        verify(ROOT)
        if args.synthetic_demo:
            local.need(args.output is not None and args.config is None and args.authorization is None and args.new_config is None,
                       'SYNTHETIC_MODE_REJECTS_EXTERNAL_CONFIG')
            demo(args.output);print('SYNTHETIC_ONLY_COMPLETE_NO_REAL_THRESHOLD_RESULT');return 0
        local.require_local() # BEFORE any real private config/metadata access.
        if args.prepare_from_metrics_provenance or args.prepare_from_metrics_config:
            local.need(args.new_config is not None and args.config is None and args.authorization is None and args.output is None,
                       'NEW_PRIVATE_CONFIG_REQUIRED')
            prepare(args.prepare_from_metrics_provenance or args.prepare_from_metrics_config,
                    'completed_metrics_provenance' if args.prepare_from_metrics_provenance else 'reviewed_metrics_config',args.new_config)
            print('THRESHOLD_CONFIG_PREPARED_SCOPE_UNRESOLVED');return 0
        local.need(args.config is not None and args.new_config is None,'NEW_PRIVATE_CONFIG_REQUIRED')
        c=local.load_json(safe_path(args.config,True));original=validate_outer(c);metadata_preflight(original)
        if args.preflight:
            print('PASS ISSUE=METADATA_ONLY_NO_SCORE_ARRAYS_READ');return 0
        execution_destinations(args,original,c)
        sys.argv=[str(ROOT/'threshold_sweep.py'),'--authorize-local' if args.authorize_local else '--execute-local',
                  '--config',str(args.config)]
        if args.authorization is not None:sys.argv+=['--authorization',str(args.authorization)]
        if args.output is not None:sys.argv+=['--output',str(args.output)]
        return local.cli(PURPOSE,execute,demo)
    except SystemExit as exc:return exc.code
    except BaseException:
        print('STOP ISSUE=THRESHOLD_SWEEP_NOT_COMPLETED_NO_PRIVATE_VALUES_DISCLOSED');return 2


if __name__=='__main__':raise SystemExit(main())
