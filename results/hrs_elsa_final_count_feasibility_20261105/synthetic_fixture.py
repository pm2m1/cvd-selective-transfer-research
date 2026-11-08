"""INVENTED populations only; never derived from clinical observations."""
from count_engine import ROLES

def raw_visit(w,mapping,event=None,prior=None):
    fs=mapping['waves'][str(w)]['fields'];raw={n:-1 for n in fs if n!='idauniq'}
    raw['indoc' if w==1 else f'w{w}indout']=11
    raw['askpx1' if w<3 else 'askpx']=2 if w==1 else 0
    for k in ['iintdaty','iintdty']:
        if k in fs:raw[k]=2000+2*w
    for k in ['iintdatm','iintdtm']:
        if k in fs:raw[k]=7 if w in (7,9) else 6
    if 'indager' in fs:raw['indager']=60
    if 'indsex' in fs:raw['indsex']=1
    if w<3:
        for n in range(1,8 if w==1 else 9):raw[f'hedim{n:02}']=-1
        raw['hedim01']=3 if event=='mi' else 8 if event=='stroke' else 1 if w==1 else 96
    else:
        for n in fs:
            if n.startswith('hedim') or n in ('hedizm51','hedizm52'):raw[n]=0
        raw['hedim96']=0 if event else 1
        if event:raw['hedimmi' if event=='mi' else 'hedimst']=1
    if w>1:
        bundle=[n for n in fs if n.startswith('hedaw') or (w==2 and n.startswith('hediaw'))]
        for n in bundle:raw[n]=-1
        raw[bundle[0]]=1  # Documented non-endpoint hypertension is allowed.
        for c,s in [(3,'mi'),(8,'st')]:
            q=f'hediac{c}' if w==2 else 'hedac'+s
            d=f'hedian{c}' if w==2 else 'hedan'+s
            if q in fs:raw[q]=1 if prior==('mi' if c==3 else 'stroke') else -1
            raw[d]=-1
        if prior:
            # Deliberately place the target code in another positional slot.
            raw[bundle[-1]]=3 if prior=='mi' else 8
    return {'wave':w,'raw':raw}

def features(w):
    out={}
    for role,unit in ROLES.items():
        exam=role in ('sbp','dbp','bmi')
        out[role]={'value':{'age':60,'sex':0,'sbp':120,'dbp':75,'bmi':25,'smoking':0,'diabetes':0,'bp_treatment':0}[role],
           'unit':unit,'source_wave':w,'context':'dated_examination' if exam else 'same_core_interview',
           'measured_lower':f'{2000+2*w}-05-01' if exam else None,
           'measured_upper':f'{2000+2*w}-05-31' if exam else None,
           'available_upper':f'{2000+2*w}-05-31' if exam else None}
    return out

def person(mapping,i=0,start=1,event_wave=None,component='mi'):
    return {'token':f'INVENTED_FINAL_COUNT_PERSON_{i:04}',
       'participation':{str(w):int(w>=start) for w in range(1,10)},
       'visits':[raw_visit(w,mapping,component if w==event_wave else None,
                   component if event_wave is not None and w>event_wave else None) for w in range(start,10)],
       'screening_history':{},'features':{'4':features(4),'6':features(6)},'prior_model_use':'no'}

def invented_people(mapping):
    return [person(mapping,i=i,start=1 if i%2 else 4,event_wave=8 if i%4==0 else None,
                   component='stroke' if i%8==0 else 'mi') for i in range(24)]
