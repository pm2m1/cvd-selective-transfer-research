"""Pure count logic. No file discovery, dataset reads, model or network calls."""
from collections import Counter
from datetime import date,timedelta
import calendar,hashlib,math,re

DESIGNS={'W6_W9':(6,9),'W4_W7':(4,7)}
ROLES={'age':'years','sex':'category','sbp':'mmHg','dbp':'mmHg','bmi':'kg/m2',
       'smoking':'category','diabetes':'category','bp_treatment':'category'}

class CountError(ValueError):pass
def need(ok,code):
    if not ok:raise CountError(code)

def num(value):
    if value is None or isinstance(value,bool):return None
    if isinstance(value,str) and re.fullmatch(r'\.[a-z]?',value):return None
    try:v=float(value)
    except (TypeError,ValueError):raise CountError('NONNUMERIC_SOURCE_REPRESENTATION') from None
    return v if math.isfinite(v) else None

def code(value):
    v=num(value)
    need(v is None or v.is_integer(),'NONINTEGER_CATEGORICAL_VALUE')
    return None if v is None else int(v)

def scalar(raw,name,fields):
    if name is None:return None
    need(name in fields,'UNMAPPED_FIELD')
    v=code(raw.get(name))
    if v is not None and fields[name]['values']:
        need(str(v) in fields[name]['values'],'CODE_OUTSIDE_OFFICIAL_DOMAIN')
    return v

def month_bounds(year,month):
    y,m=code(year),code(month)
    if y is None or m is None or y<1900 or not 1<=m<=12:return None
    return date(y,m,1),date(y,m,calendar.monthrange(y,m)[1])

def anniversary(d):
    try:return d.replace(year=d.year+6)
    except ValueError:return d.replace(year=d.year+6,day=28)

def interview(v,mapping):
    w=v['wave'];fs=mapping['waves'][str(w)]['fields'];raw=v['raw']
    value=scalar(raw,'indoc' if w==1 else f'w{w}indout',fs)
    proxy=scalar(raw,'askpx1' if w<3 else 'askpx',fs)
    if value==11 and proxy==(2 if w==1 else 0):return 'personal'
    if value in (13,23,25,27) or proxy==1:return 'proxy'
    if value in (21,26):return 'partial'
    if value==24:return 'institutional'
    if value is not None and 'died' in fs['indoc' if w==1 else f'w{w}indout']['values'].get(str(value),'').lower():return 'death_status'
    return 'unknown'

def visit_dates(v,mapping):
    fs=mapping['waves'][str(v['wave'])]['fields'];r=v['raw']
    # Older individual dates differ from household dates; never substitute them.
    for a,b in [('iintdaty','iintdatm'),('iintdty','iintdtm')]:
        if a in fs and b in fs:return month_bounds(r.get(a),r.get(b))
    return None

def reference(person,w):
    past=[(x,person['participation'].get(str(x))) for x in range(1,w)]
    known=[x for x,p in past if code(p)==1]
    if not known:return ('lifetime',None) if all(code(p)==0 for _,p in past) else ('unknown',None)
    last=max(known)
    if any(code(p) is None for x,p in past if x>last):return 'unknown',None
    return 'interval',last

def list_response(v,component,mapping):
    w=v['wave'];r=v['raw'];fs=mapping['waves'][str(w)]['fields'];target={'mi':3,'stroke':8,'diabetes':7}[component]
    if w<3:
        names=[f'hedim{i:02}' for i in range(1,8 if w==1 else 9)]
        vals=[scalar(r,n,fs) for n in names]
        if target in vals:return 'unknown' if 96 in vals else 'yes'
        # -1 may pad unused mention slots only when at least one valid answer exists.
        valid=[x for x in vals if x is not None and x>0]
        if not valid or any(x is None or (x<0 and x!=-1) for x in vals):return 'unknown'
        if 96 in valid and len(valid)!=1:return 'unknown'
        if any(x in (85,86,95) for x in valid):return 'unknown'
        return 'no'
    targetname={'mi':'hedimmi','stroke':'hedimst','diabetes':'hedimdi'}[component]
    targetvalue=scalar(r,targetname,fs)
    if targetvalue==1:return 'unknown' if scalar(r,'hedim96',fs)==1 else 'yes'
    if targetvalue!=0:return 'unknown'
    names=[n for n in fs if (n.startswith('hedim') or n in ('hedizm51','hedizm52')) and n not in {'hedim01','hedim02'}]
    # Fields are the archived merged list, not the original pre-recoding dummies.
    vals={n:scalar(r,n,fs) for n in names}
    if any(x not in (0,1) for x in vals.values()) or not any(x==1 for x in vals.values()):return 'unknown'
    if vals.get('hedim96')==1 and sum(vals.values())!=1:return 'unknown'
    if any(vals.get(n)==1 for n in ['hedim85','hedim86']):return 'unknown'
    return 'no'

