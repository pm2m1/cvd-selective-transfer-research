"""Minimal extra read-only upper-bound calculation, not a cohort-engine replay."""
from pathlib import Path
import math
import json
import pandas as pd
from downloaded_source_audit import read_member,num,key


def public_upper_bound(n):
    # Round UP, never down, and never disclose whether a small count is zero.
    return max(10,10*math.ceil(n/10))


def run(downloads):
    archives=[p for p in downloads.iterdir() if p.is_file() and p.name.startswith('5050stata_') and p.suffix=='.zip']
    if len(archives)!=1:raise ValueError('ELSA_PACKAGE_NOT_UNIQUE')
    z=archives[0]
    e,_=read_member(z,'gh_elsa_h.dta',['idauniq','r6agey',*[f'inw{w}' for w in range(1,7)]])
    e.index=key(e,'idauniq');cores={}
    for w,name in [(6,'wave_6_elsa_data_eul.dta'),(7,'wave_7_elsa_data_eul.dta'),(8,'wave_8_elsa_data_eul_v2.dta'),(9,'wave_9_elsa_data_eul_v2.dta')]:
        c,_=read_member(z,name,['idauniq','askpx',f'w{w}indout','hedim96','hedimmi','hedimst'])
        c.index=key(c,'idauniq');cores[w]=c.reindex(e.index)
    base=num(e['r6agey']).ge(50)&num(e['inw6']).eq(1)
    for w in range(1,6):base &= num(e[f'inw{w}']).eq(0)
    c=cores[6];base &= num(c['w6indout']).eq(11)&num(c['askpx']).eq(0)&num(c['hedim96']).eq(1)&num(c['hedimmi']).eq(0)&num(c['hedimst']).eq(0)
    rows=[]
    for last,horizon in [(8,4),(9,6)]:
        mi=pd.Series(False,index=e.index);stroke=mi.copy()
        for w in range(7,last+1):
            c=cores[w];personal=num(c[f'w{w}indout']).eq(11)&num(c['askpx']).eq(0)
            mi |= personal&num(c['hedimmi']).eq(1)
            stroke |= personal&num(c['hedimst']).eq(1)
        for endpoint,mask in [('mi',mi),('stroke',stroke),('composite',mi|stroke)]:
            n=int((base&mask).sum())
            rows.append({'study':'ELSA','endpoint':endpoint,'nominal_horizon_years':horizon,
                'conservative_rounded_up_max_qualifying_events':public_upper_bound(n),
                'interpretation':'not actual eligible events; upper bound before chronology, dispute/history, predictors and attrition gates',
                'population':'FIRST_PERSONAL_W6_LIFETIME_NONE_AGE50_PLUS',
                'exact_cell_not_released':True})
    return {'scope':'AUTHORIZED_READ_ONLY_BOUND_NOT_STAGE_C_REPLAY','rows':rows,
        'raw_participant_outputs_written':False,'counts_rounded_up_to_protect_small_cells':True,
        'upper_bound_proof':'Every qualifying current-rule event in this fixed baseline subgroup must have a full-personal merged MI/stroke positive report; excluding any further uncertainty can only reduce that candidate set.',
        'limitation':'not a bound for all ELSA or newly designed component-specific baseline populations; no8-year claim'}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--downloads',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        result=run(a.downloads)
        with a.output.open('x') as f:json.dump(result,f,indent=2)
    except BaseException:
        print('STOP TARGET_CEILING_NOT_COMPLETED_NO_ROWS_DISCLOSED');raise SystemExit(2)
    print('TARGET_CEILING_COMPLETE_NO_EXACT_SMALL_CELLS_DISCLOSED')
