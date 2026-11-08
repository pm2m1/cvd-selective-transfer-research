"""New independent local authorization purpose; no old operation is reused."""
import sys
import json
import time
from pathlib import Path
from local_execution import cli,need,write_json,exclusive_output,sha,require_local,load_json
from package_integrity import ROOT,verify_package,reviewed_protocol,runtime
PURPOSE='paired_epoch_zero_development_experiment_v1'


def execute(config,out):
    # Also guard direct invocation; prevents calling execute from an AI notebook.
    require_local();verify_package();protocol=reviewed_protocol(config)
    from retained_runtime import load_retained_export
    start=time.perf_counter()
    from experiment import run,condition_plan
    progress=condition_plan(protocol)
    try:
        data,history=load_retained_export(config)
        report=run(data,history,protocol,out,'RETROSPECTIVE_DEVELOPMENT_NOT_EXTERNAL_VALIDATION',progress)
    except BaseException as exc:
        from local_execution import Rejected
        write_json(out/'experiment_failure.private.json',{
            'status':'INTERRUPTED_NO_RETRY' if isinstance(exc,KeyboardInterrupt) else 'FAILED_NO_RETRY',
            'issue':exc.code if isinstance(exc,Rejected) else 'UNEXPECTED_IMPLEMENTATION_EXCEPTION',
            'conditions':progress,'pending_conditions_not_retried':True})
        raise
    need(sha(ROOT/'EXPERIMENT_CONFIG.json')==config['protocol']['sha256'],'PROTOCOL_CHANGED_DURING_OPERATION')
    verify_package()
    write_json(out/'execution_bindings.private.json',{'purpose':PURPOSE,'config':config,
        'package_manifest_sha256':sha(ROOT/'PUBLIC_PACKAGE_MANIFEST.json'),'runtime_versions':runtime(),
        'protocol_sha256':sha(ROOT/'EXPERIMENT_CONFIG.json'),'seconds_total':time.perf_counter()-start,
        'result_sha256':sha(out/'epoch_zero_comparison.private.json'),
        'prior_outputs_modified':False,'frozen_test_access':False,'scope':report['scope']})


def invented_data():
    import numpy as np
    from retained_runtime import api
    t=api();rng=np.random.default_rng(907);data={}
    for role,n in [('source_train',96),('source_validation',48),('target_pool',90)]:
        y=(rng.random(n)<.2).astype(int)
        data[role+'__ids']=np.array([f'INVENTED_EPOCH_ZERO_{role}_{i:03}' for i in range(n)])
        data[role+'__y']=y
        for v,d in t.VIEWS.items():data[role+'__'+v]=(rng.normal(size=(n,d))+.5*y[:,None]).astype('float32')
    return data


def demo(output):
    verify_package()
    protocol=json.loads((ROOT/'EXPERIMENT_CONFIG.json').read_text())
    # Explicit synthetic-only runtime reduction; no real config or external data accepted.
    protocol.update(source_epochs=2,target_epochs=3,bootstrap_repetitions=20)
    from experiment import run
    with exclusive_output(output,False) as out:
        run(invented_data(),{'synthetic_only':True},protocol,out,'INVENTED_SYNTHETIC_ONLY_NOT_CLINICAL_RESULTS')


def main():
    if sys.argv[1:]==['--runtime-info']:
        print(json.dumps(runtime(),sort_keys=True));return 0
    # Public/config/runtime readiness before authorization, with guard FIRST.
    # Actual permission confirmation and authorization remain the original CLI.
    if '--authorize-local' in sys.argv or '--execute-local' in sys.argv:
        try:
            require_local()
            import argparse
            parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--config',type=Path)
            args,_=parser.parse_known_args()
            need(args.config is not None,'CONFIG_REQUIRED')
            need(not args.config.expanduser().resolve().is_relative_to(ROOT),'PRIVATE_CONFIG_MUST_BE_OUTSIDE_PUBLIC_PACKAGE')
            verify_package();reviewed_protocol(load_json(args.config))
        except BaseException:
            print('STOP ISSUE=EPOCH_ZERO_LOCAL_READINESS_NOT_ESTABLISHED');return 2
    # Original CLI enforces require_local before reading private authorization.
    return cli(PURPOSE,execute,demo)


if __name__=='__main__':sys.exit(main())