def observation(v,component,mapping):
    """Distinguish responses, branch-inapplicability and historical confirmation."""
    if interview(v,mapping)!='personal':return 'not_personal'
    w=v['wave'];fs=mapping['waves'][str(w)]['fields'];r=v['raw']
    answer=list_response(v,component,mapping)
    if w==1:return {'yes':'new_report','no':'negative_response','unknown':'unknown'}[answer]
    c={'mi':3,'stroke':8,'diabetes':7}[component];suffix={'mi':'mi','stroke':'st','diabetes':'di'}[component]
    bundle=[n for n in fs if (re.fullmatch(r'hediaw\d+',n) if w==2 else n.startswith('hedaw'))]
    confirm=f'hediac{c}' if w==2 else 'hedac'+suffix
    dispute=f'hedian{c}' if w==2 else 'hedan'+suffix
    ff=[scalar(r,n,fs) for n in bundle]
    # These are positional mentioned-condition slots; never inspect only a
    # deceptively condition-named slot such as hedawmi.
    f=c if c in ff else -1 if ff and all(x in {-1,1,2,3,4,5,6,7,8,9,95} for x in ff) else None
    d=scalar(r,dispute,fs)
    # W9 MI confirmation is deliberately absent, not a fabricated negative.
    q=None if (w==9 and component=='mi') else scalar(r,confirm,fs)
    if d in (1,2,3,4) or q==2:return 'disputed'
    if f==c or q==1:
        return 'historical_confirmed' if q==1 and d==-1 else 'historical_unconfirmed'
    extra='hediax'+str(c)
    if extra in fs and scalar(r,extra,fs)==1:return 'historical_unconfirmed'
    if f!=-1 or d!=-1 or (confirm in fs and q!=-1):return 'unknown'
    return {'yes':'new_report','no':'negative_response','unknown':'unknown'}[answer]

def history(person,baseline,component,mapping,details=False):
    covered=set();reported=False;unconfirmed=False;disputed=False;reasons=set();anchor=False
    for v in person['visits']:
        if v['wave']>baseline:break
        w=v['wave'];obs=observation(v,component,mapping)
        if interview(v,mapping)=='proxy' and list_response(v,component,mapping)=='yes':unconfirmed=True
        if obs in ('new_report','historical_confirmed'):reported=True
        if obs=='historical_unconfirmed':unconfirmed=True
        if obs=='disputed':disputed=True
        if obs=='unknown':reasons.add('LIST_OR_CONFIRMATION_BRANCH_UNKNOWN')
        if obs=='not_personal':reasons.add('NONPERSONAL_HISTORY_OBSERVATION')
        if obs=='negative_response':
            scope,ref=reference(person,w)
            if scope=='lifetime':anchor=True;covered.add(w)
            elif scope=='interval' and ref in covered:covered.add(w)
            else:reasons.add('UNVERIFIED_REFERENCE_OR_HISTORY_GAP')
    screening=person['screening_history'].get(str(baseline),{}).get(component)
    if code(screening)==1:unconfirmed=True
    bv=next((v for v in person['visits'] if v['wave']==baseline),None)
    if bv is not None:
        # A derived first-report-wave zero is not a personal lifetime negative.
        field={'mi':'hediagmi','stroke':'hediagst'}.get(component)
        fs=mapping['waves'][str(baseline)]['fields']
        if field in fs:
            reported_wave=scalar(bv['raw'],field,fs)
            if reported_wave is not None and 1<=reported_wave<=baseline:unconfirmed=True
    state=('DISPUTED' if disputed else 'CONFIRMED_PRIOR_REPORT' if reported else
           'PRIOR_RECORD_UNCONFIRMED' if unconfirmed else 'VERIFIED_ABSENT' if baseline in covered else 'UNKNOWN')
    if not anchor:reasons.add('NO_VERIFIED_PERSONAL_LIFETIME_NEGATIVE_ANCHOR')
    return {'state':state,'diagnostic_conditions':sorted(reasons)} if details else state

