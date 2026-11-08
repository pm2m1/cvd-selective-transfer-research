"""Pure baseline-only feature availability adapter; no fitting or file reads."""
from count_engine import ROLES,history,num,code,month_bounds,scalar

def derive(person,harmonized,nurse_by_wave,mapping):
    out={};qc=[]
    for w in [4,6]:
        visit=next((v for v in person['visits'] if v['wave']==w),None)
        if visit is None:continue
        fs=mapping['waves'][str(w)]['fields'];raw=visit['raw'];nurse=nurse_by_wave.get(w,{})
        sex=scalar(raw,'indsex',fs);sex=0 if sex==1 else 1 if sex==2 else None
        diabetes=history(person,w,'diabetes',mapping)
        dm=1 if diabetes=='CONFIRMED_PRIOR_REPORT' else 0 if diabetes=='VERIFIED_ABSENT' else None
        ever=code(harmonized.get(f'r{w}smokev'));now=code(harmonized.get(f'r{w}smoken'))
        med=code(harmonized.get(f'r{w}rxhibp'))
        # Negative numeric source missing codes are unavailable, not categories.
        ever=ever if ever is not None and ever>=0 else None;now=now if now is not None and now>=0 else None
        med=med if med is not None and med>=0 else None
        from count_engine import need
        need(ever in (0,1,None) and now in (0,1,None) and med in (0,1,None),'HARMONIZED_PREDICTOR_CODE_UNREVIEWED')
        smoke={(0,0):0,(1,0):1,(1,1):2}.get((ever,now))
        if ever==0 and now==1:qc.append('CONTRADICTORY_SMOKING_W'+str(w))
        measured=month_bounds(nurse.get('visyear'),nurse.get('vismon'))
        values={'age':num(raw.get('indager')),'sex':sex,'diabetes':dm,'smoking':smoke,'bp_treatment':med,
                'sbp':num(nurse.get('sysval')),'dbp':num(nurse.get('diaval')),'bmi':num(nurse.get('bmival'))}
        features={}
        for role,unit in ROLES.items():
            exam=role in ('sbp','dbp','bmi')
            features[role]={'value':values[role],'unit':unit,'source_wave':w,
               'context':'dated_examination' if exam else 'same_core_interview',
               'measured_lower':measured[0].isoformat() if exam and measured else None,
               'measured_upper':measured[1].isoformat() if exam and measured else None,
               'available_upper':measured[1].isoformat() if exam and measured else None}
        out[str(w)]=features
    return out,qc
