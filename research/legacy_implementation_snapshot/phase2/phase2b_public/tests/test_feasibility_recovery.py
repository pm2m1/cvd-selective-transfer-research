from copy import deepcopy
import itertools
import math

import pytest
from phase2.phase2b_public import feasibility_recovery as f


def invented_cohort():
    c=dict(initial_unique_respondents=20,baseline_required_table_join_completion=18,
        baseline_survey_free_both=12,timing_eligible_baseline_free=10,
        eight_feature_complete_among_timing_eligible=8,eight_feature_binary_eligible=6,
        eight_feature_reported_positive=2,eight_feature_screening_or_observed_negative=4,
        baseline_eligible_self_core=15,
        baseline_survey_status={"interview":{"self":15,"unknown":5},"heart_attack":{"negative":12,"positive":4,"unknown":4},"stroke":{"negative":12,"positive":4,"unknown":4}},
        timing_excluded_by_reason_among_baseline_free={"same_month_order_unknown":2},
        feature_missing_among_timing_eligible={"age":1,"sex":0,"sbp":0,"dbp":0,"bmi":1,"smoking_status":0,"diabetes":0,"antihypertensive_treatment":0},
        followup={str(w):{"interview":{"self":10},"death":{"alive":10},"heart_attack_report":{"negative":7,"positive":3},"stroke_report":{"negative":10}} for w in (7,8,9)})
    c["outcome_states"]={"composite":{"reported_positive":3,f.NEGATIVE:5,"unknown":2}}
    c["eight_feature_component_binary"]={"heart_attack":{"reported_positive":2,f.NEGATIVE:4,"binary_eligible":6},"stroke":{"reported_positive":0,f.NEGATIVE:7,"binary_eligible":7}}
    return c


def test_exact_sequential_losses_no_double_counting_or_invented_intersections():
    c=invented_cohort();r=f.summarize_cohort(c)
    assert list(r["sequential_losses"].values())==[2,6,2,2,2]
    assert sum(r["sequential_losses"].values())+r["final_counts"]["participants"]==20
    assert r["exclusion_evidence"]["baseline_nonself_within_linked_bounds"]==[3,5]
    assert r["imputation_only_oracle_envelope"]["known_positive_reports_excluded_only_by_predictor_completeness"]==1
    assert r["imputation_only_oracle_envelope"]["events"]==3
    assert r["timing_relaxation_partial_identification"]["event_gain"] is None
    assert r["timing_relaxation_partial_identification"]["optimistic_positive_upper_bound_if_all_timing_excluded_were_events"]==5


@pytest.mark.parametrize("values,answer", [((10,4,6),[0,4]),((10,8,6),[4,6]),((0,0,0),[0,0])])
def test_frechet_bounds(values,answer):assert f.intersection_bounds(*values)==answer


@pytest.mark.parametrize("bad", [-1,True,1.5,"1",None])
def test_invalid_counts_reject(bad):
    with pytest.raises(ValueError):f.count(bad)


@pytest.mark.parametrize("mutation", [lambda c:c.update(eight_feature_reported_positive=8),
    lambda c:c.update(timing_eligible_baseline_free=15),lambda c:c["feature_missing_among_timing_eligible"].update(age=5),
    lambda c:c["eight_feature_component_binary"]["stroke"].update(binary_eligible=5)])
def test_invalid_aggregate_arithmetic_rejects(mutation):
    c=invented_cohort();mutation(c)
    with pytest.raises(ValueError):f.summarize_cohort(c)


def test_no_strategy_invents_counterfactuals_or_closes_formal_gate():
    r=f.compare({"analyses":{f.ANALYSIS:{"cohorts":{"HRS":invented_cohort(),"ELSA":invented_cohort()}}}})
    assert r["all_real_modeling_designs"]=="NO_GO"
    assert r["strategies"]["stroke_only"]["status"]=="NO_GO"
    assert r["strategies"]["longer_followup"]["empirical_counts"] is None
    assert r["strategies"]["expanded_baseline_and_landmark"]["empirical_counts"] is None
    assert not r["actual_test_split_created"]
    assert all(p["simultaneous_test_and_remaining_development_reserve_probability"]==0 for p in r["candidate_random_test_reserve_plans"])


@pytest.mark.parametrize("e,z,fraction", [(3,7,.5),(8,4,.25),(0,10,.3),(10,0,.5)])
def test_random_allocation_matches_exact_enumeration(e,z,fraction):
    nt=math.floor((e+z)*fraction)
    expected=0;total=math.comb(e+z,nt)
    for sample in itertools.combinations(range(e+z),nt):
        x=sum(i<e for i in sample)
        if x>=1 and nt-x>=1 and e-x>=2 and z-(nt-x)>=2:expected+=1
    r=f.random_test_allocation(e,z,fraction,1,1,test_events=1,test_nonevents=1,development_nonevent_ratio=1)
    assert r["simultaneous_test_and_remaining_development_reserve_probability"]==pytest.approx(expected/total)


def test_imputation_cannot_create_disease_observations():
    c=invented_cohort();r=f.summarize_cohort(c)
    assert r["imputation_only_oracle_envelope"]["participants_with_known_binary_outcomes"]==8
    assert r["imputation_only_oracle_envelope"]["participants_with_known_binary_outcomes"]<c["timing_eligible_baseline_free"]


def test_capacity_is_not_evaluation_permission():
    r=f.event_capacity(500,5000,50,50)
    assert r["passes_necessary_reserve_arithmetic"] and not r["precision_or_execution_authorized"]