def followup(person,baseline,end,component,mapping,policy,details=False):
    need(policy in ('wave_window','fixed_six_year'),'UNRECOGNIZED_TIMING_POLICY')
    reasons=set()
    def result(state):return {'state':state,'diagnostic_conditions':sorted(reasons)} if details else state
    base=next(v for v in person['visits'] if v['wave']==baseline);bd=visit_dates(base,mapping)
    if bd is None:return result('UNKNOWN_BASELINE_DATE')
    lo,hi=map(anniversary,bd);late=lo+timedelta(days=183);early=hi-timedelta(days=183)
    closing=next((v for v in person['visits'] if v['wave']==end),None)
    closing_dates=visit_dates(closing,mapping) if closing is not None else None
    closing_ok=closing_dates is not None and closing_dates[0]>=early and closing_dates[1]<=late
    positive=False;disputed=False;ambiguous=False;death=False;covered={baseline};last_negative=None
    for v in person['visits']:
        w=v['wave']
        if not baseline<w<=end:continue
        kind=interview(v,mapping)
        if kind=='death_status':death=True;reasons.add('RECORDED_DEATH_STATUS_NO_EXACT_DEATH_DATE');continue
        ds=visit_dates(v,mapping)
        if ds is None:reasons.add('INTERVIEW_DATE_UNKNOWN');continue
        if ds[1]>late:reasons.add('OUTSIDE_ASCERTAINMENT_WINDOW');continue
        if kind!='personal':reasons.add('NONPERSONAL_FOLLOWUP_'+kind.upper());continue
        need(not death,'PERSONAL_AFTER_RECORDED_DEATH')
        obs=observation(v,component,mapping);scope,ref=reference(person,w)
        if obs=='disputed':disputed=True;reasons.add('DISPUTED_DIAGNOSIS')
        elif obs in ('historical_confirmed','historical_unconfirmed'):
            if not positive:ambiguous=True;reasons.add('HISTORICAL_FIRST_APPEARANCE_TIMING_UNKNOWN')
        elif obs=='new_report':
            before_end=(ds[1]<=lo if policy=='fixed_six_year' else
                        (closing_ok and ds[1]<=closing_dates[1]) or ds[1]<=early)
            # A new positive needs a documented post-baseline reference, not
            # fabricated negative responses at every intervening interview.
            # Earlier unresolved historical appearance still blocks this proof.
            if scope=='interval' and ref is not None and ref>=baseline and before_end and not ambiguous:positive=True
            else:ambiguous=True;reasons.add('REPORT_TIMING_OR_REFERENCE_UNVERIFIED')
        elif obs=='negative_response' and scope=='interval' and ref in covered:
            covered.add(w);last_negative=ds[0]
        elif obs=='unknown':reasons.add('QUESTION_LIST_OR_BRANCH_UNKNOWN')
        else:reasons.add('UNCOVERED_INTERVAL_OR_HISTORY_GAP')
    if disputed:return result('DISPUTED')
    if positive:return result('INCIDENT_REPORT')
    if ambiguous:return result('UNKNOWN_EVENT_OR_TIMING')
    if policy=='wave_window':
        if closing_ok and end in covered:return result('OBSERVED_NONEVENT')
    elif last_negative is not None and last_negative>=hi:return result('OBSERVED_NONEVENT')
    if death:return result('CENSORED_DEATH_STATUS')
    if closing is not None and interview(closing,mapping)=='proxy':return result('UNKNOWN_PROXY')
    if not closing_ok:return result('UNKNOWN_CLOSING_OR_HORIZON')
    return result('UNKNOWN_GAP_OR_RESPONSE')

def combine(mi,stroke):
    if 'INCIDENT_REPORT' in (mi,stroke):return 'INCIDENT_REPORT'
    if mi==stroke=='OBSERVED_NONEVENT':return 'OBSERVED_NONEVENT'
    if 'DISPUTED' in (mi,stroke):return 'DISPUTED'
    if 'CENSORED_DEATH_STATUS' in (mi,stroke):return 'CENSORED_DEATH_STATUS'
    return 'UNKNOWN'

