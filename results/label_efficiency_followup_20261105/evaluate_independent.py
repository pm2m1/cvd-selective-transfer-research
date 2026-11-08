"""Separately authorized one-shot future evaluation; no model/threshold updates."""
import sys
import traceback
from local_execution import cli,need,Rejected
from package_runtime import verify_package
PURPOSE='genuine_new_cohort_one_shot_evaluation_v1'
def execute(c,out):
    try:
        verify_package();need(c['schema']=='prospective-evaluation-local-v1','EVALUATION_CONFIG_INVALID')
        from prospective import evaluate
        evaluate(c,out)
    except BaseException:
        traceback.print_exc()  # Preserved privately; no raw context in public status.
        raise
def demo(out):raise Rejected('USE_SYNTHETIC_TESTS_NO_REAL_COHORT_ASSUMED')
if __name__=='__main__':sys.exit(cli(PURPOSE,execute,demo))
