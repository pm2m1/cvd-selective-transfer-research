"""Canonical, fail-closed longitudinal feasibility logic; no clinical file loader.

Source-specific evidence must be established BEFORE canonical states are supplied.
Only hard-coded invented fixtures can be executed from the public CLI.
"""
from dataclasses import dataclass,field
from datetime import date,timedelta
from collections import defaultdict,Counter
import argparse
import csv
import json
import math
from pathlib import Path

STATES={'positive','negative','unknown','disputed','tia'}
KINDS={'personal','proxy','exit','partial','none','dead','unknown'}
ENDPOINTS={'composite':('mi','stroke'),'mi':('mi',),'stroke':('stroke',)}
BLOCKED='NOT_COMPUTABLE_ACCESS_BLOCKED'


def add_years(d,n):
    try:return d.replace(year=d.year+n)
    except ValueError:return d.replace(year=d.year+n,day=28)


def raw_code(value):
    if isinstance(value,bool):return None
    if value is None:return None
    if isinstance(value,str):
        value=value.strip()
        if value.startswith('.') or value in ['', '<missing>']:return None
    try:
        x=float(value)
        return int(x) if math.isfinite(x) and x.is_integer() else None
    except (TypeError,ValueError):return None


def hrs_direct(raw,scope,route_verified,component='stroke'):
    """Original Core yes1/no5 only; skip/DK/refusal is not observed negative."""
    if scope not in ['lifetime','interval'] or not route_verified:return 'unknown'
    if component not in ['stroke','mi']:raise ValueError('UNREVIEWED_COMPONENT')
    codes={1:'positive',5:'negative'}
    if component=='stroke':codes.update({2:'tia',3:'disputed',4:'disputed'})
    return codes.get(raw_code(raw),'unknown')


def hrs_mi_interval(raw,route_verified):
    code=raw_code(raw)
    if not route_verified:return 'unknown'
    return {1:'positive',5:'negative'}.get(code,'unknown')


def harmonized_mi(raw,negative_route):
    """Strict mode never promotes a harmonizer's screening-derived zero."""
    if raw_code(raw)==1:return 'positive'
    if raw_code(raw)==0 and negative_route=='direct_observed':return 'negative'
    return 'unknown'


def rand_stroke(raw,q,baseline=False,history_verified=False):
    """Follow-up Q2; baseline no remains provisional without separate history proof."""
    code=raw_code(raw)
    if code==2:return 'tia'
    if code in [3,4,5]:return 'disputed'
    if baseline:
        if code==1:return 'positive'
        if code==0 and raw_code(q) in [1,2,5,10] and history_verified:return 'negative'
        return 'unknown'
    # q=1/5 are lifetime question routes, not new interval events.
    if raw_code(q)!=2:return 'unknown'
    return {0:'negative',1:'positive'}.get(code,'unknown')


def elsa_component(merged,*,personal,scope,prior_negative_proven,branch_clear,
                   explicit_completed_list,confirmation=None,dispute_reason=None):
    """Conservative adapter contract, not a substitute for release-specific history.

    branch_clear must be independently proven from full route/history evidence.
    Neither -1 nor a missing confirmation field proves that flag on its own.
    """
    if not personal or scope not in ['lifetime','interval']:return 'unknown'
    if raw_code(confirmation)==3:return 'unknown'  # Not read is not a denial.
    if raw_code(confirmation)==2 or raw_code(dispute_reason) in [1,2,3,4]:return 'disputed'
    if raw_code(confirmation)==1:return 'positive' if scope=='lifetime' else 'unknown'
    if not branch_clear:return 'unknown'
    if scope=='interval' and not prior_negative_proven:return 'unknown'
    if raw_code(merged)==1:return 'positive'
    if raw_code(merged)==0 and explicit_completed_list:return 'negative'
    return 'unknown'


def first_personal_lifetime_none(inw,indout,askpx,none,mi,stroke):
    """Previously adopted sufficient W6 proof; not necessary for all possible histories."""
    return (len(inw)==6 and all(raw_code(x)==0 for x in inw[:5]) and raw_code(inw[5])==1
            and raw_code(indout)==11 and raw_code(askpx)==0 and raw_code(none)==1
            and raw_code(mi)==0 and raw_code(stroke)==0)


def convert_unit(value,unit,role):
    if value is None:return None
    if isinstance(value,bool):raise ValueError('BOOLEAN_NUMERIC_FEATURE')
    x=float(value)
    if not math.isfinite(x):return None
    if role in ['sbp','dbp']:
        if unit=='kPa':return x*7.50061683
        if unit=='mmHg':return x
    if role in ['total_cholesterol','hdl']:
        if unit=='mmol/L':return x*38.67
        if unit=='mg/dL':return x
    if role=='bmi' and unit=='kg/m2':return x
    if role=='age' and unit=='years':return x
    raise ValueError('UNVERIFIED_FEATURE_UNIT')


