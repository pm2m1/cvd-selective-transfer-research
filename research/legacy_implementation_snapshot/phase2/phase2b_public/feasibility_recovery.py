"""Aggregate-only redesign arithmetic; no data loader, fit, split or approval.

Private callers must keep the returned exact counts private. Unidentified
counterfactuals remain unidentified; bounds are never called recovered events.
"""
from __future__ import annotations

import math

VERSION = "phase2b-feasibility-recovery-v1"
NEGATIVE = "screening_or_observed_negative"
ANALYSIS = "screening_assumed_negative_sensitivity"


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError("AGGREGATE_COUNT_INVALID")
    return value


def intersection_bounds(universe, group, margin):
    universe, group, margin = map(count, (universe, group, margin))
    if max(group, margin) > universe: raise ValueError("MARGINAL_DENOMINATOR_INVALID")
    return [max(0, group+margin-universe), min(group, margin)]


def event_capacity(events, nonevents, adaptation, validation, *, test_events=200, test_nonevents=100,
                   development_nonevent_ratio=3):
    """Necessary reserves only; never creates a case-control or enriched test."""
    e, z, a, v, te, tz, ratio = map(count, (events, nonevents, adaptation, validation,
        test_events, test_nonevents, development_nonevent_ratio))
    return {"test_event_reserve": te, "test_nonevent_screen_only": tz,
        "adaptation_events": a, "validation_events": v, "development_nonevent_ratio_assumption": ratio,
        "passes_necessary_reserve_arithmetic": e >= te+a+v and z >= tz+ratio*(a+v),
        "precision_or_execution_authorized": False}


def random_test_allocation(events, nonevents, fraction, adaptation, validation, **requirements):
    """Hypergeometric natural-random-test reserve probability; no actual split.

    Simultaneously reserves development event/non-event capacities. It does not
    guarantee a later randomly drawn validation pool or a feasible fitted model.
    """
    from scipy.stats import hypergeom
    e, z = count(events), count(nonevents)
    if not isinstance(fraction, (float, int)) or isinstance(fraction, bool) or not 0 < fraction < 1:
        raise ValueError("TEST_FRACTION_INVALID")
    reserves = event_capacity(e, z, adaptation, validation, **requirements)
    total = e+z; test_n = math.floor(total*fraction)
    te, tz = reserves["test_event_reserve"], reserves["test_nonevent_screen_only"]
    de = reserves["adaptation_events"]+reserves["validation_events"]
    dz = de*reserves["development_nonevent_ratio_assumption"]
    lower = max(te, test_n-z+dz, test_n-z, 0)
    upper = min(e-de, test_n-tz, e, test_n)
    if total == 0 or lower > upper:
        probability = 0.0
    else:
        distribution = hypergeom(total, e, test_n)
        probability = float(max(distribution.cdf(upper)-distribution.cdf(lower-1),
            distribution.sf(lower-1)-distribution.sf(upper)))
    return {**reserves, "design": "NATURAL_PREVALENCE_SIMPLE_RANDOM_TARGET_TEST",
        "test_fraction_candidate": fraction, "test_size_candidate": test_n,
        "expected_test_events": test_n*e/total if total else 0,
        "simultaneous_test_and_remaining_development_reserve_probability": max(0., min(1., probability)),
        "event_count_support": [lower, upper] if lower <= upper else None,
        "actual_people_or_test_lock_created": False}