def feature_status(person,baseline,mapping):
    fs=person['features'].get(str(baseline))
    if fs is None:return 'NOT_SUPPLIED',{}
    need(set(fs)==set(ROLES),'FEATURE_ROLES_INVALID')
    base=next(v for v in person['visits'] if v['wave']==baseline);ds=visit_dates(base,mapping)
    statuses={}
    for role,unit in ROLES.items():
        x=fs[role];need(set(x)=={'value','unit','source_wave','context','measured_lower','measured_upper','available_upper'},'FEATURE_SCHEMA_INVALID')
        value=num(x['value'])
        if value is None or value<0:statuses[role]='MISSING';continue
        if role in ('age','sbp','dbp','bmi') and value==0:statuses[role]='INVALID';continue
        need(x['unit']==unit,'FEATURE_UNIT_MISMATCH')
        if role in ('sex','diabetes','bp_treatment'):need(value in (0,1),'FEATURE_CATEGORY_INVALID')
        if role=='smoking':need(value in (0,1,2),'FEATURE_CATEGORY_INVALID')
        need(type(x['source_wave']) is int and 1<=x['source_wave']<=baseline,'POST_BASELINE_FEATURE_WAVE')
        if x['context']=='same_core_interview':
            need(x['source_wave']==baseline and role not in ('sbp','dbp','bmi'),'UNJUSTIFIED_SAME_SESSION_FEATURE')
            statuses[role]='VALID';continue
        need(x['context']=='dated_examination','FEATURE_CONTEXT_INVALID')
        if ds is None or any(x[k] is None for k in ['measured_lower','measured_upper','available_upper']):
            statuses[role]='TIMING_UNKNOWN';continue
        ml,mu,au=map(date.fromisoformat,[x['measured_lower'],x['measured_upper'],x['available_upper']])
        need(ml<=mu<=au,'FEATURE_DATES_INVALID')
        statuses[role]='VALID' if au<=ds[0] else 'AFTER_OR_OVERLAPS_BASELINE'
    overall='COMPLETE_TIMELY' if all(v=='VALID' for v in statuses.values()) else 'INCOMPLETE_OR_UNTIMELY'
    return overall,statuses

def partition(token,protocol):
    u=int.from_bytes(hashlib.sha256((protocol['partition_salt']+'\0'+token).encode()).digest()[:8],'big')/2**64
    for role,weight in protocol['partition_fractions'].items():
        u-=weight
        if u<0:return role
    raise CountError('PARTITION_FRACTIONS_INVALID')

def validate_people(people,mapping):
    ids=set()
    for p in people:
        need(set(p)=={'token','participation','visits','screening_history','features','prior_model_use'},'PERSON_SCHEMA_INVALID')
        need(isinstance(p['token'],str) and p['token'] and p['token'] not in ids,'DUPLICATE_PERSON')
        ids.add(p['token']);waves=set();previous=0;death_seen=False
        need(p['prior_model_use'] in ('no','yes','unknown'),'EXPOSURE_STATE_INVALID')
        need(set(p['participation'])==set(map(str,range(1,10))),'PARTICIPATION_HISTORY_INCOMPLETE')
        need(all(code(x) in (0,1,None) for x in p['participation'].values()),'PARTICIPATION_CODE_INVALID')
        for v in p['visits']:
            need(set(v)=={'wave','raw'} and type(v['wave']) is int and 1<=v['wave']<=9,'VISIT_SCHEMA_INVALID')
            w=v['wave'];need(w not in waves and w>previous,'DUPLICATE_OR_UNORDERED_WAVE');waves.add(w);previous=w
            fs=mapping['waves'][str(w)]['fields'];need(set(v['raw'])<=set(fs),'UNEXPECTED_OR_UNAVAILABLE_RAW_FIELD')
            need(all(k==k.lower() for k in v['raw']),'RAW_FIELD_CASE_NOT_NORMALIZED')
            kind=interview(v,mapping)
            need(not (death_seen and kind=='personal'),'PERSONAL_AFTER_RECORDED_DEATH')
            if kind=='death_status':death_seen=True
            if kind in ('personal','partial','proxy','institutional'):
                flag=code(p['participation'][str(w)])
                need(flag is not None,'PARTICIPATION_INTERVIEW_STATUS_UNRESOLVED')
                need(flag==1,'PARTICIPATION_INTERVIEW_CONFLICT')