@dataclass(frozen=True)
class Feature:
    value:object
    measured:date
    available:date
    unit:str='category'


@dataclass(frozen=True)
class Visit:
    study:str
    person:str
    wave:int
    when:date
    kind:str='personal'
    age:float|None=60.
    mi:str='negative'
    stroke:str='negative'
    scope:str='interval'
    interval_start:date|None=None
    mi_date:date|None=None
    stroke_date:date|None=None
    features:dict=field(default_factory=dict)
    linkage_valid:bool=True


def link(records):
    linked=defaultdict(list);keys=set()
    for r in records:
        if r.study not in ['HRS','ELSA'] or not isinstance(r.person,str) or not r.person.strip():raise ValueError('INVALID_EXACT_ID')
        if r.mi not in STATES or r.stroke not in STATES or r.kind not in KINDS:raise ValueError('UNSUPPORTED_CANONICAL_STATE')
        key=(r.study,r.person,r.wave)
        if key in keys:raise ValueError('DUPLICATE_PERSON_WAVE')
        keys.add(key);linked[(r.study,r.person)].append(r)
    for key,rows in linked.items():
        rows.sort(key=lambda r:r.when)
        if len({r.when for r in rows})!=len(rows):raise ValueError('DUPLICATE_INTERVIEW_DATE')
        if [r.wave for r in rows]!=sorted(r.wave for r in rows):raise ValueError('NONMONOTONE_WAVES')
    return dict(linked)


def component(rows,base,name,years,tolerance=183):
    """Fixed horizon conservative classification, preserving censoring/interval ambiguity.

    A valid negative interval must continuously cover baseline through the target
    date. Assessments later than target+183 days cannot extend negative coverage.
    A positive whose undated interval straddles the target is UNKNOWN, not dated
    at its reporting interview. Positives established before death remain cases.
    """
    target=add_years(base.when,years);coverage=base.when;event=False;disputed=False;death=False
    for r in rows:
        if r.when<=base.when:continue
        if r.when>target+timedelta(days=tolerance):continue
        if r.kind=='dead':
            if r.when<=target:death=True
            continue
        if r.kind!='personal':continue
        if death:raise ValueError('PERSONAL_INTERVIEW_AFTER_RECORDED_DEATH')
        value=getattr(r,name)
        if value=='disputed':disputed=True;continue
        if event and r.scope=='lifetime' and value=='negative':disputed=True;continue
        if value=='positive':
            d=getattr(r,name+'_date')
            if r.scope!='interval':continue
            if d is not None:
                if not base.when<d<=r.when:raise ValueError('INVALID_EVENT_DATE')
                if d<=target:event=True
            elif r.when<=target and r.interval_start is not None and r.interval_start>=base.when:
                event=True
        if value=='negative' and r.scope=='interval' and r.interval_start is not None:
            if r.interval_start>=r.when:raise ValueError('INVALID_INTERVAL')
            if r.interval_start<=coverage:coverage=max(coverage,r.when)
    if disputed:return 'DISPUTED'
    if event:return 'POSITIVE'
    if death:return 'CENSORED_DEATH'
    if coverage>=target:return 'NEGATIVE'
    return 'UNKNOWN'


def features_valid(base,required):
    missing=[]
    for name in required:
        f=base.features.get(name)
        if f is None or f.value is None:missing.append(name);continue
        if f.measured>base.when or f.available>base.when:raise ValueError('POST_BASELINE_FEATURE_LEAKAGE')
        if name in ['age','sbp','dbp','bmi','total_cholesterol','hdl']:
            if convert_unit(f.value,f.unit,name) is None:missing.append(name)
        elif f.value in ['unknown','missing','disputed','refused']:missing.append(name)
    return missing


