"""Count-only logic for an explicit, reviewed canonical input contract.

No dataset loader, file search, model fitting or private input at import.
This does not certify that a raw unselected dummy is a lifetime negative.
"""
from datetime import date,timedelta
from collections import Counter
import math

STATES={'no','yes','historical','disputed','tia','unknown'}
CONDITIONS={'hypertension','angina','mi','heart_failure','heart_murmur','arrhythmia','diabetes','stroke','high_cholesterol','other'}
KINDS={'personal','proxy','partial','institutional','exit','none','dead','withdrawn','unknown'}
DESIGNS={'A':6,'B':6,'C_W4':4}
RAW6_FIELDS={'r6agey','w6indout','askpx','r6hrtatte','r6stroke','hedim96','hedimmi','hedimst',*('inw'+str(w) for w in range(1,7))}


def add_years(d,n):
    try:return d.replace(year=d.year+n)
    except ValueError:return d.replace(year=d.year+n,day=28)


def code(x):
    if x is None or isinstance(x,bool):return None
    try:
        z=float(x)
        return int(z) if math.isfinite(z) and z.is_integer() else None
    except (ValueError,TypeError):return None


def common6(raw):
    age=raw.get('r6agey')
    return (isinstance(age,(float,int)) and not isinstance(age,bool) and math.isfinite(age) and age>=50
            and code(raw.get('inw6'))==1 and code(raw.get('w6indout'))==11 and code(raw.get('askpx'))==0)


def harmonized6(raw):
    return common6(raw) and code(raw.get('r6hrtatte'))==0 and code(raw.get('r6stroke'))==0


def strict6(raw):
    return (common6(raw) and all(code(raw.get('inw'+str(w)))==0 for w in range(1,6))
            and code(raw.get('hedim96'))==1 and code(raw.get('hedimmi'))==0 and code(raw.get('hedimst'))==0)


def strict_predicates(raw):
    # This order defines first-failure attribution; marginals are reported too.
    return {'common_personal_age50':common6(raw),
            'no_earlier_any_response':all(code(raw.get('inw'+str(w)))==0 for w in range(1,6)),
            'none_of_listed_conditions':code(raw.get('hedim96'))==1,
            'mi_unselected':code(raw.get('hedimmi'))==0,'stroke_unselected':code(raw.get('hedimst'))==0}


def overlap_bounds(universe,h,s):
    if not all(type(n) is int for n in [universe,h,s]) or not 0<=h<=universe or not 0<=s<=universe:raise ValueError('INVALID_MARGINALS')
    lo=max(0,h+s-universe);hi=min(h,s)
    return {'intersection':[lo,hi],'H_only':[h-hi,h-lo],'S_only':[s-hi,s-lo],
            'neither':[universe-h-s+lo,universe-h-s+hi]}


def dates(visit):
    lo=date.fromisoformat(visit['date_lower']);hi=date.fromisoformat(visit['date_upper'])
    if hi<lo:raise ValueError('DATE_BOUNDS_REVERSED')
    return lo,hi


def validate_people(people):
    if not isinstance(people,list):raise ValueError('PEOPLE_ARRAY_REQUIRED')
    ids=set()
    for person in people:
        if set(person)!={'person_token','raw6','visits'}:raise ValueError('PERSON_FIELDS_INVALID')
        pid=person['person_token']
        if not isinstance(pid,str) or not pid or pid in ids:raise ValueError('PERSON_TOKEN_DUPLICATED_OR_INVALID')
        ids.add(pid);waves=set();prior_hi=None;prior_wave=0
        if not isinstance(person['raw6'],dict) or not isinstance(person['visits'],list):raise ValueError('PERSON_STRUCTURE_INVALID')
        if not set(person['raw6'])<=RAW6_FIELDS:raise ValueError('UNEXPECTED_RAW_SCREEN_FIELDS')
        for v in person['visits']:
            required={'wave','date_lower','date_upper','kind','age','scope','since_wave','list_complete','branch_clear','mi','stroke','conditions','diagnosis_bounds'}
            if set(v)!=required:raise ValueError('VISIT_FIELDS_INVALID')
            w=v['wave'];lo,hi=dates(v)
            if type(w) is not int or not 1<=w<=9 or w in waves:raise ValueError('DUPLICATE_OR_UNSUPPORTED_WAVE')
            if w<=prior_wave:raise ValueError('WAVES_NOT_ORDERED')
            if prior_hi is not None and lo<=prior_hi:raise ValueError('VISITS_NOT_ORDERED_OR_DATE_BOUNDS_OVERLAP')
            if v['since_wave'] is not None and (type(v['since_wave']) is not int or v['since_wave']>=w):raise ValueError('QUESTION_REFERENCE_NOT_PRIOR')
            if v['kind'] not in KINDS or v['scope'] not in {'lifetime','interval','unknown'}:raise ValueError('UNSUPPORTED_INTERVIEW_SCOPE')
            if any(value is not None and type(value) is not bool for value in [v['list_complete'],v['branch_clear']]):raise ValueError('ROUTE_PROOF_INVALID')
            if v['mi'] not in STATES or v['stroke'] not in STATES or not isinstance(v['conditions'],list) or not set(v['conditions'])<=CONDITIONS:raise ValueError('COMPONENT_STATE_INVALID')
            if v['mi']=='tia':raise ValueError('TIA_IS_NOT_MI_STATE')
            for component in ['mi','stroke']:
                if component in v['conditions'] and v[component] not in ['yes','historical','disputed']:
                    raise ValueError('CONTRADICTORY_COMPONENT_LIST')
            if w<6 and v['kind'] in ['personal','partial','proxy','institutional'] and code(person['raw6'].get('inw'+str(w)))==0:
                raise ValueError('RAW_INW_CONFLICTS_WITH_RECORDED_RESPONSE')
            if set(v['diagnosis_bounds'])!={'mi','stroke'}:raise ValueError('DIAGNOSIS_COMPONENTS_INVALID')
            for value in v['diagnosis_bounds'].values():
                if value is not None:
                    if set(value)!={'lower','upper'} or date.fromisoformat(value['upper'])<date.fromisoformat(value['lower']):raise ValueError('DIAGNOSIS_DATE_INVALID')
                    if date.fromisoformat(value['upper'])>hi:raise ValueError('DIAGNOSIS_AFTER_INTERVIEW')
            waves.add(w);prior_hi=hi;prior_wave=w


