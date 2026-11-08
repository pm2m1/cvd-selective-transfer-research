"""Rebuild factual variable/value mappings from official PUBLIC dictionaries only.

Development documentation utility; never accepts clinical files. textutil is used
only to convert the pinned publisher RTF files. Runtime counting is cross-platform.
"""
from pathlib import Path
import hashlib,json,re,subprocess,zipfile

ROOT=Path(__file__).resolve().parent
ZIP_SHA='32161c5b497f5ae3df03cc81169b018548967e429eaaf0299bfd6b0f1c1082ae'
URL='https://doc.ukdataservice.ac.uk/doc/5050/mrdoc/ukda_data_dictionaries.zip'
MEMBERS={1:'wave_1_core_data_v3',2:'wave_2_core_data_v4',3:'wave_3_elsa_data_v4',
         **{w:'wave_'+str(w)+'_elsa_data_eul'+('_v2' if w in (8,9) else '') for w in range(4,10)}}

def sha(b):return hashlib.sha256(b).hexdigest()

def sections(text):
    out={}
    for s in re.split(r'(?=Pos\.\s*=\s*[\d,]+\s+Variable\s*=)',text):
        m=re.match(r'Pos\.\s*=\s*([\d,]+)\s+Variable\s*=\s*(\S+)\s+Variable label\s*=\s*([^\n]*)',s)
        if not m:continue
        key=m[2].lower()
        if key in out:raise ValueError('DUPLICATE_PUBLIC_VARIABLE')
        labels={str(int(float(n))):label.strip() for n,label in re.findall(r'Value\s*=\s*([-\d.]+)\s+Label\s*=\s*([^\n]*)',s)}
        out[key]={'archived_name':m[2],'position':int(m[1].replace(',','')),'label':m[3].strip(),
                  'values':labels,'section_sha256':sha(s.encode()),
                  'missing_range_metadata':next((x.strip() for x in s.splitlines() if x.startswith('SPSS user missing values')),None)}
    return out

def fields_for(w,allfields):
    names={'idauniq','indsex','indoc','w'+str(w)+'indout','askpx' if w>=3 else 'askpx1',
           'iintdatm','iintdaty','iintdtm','iintdty','intdatm','intdaty','indager','diagr','diag','indobyr',
           'hediagmi','hediagst','heagb','heage','heagbry','heagery','heagbr','heager',
           'hediax3','hediax8','henmmi','henmst','hedizm51','hedizm52'}
    if w<=2:
        names|={f'hedim{n:02}' for n in range(1,8 if w==1 else 9)}
        if w==2:names|={stem+str(n) for stem in ['hediaw','hediac','hedian'] for n in range(1,10)}
    else:
        names|={stem+s for stem in ['hedia','hedim'] for s in ['bp','an','mi','hf','hm','ar','di','st','ch','85','86','95','96','51','52']}
        names|={'hedaw'+s for s in ['bp','an','mi','hf','hm','ar','di','st','ch','ot','95']}
        names|={stem+s for stem in ['hedac','hedan'] for s in ['mi','st','di']}
    return {k:v for k,v in allfields.items() if k in names},sorted(names-set(allfields))

def build():
    path=ROOT/'public_documentation/ukda_data_dictionaries.zip'
    if sha(path.read_bytes())!=ZIP_SHA:raise ValueError('PUBLIC_DICTIONARY_HASH_MISMATCH')
    out={'schema':'elsa-official-field-map-v1','dictionary_url':URL,'dictionary_zip_sha256':ZIP_SHA,
         'retrieved_date':'2026-11-05','archive_edition_authenticated':False,
         'scope':'EXACT_NAMED_PUBLIC_DICTIONARIES_NOT_FROZEN_DISTRIBUTOR_AUTHENTICATION','waves':{},'nurse':{}}
    with zipfile.ZipFile(path) as z:
        for w,base in MEMBERS.items():
            name=base+'_ukda_data_dictionary.rtf';raw=z.read(name)
            text=subprocess.run(['textutil','-convert','txt','-stdin','-stdout'],input=raw,capture_output=True,check=True).stdout.decode()
            fields,absent=fields_for(w,sections(text))
            out['waves'][str(w)]={'dataset_basename':base+'.dta','dictionary_member':name,
                 'dictionary_member_sha256':sha(raw),'fields':fields,'checked_absent_fields':absent}
        for w,base in [(4,'wave_4_nurse_data'),(6,'wave_6_elsa_nurse_data_v2')]:
            name=base+'_ukda_data_dictionary.rtf';raw=z.read(name)
            text=subprocess.run(['textutil','-convert','txt','-stdin','-stdout'],input=raw,capture_output=True,check=True).stdout.decode()
            fs=sections(text)
            out['nurse'][str(w)]={'dataset_basename':base+'.dta','dictionary_member':name,'dictionary_member_sha256':sha(raw),
               'fields':{k:fs[k] for k in ['idauniq','vismon','visyear','sysval','diaval','bmival','bmiok','height','weight','relhite','relwait'] if k in fs}}
    destination=ROOT/'official_variable_map.json'
    with destination.open('x') as f:json.dump(out,f,indent=2,ensure_ascii=False);f.write('\n')
    return out

if __name__=='__main__':
    x=build();print('PUBLIC_DICTIONARY_MAPPING_CREATED_NO_CLINICAL_DATA')
