"""Canonical baseline-only interfaces; no raw clinical loaders."""
import hashlib
import numpy as np

FEATURES = ('age','sex','sbp','dbp','bmi','smoking','diabetes','bp_treatment')
VIEWS = {'background':(0,1), 'haemodynamic':(2,3), 'metabolic':(4,),
         'behaviour':(5,), 'comorbidity_medication':(6,7)}
DEV_ROLES = ('source_train','source_stop','target_fit','target_stop','target_calibration','target_validation')
SOURCE_ENDPOINT = 'HRS_SCREENING_ASSUMED_NEGATIVE_SENSITIVITY_ONLY'
TARGET_ENDPOINT = 'ELSA_PERSONAL_FIRST_QUALIFYING_SURVEY_REPORT'


def need(value, code):
    if not value:
        raise ValueError(code)


def membership(ids):
    return hashlib.sha256('\n'.join(sorted(map(str,ids))).encode()).hexdigest()


def load_bundle(path,roles):
    expected={r+'__'+s for r in roles for s in ('x','y','ids','availability')}
    with np.load(path,allow_pickle=False) as archive:
        # Inspect names BEFORE dereferencing any array: an injected test array
        # must never be read during development, even when the input is rejected.
        need(set(archive.files)==expected,'EXTRA_OR_MISSING_INPUT_ARRAYS')
        return {key:archive[key] for key in sorted(expected)}


def validate(data, roles, manifest):
    need(manifest.get('schema')=='hrs-elsa-canonical-baseline-v1','INPUT_SCHEMA_INVALID')
    need(manifest.get('feature_names')==list(FEATURES),'FEATURE_ORDER_MISMATCH')
    need(manifest.get('source_endpoint')==SOURCE_ENDPOINT and manifest.get('target_endpoint')==TARGET_ENDPOINT,
         'UNAPPROVED_ENDPOINT_SUBSTITUTION')
    need(manifest.get('source_design')=='HRS_2012_2018_SOURCE_SPECIFIC_REPORT'
         and manifest.get('target_design') in ('W6_W9','W4_W7'),'UNAPPROVED_COHORT_WINDOW')
    need(set(data)=={r+'__'+s for r in roles for s in ('x','y','ids','availability')},'EXTRA_OR_MISSING_INPUT_ARRAYS')
    need(set(manifest['roles'])==set(roles),'ROLE_MANIFEST_MISMATCH')
    seen=set()
    for role in roles:
        x,y,ids,a=(np.asarray(data[role+'__'+s]) for s in ('x','y','ids','availability'))
        need(x.dtype.kind in 'fi' and x.ndim==2 and x.shape[1]==8 and len(x)>0,'INVALID_FEATURE_MATRIX')
        need(not np.isinf(x).any(),'INFINITE_PREDICTOR')
        need(y.shape==(len(x),) and np.isin(y,[0,1]).all(),'UNKNOWN_OR_NONBINARY_OUTCOME')
        need(ids.shape==(len(x),) and ids.dtype.kind=='U' and all(str(i) for i in ids),'EXACT_PRIVATE_MEMBERSHIP_REQUIRED')
        tokens=set(map(str,ids));need(len(tokens)==len(ids) and not tokens&seen,'DUPLICATE_OR_OVERLAPPING_MEMBERSHIP');seen|=tokens
        need(a.shape==x.shape and a.dtype.kind=='b' and a.all(),'UNJUSTIFIED_MEASUREMENT_OR_FUTURE_FEATURE')
        for j,allowed in {1:{0,1},5:{0,1,2},6:{0,1},7:{0,1}}.items():
            values=x[:,j];need(set(values[np.isfinite(values)])<=allowed,'UNMAPPED_CATEGORY')
        for j in (0,2,3,4):
            need((x[np.isfinite(x[:,j]),j]>0).all(),'INVALID_CONTINUOUS_PREDICTOR')
        m=manifest['roles'][role]
        need(m['n']==len(x) and m['positive']==int(y.sum()) and m['membership_sha256']==membership(ids),'ROLE_MEMBERSHIP_BINDING_MISMATCH')
        if role.startswith('target'):
            need(all(str(i).startswith('ELSA_') for i in ids),'TARGET_NAMESPACE_MISMATCH')
        else:
            need(all(str(i).startswith('HRS_') for i in ids),'SOURCE_NAMESPACE_MISMATCH')
    return seen


def split_indices(ids, fractions):
    """Outcome-blind hash thresholds; same person's role stable across windows."""
    need(abs(sum(fractions.values())-1)<1e-10 and all(v>0 for v in fractions.values()),'INVALID_SPLIT_FRACTIONS')
    answer={k:[] for k in fractions}
    for i,key in enumerate(ids):
        u=int.from_bytes(hashlib.sha256(('HRS_ELSA_FASTTRACK_V1\0'+str(key)).encode()).digest()[:8],'big')/2**64
        cumulative=0.
        for role,fraction in fractions.items():
            cumulative+=fraction
            if u<cumulative:
                answer[role].append(i);break
    return {k:np.asarray(v,dtype=int) for k,v in answer.items()}
