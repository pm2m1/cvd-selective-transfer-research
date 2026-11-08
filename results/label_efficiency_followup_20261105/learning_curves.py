"""Fresh human-authorized development follow-up; no old execution is reused."""
from pathlib import Path
import json
import time
import traceback
import sys
from local_execution import cli,need,write_json,exclusive_output,sha
from package_runtime import verify_package,protocol_from,load_retained_export,ROOT

PURPOSE='retained_development_label_efficiency_followup_v1'


def execute(config,out):
    start=time.perf_counter()
    try:
        verify_package()
        need(config['schema']=='label-efficiency-local-v1' and config['mode']=='independent_local_only','FOLLOWUP_CONFIG_INVALID')
        protocol=protocol_from(config)
        data,history=load_retained_export(config)
        from experiment import run
        report=run(data,history,protocol,config['outer_folds'],out)
        write_json(out/'followup_execution.private.json',{'purpose':PURPOSE,'config':config,
            'package_manifest_sha256':sha(ROOT/'PUBLIC_PACKAGE_MANIFEST.json'),'seconds_total':time.perf_counter()-start,
            'scope':report['scope'],'external_validation':False,'test_access':False})
    except BaseException:
        traceback.print_exc()  # Original CLI already redirects Python/native output privately.
        raise


def invented_data():
    import numpy as np
    from package_runtime import api
    t=api();rng=np.random.default_rng(109);data={}
    for role,n,e in [('source_train',60,12),('source_validation',30,6),('target_pool',150,30)]:
        y=np.r_[np.ones(e),np.zeros(n-e)].astype(int);rng.shuffle(y)
        data[role+'__ids']=np.array([f'SYNTHETIC_FOLLOWUP_{role}_{i}' for i in range(n)])
        data[role+'__y']=y
        for v,dim in t.VIEWS.items():data[role+'__'+v]=(rng.normal(size=(n,dim))+.2*y[:,None]).astype('float32')
    return data


def demo(output):
    verify_package()
    p=json.loads((ROOT/'protocol_v1.json').read_text());p['repeat_seeds']=p['repeat_seeds'][:1]
    from experiment import run
    with exclusive_output(output,False) as out:
        run(invented_data(),{'synthetic_only':True},p,3,out,synthetic=True)


if __name__=='__main__':sys.exit(cli(PURPOSE,execute,demo))
