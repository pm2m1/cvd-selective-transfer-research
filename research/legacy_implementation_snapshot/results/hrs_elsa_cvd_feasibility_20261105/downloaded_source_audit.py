"""Read-only, selected-column HRS/ELSA screen explicitly authorized in this session.

Never invokes a historical controller, exports observations, or loads old results.
Only conservative aggregate screens are written; they are NOT certified incident
cohorts. Exact-calendar chronology and raw-route gaps are retained explicitly.
"""
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import csv
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parent


def read_member(archive,basename,columns):
    with ZipFile(archive) as z:
        names=[n for n in z.namelist() if Path(n).name==basename]
        if len(names)!=1:raise ValueError('EXPECTED_PRODUCT_MEMBER_UNRESOLVED')
        with z.open(names[0]) as stream:
            with pd.io.stata.StataReader(stream,convert_categoricals=False) as reader:
                labels=reader.variable_labels()
        present=[c for c in columns if c in labels]
        with z.open(names[0]) as stream:
            frame=pd.read_stata(stream,columns=present,convert_categoricals=False,convert_missing=False)
        return frame,{'member':basename,'required_present':present,'required_absent':[c for c in columns if c not in labels]}


def num(s):return pd.to_numeric(s,errors='coerce')


def key(frame,field,width=None):
    s=num(frame[field])
    if s.isna().any() or (s%1!=0).any():raise ValueError('INVALID_EXACT_LINKAGE_KEY')
    out=s.astype('int64').astype(str)
    if width:out=out.str.zfill(width)
    if out.duplicated().any():raise ValueError('NONUNIQUE_PRODUCT_KEY')
    return out


def count_rows(study,mask,metric,notes,endpoint='DOCUMENTARY_SCREEN',horizon='not_applied'):
    return {'study':study,'endpoint':endpoint,'horizon_years':horizon,'metric':metric,
            'value':int(mask.sum()),'status':'OBSERVED_AGGREGATE_SCREEN_NOT_FINAL_INCIDENT_COHORT','limitation':notes}


def suppress_family(rows):
    """Suppress whole numeric table if a positive small cell can be reconstructed.

    Threshold10 is a conservative engineering rule, not publisher clearance.
    No complementary totals are emitted for a family containing such a cell.
    """
    unsafe=any(isinstance(r['value'],int) and r['value']<10 for r in rows)
    return [{**r,'value':'SUPPRESSED_FAMILY','status':'DISCLOSURE_REVIEW_REQUIRED'} for r in rows] if unsafe else rows