def summarize_cohort(c):
    keys = ("initial_unique_respondents", "baseline_required_table_join_completion", "baseline_survey_free_both",
        "timing_eligible_baseline_free", "eight_feature_complete_among_timing_eligible", "eight_feature_binary_eligible")
    stages = [count(c[k]) for k in keys]
    if any(a < b for a,b in zip(stages, stages[1:])): raise ValueError("WATERFALL_NOT_NESTED")
    initial, joined, free, timing, complete, binary = stages
    losses = [a-b for a,b in zip(stages, stages[1:])]
    if sum(losses)+binary != initial: raise ValueError("WATERFALL_ACCOUNTING_INVALID")
    positive, negative = count(c["eight_feature_reported_positive"]), count(c["eight_feature_"+NEGATIVE])
    if positive+negative != binary: raise ValueError("BINARY_ACCOUNTING_INVALID")
    states = c["outcome_states"]["composite"]
    full_positive, full_negative = count(states["reported_positive"]), count(states[NEGATIVE])
    if full_positive < positive or full_negative < negative or sum(map(count, states.values())) != timing:
        raise ValueError("PRECOMPLETE_OUTCOME_ACCOUNTING_INVALID")
    component = {}
    for name in ("heart_attack", "stroke"):
        b = c["eight_feature_component_binary"][name]
        if count(b["reported_positive"])+count(b[NEGATIVE]) != count(b["binary_eligible"]):
            raise ValueError("COMPONENT_ACCOUNTING_INVALID")
        component[name] = {"participants": b["binary_eligible"], "events": b["reported_positive"],
            "negatives": b[NEGATIVE], "has_both_classes": b["reported_positive"] > 0 and b[NEGATIVE] > 0,
            "baseline_scope": "COMMON_BOTH_DISEASE_FREE_BASELINE_NOT_COMPONENT_SPECIFIC_BASELINE"}
    feature_missing = {k: count(v) for k,v in c["feature_missing_among_timing_eligible"].items()}
    if sum(feature_missing.values()) < timing-complete or any(v > timing-complete for v in feature_missing.values()):
        raise ValueError("FEATURE_MARGIN_ACCOUNTING_INVALID")
    marginal_exclusions = {
        "baseline_nonself_within_linked_bounds": intersection_bounds(initial, joined, initial-count(c["baseline_eligible_self_core"])),
        "baseline_disease_and_unknown_margins_primary_universe": c["baseline_survey_status"],
        "timing_exclusions_among_baseline_free_exact": c["timing_excluded_by_reason_among_baseline_free"],
        "missing_predictor_margins_timing_eligible_not_additive": feature_missing,
        "outcome_states_all_timing_eligible_exact": states,
        "nonbinary_outcome_contributions_within_complete_bounds": {
            k: [max(0, count(v)-(timing-complete)), min(count(v), complete-binary)]
            for k,v in states.items() if k not in {"reported_positive", NEGATIVE}},
        "followup_margins_timing_eligible_not_additive_across_waves": c["followup"],
        "route_reasons_all_primary_rows_not_analytic_cohort": c.get("candidate_route_reasons_all_primary_rows"),
        "branch_reasons_all_primary_rows_overlap": c.get("candidate_branch_reasons_all_primary_rows"),
        "chain_leaf_specific_exclusion_counts": "NOT_RECORDED_CANNOT_SEPARATE_FIRST_INTERVIEW_FROM_OTHER_DIAGNOSIS_FAILURES",
        "joint_baseline_and_followup_causal_attribution": "NOT_IDENTIFIABLE_FROM_RECORDED_MARGINS"}
    return {"waterfall": [{"stage":k,"retained":v} for k,v in zip(keys, stages)],
        "sequential_losses": dict(zip(("required_linkage", "combined_baseline_history_and_self_route",
            "timing", "incomplete_predictors", "nonbinary_outcome_among_complete"), losses)),
        "final_counts": {"participants":binary,"events":positive,"negatives":negative},
        "event_fraction": positive/binary if binary else None,
        "mi_only_change_on_same_baseline": {"additional_events":component["heart_attack"]["events"]-positive,
            "additional_negatives":component["heart_attack"]["negatives"]-negative,
            "additional_participants":component["heart_attack"]["participants"]-binary,
            "interpretation":"CHANGED_COMPONENT_ENDPOINT_NOT_A_RECOVERED_COMPOSITE"},
        "components": component, "exclusion_evidence": marginal_exclusions,
        "imputation_only_oracle_envelope": {"participants_with_known_binary_outcomes":full_positive+full_negative,
            "events":full_positive,"negatives":full_negative,
            "known_positive_reports_excluded_only_by_predictor_completeness":full_positive-positive,
            "known_negatives_excluded_only_by_predictor_completeness":full_negative-negative,
            "not_empirical_imputation_result":True,
            "can_reach_default_test_event_aim_before_development_reserves":full_positive>=200},
        "timing_relaxation_partial_identification": {
            "excluded_people":free-timing,
            "optimistic_positive_upper_bound_if_all_timing_excluded_were_events":full_positive+free-timing,
            "event_gain":None,"feature_compatibility":None,"scientific_validity":None,
            "interpretation":"COMBINATORIAL_UPPER_BOUND_NOT_RECOVERED_OR_PLAUSIBLE_EVENTS"}}


