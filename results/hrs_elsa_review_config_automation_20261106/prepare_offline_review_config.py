"""Independent local metadata binding only. No review execution or approval.

Standard library only. Never import clinical readers or discover recursively.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

ORIGINAL_MANIFEST_SHA256 = '5bb62e1cfec5326b9f9bdd5221e4b2e0b9b51457f5eb8244768e2d669729d130'
ROLES = ('diagnostic_config','diagnostic_authorization','diagnostic_completion','diagnostic_integrity',
         'diagnostic_report','diagnostic_input_validation','failed_count_config','failed_count_authorization',
         'failed_count_completion','source_registration')
HISTORICAL = ('hrs_elsa_interview_status_diagnostic_20261106_run',
              'hrs_elsa_counts_registered_20261106_run','hrs_elsa_registration_20261105_run')
DECLARATIONS = ('source_use_review','isolation_review','reviewed_scope')
HEX = re.compile('[0-9a-f]{64}')
LIMIT = 16 * 1024 * 1024
HELPER_ROOT = Path(__file__).resolve().parent


class Stop(ValueError):
    pass


def need(value, code='METADATA_BINDING_NOT_READY'):
    if not value: raise Stop(code)


def independent():
    keys=('CODEX_HOME','CODEX_SESSION_ID','CODEX_THREAD_ID','CODEX_CI','CI','GITHUB_ACTIONS','CHATGPT_SESSION_ID')
    need(not any(os.environ.get(k) for k in keys) and sys.stdin.isatty(),'INDEPENDENT_LOCAL_OPERATOR_REQUIRED')


def absolute(path):
    p=Path(path)
    need(p.is_absolute() and '..' not in p.parts,'PRIVATE_FILESYSTEM_UNSAFE')
    need(not any(q.is_symlink() for q in (p,*p.parents)),'PRIVATE_FILESYSTEM_UNSAFE')
    return p


def directory(path, root=None):
    p=absolute(path);s=p.stat()
    need(stat.S_ISDIR(s.st_mode) and s.st_uid==os.getuid() and s.st_mode&0o077==0,'PRIVATE_FILESYSTEM_UNSAFE')
    if root is not None:
        need(p.is_relative_to(root),'PRIVATE_FILESYSTEM_UNSAFE')
        for q in p.parents:
            if not q.is_relative_to(root): break
            s=q.stat();need(s.st_uid==os.getuid() and s.st_mode&0o077==0,'PRIVATE_FILESYSTEM_UNSAFE')
    return p


def json_bytes(data):
    def pairs(items):
        result={}
        for k,v in items:
            need(k not in result,'DUPLICATE_JSON_FIELD');result[k]=v
        return result
    def invalid(_):raise Stop('INVALID_JSON_METADATA')
    return json.loads(data,object_pairs_hook=pairs,parse_constant=invalid)


def read(path, root=None, private=True):
    p=absolute(path)
    need(p.suffix=='.json','JSON_METADATA_REQUIRED')
    if private:
        need(root is not None and p.is_relative_to(root),'PRIVATE_FILESYSTEM_UNSAFE')
        directory(p.parent,root)
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        s=os.fstat(f.fileno())
        need(stat.S_ISREG(s.st_mode) and s.st_size<=LIMIT,'PRIVATE_FILESYSTEM_UNSAFE')
        if private:need(s.st_uid==os.getuid() and stat.S_IMODE(s.st_mode)==0o600,'PRIVATE_FILESYSTEM_UNSAFE')
        data=f.read(LIMIT+1)
    need(len(data)<=LIMIT,'INVALID_JSON_METADATA')
    return json_bytes(data),data,hashlib.sha256(data).hexdigest(),(s.st_dev,s.st_ino)


def review_tool(path):
    """Verify the EXISTING public release in place, never install or modify it."""
    sys.dont_write_bytecode=True # Also protect frozen tools when called as an API.
    root=absolute(path)
    manifest,_,digest,_=read(root/'RELEASE_MANIFEST.json',private=False)
    need(digest==ORIGINAL_MANIFEST_SHA256,'PUBLIC_REVIEW_RELEASE_MISMATCH')
    for name,pin in manifest['files'].items():
        n=Path(name);need(not n.is_absolute() and '..' not in n.parts,'PUBLIC_REVIEW_RELEASE_MISMATCH')
        p=absolute(root/n)
        need(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==pin,'PUBLIC_REVIEW_RELEASE_MISMATCH')
    # Bind original module imports explicitly; no caller's module or source is substituted.
    saved={name:sys.modules.get(name) for name in ('local_execution','review_logic')}
    try:
        for name in saved:
            spec=importlib.util.spec_from_file_location(name,root/(name+'.py'))
            module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
        spec=importlib.util.spec_from_file_location('_verified_original_review',root/'offline_scientific_review.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    finally:
        for name,value in saved.items():
            if value is None:sys.modules.pop(name,None)
            else:sys.modules[name]=value
    template=json_bytes((root/'review_config.template.json').read_bytes())
    return module,template


def artifacts(config):
    return {name:config.with_name(config.name+suffix) for name,suffix in
            [('backup','.prebinding.backup.json'),('stage','.binding.staging.json'),('record','.binding.record.json')]}


def run_directory(config, check=False):
    a=artifacts(config)
    expected={config.name}|({a['backup'].name,a['record'].name} if check else set())
    need({p.name for p in config.parent.iterdir()}==expected,'REVIEW_RUN_HAS_PRIOR_OR_PARTIAL_ARTIFACTS')
    return a


def config_location(config, root, tools):
    p=absolute(config)
    need(p.is_relative_to(root) and not p.is_relative_to(tools) and not p.is_relative_to(HELPER_ROOT),'PRIVATE_FILESYSTEM_UNSAFE')
    need(not any(p.is_relative_to(root/n) for n in HISTORICAL),'HISTORICAL_RECORD_WRITE_REFUSED')
    directory(p.parent,root)
    return p


def known_candidates(folder, pattern):
    # ONE approved directory, ONE shallow listing, bounded JSON filename family.
    found=[p for p in folder.iterdir() if re.fullmatch(pattern,p.name)]
    need(0<len(found)<=32,'EVIDENCE_MISSING_OR_AMBIGUOUS')
    return found


def discover_operation(folder, root, purpose, config_schema):
    directory(folder,root)
    auths=known_candidates(folder,r'(?i)(?:[A-Za-z0-9_.-]+[._-])?authorization(?:[._-][A-Za-z0-9_.-]+)?\.json')
    need(len(auths)==1,'EVIDENCE_MISSING_OR_AMBIGUOUS') # Never choose among several authorizations.
    auth,_,_,_=read(auths[0],root)
    need(auth.get('purpose')==purpose and auth.get('authorized') is True
         and auth.get('scope_confirmed_by_operator') is True and isinstance(auth.get('config_sha256'),str)
         and HEX.fullmatch(auth['config_sha256']),'EVIDENCE_ROLE_MISMATCH')
    matches=[]
    for p in known_candidates(folder,r'(?i)(?:[A-Za-z0-9_.-]+[._-])?(?:config(?:uration)?|reviewed)(?:[._-][A-Za-z0-9_.-]+)?\.json'):
        c,_,h,_=read(p,root)
        if h==auth['config_sha256']:
            need(c.get('schema')==config_schema,'EVIDENCE_ROLE_MISMATCH');matches.append((p,c))
    need(len(matches)==1,'EVIDENCE_MISSING_OR_AMBIGUOUS')
    out=absolute(auth['output_binding']);need(out.is_relative_to(folder),'EVIDENCE_ROLE_MISMATCH')
    directory(out,root)
    return auths[0],matches[0][0],matches[0][1],out


def discover(root, original):
    contract=original.public_json('references/PUBLIC_CONTRACT.json')
    da,dc,dconfig,dout=discover_operation(root/HISTORICAL[0],root,contract['diagnostic_purpose'],'elsa-status-diagnostic-local-config-v1')
    fa,fc,_,fout=discover_operation(root/HISTORICAL[1],root,contract['count_purpose'],'elsa-final-count-local-config-v1')
    registration=dconfig.get('source_registration')
    need(isinstance(registration,dict) and set(registration)=={'path','sha256'}
         and isinstance(registration['sha256'],str) and HEX.fullmatch(registration['sha256']),'EVIDENCE_ROLE_MISMATCH')
    rp=absolute(registration['path'])
    need(rp.is_relative_to(root/HISTORICAL[2]) and rp.name=='source_registration.private.json','EVIDENCE_ROLE_MISMATCH')
    return {'diagnostic_config':{'path':str(dc)},'diagnostic_authorization':{'path':str(da)},
        'diagnostic_completion':{'path':str(dout/'completion.private.json')},
        'diagnostic_integrity':{'path':str(dout/'diagnostic_integrity.private.json')},
        'diagnostic_report':{'path':str(dout/'status_diagnostic.private.json')},
        'diagnostic_input_validation':{'path':str(dout/'input_validation.private.json')},
        'failed_count_config':{'path':str(fc)},'failed_count_authorization':{'path':str(fa)},
        'failed_count_completion':{'path':str(fout/'completion.private.json')},'source_registration':registration}


def explicit_map(path, root, config):
    independent()
    p=absolute(path);need(p.parent!=config.parent,'EVIDENCE_MAP_MUST_BE_OUTSIDE_REVIEW_RUN')
    value,_,_,_=read(p,root)
    need(isinstance(value,dict) and set(value)=={'schema','evidence'}
         and value['schema']=='elsa-review-evidence-paths-v1','EVIDENCE_ROLE_MISMATCH')
    return value['evidence']


def bind_descriptors(locations,root,tools,config):
    need(isinstance(locations,dict) and set(locations)==set(ROLES),'EVIDENCE_ROLE_MISMATCH')
    descriptors={};seen=set()
    for role,entry in locations.items():
        need(isinstance(entry,dict) and set(entry) in ({'path'},{'path','sha256'}) and isinstance(entry.get('path'),str),'EVIDENCE_ROLE_MISMATCH')
        p=absolute(entry['path'])
        need(p not in seen and not p.is_relative_to(tools) and not p.is_relative_to(config.parent),'EVIDENCE_ROLE_MISMATCH')
        seen.add(p)
        _,_,digest,_=read(p,root)
        if 'sha256' in entry:
            need(isinstance(entry['sha256'],str) and HEX.fullmatch(entry['sha256']) and entry['sha256']==digest,'EVIDENCE_HASH_MISMATCH')
        descriptors[role]={'path':str(p),'sha256':digest}
    return descriptors


def core_hash(config):
    core={k:v for k,v in config.items() if k not in DECLARATIONS}
    return hashlib.sha256(json.dumps(core,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def exclusive(path, data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:
        os.fchmod(f.fileno(),0o600);f.write(data);f.flush();os.fsync(f.fileno())


def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def validate_bindings(config,root,original):
    # Reuse the frozen METADATA validator only. It does not examine classification
    # cells, generate a worksheet, invoke execution/authorization, or read sources.
    report,_=original.verify_existing_evidence(config,root,root/'UNUSED_BINDING_VALIDATION_DESTINATION')
    need(report.get('schema')=='elsa-private-status-diagnostic-v1'
         and report.get('scope')=='STATUS_ONLY_NO_DISEASE_ENDPOINTS_NO_ELIGIBILITY_CHANGES'
         and report.get('participant_rows_or_keys_written') is False,'EVIDENCE_ROLE_MISMATCH')


def bind(config,root,tools,locations=None,discover_known=False):
    independent()
    original,template=review_tool(tools);root=directory(root);config=config_location(config,root,tools)
    a=run_directory(config)
    initial,raw,old_sha,identity=read(config,root)
    need(initial==template,'CONFIG_NOT_PRISTINE')
    need((locations is not None) != discover_known,'EVIDENCE_SELECTION_REQUIRED')
    locations=discover(root,original) if discover_known else locations
    descriptors=bind_descriptors(locations,root,tools,config)
    updated=copy.deepcopy(initial);updated['private_root']=str(root);updated['evidence']=descriptors
    validate_bindings(updated,root,original)
    need(all(updated[k]==initial[k] for k in DECLARATIONS),'CONFIG_SEMANTICS_CHANGED')
    new_raw=(json.dumps(updated,indent=2,allow_nan=False)+'\n').encode()
    record={'schema':'elsa-metadata-config-binding-record-v1','not_authorization':True,
        'original_template_bytes_sha256':old_sha,'bound_core_sha256':core_hash(updated),
        'initial_bound_bytes_sha256':hashlib.sha256(new_raw).hexdigest(),
        'original_public_review_manifest_sha256':ORIGINAL_MANIFEST_SHA256}
    run_directory(config) # Recheck after input verification, before any write.
    exclusive(a['backup'],raw);sync_directory(config.parent)
    exclusive(a['stage'],new_raw);sync_directory(config.parent)
    _,again,h,ident=read(config,root)
    need(h==old_sha and again==raw and ident==identity,'CONFIG_CHANGED_DURING_PREPARATION')
    for d in descriptors.values():need(read(d['path'],root)[2]==d['sha256'],'EVIDENCE_HASH_MISMATCH')
    need({p.name for p in config.parent.iterdir()}=={config.name,a['backup'].name,a['stage'].name},
         'REVIEW_RUN_HAS_PRIOR_OR_PARTIAL_ARTIFACTS')
    os.replace(a['stage'],config);sync_directory(config.parent)
    need(read(config,root)[2]==record['initial_bound_bytes_sha256'],'ATOMIC_BINDING_NOT_COMPLETED')
    need({p.name for p in config.parent.iterdir()}=={config.name,a['backup'].name},
         'REVIEW_RUN_HAS_PRIOR_OR_PARTIAL_ARTIFACTS')
    # A binding record exists only AFTER atomic replacement and its verification.
    # An interrupted preparation is retained, never mistaken for a completed bind.
    exclusive(a['record'],(json.dumps(record,indent=2)+'\n').encode());sync_directory(config.parent)
    run_directory(config,check=True)
    need(read(config,root)[2]==record['initial_bound_bytes_sha256'],'CONFIG_CHANGED_DURING_PREPARATION')


def check(config,root,tools):
    independent()
    original,template=review_tool(tools);root=directory(root);config=config_location(config,root,tools)
    a=run_directory(config,check=True)
    c,_,_,_=read(config,root);backup,_,old_sha,_=read(a['backup'],root);record,_,_,_=read(a['record'],root)
    need(backup==template and record.get('schema')=='elsa-metadata-config-binding-record-v1'
         and record.get('not_authorization') is True and record.get('original_template_bytes_sha256')==old_sha
         and record.get('original_public_review_manifest_sha256')==ORIGINAL_MANIFEST_SHA256,'BINDING_RECORD_MISMATCH')
    require_keys=set(template)
    need(set(c)==require_keys and core_hash(c)==record.get('bound_core_sha256') and c['private_root']==str(root),'CONFIG_CHANGED_AFTER_BINDING')
    unresolved=tuple(template[k] for k in DECLARATIONS)
    independently_recorded=(original.REVIEW,original.ISOLATION,original.public_json('references/REVIEW_SCOPE.json')['required_scope'])
    need(tuple(c[k] for k in DECLARATIONS) in (unresolved,independently_recorded),'INCOMPLETE_SCOPE_DECLARATIONS')
    need(bind_descriptors(c['evidence'],root,tools,config)==c['evidence'],'EVIDENCE_HASH_MISMATCH')
    validate_bindings(c,root,original)


class Parser(argparse.ArgumentParser):
    def error(self,message):raise Stop('INVALID_COMMAND_LINE')


def main():
    try:
        p=Parser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
        mode.add_argument('--bind',action='store_true');mode.add_argument('--check',action='store_true')
        p.add_argument('--private-root',type=Path,required=True);p.add_argument('--config',type=Path,required=True)
        p.add_argument('--review-tools',type=Path,required=True)
        choices=p.add_mutually_exclusive_group();choices.add_argument('--discover-known-layout',action='store_true');choices.add_argument('--evidence-map',type=Path)
        args=p.parse_args();independent();sys.dont_write_bytecode=True
        root=directory(args.private_root);tools=absolute(args.review_tools);config=absolute(args.config)
        if args.check:
            need(not args.discover_known_layout and args.evidence_map is None,'INVALID_COMMAND_LINE')
            check(config,root,tools);print('PASS ISSUE=METADATA_CONFIGURATION_VERIFIED_NO_AUTHORIZATION')
        else:
            locations=explicit_map(args.evidence_map,root,config) if args.evidence_map else None
            bind(config,root,tools,locations,args.discover_known_layout)
            print('PASS ISSUE=METADATA_BOUND_SCOPE_UNCHANGED')
        return 0
    except SystemExit as exc:return exc.code
    except Stop as exc:
        print('STOP ISSUE='+str(exc));return 2
    except BaseException:
        print('STOP ISSUE=METADATA_BINDING_NOT_COMPLETED');return 2


if __name__=='__main__':raise SystemExit(main())
