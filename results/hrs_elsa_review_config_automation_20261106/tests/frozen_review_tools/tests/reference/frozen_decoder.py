"""Exact selected pure frozen functions; no cohort pipeline or source I/O."""
import math,re

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
