"""Optional Stata reader for a NEW independently permitted operation only.

Never called at import or by synthetic tests with real files. Exact local input
descriptors are supplied by the independent operator, never discovered.
"""
from pathlib import Path
import hashlib,math,re
from count_engine import need,num,CountError
from local_execution import require_local,descriptor,load_json

def bound(d):
    need(isinstance(d,dict) and isinstance(d.get('path'),str) and Path(d['path']).is_absolute(),'ABSOLUTE_REVIEWED_SOURCE_PATH_REQUIRED')
    return descriptor(d)

def person_key(x):
    # IDAUNIQ is numeric in the named release dictionaries. No fuzzy/string join.
    need(not isinstance(x,(str,bool)),'UNSUPPORTED_LINKAGE_STORAGE')
    v=num(x);need(v is not None and v.is_integer() and 0<v<2**53,'INVALID_EXACT_PERSON_KEY')
    return 'ELSA_NUMERIC_'+str(int(v))

def plain(x):
    # Preserve Stata missing tags as strings, never numeric zeros.
    if x is None:return None
    if type(x).__name__=='StataMissingValue':return str(x)
    if hasattr(x,'item'):x=x.item()
    if isinstance(x,float) and not math.isfinite(x):return None
    return x

def count_fields(w,fields):
    names={'idauniq','indoc' if w==1 else f'w{w}indout','askpx1' if w<3 else 'askpx',
           'iintdatm','iintdaty','iintdtm','iintdty','hediax3','hediax8','hediagmi','hediagst','hedizm51','hedizm52'}
    if w in (4,6):names.add('indager')
    names|={n for n in fields if n.startswith('hedim') or n.startswith('hedaw')}
    if w in (4,6):names.add('indsex')
    if w==2:names|={n for n in fields if re.fullmatch(r'hediaw\d+',n)}|{'hediac3','hediac7','hediac8','hedian3','hedian7','hedian8'}
    elif w>2:names|={'hedacmi','hedacdi','hedacst','hedanmi','hedandi','hedanst'}
    return names&set(fields)

def load_selected(path,allowed,required=None,forbidden=()):
    require_local()
    import pandas as pd
    # Reading variable names is part of this newly authorized restricted operation.
    with pd.io.stata.StataReader(path,convert_categoricals=False,convert_missing=True) as reader:
        labels=reader.variable_labels();names={}
        for name in labels:
            key=name.lower();need(key not in names,'COLUMN_CASE_COLLISION');names[key]=name
        need('idauniq' in names,'PERSON_KEY_COLUMN_MISSING')
        need(set(required or {'idauniq'})<=set(names),'REQUIRED_PUBLIC_MAPPING_FIELD_MISSING')
        need(not set(forbidden)&set(names),'SOURCE_REVISION_INCOMPATIBLE_WITH_OFFICIAL_MAP')
        cols=[names[k] for k in allowed if k in names]
        frame=reader.read(columns=cols)
    frame.columns=[c.lower() for c in frame.columns]
    need(not frame['idauniq'].duplicated().any(),'DUPLICATE_SOURCE_PERSON')
    return {person_key(row['idauniq']):{k:plain(v) for k,v in row.items() if k!='idauniq'}
            for row in frame.to_dict('records')}

