"""Transparent hypothetical precision arithmetic; never actual model performance."""
from math import ceil,sqrt,log,exp
import json
from pathlib import Path


def sensitivity_events(sensitivity=.8,half_width=.05,z=1.96):
    return ceil(z*z*sensitivity*(1-sensitivity)/half_width**2)


def independent_test_size(prevalence,test_events=200,adapt_events=50,stop_events=50,calibration_events=50):
    """Expected allocations only; not probability guarantees or positive enrichment."""
    return {'test_n_expected':ceil(test_events/prevalence),
            'target_total_n_expected':ceil((test_events+adapt_events+stop_events+calibration_events)/prevalence),
            'required_target_events_sum':test_events+adapt_events+stop_events+calibration_events}


def shrinkage_criterion(parameters,r2_cs,shrinkage=.9):
    # Riley shrinkage criterion only, not all development-sample requirements.
    if not 0<r2_cs<shrinkage<1:raise ValueError('INVALID_PLANNING_ASSUMPTION')
    return ceil(parameters/((shrinkage-1)*log(1-r2_cs/shrinkage)))


def scenarios():
    return {'scope':'HYPOTHETICAL_ASSUMPTIONS_NOT_REAL_COHORT_OR_MODEL_RESULTS',
        'sensitivity_precision':[{'events':e,'assumed_sensitivity':.8,'normal_approx_half_width':1.96*sqrt(.8*.2/e)} for e in [21,49,100,200,400]],
        'event_requirement_sensitivity_080_halfwidth_005':sensitivity_events(),
        'event_requirement_worstcase_halfwidth_005':sensitivity_events(.5),
        'expected_target_allocations':[{'assumed_prevalence':p,**independent_test_size(p)} for p in [.02,.05,.10]],
        'model_development_shrinkage_only':[{'candidate_parameters':p,'assumed_Cox_Snell_R2':r,
                'required_n_shrinkage_only':shrinkage_criterion(p,r)} for p in [8,16] for r in [.05,.10,.15]],
        'limitations':['not AP/AUROC/calibration-slope precision','not a neural-network sample-size certificate',
                      'expected event allocations do not ensure realized counts','no real event prevalence assumed known']}


if __name__=='__main__':
    with (Path(__file__).parent/'PLANNING_SCENARIOS.json').open('x') as f:json.dump(scenarios(),f,indent=2)
