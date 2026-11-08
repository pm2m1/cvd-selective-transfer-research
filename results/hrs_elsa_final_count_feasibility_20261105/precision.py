"""Assumption-based planning arithmetic; never model performance or a GO gate."""
import math

def wilson(successes,total,z=1.959963984540054):
    if total<=0:return None
    p=successes/total;denom=1+z*z/total
    center=(p+z*z/(2*total))/denom
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/denom
    return [max(0,center-half),min(1,center+half)]

def required_cases(sensitivity=.8,half_width=.1):
    # Conventional planning approximation, not an exact small-sample guarantee.
    if not 0<sensitivity<1 or not 0<half_width<1:raise ValueError('PLANNING_ASSUMPTIONS_INVALID')
    return math.ceil(1.959963984540054**2*sensitivity*(1-sensitivity)/half_width**2)

def auc_se(events,nonevents,assumed_auc=.70):
    if events<=0 or nonevents<=0:return None
    a=assumed_auc;q1=a/(2-a);q2=2*a*a/(1+a)
    var=(a*(1-a)+(events-1)*(q1-a*a)+(nonevents-1)*(q2-a*a))/(events*nonevents)
    return math.sqrt(max(0,var))

def both_classes_probability(events,nonevents,test_n):
    total=events+nonevents
    if not 1<=test_n<=total:return None
    denom=math.comb(total,test_n)
    same=lambda n:math.comb(n,test_n) if n>=test_n else 0
    return 1-(same(events)+same(nonevents))/denom

def summarize(aggregates):
    result={'scope':'PLANNING_ASSUMPTIONS_NOT_OBSERVED_MODEL_METRICS',
            'sensitivity_assumption':.80,'sensitivity_desired_95_half_width':.10,
            'approx_test_case_requirement':required_cases(),
            'specificity_assumption':.90,'specificity_desired_95_half_width':.05,
            'approx_test_nonevent_requirement':required_cases(.90,.05),
            'assumed_auc':.70,'AP_precision':'NOT_IDENTIFIABLE_FROM_COUNTS_ALONE',
            'paired_AP_difference_precision':'REQUIRES_JOINT_SCORE_ASSUMPTIONS_OR_INDEPENDENT_SCORES',
            'calibration_slope_precision':'REQUIRES_SCORE_DISTRIBUTION_AND_MISCALIBRATION_ASSUMPTIONS',
            'source_training_sufficiency':'HRS_NOT_PROCESSED_BY_THIS_ELSA_COUNTER','designs':{}}
    for name,design in aggregates['designs'].items():
        out=design['outcomes']['wave_window'];s=out['summary'];e=s['unique_composite_incident_reports'];n=s['observed_composite_nonevents']
        actualtest=out['potential_untouched_evaluation'];te=actualtest.get('INCIDENT_REPORT',0);tn=actualtest.get('OBSERVED_NONEVENT',0)
        available=out['partition_status']!='NOT_COMPUTED_FEATURE_EVIDENCE_UNAVAILABLE'
        reserves={}
        for role,counts in out['partition_scenarios'].items():
            a=counts.get('INCIDENT_REPORT',0);b=counts.get('OBSERVED_NONEVENT',0)
            reserves[role]={'events':a if available else None,'nonevents':b if available else None,
               'both_classes':a>0 and b>0 if available else None,
               'bootstrap_probability_no_events':(b/(a+b))**(a+b) if available and a+b else None,
               'stable_stopping_calibration_guaranteed':False}
        result['designs'][name]={'report_fraction_among_ascertained':e/(e+n) if e+n else None,
          'report_fraction_wilson_95':wilson(e,e+n),
          'hypothetical_all_ascertained_auc_se_at_point70':auc_se(e,n),
          'potential_untouched_test_case_support':te if available else None,'potential_untouched_test_nonevent_support':tn if available else None,
          'partition_status':out['partition_status'],
          'disjoint_role_support_scenarios':reserves,
          'adaptation_positive_budget_ceiling_checks':{str(k):reserves['adaptation']['events']>=k if available else None for k in [10,25,50]},
          'test_auc_se_at_ASSUMED_point70':auc_se(te,tn) if available else None,
          'sensitivity_half_width_APPROX_at_ASSUMED_point80':1.959963984540054*math.sqrt(.8*.2/te) if available and te else None,
          'random20percent_test_both_class_probability':both_classes_probability(e,n,max(1,math.floor(.2*(e+n)))) if e+n else None,
          'status':'NOT_SCIENTIFIC_ACCEPTANCE_OR_TRAINING_AUTHORIZATION'}
    return result
