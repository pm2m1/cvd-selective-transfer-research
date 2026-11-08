"""Final private evidence interpretation, not a reviewer/comparison replay.

Reads two existing assessments plus authorization/start/result/config metadata.
No raw aggregate, respondent reader, simulation, model fit, or cohort engine.
Only the new private decision is written; console says nothing about A/B/C/D.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import warnings

sys.dont_write_bytecode = True
VERSION = "phase2b_scientific_adjudication_v1"
FRAMEWORK = "SCIENTIFIC_ADJUDICATION_FRAMEWORK_V1.json"
LOCK = VERSION + ".source_lock.json"
DEST = VERSION + ".private.json"
ACK = "REVIEW ISSUE=PRIVATE_SCIENTIFIC_DECISION_WRITTEN_DISCLOSURE_REVIEW_REQUIRED"
NOT_COMPLETED = "REVIEW ISSUE=LOCAL_ADJUDICATION_NOT_COMPLETED_PRESERVE_ARTIFACTS"
REDESIGN_LOCK = 'WITHHELD_REFERENCE_BINDING'
STAGES = ("initial_unique_respondents", "baseline_required_table_join_completion", "baseline_survey_free_both",
    "timing_eligible_baseline_free", "eight_feature_complete_among_timing_eligible", "eight_feature_binary_eligible")
NEGATIVE = "screening_or_observed_negative"


class EvidenceError(ValueError):
    pass


def require(condition):
    if not condition:
        raise EvidenceError("EVIDENCE_INSUFFICIENT")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count(x):
    require(type(x) is int and x >= 0)
    return x


def both_classes_probability(events, nonevents, test_size):
    """SRS without replacement, conditional on recorded cohort class counts."""
    e, z, n = map(count, (events, nonevents, test_size))
    total = e+z
    require(n <= total)
    if not e or not z or n < 2:
        return 0.0
    if n == total:
        return 1.0
    log_total = math.lgamma(total+1)-math.lgamma(n+1)-math.lgamma(total-n+1)
    def pure(group):
        if n > group:
            return 0.0
        return math.exp(min(0., math.lgamma(group+1)-math.lgamma(n+1)-math.lgamma(group-n+1)-log_total))
    return max(0., min(1., 1-pure(e)-pure(z)))


def bootstrap_both_classes(events, nonevents):
    e, z = count(events), count(nonevents)
    total = e+z
    return max(0., min(1., 1-(e/total)**total-(z/total)**total)) if e and z else 0.0


def verified_pair(prior, comparison):
    """Cross-bind recorded observed evidence; do not rerun old calculations."""
    require(prior.get("identity") == "stage_c_postrun_feasibility_review_v1" and
        prior.get("technical_decision") == "AUTOMATED_TECHNICAL_ACCEPT_AGGREGATE_CONSISTENCY_ONLY" and
        prior.get("disclosure_status") == "PRIVATE_UNRELEASED" and prior.get("phase2b_real_data") == "NO_GO" and
        prior.get("scientific_acceptance_granted") is False and
        comparison.get("identity") == "phase2b-feasibility-recovery-v1" and
        comparison.get("disclosure_status") == "PRIVATE_UNRELEASED" and
        comparison.get("source_lock_sha256") == REDESIGN_LOCK and
        comparison.get("all_real_modeling_designs") == "NO_GO" and
        comparison.get("clinical_incidence_claim") is False and
        comparison.get("actual_test_split_created") is False and
        comparison.get("formal_gate_changed") is False and comparison.get("actual_restricted_cohort_processing") is False)
    observed = prior["audited_private_aggregate_evidence"]["cohorts"]
    require(set(observed) == set(comparison["cohorts"]) == set(prior["reviewed_counts"]) == {"HRS", "ELSA"})
    for name, c in observed.items():
        require(c.get("negative_analysis") == "screening_assumed_negative_sensitivity" and
            "eight_feature_observed_negative" not in c and
            c.get("scientific_approval") == "AI_SCIENTIFIC_DECISION_ADOPTED" and c.get("independent_human_approval") is False)
        recorded = comparison["cohorts"][name]; earlier = prior["reviewed_counts"][name]
        require(recorded["waterfall"] == [{"stage": k, "retained": count(c[k])} for k in STAGES])
        final = {"participants": count(c["eight_feature_binary_eligible"]),
            "events": count(c["eight_feature_reported_positive"]), "negatives": count(c["eight_feature_"+NEGATIVE])}
        require(all(type(v) is int and v >= 0 for v in recorded["final_counts"].values()) and
            recorded["final_counts"] == final and final["events"]+final["negatives"] == final["participants"] and
            earlier["initial"] == c[STAGES[0]] and earlier["final_n"] == final["participants"] and
            earlier["events"] == final["events"] and earlier["negatives"] == final["negatives"])
        oracle = recorded["imputation_only_oracle_envelope"]; raw = c["outcome_states"]["composite"]
        require(oracle["events"] == count(raw["reported_positive"]) and oracle["negatives"] == count(raw[NEGATIVE]) and
            oracle["participants_with_known_binary_outcomes"] == oracle["events"]+oracle["negatives"] and
            oracle["not_empirical_imputation_result"] is True and oracle["events"] >= final["events"])
        for component in ("heart_attack", "stroke"):
            r = recorded["components"][component]; b = c["eight_feature_component_binary"][component]
            require((r["participants"], r["events"], r["negatives"]) ==
                (count(b["binary_eligible"]), count(b["reported_positive"]), count(b[NEGATIVE])) and
                r["events"]+r["negatives"] == r["participants"] and
                r["baseline_scope"] == "COMMON_BOTH_DISEASE_FREE_BASELINE_NOT_COMPONENT_SPECIFIC_BASELINE")
    # The frozen comparison never evaluates these new populations empirically.
    for name in ("original_strict", "longer_followup", "expanded_baseline_and_landmark"):
        require(comparison["strategies"][name]["empirical_counts"] is None)
    plans = comparison["candidate_random_test_reserve_plans"]
    require(len(plans) == 6 and {(p["test_fraction_candidate"], p["adaptation_events"]) for p in plans} ==
        {(f, a) for f in (.3, .5) for a in (10, 25, 50)})
    for plan in plans:
        require(plan["test_event_reserve"] == 200 and plan["test_nonevent_screen_only"] == 100 and
            plan["validation_events"] == 50 and plan["development_nonevent_ratio_assumption"] == 3 and
            plan["precision_or_execution_authorized"] is False and plan["actual_people_or_test_lock_created"] is False and
            type(plan["simultaneous_test_and_remaining_development_reserve_probability"]) in (float, int) and
            0 <= plan["simultaneous_test_and_remaining_development_reserve_probability"] <= 1)
    return observed


def decide(prior, comparison, framework):
    """PRIVATE A/B/C/D disposition. Counts and verdicts never reach console."""
    require(framework["identity"] == VERSION+"_framework" and framework["default_target_test_events"] == 200 and
        framework["test_nonevent_screen_not_precision_guarantee"] == 100 and
        framework["real_modeling_authorized"] is False)
    observed = verified_pair(prior, comparison)
    target = comparison["cohorts"]["ELSA"]; source = comparison["cohorts"]["HRS"]
    e, z = (target["final_counts"][k] for k in ("events", "negatives"))
    event_aim = framework["default_target_test_events"]
    target_conditions = []
    if not e or not z: target_conditions.append("CURRENT_TARGET_LACKS_A_BINARY_CLASS")
    if e < event_aim: target_conditions.append("CURRENT_TARGET_TOTAL_CANNOT_SUPPLY_FIXED_TEST_EVENT_AIM")
    if z < framework["test_nonevent_screen_not_precision_guarantee"]:
        target_conditions.append("CURRENT_TARGET_TOTAL_CANNOT_SUPPLY_NONEVENT_SCREEN")
    missing = ["MODEL_SPECIFIC_SOURCE_DEVELOPMENT_SAMPLE_SIZE_NOT_ESTABLISHED",
        "FORMAL_SETTING_SPECIFIC_AP_AUC_CALIBRATION_AND_PAIRED_PRECISION_NOT_ESTABLISHED",
        "PREDICTOR_VARIATION_MEASUREMENT_EQUIVALENCE_AND_COMMON_SUPPORT_UNASSESSED",
        "PROSPECTIVE_DISJOINT_DEVELOPMENT_AND_UNTOUCHED_TEST_DESIGN_NOT_LOCKED"]
    plans = []
    for plan in comparison["candidate_random_test_reserve_plans"]:
        n = count(plan["test_size_candidate"])
        require(n == math.floor((e+z)*plan["test_fraction_candidate"]))
        plans.append({"fraction": plan["test_fraction_candidate"], "adaptation_events": plan["adaptation_events"],
            "recorded_simultaneous_reserve_probability": plan["simultaneous_test_and_remaining_development_reserve_probability"],
            "new_probability_test_has_both_classes": both_classes_probability(e, z, n),
            "probability_is_not_precision_or_power": True})
    candidates = {
        "current_sensitivity_composite": {"scientific_question": "SOURCE_SPECIFIC_FIRST_LATER_WAVE_REPORT_AMONG_NARROW_BASELINE_FREE_OBSERVABLE_RESPONDENTS",
            "observed_counts": target["final_counts"], "necessary_count_failures": target_conditions,
            "A_status": "INFEASIBLE_UNDER_FIXED_EVENT_CONTRACT" if target_conditions else "EVIDENCE_INSUFFICIENT_FOR_A",
            "remaining_evidence": missing, "strict_primary_promotion": False},
        "predictor_only_recovery": {"evidence_class": "MATHEMATICAL_BOUND_USING_RECORDED_KNOWN_OUTCOMES",
            "oracle": target["imputation_only_oracle_envelope"],
            "test_aim_impossible_even_at_oracle_ceiling": target["imputation_only_oracle_envelope"]["events"] < event_aim,
            "B_status": "EVIDENCE_INSUFFICIENT_NO_VALIDATED_IMPUTED_COHORT"},
        "expanded_history_landmark_or_later_wave": {"evidence_class": "UNAVAILABLE",
            "B_status": "EVIDENCE_INSUFFICIENT_NO_OBSERVED_COMPATIBLE_EXPANDED_COHORT",
            "event_gain": None},
        "all_target_zero_shot": {"scientific_question": "FROZEN_SOURCE_MODEL_TRANSPORT_EVALUATION_WITHOUT_TARGET_ADAPTATION",
            "meets_total_event_aim_only": e >= event_aim, "precision": "EVIDENCE_INSUFFICIENT",
            "original_sparse_label_adaptation_question_answered": False},
        "source_only_model": {"scientific_question": "HRS_INTERNAL_EXPLORATORY_REPORT_PREDICTION_NOT_VALIDATED_TRANSPORT",
            "observed_counts": source["final_counts"],
            "training_support": "BINARY_CLASS_ABSENT" if not source["final_counts"]["events"] or not source["final_counts"]["negatives"] else "EVIDENCE_INSUFFICIENT_NO_MODEL_SPECIFIC_SAMPLE_SIZE_PLAN"}}
    for component, r in target["components"].items():
        candidates[component+"_common_baseline"] = {"observed_counts": r,
            "binary_evaluation": "NOT_ESTIMABLE_MISSING_CLASS" if not r["events"] or not r["negatives"] else "COUNTS_EXIST_PRECISION_NOT_ESTABLISHED",
            "can_cover_fixed_test_event_aim_before_development": r["events"] >= event_aim,
            "independent_component_baseline_rederived": False, "A_or_B_supported": False}
    descriptive = all(count(c["initial_unique_respondents"]) > 0 for c in observed.values())
    return {"identity": VERSION, "framework_id": framework["identity"],
        "decision": "C_RESTRICT_TO_EXPLORATORY_RESEARCH" if descriptive else "D_CURRENT_DATA_INSUFFICIENT",
        "decision_scope": "AGGREGATE_ASCERTAINMENT_SELECTION_AND_TRANSFER_FEASIBILITY_ONLY_NO_MODEL_AUTHORIZATION",
        "A_retain_design_established": False, "B_viable_redesign_established": False,
        "C_observed_source_target_aggregate_universes_available": descriptive,
        "candidate_decisions": candidates, "candidate_evaluation_plans": plans,
        "target_event_reserve_arithmetic_not_a_split": [{"test_event_aim":event_aim,
            "adaptation_positives":budget, "events_left_for_separate_validation":e-event_aim-budget,
            "interpretation":"NONPOSITIVE_REMAINDER_CANNOT_SUPPLY_POSITIVE_TARGET_VALIDATION_POSITIVE_REMAINDER_IS_NOT_SUFFICIENCY"}
            for budget in framework["adaptation_positive_candidates"]],
        "nonevents_after_test_screen_before_all_development_use":z-framework["test_nonevent_screen_not_precision_guarantee"],
        "ordinary_bootstrap_probability_both_classes": bootstrap_both_classes(e, z),
        "bootstrap_precision_or_validity_guaranteed": False,
        "recorded_hypothetical_precision": comparison.get("private_count_conditioned_hypothetical_precision_not_actual_performance"),
        "hypothetical_simulation_can_satisfy_formal_precision_gate": False,
        "evidence_classes": framework["evidence_classes"],
        "source_archives": "QUALIFIED_LOCAL_ARCHIVE_PROVENANCE_NOT_INDEPENDENT_DISTRIBUTOR_AUTHENTICATION",
        "author_kind": "AI_AUTHORED_FRAMEWORK_APPLIED_DETERMINISTICALLY_LOCAL_ONLY",
        "independent_human_scientific_approval": False, "real_modeling_authorized": False,
        "formal_gate_changed": False, "disclosure_status": "PRIVATE_UNRELEASED"}


def public_context(project, expected):
    source = project/"phase2/phase2b_public"; p = source/LOCK
    require(re.fullmatch(r"[0-9a-f]{64}", expected or "") is not None and not p.is_symlink() and sha(p) == expected)
    lock = json.loads(p.read_bytes()); require(lock["identity"] == VERSION+"_source_lock")
    for relative, digest in lock["public_files"].items():
        f = project/relative
        require(f.resolve(strict=True) == f and not f.is_symlink() and sha(f) == digest)
    from . import human_feasibility_redesign as previous
    old, recovery, boot, _, _, _ = previous.public_context(project, REDESIGN_LOCK)
    framework = json.loads((source/FRAMEWORK).read_bytes())
    return previous, old, recovery, boot, framework


def read_evidence(root, project, expected):
    previous, old, recovery, boot, framework = public_context(project, expected)
    _, _, q, _, patch, qualified, _, lock = boot
    require(root.is_absolute() and root.resolve(strict=True) == root and not root.stat().st_mode & 0o077 and
        root != project and root not in project.parents and project not in root.parents)
    files = {"assessment": root/"output"/old.REPORT, "comparison": root/"output"/previous.DEST,
        "authorization": root/"config"/(recovery.VERSION+".authorization.json"),
        "started": recovery.paths(root)["started"], "result": recovery.paths(root)["result"],
        "config": root/q.INPUTS["config"]}
    for p in files.values(): q.private_file(p, root)
    hashes = {k:q.digest(p) for k,p in files.items()}
    data = {k:q.json_read(p) for k,p in files.items()}
    prior, comparison = data["assessment"], data["comparison"]
    integrity = prior["integrity"]; b = integrity["completed_run_bindings"]
    require(integrity["review_source_lock_sha256"] == previous.OLD_LOCK and integrity["receipt_bindings_verified"] is True and
        comparison["existing_evidence_sha256"]["prior_assessment"] == hashes["assessment"] and
        set(comparison["existing_evidence_sha256"]) == {"prior_assessment", "output", "authorization", "started", "result", "config"} and
        set(integrity["existing_input_sha256"]) == {"output", "authorization", "started", "result", "config"})
    for key in ("authorization", "started", "result", "config"):
        require(hashes[key] == integrity["existing_input_sha256"][key] == comparison["existing_evidence_sha256"][key])
    require(comparison["existing_evidence_sha256"]["output"] == integrity["existing_input_sha256"]["output"] == data["result"]["private_aggregates_sha256"] and
        all(b.get(k) == v for k,v in qualified["trusted_inputs"].items()) and hashes["config"] == b["config_sha256"])
    recovery.validate_authorization(data["authorization"], b)
    recovery.fixed_bindings(lock, b["recovery_lock_sha256"], b)
    require(b["recovery_lock_sha256"] == sha(project/"phase2/phase2a_6_wave_based_audit/stage_c_elsa_recovery_v1.lock.json"))
    start, result = data["started"], data["result"]
    envelope = {k:v for k,v in start.items() if k not in {"identity", "status"}}
    require(start["identity"] == recovery.VERSION+"_started" and start["status"] == "STARTED_NO_RETRY" and
        result["identity"] == recovery.VERSION+"_result" and all(result.get(k) == v for k,v in envelope.items()) and
        (result["status"], result["stage"], result["substage"], result["code"], result["category"], result["returncode"]) ==
        ("COMPLETED_PRIVATE_REVIEW_PENDING", "NONE", "NONE", "NONE", "NONE", 0) and type(result["returncode"]) is int and
        envelope["bindings"] == b and envelope["attempt_consumed"] is True and envelope["phase2b_authorized"] is False and
        envelope["recovery_authorization_sha256"] == hashes["authorization"] and envelope["protocol_id"] == recovery.PROTOCOL and
        envelope["controller_sha256"] == b["recovery_controller_sha256"] and
        envelope["evidence_tier"] == "QUALIFIED_LOCAL_ARCHIVE_PROVENANCE" and
        all(envelope.get(k) is False for k in ("v1_retried", "cause_diagnostic_retried", "independent_distributor_authentication", "independent_human_scientific_approval")) and
        hashlib.sha256(json.dumps(envelope["dependency_environment"], sort_keys=True).encode()).hexdigest() == b["recovery_environment_sha256"])
    config = deepcopy(data["config"])
    config["cohorts"]["ELSA"], amendment = patch.correct_interview_maps(config["cohorts"]["ELSA"])
    require(recovery.fingerprint(config) == b["corrected_config_sha256"] and recovery.fingerprint(amendment) == b["correction_record_sha256"])
    # No raw aggregate is opened or re-hashed. Its recorded SHA is chained to
    # the completed receipt and both assessments, not reverified against bytes.
    return {"root":root, "q":q, "files":files, "hashes":hashes, "prior":prior, "comparison":comparison,
        "framework":framework, "source_lock_sha256":expected, "destination":root/"output"/DEST}


def write_once(ctx, result):
    for k,p in ctx["files"].items():
        ctx["q"].private_file(p, ctx["root"]); require(ctx["q"].digest(p) == ctx["hashes"][k])
    result.update(input_sha256=ctx["hashes"], adjudication_source_lock_sha256=ctx["source_lock_sha256"],
        processed_at_utc=datetime.now(timezone.utc).isoformat(),
        raw_aggregate_current_bytes_reverified=False, original_review_or_comparison_replayed=False)
    fd = os.open(ctx["destination"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
    return ACK


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print(NOT_COMPLETED); raise SystemExit(2)


def main(argv=None):
    parser = SafeParser(description="Private scientific interpretation of two completed assessments only")
    parser.add_argument("--private-root", required=True); parser.add_argument("--expected-source-lock-sha256", required=True)
    args = parser.parse_args(argv)
    if os.environ.get("HRS_HUMAN_RUN") != "YES" or any(os.environ.get(k) for k in
        ("CODEX_HOME", "CODEX_SESSION_ID", "CODEX_THREAD_ID", "CI", "GITHUB_ACTIONS")):
        print(NOT_COMPLETED); return 2
    try:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            ctx = read_evidence(Path(args.private_root), Path(__file__).resolve().parents[2], args.expected_source_lock_sha256)
            try: result = decide(ctx["prior"], ctx["comparison"], ctx["framework"])
            except Exception:
                result = {"identity":VERSION, "decision":"EVIDENCE_INSUFFICIENT", "real_modeling_authorized":False,
                    "formal_gate_changed":False, "disclosure_status":"PRIVATE_UNRELEASED", "issue":"ASSESSMENT_SCHEMA_OR_CONSISTENCY_UNRESOLVED"}
            acknowledgment = write_once(ctx, result)
        print(acknowledgment); return 0
    except (Exception, KeyboardInterrupt, SystemExit):
        print(NOT_COMPLETED); return 2


if __name__ == "__main__": raise SystemExit(main())