def run(downloads):
    # Only explicit study archives. No recursive searches or private results.
    rand=downloads/'randhrs1992_2022v1_STATA.zip';gateway=downloads/'H_HRS_d_stata.zip'
    elsa=[p for p in downloads.iterdir() if p.is_file() and p.name.startswith('5050stata_') and p.suffix=='.zip']
    if len(elsa)!=1 or not rand.is_file() or not gateway.is_file():raise ValueError('EXACT_DOWNLOADED_PACKAGE_NOT_UNIQUE')
    elsa=elsa[0];headers={};rows=[];missingness=[]
    randcols=['hhidpn','ragender','raedyrs','raeduc']+[f'inw{w}' for w in range(11,16)]
    randcols += [f'r{w}{s}' for w in range(1,16) for s in ['strok','strokq']]
    randcols += [f'r{w}{s}' for w in range(11,16) for s in ['proxy','iwstat','iwendy','iwendm','agey_e']]
    randcols += [f'r11{s}' for s in ['diabe','smokev','smoken','hibpe','shlt','drink','vgactx','adla']]
    r,headers['HRS_RAND']=read_member(rand,'randhrs1992_2022v1.dta',randcols)
    r.index=key(r,'hhidpn',9)
    gcols=['hhid','pn']+[f'r{w}{s}' for w in range(11,16) for s in ['hrtatte','hrtatt','systo','diasto','mbmi','rxhibp']]
    g,headers['HRS_GATEWAY']=read_member(gateway,'H_HRS_d.dta',gcols)
    hhid=num(g['hhid']);pn=num(g['pn'])
    if hhid.isna().any() or pn.isna().any():raise ValueError('GATEWAY_KEY_MISSING')
    g.index=hhid.astype('int64').astype(str).str.zfill(6)+pn.astype('int64').astype(str).str.zfill(3)
    if g.index.duplicated().any():raise ValueError('GATEWAY_KEY_DUPLICATE')
    # Exact one-to-one join; unmatched records remain missing, never zeros.
    x=r.join(g.drop(columns=['hhid','pn']),how='left',validate='one_to_one')
    allr=pd.Series(True,index=x.index);base=num(x['inw11']).eq(1)
    age=base&num(x['r11agey_e']).ge(50);selfr=age&num(x['r11proxy']).eq(0)
    baseline_screen=selfr&num(x['r11hrtatte']).eq(0)&num(x['r11strok']).eq(0)
    note='Counts selected released records; no inference of strict incident eligibility or exact-calendar follow-up.'
    for name,mask in [('product_unique_records',allr),('baseline_response_flag',base),('baseline_age_50_plus',age),
                      ('baseline_self_response_screen',selfr),('harmonized_composite_history_negative_screen',baseline_screen)]:
        rows.append(count_rows('HRS',mask,name,note))
    for role,column in [('age','r11agey_e'),('sex','ragender'),('sbp','r11systo'),('dbp','r11diasto'),('bmi','r11mbmi'),
                        ('diabetes','r11diabe'),('smoking_ever','r11smokev'),('smoking_current','r11smoken'),('antihypertensive','r11rxhibp')]:
        available=num(x[column]).notna()&num(x[column]).ge(0)
        missingness.append(count_rows('HRS',selfr&~available,'missing_'+role,'Per-field metadata/value screen; not a complete-case or timing certificate.'))
    for endwave,horizon in [(13,4),(14,6),(15,8)]:
        definite=pd.Series(False,index=x.index);mi=pd.Series(False,index=x.index)
        for w in range(12,endwave+1):
            personal=num(x[f'inw{w}']).eq(1)&num(x[f'r{w}proxy']).eq(0)
            definite |= personal&num(x[f'r{w}strok']).eq(1)&num(x[f'r{w}strokq']).eq(2)
            if f'r{w}hrtatt' in x:mi |= personal&num(x[f'r{w}hrtatt']).eq(1)
        for label,event in [('mi_positive_report_screen',mi),('definite_Q2_stroke_positive_report_screen',definite),('unique_composite_positive_report_screen',mi|definite)]:
            rows.append(count_rows('HRS',baseline_screen&event,label,
                'Upper-screen among harmonized-history zeros; strict baseline/negative routes, death, features and timing NOT certified. Do not call incident events.',
                'HARMONIZED_REPORT_SCREEN',horizon))
    ecols=['idauniq','ragender','raeducl']+[f'inw{w}' for w in range(1,11)]
    ecols += [f'r{w}{s}' for w in range(6,11) for s in ['agey','iwy','iwm','stroke','hrtatte','strokf','hrtattf','diabe','smokev','smoken','rxhibp','hibpe','shlt','systo','diasto','mbmi','drink','vgactx_e','adla']]
    e,headers['ELSA_HARMONIZED']=read_member(elsa,'gh_elsa_h.dta',ecols);e.index=key(e,'idauniq')
    core={}
    for w,name in [(6,'wave_6_elsa_data_eul.dta'),(7,'wave_7_elsa_data_eul.dta'),(8,'wave_8_elsa_data_eul_v2.dta'),(9,'wave_9_elsa_data_eul_v2.dta')]:
        cols=['idauniq','askpx',f'w{w}indout','hedim96','hedimmi','hedimst','hedacmi','hedacst','hedanmi','hedanst','indsex','iintdatm','iintdaty']
        c,headers[f'ELSA_CORE{w}']=read_member(elsa,name,cols);c.index=key(c,'idauniq');core[w]=c.reindex(e.index)
    all_e=pd.Series(True,index=e.index);base=num(e['inw6']).eq(1);age=base&num(e['r6agey']).ge(50)
    selfr=age&num(core[6]['w6indout']).eq(11)&num(core[6]['askpx']).eq(0)
    history=all_e.copy()
    for w in range(1,6):history &= num(e[f'inw{w}']).eq(0)
    lifetime=selfr&history&num(core[6]['hedim96']).eq(1)&num(core[6]['hedimmi']).eq(0)&num(core[6]['hedimst']).eq(0)
    harmonized=selfr&num(e['r6hrtatte']).eq(0)&num(e['r6stroke']).eq(0)
    for name,mask in [('product_unique_records',all_e),('baseline_response_flag',base),('baseline_age_50_plus',age),
                      ('baseline_full_personal',selfr),('harmonized_composite_history_negative_screen',harmonized),
                      ('first_personal_W6_lifetime_none_sufficient_baseline_screen',lifetime)]:
        rows.append(count_rows('ELSA',mask,name,
            'Sufficient lifetime-none baseline is narrow and not all disease-free respondents. This does not certify downstream incident routes.'))
    for role,column in [('age','r6agey'),('sex','ragender'),('sbp','r6systo'),('dbp','r6diasto'),('bmi','r6mbmi'),
                        ('diabetes','r6diabe'),('smoking_ever','r6smokev'),('smoking_current','r6smoken'),('antihypertensive','r6rxhibp')]:
        available=num(e[column]).notna()&num(e[column]).ge(0)
        missingness.append(count_rows('ELSA',selfr&~available,'missing_'+role,'Per-field availability among personal age50+; nurse timing NOT certified.'))
    # Do not derive ELSA interval endpoints from rWhrtatte/rWstroke transitions.
    # They require release-specific branch, confirmation and historical proof.
    report={'scope':'AUTHORIZED_READ_ONLY_SELECTED_COLUMN_SCREEN_NOT_COMPLETED_STAGE_C_REPLAY',
        'headers':headers,'cohort_screens':suppress_family(rows),
        'missingness_screens':suppress_family(missingness),
        'raw_participant_rows_written':False,'strict_primary_event_counts_computed':False,
        'gate':'STRICT_RAW_ROUTE_AND_CALENDAR_TIMING_ADAPTER_NOT_CERTIFIED',
        'original_controllers_invoked':False,'prior_private_outputs_read':False,
        'archive_origins_independently_authenticated':False,
        'permission_basis':'explicit researcher authorization in this conversation; no forged external approval',
        'disclosure_rule':'whole-family suppression if any cell below10; not a formal clearance certificate'}
    return report


def main():
    # Deliberately no broad search CLI or automatic real-data invocation at import.
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--downloads',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        report=run(a.downloads)
        with a.output.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
    except BaseException:
        print('STOP LOCAL_SOURCE_SCREEN_NOT_COMPLETED_NO_ROWS_DISCLOSED');return 2
    print('LOCAL_READ_ONLY_SCREEN_COMPLETE_NO_ROWS_DISCLOSED');return 0


if __name__=='__main__':raise SystemExit(main())