def load_people(config,mapping):
    require_local()
    need(config.get('source_format')=='registered_stata_tables_v1','SOURCE_FORMAT_INVALID')
    required={'harmonized'}|{'core'+str(w) for w in range(1,10)}
    need(set(config['sources'])==required,'REQUIRED_HISTORY_TABLES_INCOMPLETE')
    tables={};bindings={};paths={}
    for role,d in config['sources'].items():
        expected='gh_elsa_h.dta' if role=='harmonized' else mapping['waves'][role[4:]]['dataset_basename']
        need(d.get('dataset_basename')==expected,'SOURCE_PRODUCT_IDENTITY_MISMATCH')
        path=bound(d);paths[role]=path
        allowed=({'idauniq'}|{f'inw{w}' for w in range(1,10)}|
                 {f'r{w}{s}' for w in [4,6] for s in ['hrtatte','stroke','smokev','smoken','rxhibp']}) if role=='harmonized' else count_fields(int(role[4:]),mapping['waves'][role[4:]]['fields'])
        required_fields=({'idauniq'}|{f'inw{w}' for w in range(1,10)}) if role=='harmonized' else allowed-{
            'hediagmi','hediagst','hediax3','hediax8','iintdtm','iintdty'}
        tables[role]=load_selected(path,allowed,required_fields,{'hedacmi'} if role=='core9' else ())
        bindings[role]={'dataset_basename':expected,'sha256':d['sha256'],'claimed_archive_edition':d.get('claimed_archive_edition','UNRESOLVED')}
    measurements={}
    if config.get('measurement_sources') is not None:
        need(set(config['measurement_sources'])=={'4','6'},'MEASUREMENT_SOURCE_ROLES_INCOMPLETE')
        hfeatures={f'r{w}{s}' for w in [4,6] for s in ['smokev','smoken','rxhibp']}
        # Whole missing columns differ from missing individual responses.
        sample=next(iter(tables['harmonized'].values()),{})
        need(hfeatures<=set(sample),'BASELINE_FEATURE_FIELDS_MISSING_FROM_HARMONIZED_PRODUCT')
        for w,d in config['measurement_sources'].items():
            expected=mapping['nurse'][w]['dataset_basename'];need(d.get('dataset_basename')==expected,'NURSE_PRODUCT_IDENTITY_MISMATCH')
            path=bound(d);role='nurse'+w;paths[role]=path
            cols={'idauniq','vismon','visyear','sysval','diaval','bmival'}
            measurements[int(w)]=load_selected(path,cols,cols)
            bindings[role]={'dataset_basename':expected,'sha256':d['sha256']}
    h=tables['harmonized'];need(h,'HARMONIZED_POPULATION_EMPTY');people=[]
    feature_meta={}
    if config.get('feature_metadata') is not None:
        path=bound(config['feature_metadata']);paths['feature_metadata']=path
        fm=load_json(path)
        need(fm.get('schema')=='elsa-baseline-feature-evidence-v1' and fm.get('baseline_only_reviewed') is True
             and fm.get('mapping_sha256')==config['mapping_sha256']
             and fm.get('source_bindings') and fm.get('derivation_source_sha256')
             and re.fullmatch('[0-9a-f]{64}',fm['derivation_source_sha256']), 'FEATURE_EVIDENCE_UNREVIEWED')
        for row in fm['people']:
            need(set(row)=={'idauniq','features','prior_model_use'},'FEATURE_EVIDENCE_SCHEMA_INVALID')
            token=person_key(row['idauniq']);need(token not in feature_meta,'DUPLICATE_FEATURE_METADATA')
            need(token in h,'FEATURE_METADATA_OUTSIDE_REGISTERED_POPULATION');feature_meta[token]=row
        bindings['feature_metadata']={'sha256':config['feature_metadata']['sha256']}
    qc={}
    for token,rawh in h.items():
        visits=[{'wave':w,'raw':tables['core'+str(w)][token]} for w in range(1,10) if token in tables['core'+str(w)]]
        fm=feature_meta.get(token,{})
        people.append({'token':token,'participation':{str(w):rawh.get('inw'+str(w)) for w in range(1,10)},
             'visits':visits,'screening_history':{str(w):{'mi':rawh.get(f'r{w}hrtatte'),'stroke':rawh.get(f'r{w}stroke')} for w in [4,6]},
             'features':fm.get('features',{}),'prior_model_use':fm.get('prior_model_use','unknown')})
        if measurements:
            from baseline_features import derive
            feature_rows,issues=derive(people[-1],rawh,{w:rows.get(token,{}) for w,rows in measurements.items()},mapping)
            feature_rows.update(fm.get('features',{}));people[-1]['features']=feature_rows
            for issue in issues:qc[issue]=qc.get(issue,0)+1
    qa={'population':'HARMONIZED_H_UNIQUE_PERSON_KEYS_WITH_ORIGINAL_CORE_HISTORY',
        'unmatched_core_people_outside_registered_harmonized_population':{role:len(set(t)-set(h)) for role,t in tables.items() if role!='harmonized'},
        'feature_metadata_supplied':config.get('feature_metadata') is not None,
        'automatic_baseline_feature_derivation':bool(measurements),'feature_derivation_QC_counts':qc}
    # A changed file invalidates the consumed operation, not its historical evidence.
    for role,path in paths.items():
        original=config['feature_metadata'] if role=='feature_metadata' else config['measurement_sources'][role[5:]] if role.startswith('nurse') else config['sources'][role]
        descriptor(original)
    return people,bindings,qa
