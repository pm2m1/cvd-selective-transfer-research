"""Public invented demo OR separate independent real-data operations."""
from pathlib import Path
import sys,argparse,json
ROOT=Path(__file__).resolve().parents[1]
for folder in (ROOT,ROOT/'src',ROOT/'vendor'):sys.path.insert(0,str(folder))
from local_execution import cli,require_local,load_json
from fasttrack.runtime import metadata_preflight,execute
from release import verify


class SafeParser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('INVALID_COMMAND_LINE')


def main():
    parser=SafeParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    for flag in ('synthetic-demo','preflight','authorize-local','execute-local'):group.add_argument('--'+flag,action='store_true')
    parser.add_argument('--config',type=Path);parser.add_argument('--authorization',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--device',choices=('cpu','mps'),default='cpu')
    try:
        args=parser.parse_args()
        verify()
        if args.synthetic_demo:
            if args.config or args.authorization or args.output is None:raise ValueError('SYNTHETIC_MODE_REJECTS_PRIVATE_CONFIG')
            from fasttrack.synthetic import demo
            config=load_json(ROOT/'configs/synthetic_demo.json');config['device']=args.device
            demo(args.output,config)
            print('SYNTHETIC_ONLY COMPLETE NO_REAL_COHORT_OR_CLINICAL_PERFORMANCE_CLAIM');return 0
        require_local()  # Precedes all private config/evidence access.
        if args.config is None:raise ValueError('NEW_PRIVATE_CONFIG_REQUIRED')
        c=load_json(args.config)
        metadata_preflight(c)
        if args.preflight:
            print('PASS ISSUE=METADATA_PREFLIGHT_ONLY_ARRAY_BYTES_NOT_VERIFIED');return 0
        purpose='hrs_elsa_fasttrack_'+('development' if c['phase']=='development' else 'locked_evaluation')+'_v1_20261106'
        # Existing runtime parses the original --authorize-local/--execute-local flags.
        sys.argv=[sys.argv[0],'--authorize-local' if args.authorize_local else '--execute-local','--config',str(args.config)]
        if args.authorization is not None:sys.argv+=['--authorization',str(args.authorization)]
        if args.output is not None:sys.argv+=['--output',str(args.output)]
        return cli(purpose,execute,lambda _:None)
    except SystemExit as exc:return exc.code
    except BaseException:
        print('STOP ISSUE=FASTTRACK_NOT_COMPLETED_NO_SCIENTIFIC_APPROVAL');return 2


if __name__=='__main__':raise SystemExit(main())
