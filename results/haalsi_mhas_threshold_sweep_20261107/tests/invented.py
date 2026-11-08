"""Invented frozen-style score files. No actual participant data or approvals."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import frozen_metrics as frozen


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n');path.chmod(0o600);return descriptor(path)


def descriptor(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def fixture(tmp):
    tmp.mkdir(mode=0o700,exist_ok=True)
    rng=np.random.default_rng(20261107);y=np.r_[np.ones(21),np.zeros(262)].astype(int)
    models={'calibrated_logical':rng.uniform(.01,.65,(10,283)),'source_multiview':rng.uniform(.01,.5,(1,283))}
    ids=[f'INVENTED_MHAS_TEST_{i:04}' for i in range(283)]
    bp=tmp/'INVENTED_retained.npz'
    with bp.open('xb') as f:np.savez_compressed(f,observed_labels=y,**{'primary_25_75__'+k:v for k,v in models.items()})
    bp.chmod(0o600);ip=tmp/'INVENTED_ordered_ids.json';write(ip,{'ordered_participant_ids':ids})
    c=copy.deepcopy(json.loads((ROOT/'ORIGINAL_CONFIG_SCHEMA_REFERENCE.json').read_text()))
    c['models']=[copy.deepcopy(m) for m in c['models'] if m['model_id'] in models]
    entries=[]
    for m in c['models']:
        m['checkpoint_sha256_by_draw']={str(d):hashlib.sha256(('INVENTED_CHECKPOINT_'+m['model_id']+str(d)).encode()).hexdigest() for d in m['draw_ids']}
        for d in m['draw_ids']:entries.append({'method':m['model_id'],'budget':m['budget'],
            'repetition':None if d=='source' else d,'checkpoint_sha256':m['checkpoint_sha256_by_draw'][str(d)]})
    rp=tmp/'INVENTED_registration.json';write(rp,{'models':entries})
    mp=tmp/'INVENTED_completed_manifest.json';write(mp,{'status':'RECOVERY_COMPLETE_AFTER_FAILED_ORIGINAL_ATTEMPT',
        'registration_sha256':frozen.sha(rp),'no_fitting_performed':True,'test_participants':283,'test_positive_reports':21,
        'private_prediction_bundle_sha256':frozen.sha(bp),'private_ids_sha256':frozen.sha(ip)})
    refs={'models':{}}
    for name,matrix in models.items():
        rows=[frozen.metrics(y,p) for p in matrix]
        refs['models'][name]={k:{'mean':float(np.mean([r[k] for r in rows])),'per_draw':[r[k] for r in rows]} for k in ('ap','auroc','brier')}
    fp=tmp/'INVENTED_references.json';write(fp,refs)
    c.update(registration=descriptor(rp),completed_manifest=descriptor(mp),public_references=descriptor(fp),
        predictions={'path':str(bp),'labels_key':'observed_labels'},ids={'path':str(ip),'ordered_ids_key':'ordered_participant_ids'},validation_threshold=None)
    return c,y,models,refs


def validation(tmp,c,overlap=False,partial=False):
    y=np.r_[np.ones(13),np.zeros(158)].astype(int)
    ids=np.array([f'INVENTED_ORIGINAL_VALIDATION_{i:04}' for i in range(171)])
    if overlap:ids[0]='INVENTED_MHAS_TEST_0000'
    arrays={'original_ids':ids,'original_labels':y,'UNSELECTED_OBJECT_ARRAY':np.array([{'INVENTED':'MUST_NOT_BE_READ'}],dtype=object)}
    keys={};checkpoints={}
    for m in c['models']:
        if partial and m['model_id']=='source_multiview':continue
        key='original_scores__'+m['model_id'];keys[m['model_id']]=key
        arrays[key]=np.tile(np.linspace(.4,.01,171),(len(m['draw_ids']),1));checkpoints[m['model_id']]=m['checkpoint_sha256_by_draw']
    vp=tmp/'INVENTED_validation.npz'
    with vp.open('xb') as f:np.savez_compressed(f,**arrays)
    vp.chmod(0o600)
    vm=tmp/'INVENTED_original_validation_provenance.json';write(vm,{'role':'target_validation','origin':'retained_original_development_predictions',
        'payload_sha256':frozen.sha(vp),'registration_sha256':c['registration']['sha256'],'checkpoints':checkpoints})
    c['validation_threshold']={'rule':'validation_f1_highest_threshold_tie','payload':descriptor(vp),'provenance':descriptor(vm),
        'ids_key':'original_ids','labels_key':'original_labels','model_keys':keys}
    return c


def pin_invented(c,monkeypatch):
    # Test process only; no production flag disables the real fixed pins.
    for variable,key in [('REGISTRATION_SHA','registration'),('MANIFEST_SHA','completed_manifest'),('REFERENCE_SHA','public_references')]:
        monkeypatch.setattr(frozen,variable,c[key]['sha256'])