def observed(v):
    return v['kind']=='personal' and v['list_complete'] is True and v['branch_clear'] is True


def negative_history(visits,baseline,component):
    rows=[v for v in visits if v['wave']<=baseline]
    if not rows or rows[-1]['wave']!=baseline:return False
    # Never erase any reported previous endpoint or unresolved dispute with a later no.
    if any(v[component] in ['yes','historical','disputed','tia'] for v in rows):return False
    covered=set()
    for v in rows:
        if not observed(v) or v[component]!='no':continue
        if v['scope']=='lifetime':covered.add(v['wave'])
        elif v['scope']=='interval' and v['since_wave'] in covered:covered.add(v['wave'])
    return baseline in covered


def outcome(visits,baseline,component):
    base=next(v for v in visits if v['wave']==baseline)
    blo,bhi=dates(base);target_lo=add_years(blo,6);target_hi=add_years(bhi,6)
    covered={baseline};negative_end=None;positive=False;dispute=False;ambiguous=False;death=False
    # Do not let post-window clinical observations supply six-year negatives.
    for v in visits:
        if v['wave']<=baseline:continue
        lo,hi=dates(v)
        if hi>target_lo+timedelta(days=183):continue
        if v['kind']=='dead':
            if lo<=target_hi:death=True
            continue
        if v['kind'] in ['withdrawn','none','exit','partial','proxy','institutional','unknown']:continue
        if death:raise ValueError('PERSONAL_OBSERVATION_AFTER_DEATH')
        s=v[component]
        if s=='disputed':dispute=True;continue
        if s in ['historical','tia']:
            if not positive:ambiguous=True
            continue
        if not observed(v):continue
        if s=='yes' and v['scope']=='interval':
            d=v['diagnosis_bounds'][component]
            if d is not None:
                dl=date.fromisoformat(d['lower']);dh=date.fromisoformat(d['upper'])
                if dh<=blo:dispute=True  # delayed report of pre-baseline diagnosis
                elif dl>bhi and dh<=target_lo:positive=True
                else:ambiguous=True
            elif v['since_wave'] in covered and hi<=target_lo:
                # First qualifying interval REPORT, not clinically adjudicated onset.
                positive=True
            else:ambiguous=True
        elif s=='no' and v['scope']=='interval' and v['since_wave'] in covered:
            covered.add(v['wave']);negative_end=lo
    if dispute:return 'DISPUTED_OR_PRIOR_OR_TIA'
    if positive:return 'POSITIVE_REPORT'
    if ambiguous:return 'UNKNOWN_TIMING'
    if death:return 'CENSORED_DEATH'
    if negative_end is not None and negative_end>=target_hi:return 'NEGATIVE_REPORT'
    return 'UNKNOWN_OBSERVATION'


