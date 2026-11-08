"""Invented longitudinal histories -> baseline-only canonical synthetic bundles."""
import json
from pathlib import Path
import numpy as np
from .contracts import FEATURES,DEV_ROLES,SOURCE_ENDPOINT,TARGET_ENDPOINT,membership,split_indices,load_bundle
from .pipeline import development,evaluation,write_json,digest


def population(n,cohort,seed):
    rng=np.random.default_rng(seed);latent=rng.normal(size=n)
    x=np.column_stack([rng.uniform(50,85,n),rng.integers(0,2,n),
        125+12*latent+rng.normal(0,8,n),75+6*latent+rng.normal(0,5,n),
        26+2*latent+rng.normal(0,2,n),rng.integers(0,3,n),rng.binomial(1,.25,n),rng.binomial(1,.3,n)])
    if cohort=='ELSA':x[:,2]+=5;x[:,4]+=1
    risk=-1.4+.035*(x[:,0]-65)+.03*(x[:,2]-125)+.5*x[:,6]+.25*(x[:,5]==2)
    y=rng.binomial(1,1/(1+np.exp(-risk)))
    # Invented baseline and later report histories; unknown follow-up excluded,
    # never converted to a nonevent. No clinical questionnaire mapping is claimed.
    prior=rng.binomial(1,.04,n);observed=rng.random(n)>.03
    retain=(prior==0)&observed
    ids=np.array([f'{cohort}_INVENTED_{seed}_{i}' for i in range(n)])
    x[rng.random(x.shape)<.035]=np.nan
    return x[retain],y[retain],ids[retain],{'invented_total':n,'prior_report_excluded':int(prior.sum()),
        'unknown_followup_excluded_after_prior':int(((prior==0)&~observed).sum()),'retained':int(retain.sum())}


def fixtures(seed=20261106):
    data={};flows={}
    for cohort,n,fractions in [('HRS',480,{'source_train':.75,'source_stop':.25}),
          ('ELSA',800,{'target_fit':.4,'target_stop':.15,'target_calibration':.15,'target_validation':.15,'target_test':.15})]:
        x,y,ids,flows[cohort]=population(n,cohort,seed+(cohort=='ELSA'))
        for role,ix in split_indices(ids,fractions).items():
            data[role+'__x']=x[ix];data[role+'__y']=y[ix];data[role+'__ids']=ids[ix]
            data[role+'__availability']=np.ones_like(x[ix],dtype=bool)
    manifests={}
    for phase,roles in [('development',DEV_ROLES),('evaluation',('target_test',))]:
        manifests[phase]={'schema':'hrs-elsa-canonical-baseline-v1','feature_names':list(FEATURES),
            'source_design':'HRS_2012_2018_SOURCE_SPECIFIC_REPORT','target_design':'W6_W9',
            'source_endpoint':SOURCE_ENDPOINT,'target_endpoint':TARGET_ENDPOINT,'synthetic_only':True,
            'partition_method':'FROZEN_OUTCOME_BLIND_HASH','roles':{r:{'n':len(data[r+'__y']),
                'positive':int(data[r+'__y'].sum()),'membership_sha256':membership(data[r+'__ids'])} for r in roles}}
    return data,manifests,flows


def demo(output,config):
    output=Path(output);output.mkdir(mode=0o700,exist_ok=False)
    data,manifests,flows=fixtures(config['seed'])
    dev={k:v for k,v in data.items() if not k.startswith('target_test__')}
    test={k:v for k,v in data.items() if k.startswith('target_test__')}
    for phase,values in [('development',dev),('evaluation',test)]:
        with (output/f'SYNTHETIC_{phase}.npz').open('xb') as f:np.savez_compressed(f,**values)
        manifests[phase]['data_sha256']=digest(output/f'SYNTHETIC_{phase}.npz')
        write_json(output/f'SYNTHETIC_{phase}.manifest.json',manifests[phase])
    write_json(output/'SYNTHETIC_LONGITUDINAL_FLOW.json',flows)
    d=output/'development';d.mkdir();e=output/'evaluation';e.mkdir()
    dev=load_bundle(output/'SYNTHETIC_development.npz',DEV_ROLES)
    report=development(dev,manifests['development'],config,d,synthetic=True)
    test=load_bundle(output/'SYNTHETIC_evaluation.npz',('target_test',))
    result=evaluation(test,manifests['evaluation'],d/'frozen_models.private.joblib',
        json.loads((d/'freeze.private.json').read_text()),config,e,synthetic=True)
    write_json(output/'SYNTHETIC_RESULT.json',{'scope':'INVENTED_DATA_NOT_HRS_ELSA_RESULTS',
        'development_selected_method':report['selected_on_development_AP_only'],
        'evaluation':result,'real_clinical_training_executed':False})
    # Only invented public artifacts are used by this path.
    return result