def compare(aggregate):
    if set(aggregate.get("analyses", {})) != {ANALYSIS}: raise ValueError("SENSITIVITY_SCOPE_REQUIRED")
    cohorts = aggregate["analyses"][ANALYSIS]["cohorts"]
    if set(cohorts) != {"HRS", "ELSA"}: raise ValueError("BOTH_COHORTS_REQUIRED")
    output = {"identity": VERSION, "scope":"EXISTING_AGGREGATES_ONLY_NO_RESPONDENT_PROCESSING",
        "cohorts": {k:summarize_cohort(v) for k,v in cohorts.items()}, "all_real_modeling_designs":"NO_GO",
        "clinical_incidence_claim":False,"actual_test_split_created":False}
    target = output["cohorts"]["ELSA"]
    output["candidate_random_test_reserve_plans"] = [random_test_allocation(target["final_counts"]["events"],
        target["final_counts"]["negatives"],fraction,budget,validation=50)
        for fraction in (.3,.5) for budget in (10,25,50)]
    output["zero_shot_all_target_evaluation"] = {"target_development_labels":0,
        "event_count":target["final_counts"]["events"],
        "can_cover_existing_event_design_aim":target["final_counts"]["events"]>=200,
        "interpretation":"SOURCE_ONLY_TRANSPORT_EVALUATION_NOT_SPARSE_LABEL_ADAPTATION", "real_modeling":"NO_GO"}
    output["strategies"] = {
        "original_strict": {"status":"NO_GO_MISSING_DIRECT_HRS_MI_NEGATIVE_ROUTE","empirical_counts":None},
        "source_specific_current": {"status":"NO_GO_PENDING_ENDPOINT_PRECISION_AND_AUTHORIZATION",
            "empirical_scope":"EXACT_CURRENT_SENSITIVITY_COUNTS_ONLY"},
        "mi_only": {"status":"NO_GO_UNTIL_COMPONENT_PRECISION_AND_DESIGN_RESOLVED","empirical_scope":"COMMON_BASELINE_COMPONENT_COUNTS_ONLY"},
        "stroke_only": {"status":"NO_GO" if not target["components"]["stroke"]["has_both_classes"] else "NO_GO_PENDING_PRECISION",
            "empirical_scope":"COMMON_BASELINE_COMPONENT_COUNTS_ONLY"},
        "longer_followup": {"status":"NO_GO_NEW_SOURCE_WINDOW_AND_CENSORING_EVIDENCE_NEEDED","empirical_counts":None},
        "expanded_baseline_and_landmark": {"status":"NO_GO_COMPONENT_HISTORY_AND_LANDMARK_EVIDENCE_NEEDED","empirical_counts":None},
        "missing_predictor_handling": {"status":"NO_GO_UNTIL_MEASUREMENT_MISSINGNESS_AND_TRAIN_ONLY_IMPUTATION_VALIDATED",
            "empirical_scope":"EXACT_KNOWN_OUTCOME_CEILING_NOT_IMPUTED_PERFORMANCE"},
        "heterogeneous_composite": {"status":"NO_GO_FOR_VALIDATED_CROSS_COHORT_RISK_CLAIMS",
            "additional_target_events_created_by_pooling":0},
        "hrs_only": {"status":"NO_GO_REAL_TRAINING_PENDING_SOURCE_DESIGN_AND_AUTHORIZATION",
            "interpretation":"POSSIBLE_EXPLORATORY_SOURCE_REPORT_MODEL_NOT_VALIDATED_HRS_TO_ELSA_TRANSFER"}}
    return output
