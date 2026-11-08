"""NEW private development export using the existing verified development-only loader.
Independent operation only. Never invokes a final evaluator or HRS/ELSA audit.
"""
from pathlib import Path
import sys,os,contextlib,json,io
import numpy as np
from local_execution import need,descriptor,write_json,sha,cli
PURPOSE='new_private_development_export_no_target_test_v1'
def execute(c,out):
    # Researcher supplies an authorized isolated copy of public project code/records.
    project=Path(c['isolated_public_project']).expanduser().resolve()
    need(project.is_dir() and c['no_test_rows'] is True,'ISOLATED_DEVELOPMENT_PROJECT_REQUIRED')
    pinned=c['public_source_bindings'];need(isinstance(pinned,dict) and pinned,'PUBLIC_CODE_BINDINGS_REQUIRED')
    for rel,h in pinned.items():
        p=(project/rel).resolve();need(p.is_relative_to(project) and p.is_file() and sha(p)==h,'PUBLIC_PREPARATION_CODE_MISMATCH')
    sys.path.insert(0,str(project/'src'));old=Path.cwd();os.chdir(project)
    # Import only in the independent real operation, never at import/test collection.
    from dmv_mat_cvd.real_baselines import load_verified_development,_part,ASSIGNMENTS_SHA256
    from dmv_mat_cvd.data.public_preprocessing import PublicPreprocessor
    from dmv_mat_cvd.safeguards import SplitRole
    try:
        # No library diagnostic may leak a protected path/value to the terminal.
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            source,target,assignments,*_=load_verified_development(Path(c['data_root']),Path(c['master_file']),Path(c['questionnaire']))
            st=_part(source,set(assignments['source_partitions']['source_train']),SplitRole.SOURCE_TRAIN)
            pp=PublicPreprocessor().fit(st,SplitRole.SOURCE_TRAIN)
            payload={};roles={'source_train':st,'source_validation':_part(source,set(assignments['source_partitions']['source_validation']),SplitRole.SOURCE_VALIDATION),'target_pool':_part(target,set(assignments['target_partitions']['target_adaptation_pool']),SplitRole.TARGET_ADAPTATION),'target_validation':_part(target,set(assignments['target_partitions']['target_validation']),SplitRole.TARGET_VALIDATION)}
            enums={'source_train':SplitRole.SOURCE_TRAIN,'source_validation':SplitRole.SOURCE_VALIDATION,'target_pool':SplitRole.TARGET_ADAPTATION,'target_validation':SplitRole.TARGET_VALIDATION}
            for role,frame in roles.items():
                frame=frame.reset_index(drop=True);ds=pp.transform(frame,enums[role]);payload[role+'__ids']=frame.participant_id.to_numpy(dtype=str);payload[role+'__y']=ds.labels.numpy().astype(int)
                for v,x in ds.views.items():payload[role+'__'+v]=x.numpy()
            position={p:i for i,p in enumerate(payload['target_pool__ids'].tolist())}
            for i in range(10):payload[f'draw_{i}']=np.asarray([position[p] for p in assignments['adaptation_draws'][str(i)]['primary_25_75']],dtype=np.int64)
            pp.save(out/'source_preprocessing.private.json')
            from train_exploratory_candidates import validate_bundle
            m={'preprocessing_fit_role':'source_train','protocol':'public-haalsi-mhas-v2','test_rows_included':False,'source_assignments_sha256':ASSIGNMENTS_SHA256}
            validate_bundle(payload,m)
            with (out/'development_bundle.private.npz').open('xb') as f:np.savez_compressed(f,**payload)
            m.update(bundle_sha256=sha(out/'development_bundle.private.npz'),preprocessor_sha256=sha(out/'source_preprocessing.private.json'),preparation_script_sha256=sha(__file__),public_source_bindings=pinned)
            write_json(out/'development_manifest.private.json',m)
    finally:os.chdir(old)
def demo(out):
    from local_execution import Rejected
    raise Rejected('NO_PRIVATE_DEVELOPMENT_EXPORT_DEMO_USE_INVENTED_TRAINING_FIXTURE')
if __name__=='__main__':sys.exit(cli(PURPOSE,execute,demo))