def audit(records,baseline_wave,endpoint='composite',years=6,required_features=('age','sex','bmi')):
    if endpoint not in ENDPOINTS or years not in [4,6,8]:raise ValueError('UNREGISTERED_ANALYSIS')
    linked=link(records);flow=Counter();states=Counter();mi_events=stroke_events=composite_events=0
    retained=[];missing=Counter();by_age=Counter();by_sex=Counter()
    for (study,pid),rows in linked.items():
        flow['total_unique']+=1
        baselines=[r for r in rows if r.wave==baseline_wave[study]]
        if not baselines:flow['excluded_not_at_primary_baseline']+=1;continue
        flow['baseline_present']+=1;base=baselines[0]
        if not base.linkage_valid or base.age is None or not math.isfinite(base.age) or base.age<50:
            flow['excluded_invalid_age_or_linkage']+=1;continue
        flow['valid_age_linkage']+=1
        if base.kind!='personal':flow['excluded_baseline_interview']+=1;continue
        if base.scope!='lifetime':flow['excluded_unproven_baseline_history']+=1;continue
        previous=[getattr(base,n) for n in ENDPOINTS[endpoint]]
        if 'positive' in previous:flow['excluded_prior_endpoint_disease']+=1;continue
        if any(s!='negative' for s in previous):flow['excluded_unknown_baseline_history']+=1;continue
        flow['baseline_disease_free']+=1
        components={n:component(rows,base,n,years) for n in ['mi','stroke']}
        relevant=[components[n] for n in ENDPOINTS[endpoint]]
        status=('POSITIVE' if 'POSITIVE' in relevant else 'NEGATIVE' if all(s=='NEGATIVE' for s in relevant)
                else 'DISPUTED' if 'DISPUTED' in relevant else 'CENSORED_DEATH' if 'CENSORED_DEATH' in relevant else 'UNKNOWN')
        states[status]+=1
        if status not in ['POSITIVE','NEGATIVE']:flow['excluded_unascertained_outcome']+=1;continue
        flow['outcome_ascertainable']+=1
        miss=features_valid(base,required_features);missing.update(miss)
        if miss:flow['excluded_missing_predictors']+=1;continue
        flow['retained']+=1;positive=int(status=='POSITIVE')
        flow['positive']+=positive;flow['negative']+=1-positive
        mi_events+=int(components['mi']=='POSITIVE');stroke_events+=int(components['stroke']=='POSITIVE')
        composite_events+=int(components['mi']=='POSITIVE' or components['stroke']=='POSITIVE')
        age='50-64' if base.age<65 else '65-74' if base.age<75 else '75+'
        by_age[age]+=positive;by_sex[str(base.features.get('sex',Feature(None,base.when,base.when)).value)]+=positive
        retained.append((study,pid,positive))
    excluded=sum(v for k,v in flow.items() if k.startswith('excluded_'))
    if excluded+flow['retained']!=flow['total_unique'] or flow['positive']+flow['negative']!=flow['retained']:
        raise AssertionError('WATERFALL_PARTITION_FAILURE')
    if composite_events>mi_events+stroke_events:raise AssertionError('COMPONENT_UNION_FAILURE')
    return {'scope':'CANONICAL_INPUTS_NOT_RAW_RELEASE_VALIDATION','endpoint':endpoint,'horizon_years':years,
        'flow':dict(flow),'outcome_states':dict(states),'missing_predictors':dict(missing),
        'retained_mi_reports':mi_events,'retained_stroke_reports':stroke_events,
        'retained_composite_people':composite_events,'event_fraction':flow['positive']/flow['retained'] if flow['retained'] else None,
        'events_by_age':dict(by_age),'events_by_sex':dict(by_sex),'retained_internal':retained}


def partition(ids,fractions=(.6,.15,.1,.15),seed=20261105):
    """Outcome-blind participant allocation, not guaranteed event support."""
    import random
    if len(set(ids))!=len(ids) or abs(sum(fractions)-1)>1e-9 or min(fractions)<=0:raise ValueError('INVALID_PARTITION')
    order=sorted(ids);random.Random(seed).shuffle(order);result=[];position=0
    for i,f in enumerate(fractions):
        n=int(len(order)*f) if i<len(fractions)-1 else len(order)-position
        result.append(order[position:position+n]);position+=n
    assert sum(map(len,result))==len(ids)
    return result


def invented_records():
    d=date(2012,6,1);features={
        'age':Feature(60,d,d,'years'),'sex':Feature('female',d,d),'bmi':Feature(25,d,d,'kg/m2')}
    rows=[]
    for study,wave in [('HRS',11),('ELSA',6)]:
        for i in range(8):
            pid=f'INVENTED_{study}_{i:03}'
            rows.append(Visit(study,pid,wave,d,scope='lifetime',features=features))
            for step in [1,2,3]:
                when=add_years(d,2*step)
                rows.append(Visit(study,pid,wave+step,when,mi='positive' if i==0 and step==1 else 'negative',
                    stroke='positive' if i==1 and step==2 else 'negative',interval_start=add_years(d,2*(step-1))))
    return rows


def main():
    parser=argparse.ArgumentParser(description='INVENTED DATA DEMO ONLY; no clinical-input mode')
    parser.add_argument('--synthetic-demo',action='store_true',required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();a.output.mkdir(mode=0o700,exist_ok=False)
    report={}
    for endpoint in ENDPOINTS:
        result=audit(invented_records(),{'HRS':11,'ELSA':6},endpoint)
        result.pop('retained_internal');result['scope']='INVENTED_SYNTHETIC_ONLY_NOT_EMPIRICAL_COHORT_COUNTS'
        report[endpoint]=result
    with (a.output/'SYNTHETIC_ONLY.json').open('x') as f:json.dump(report,f,indent=2)
    print('SYNTHETIC_ONLY COMPLETE; REAL EMPIRICAL COUNTS NOT COMPUTED')


if __name__=='__main__':main()