def baseline_eligible(person,design,endpoint):
    baseline=DESIGNS[design];bywave={v['wave']:v for v in person['visits']}
    if baseline not in bywave:return False,'NO_BASELINE'
    v=bywave[baseline]
    if v['kind']!='personal' or not isinstance(v['age'],(int,float)) or not math.isfinite(v['age']) or v['age']<50:return False,'AGE_OR_INTERVIEW'
    if design=='B' and not common6(person['raw6']):return False,'W6_COMMON_SCREEN'
    if design=='A' and not strict6(person['raw6']):return False,'A_RAW_RECIPE'
    components=['mi','stroke'] if endpoint=='composite' else [endpoint]
    if baseline==6:
        fields={'mi':['r6hrtatte','hedimmi'],'stroke':['r6stroke','hedimst']}
        if any(code(person['raw6'].get(k))==1 for c in components for k in fields[c]):
            return False,'POSITIVE_BASELINE_SOURCE_HISTORY'
    if not all(negative_history(person['visits'],baseline,c) for c in components):return False,'UNVERIFIED_ENDPOINT_HISTORY'
    return True,'ELIGIBLE_BASELINE'


def count(people):
    validate_people(people)
    common=[p for p in people if common6(p['raw6'])]
    h={p['person_token'] for p in common if harmonized6(p['raw6'])}
    s={p['person_token'] for p in common if strict6(p['raw6'])}
    first_fail=Counter();marginal=Counter()
    for p in common:
        conditions=strict_predicates(p['raw6']);failed=[k for k,value in conditions.items() if not value]
        if failed:first_fail[failed[0]]+=1
        else:first_fail['PASS_ALL']+=1
        marginal.update(failed)
    designs={}
    for design,baseline in DESIGNS.items():
        for endpoint in ['composite','mi','stroke']:
            baseline_n=0;excluded=Counter();states=Counter()
            for p in people:
                eligible,reason=baseline_eligible(p,design,endpoint)
                if not eligible:excluded[reason]+=1;continue
                baseline_n+=1
                cs=[outcome(p['visits'],baseline,c) for c in (['mi','stroke'] if endpoint=='composite' else [endpoint])]
                result=('POSITIVE_REPORT' if 'POSITIVE_REPORT' in cs else 'NEGATIVE_REPORT' if all(c=='NEGATIVE_REPORT' for c in cs)
                        else 'DISPUTED_OR_PRIOR_OR_TIA' if 'DISPUTED_OR_PRIOR_OR_TIA' in cs
                        else 'CENSORED_DEATH' if 'CENSORED_DEATH' in cs else 'UNKNOWN')
                states[result]+=1
            if baseline_n!=sum(states.values()) or baseline_n+sum(excluded.values())!=len(people):
                raise ValueError('ACCOUNTING_PARTITION_FAILED')
            designs[design+'_'+endpoint]={'eligible_baseline':baseline_n,'excluded':dict(excluded),'outcome_states':dict(states),
                'ascertainable':states['POSITIVE_REPORT']+states['NEGATIVE_REPORT'],
                'feature_timing_complete_cohort':'NOT_COMPUTED_NO_PREDICTOR_CONTRACT',
                'not_modeling_authorization':True}
    return {'schema':'elsa-eligibility-counts-v1','count_unit':'unique_person',
        'raw_screen_overlap':{'C':len(common),'H':len(h),'S':len(s),'intersection':len(h&s),
                              'H_only':len(h-s),'S_only':len(s-h),'neither':len(common)-len(h|s)},
        'ordered_first_failure':dict(first_fail),'overlapping_marginal_failures':dict(marginal),
        'designs':designs,'participant_rows_or_ids_in_output':False,
        'scope':'REVIEWED_CANONICAL_REPORT_ENDPOINT_COUNTS_NOT_CLINICAL_INCIDENCE',
        'independent_test_status':'NOT_ESTABLISHED'}


def invented_people():
    people=[]
    for i in range(12):
        raw={'r6agey':60,'inw6':1,'w6indout':11,'askpx':0,'hedim96':1,'hedimmi':0,'hedimst':0,'r6hrtatte':0,'r6stroke':0,
             **{'inw'+str(w):0 for w in range(1,6)}}
        visits=[]
        for w in range(4,10):
            # Only W6 lifetime for most records; W4 start illustrates designC.
            when=date(2008+2*(w-4),6,1).isoformat()
            first=6 if i%2==0 else 4;active=w>=first
            visits.append({'wave':w,'date_lower':when,'date_upper':when,'kind':'personal' if active else 'none','age':56+2*(w-4),
                'scope':'unknown' if not active else 'lifetime' if w==first else 'interval',
                'since_wave':w-1 if active and w!=first else None,
                'list_complete':active,'branch_clear':active,'mi':'yes' if i==0 and w==7 else 'no' if active else 'unknown',
                'stroke':'no' if active else 'unknown',
                'conditions':['mi'] if i==0 and w==7 else [],'diagnosis_bounds':{'mi':None,'stroke':None}})
        if i%2:
            raw.update(inw4=1,inw5=1)
        # These are deliberately invented canonical fixtures, not raw-source claims.
        people.append({'person_token':f'INVENTED_REASSESSMENT_{i:03}','raw6':raw,'visits':visits})
    return people
