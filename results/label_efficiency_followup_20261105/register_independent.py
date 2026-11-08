"""Fresh independent-human registration; refuses absent/new-cohort evidence."""
import sys
import traceback
from local_execution import cli,need,Rejected
from package_runtime import verify_package
PURPOSE='genuine_new_cohort_registration_no_outcome_access_v1'
def execute(c,out):
    try:
        verify_package();need(c['schema']=='prospective-registration-local-v1','REGISTRATION_CONFIG_INVALID')
        from prospective import register
        register(c,out)
    except BaseException:
        traceback.print_exc()  # Original CLI redirects this only into its private log.
        raise
def demo(out):raise Rejected('USE_SYNTHETIC_TESTS_NO_REAL_COHORT_ASSUMED')
if __name__=='__main__':sys.exit(cli(PURPOSE,execute,demo))
