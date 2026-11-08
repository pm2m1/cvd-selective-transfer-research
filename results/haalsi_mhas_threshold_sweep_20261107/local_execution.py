"""Independent-local boundary and exclusive private outputs. No data at import."""
from pathlib import Path
import argparse,contextlib,hashlib,json,os,sys,datetime
ROOT=Path(__file__).resolve().parent
class Rejected(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
def need(test,code):
    if not test:raise Rejected(code)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def load_json(path):
    with Path(path).open() as f:return json.load(f)
def write_json(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')
def code_hashes():return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(ROOT.rglob('*.py')) if 'tests' not in p.parts and '__pycache__' not in p.parts}
def require_local():
    keys=('CODEX_HOME','CODEX_SESSION_ID','CODEX_THREAD_ID','CODEX_CI','CI','GITHUB_ACTIONS','CHATGPT_SESSION_ID')
    need(not any(os.environ.get(k) for k in keys) and sys.stdin.isatty(),'INDEPENDENT_LOCAL_OPERATOR_REQUIRED')
def descriptor(d):
    need(isinstance(d,dict) and isinstance(d.get('path'),str) and len(d.get('sha256',''))==64,'MISSING_REVIEWED_FILE_BINDING')
    raw=Path(d['path']).expanduser();need(not raw.is_symlink(),'FILE_BINDING_MISMATCH');p=raw.resolve();need(p.is_file() and sha(p)==d['sha256'],'FILE_BINDING_MISMATCH');return p
@contextlib.contextmanager
def exclusive_output(path,private=True):
    p=Path(path).expanduser().resolve()
    need(not p.exists(),'OUTPUT_ALREADY_EXISTS_NO_RETRY')
    if private:
        need(not p.is_relative_to(ROOT),'PRIVATE_OUTPUT_MUST_BE_OUTSIDE_TOOL_WORKSPACE')
        need(p.parent.is_dir() and p.parent.stat().st_mode&0o077==0,'PRIVATE_PARENT_PERMISSIONS_REQUIRED')
    p.mkdir(mode=0o700,parents=not private,exist_ok=False);os.chmod(p,0o700)
    previous_umask=os.umask(0o077)
    write_json(p/'operation_started.private.json',{'status':'STARTED_CONSUMED','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
    try:yield p
    except BaseException as exc:
        code=exc.code if isinstance(exc,Rejected) else 'UNEXPECTED_IMPLEMENTATION_EXCEPTION'
        write_json(p/'completion.private.json',{'status':'INTERRUPTED_NO_RETRY' if isinstance(exc,KeyboardInterrupt) else 'FAILED_NO_RETRY','issue':code,'attempt_consumed':True})
        raise
    else:write_json(p/'completion.private.json',{'status':'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED','attempt_consumed':True})
    finally:os.umask(previous_umask)
def cli(purpose,execute,demo):
    p=argparse.ArgumentParser(description=purpose);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--authorize-local',action='store_true');g.add_argument('--execute-local',action='store_true');g.add_argument('--synthetic-demo',action='store_true')
    p.add_argument('--config',type=Path);p.add_argument('--authorization',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:
        if a.synthetic_demo:
            need(a.output is not None and a.config is None and a.authorization is None,'SYNTHETIC_MODE_REJECTS_EXTERNAL_CONFIG')
            demo(a.output);print('SYNTHETIC_ONLY COMPLETED');return 0
        require_local() # Must precede any reading of local private config or artifacts.
        need(a.config is not None and a.authorization is not None and a.output is not None,'CONFIG_AUTHORIZATION_AND_NEW_OUTPUT_REQUIRED')
        if a.authorize_local:
            need(not a.authorization.exists() and not a.output.exists(),'AUTHORIZATION_OR_OUTPUT_ALREADY_EXISTS')
            config=load_json(a.config)
            def checked_fields(value):
                if isinstance(value,dict):
                    if 'path' in value:need(isinstance(value['path'],str) and bool(value['path']) and isinstance(value.get('sha256'),str) and len(value['sha256'])==64,'CONFIG_FILE_BINDING_INCOMPLETE')
                    for key,entry in value.items():
                        if key in ('isolated_public_project','data_root','master_file','questionnaire'):need(isinstance(entry,str) and bool(entry),'CONFIG_LOCATION_INCOMPLETE')
                        checked_fields(entry)
                elif isinstance(value,list):
                    for entry in value:checked_fields(entry)
            checked_fields(config)
            need(config.get('mode')=='independent_local_only','CONFIG_MODE_INVALID')
            name=input('Independent authorized operator name (stored privately): ').strip()
            phrase=input('Type AUTHORIZE LOCAL SUPPLEMENTARY OPERATION after confirming provider and institutional scope, isolated environment and private outputs: ')
            need(name and phrase=='AUTHORIZE LOCAL SUPPLEMENTARY OPERATION','AUTHORIZATION_NOT_CONFIRMED')
            write_json(a.authorization,{'purpose':purpose,'output_binding':str(a.output.expanduser().resolve()),'operator':name,'authorized':True,'scope_confirmed_by_operator':True,'config_sha256':sha(a.config),'code_bindings':code_hashes(),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
            print('LOCAL_AUTHORIZATION_RECORDED_NO_DATA_PROCESSING');return 0
        auth=load_json(a.authorization)
        need(auth.get('output_binding')==str(a.output.expanduser().resolve()) and auth.get('purpose')==purpose and auth.get('authorized') is True and auth.get('scope_confirmed_by_operator') is True and bool(auth.get('operator')) and auth.get('config_sha256')==sha(a.config) and auth.get('code_bindings')==code_hashes(),'AUTHORIZATION_BINDING_MISMATCH')
        need(a.output is not None,'NEW_PRIVATE_OUTPUT_REQUIRED')
        with exclusive_output(a.output) as out:
            # Redirect Python and native-library output into a private log.
            fd=os.open(out/'runtime.private.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            saved=[os.dup(1),os.dup(2)]
            try:
                os.dup2(fd,1);os.dup2(fd,2)
                with os.fdopen(os.dup(fd),'w') as stream,contextlib.redirect_stdout(stream),contextlib.redirect_stderr(stream):execute(load_json(a.config),out)
            finally:
                os.dup2(saved[0],1);os.dup2(saved[1],2)
                for handle in saved+[fd]:os.close(handle)
        print('REVIEW ISSUE=PRIVATE_OUTPUT_REQUIRES_DISCLOSURE_REVIEW');return 0
    except BaseException:
        # No arbitrary exception messages/tracebacks, paths, identifiers or counts.
        print('REVIEW ISSUE=LOCAL_OPERATION_NOT_COMPLETED_INSPECT_PRIVATE_RECEIPT');return 2