def analyze(people,mapping,protocol):
    validate_people(people,mapping)
    fractions=protocol['partition_fractions'];need(all(x>0 for x in fractions.values()) and abs(sum(fractions.values())-1)<1e-12,'PARTITION_FRACTIONS_INVALID')
    result={'schema':'elsa-final-count-aggregates-v1','scope':'PRIVATE_FIRST_QUALIFYING_SURVEY_REPORTS_NOT_ADJUDICATED_CLINICAL_INCIDENCE',
            'designs':{},'independent_test_status':'NOT_ESTABLISHED_BY_COUNTS','training_authorized':False,
            'participant_rows_or_ids_written':False}
    for name,(baseline,end) in DESIGNS.items():
        flow=Counter();marginal=Counter();histjoint=Counter();featurecounts=Counter();featurecells=Counter();historyreasons=Counter();baselinekinds=Counter()
        flow.update({k:0 for k in ['input_unique_people','excluded_no_baseline_response','baseline_participants',
           'excluded_missing_core','excluded_unknown_age','excluded_age_under50','age50plus',
           'excluded_nonpersonal_baseline','personal_age50plus','excluded_prior_MI_first',
           'excluded_prior_stroke_after_MI','excluded_unknown_or_disputed_history','verified_MI_stroke_free']})
        outputs={policy:{'components':{'mi':Counter(),'stroke':Counter()},'joint':Counter(),'composite':Counter(),
                 'timely_feature_composite':Counter(),'partition_scenarios':{r:Counter() for r in fractions},
                 'potential_untouched_evaluation':Counter(),'prior_use_evidence_in_binary_complete_cases':Counter(),
                 'observation_diagnostic_marginals':Counter()} for policy in ['wave_window','fixed_six_year']}
        for p in people:
            flow['input_unique_people']+=1
            if code(p['participation'][str(baseline)])!=1:flow['excluded_no_baseline_response']+=1;continue
            flow['baseline_participants']+=1
            base=next((v for v in p['visits'] if v['wave']==baseline),None)
            if base is None:flow['excluded_missing_core']+=1;continue
            age=num(base['raw'].get('indager'))
            if age is None or age<0:flow['excluded_unknown_age']+=1;continue
            if age<50:flow['excluded_age_under50']+=1;continue
            flow['age50plus']+=1
            kind=interview(base,mapping)
            if kind!='personal':flow['excluded_nonpersonal_baseline']+=1;baselinekinds[kind]+=1;continue
            flow['personal_age50plus']+=1
            hd={c:history(p,baseline,c,mapping,True) for c in ['mi','stroke']}
            hs={c:d['state'] for c,d in hd.items()}
            for c,d in hd.items():
                if d['state']!='VERIFIED_ABSENT':historyreasons.update(c+'_'+reason for reason in d['diagnostic_conditions'])
            histjoint[hs['mi']+'|'+hs['stroke']]+=1
            for c,state in hs.items():marginal[c+'_'+state]+=1
            if hs['mi']=='CONFIRMED_PRIOR_REPORT':flow['excluded_prior_MI_first']+=1;continue
            if hs['stroke']=='CONFIRMED_PRIOR_REPORT':flow['excluded_prior_stroke_after_MI']+=1;continue
            if any(s!='VERIFIED_ABSENT' for s in hs.values()):flow['excluded_unknown_or_disputed_history']+=1;continue
            flow['verified_MI_stroke_free']+=1
            fstatus,perfeature=feature_status(p,baseline,mapping);featurecounts[fstatus]+=1
            for role,state in perfeature.items():featurecells[role+'_'+state]+=1
            for policy,out in outputs.items():
                detailed={c:followup(p,baseline,end,c,mapping,policy,True) for c in ['mi','stroke']}
                states={c:d['state'] for c,d in detailed.items()}
                for c,d in detailed.items():
                    if d['state'] not in ('INCIDENT_REPORT','OBSERVED_NONEVENT'):
                        out['observation_diagnostic_marginals'].update(c+'_'+reason for reason in d['diagnostic_conditions'])
                for c,s in states.items():out['components'][c][s]+=1
                out['joint'][states['mi']+'|'+states['stroke']]+=1
                s=combine(states['mi'],states['stroke']);out['composite'][s]+=1
                if fstatus=='COMPLETE_TIMELY':
                    out['timely_feature_composite'][s]+=1
                    if s in ('INCIDENT_REPORT','OBSERVED_NONEVENT'):
                        role=partition(p['token'],protocol);out['partition_scenarios'][role][s]+=1
                        out['prior_use_evidence_in_binary_complete_cases'][p['prior_model_use']]+=1
                        if role=='evaluation' and p['prior_model_use']=='no':out['potential_untouched_evaluation'][s]+=1
        need(flow['input_unique_people']==flow['baseline_participants']+flow['excluded_no_baseline_response'],'FLOW_ACCOUNTING_FAILED')
        need(flow['baseline_participants']==sum(flow[k] for k in ['excluded_missing_core','excluded_unknown_age','excluded_age_under50','excluded_nonpersonal_baseline','excluded_prior_MI_first','excluded_prior_stroke_after_MI','excluded_unknown_or_disputed_history','verified_MI_stroke_free']),'FLOW_ACCOUNTING_FAILED')
        for policy,out in outputs.items():
            need(sum(out['composite'].values())==flow['verified_MI_stroke_free'],'OUTCOME_PARTITION_FAILED')
            need(sum(out['joint'].values())==flow['verified_MI_stroke_free'],'COMPONENT_PARTITION_FAILED')
            need(all(sum(out['components'][c].values())==flow['verified_MI_stroke_free'] for c in ['mi','stroke']),'COMPONENT_DENOMINATOR_FAILED')
            n=flow['verified_MI_stroke_free'];co=out['composite']
            out['summary']={'eligible_baseline':n,
               'incident_MI_reports':out['components']['mi']['INCIDENT_REPORT'],
               'incident_stroke_reports':out['components']['stroke']['INCIDENT_REPORT'],
               'unique_composite_incident_reports':co['INCIDENT_REPORT'],
               'observed_composite_nonevents':co['OBSERVED_NONEVENT'],
               'ascertained_binary_outcomes':co['INCIDENT_REPORT']+co['OBSERVED_NONEVENT'],
               'unknown_disputed_or_censored':n-co['INCIDENT_REPORT']-co['OBSERVED_NONEVENT'],
               'both_component_states_binary':sum(n for k,n in out['joint'].items() if all(s in ['INCIDENT_REPORT','OBSERVED_NONEVENT'] for s in k.split('|'))),
               'timely_complete_case_binary':out['timely_feature_composite']['INCIDENT_REPORT']+out['timely_feature_composite']['OBSERVED_NONEVENT']}
            out['partition_status']=('EMPTY_BASELINE' if not n else 'NOT_COMPUTED_FEATURE_EVIDENCE_UNAVAILABLE'
                 if featurecounts['NOT_SUPPLIED']==n else 'PARTIAL_INPUT_PROVEN_SUBSET_ONLY'
                 if featurecounts['NOT_SUPPLIED'] else 'SCENARIO_COUNTS_NOT_A_REGISTERED_TEST')
            out['summary']['complete_case_availability_status']=out['partition_status']
            if out['partition_status']=='NOT_COMPUTED_FEATURE_EVIDENCE_UNAVAILABLE':out['summary']['timely_complete_case_binary']=None
            need(out['summary']['unique_composite_incident_reports']<=out['summary']['incident_MI_reports']+out['summary']['incident_stroke_reports'],'COMPOSITE_UNION_FAILED')
        result['designs'][name]={'flow_ordered':dict(flow),'baseline_component_marginals':dict(marginal),
            'baseline_history_joint':dict(histjoint),'feature_availability':dict(featurecounts),
            'nonpersonal_baseline_exclusions_by_kind':dict(baselinekinds),
            'baseline_history_diagnostic_marginals':dict(historyreasons),
            'feature_status_marginals':dict(featurecells),'outcomes':outputs,
            'clinical_onset_date_confirmed_incident_events':'NOT_ESTABLISHED_WITH_THESE_RELEASE_FIELDS'}
    # Convert counters to ordinary dictionaries; no person-level artifact is retained.
    import json
    return json.loads(json.dumps(result))
