"""Development and SEPARATE locked-test stages. Synthetic or authorized-local only."""
import copy
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import torch
from importlib.metadata import version
from .contracts import DEV_ROLES,FEATURES,validate,membership,need
from .preprocessing import BaselinePreprocessor
from .models import train_models,predict,METHODS
from .metrics import metrics,OperatingPoint,paired_bootstrap


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def algorithm_bindings():
    root=Path(__file__).resolve().parents[2]
    files=['src/fasttrack/'+n+'.py' for n in ('contracts','preprocessing','models','metrics','pipeline')]
    files+=['vendor/dmv_mat_cvd/'+n for n in ('models/multiview_mlp.py','transfer/adapt.py','transfer/calibration.py','transfer/scores.py')]
    return {n:digest(root/n) for n in files}


def runtime_versions():
    return {n:version(n) for n in ('torch','numpy','scikit-learn','joblib')}


def write_json(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def development(data,manifest,config,out,synthetic=False):
    identities=validate(data,DEV_ROLES,manifest)
    pre=BaselinePreprocessor().fit(data['source_train__x'],'source_train')
    # Budget membership is outcome blind; total consumed target-label roles reported separately.
    ids=data['target_fit__ids'];order=sorted(range(len(ids)),key=lambda i:hashlib.sha256(str(ids[i]).encode()).digest())
    n=min(len(ids),config['target_fit_budget']);need(n>0,'EMPTY_TARGET_LABEL_BUDGET')
    use=np.asarray(order[:n]);sub=dict(data)
    for key in ('x','y','ids','availability'):sub['target_fit__'+key]=data['target_fit__'+key][use]
    views={r:pre.transform(sub[r+'__x']) for r in DEV_ROLES};labels={r:sub[r+'__y'] for r in DEV_ROLES}
    need(len(np.unique(labels['target_validation']))==2,'NO_VALID_TARGET_MODEL_SELECTION_POPULATION')
    fitting_roles=('source_train','source_stop','target_fit','target_stop')
    trained,traces=train_models({r:views[r] for r in fitting_roles},{r:labels[r] for r in fitting_roles},config,synthetic)
    rows={};operating={};validation_predictions={}
    for name,item in trained.items():
        calibration=predict(item,views['target_calibration'],config['device'])
        point=OperatingPoint().fit(labels['target_calibration'],calibration,'target_calibration');operating[name]=point
        p=predict(item,views['target_validation'],config['device']);validation_predictions[name]=p
        rows[name]={'raw_fixed_0_50':metrics(labels['target_validation'],p),
                    'training_side_calibrated_operating_point':point.report(labels['target_validation'],p)}
        if item['kind']=='neural':
            with (out/(name+'.weights.pt')).open('xb') as f:torch.save(item['model'].state_dict(),f)
    winner=min(rows,key=lambda k:(-rows[k]['raw_fixed_0_50']['ap'],rows[k]['raw_fixed_0_50']['brier'],METHODS.index(k)))
    artifact={'schema':'hrs-elsa-frozen-model-artifact-v1','preprocessor':pre,'models':trained,'operating':operating,
              'development_ids':identities,'selected_method':winner,'feature_names':FEATURES,'config':config,
              'target_design':manifest['target_design']}
    with (out/'frozen_models.private.joblib').open('xb') as f:joblib.dump(artifact,f)
    with (out/'validation_predictions.private.npz').open('xb') as f:
        np.savez_compressed(f,labels=labels['target_validation'],**validation_predictions)
    report={'scope':'SYNTHETIC_ONLY' if synthetic else 'PRIVATE_DEVELOPMENT_ONLY_NOT_EXTERNAL_VALIDATION',
            'methods':rows,'training_traces':traces,'selected_on_development_AP_only':winner,
            'target_label_accounting':{r:len(labels[r]) for r in DEV_ROLES if r.startswith('target')},
            'total_target_labels_consumed':sum(len(labels[r]) for r in DEV_ROLES if r.startswith('target')),
            'target_label_rows_read_for_integrity':{r:len(data[r+'__y']) for r in DEV_ROLES if r.startswith('target')},
            'label_budget_is_fitting_only_not_free_validation_labels':True,
            'target_test_accessed':False,'source_endpoint':manifest['source_endpoint'],'target_endpoint':manifest['target_endpoint']}
    write_json(out/'development.private.json',report)
    write_json(out/'freeze.private.json',{'schema':'hrs-elsa-development-freeze-v1',
        'artifact_sha256':digest(out/'frozen_models.private.joblib'),'selected_method':winner,
        'target_design':manifest['target_design'],
        'registered_methods':list(trained),'feature_names':list(FEATURES),
        'primary_contrast':'selective_minus_full_raw_AP','training_config':config,
        'operating_thresholds':{k:v.threshold for k,v in operating.items()},
        'algorithm_bindings':algorithm_bindings(),'runtime_versions':runtime_versions(),
        'all_development_membership_sha256':membership(np.array(sorted(identities))),
        'test_accessed':False,'synthetic_only':synthetic})
    return report


def registered_artifact(artifact_path,freeze,synthetic):
    need(freeze.get('schema')=='hrs-elsa-development-freeze-v1','FROZEN_REGISTRATION_SCHEMA_INVALID')
    need(digest(artifact_path)==freeze['artifact_sha256'] and freeze['test_accessed'] is False,'FROZEN_MODEL_BINDING_INVALID')
    need(freeze.get('synthetic_only')==synthetic,'SYNTHETIC_REAL_ARTIFACT_MIXING')
    need(freeze.get('algorithm_bindings')==algorithm_bindings() and freeze.get('runtime_versions')==runtime_versions(),
         'FROZEN_ALGORITHM_OR_RUNTIME_MISMATCH')
    # Joblib loads only a locally authorized, digest-bound artifact, never an arbitrary upload.
    artifact=joblib.load(artifact_path)
    need(artifact['selected_method']==freeze['selected_method'] and list(artifact['models'])==freeze['registered_methods'],
         'REGISTERED_METHOD_SUBSTITUTION')
    need(set(artifact['models'])==set(METHODS),'INCOMPLETE_REGISTERED_COMPARISON_NO_TEST_ACCESS')
    need(artifact['config']==freeze['training_config'] and
         {k:v.threshold for k,v in artifact['operating'].items()}==freeze['operating_thresholds'],
         'FROZEN_TRAINING_OR_THRESHOLD_MISMATCH')
    need(artifact['target_design']==freeze['target_design'],'FROZEN_COHORT_WINDOW_MISMATCH')
    return artifact


def evaluation(data,manifest,artifact_path,freeze,config,out,synthetic=False,artifact=None):
    artifact=registered_artifact(artifact_path,freeze,synthetic) if artifact is None else artifact
    test_ids=validate(data,('target_test',),manifest)
    need(not test_ids&artifact['development_ids'],'TEST_DEVELOPMENT_OVERLAP')
    need(manifest['target_design']==artifact['target_design'],'TEST_COHORT_WINDOW_SUBSTITUTION')
    views=artifact['preprocessor'].transform(data['target_test__x']);y=data['target_test__y']
    rows={};predictions={}
    for name,item in artifact['models'].items():
        p=predict(item,views,config['device']);predictions[name]=p
        rows[name]={'raw_fixed_0_50':metrics(y,p),'frozen_training_side_operating_point':artifact['operating'][name].report(y,p)}
    report={'scope':'SYNTHETIC_ONLY' if synthetic else 'PRIVATE_ONE_TIME_REGISTERED_EVALUATION_REQUIRES_SCIENTIFIC_REVIEW',
            'methods':rows,'selected_before_test':freeze['selected_method'],
            'primary_contrast':'selective_minus_full_raw_AP',
            'primary_AP_difference':None if not {'selective','full'}<=set(rows) else
                (None if rows['selective']['raw_fixed_0_50']['ap'] is None else rows['selective']['raw_fixed_0_50']['ap']-rows['full']['raw_fixed_0_50']['ap']),
            'uncertainty':paired_bootstrap(y,predictions,config['bootstrap_resamples'],config['seed']),
            'test_thresholds_changed':False,'test_model_selection_performed':False,
            'survey_design_and_training_uncertainty_not_captured':True}
    write_json(out/'evaluation.private.json',report)
    with (out/'test_predictions.private.npz').open('xb') as f:np.savez_compressed(f,labels=y,**predictions)
    return report
