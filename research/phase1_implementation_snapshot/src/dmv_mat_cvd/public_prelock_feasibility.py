"""Aggregate-only public prelock feasibility from two independent audits."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .data.public_v2 import SCHEMA_VERSIONS
from .public_lock import PublicLockPolicy, aggregate_budget_plan


def build_prelock_feasibility(cohort_evidence: dict, independent: dict,
                              config: dict) -> dict:
    expected = {"haalsi_ten_doctor": "doctor_diabetes",
                "haalsi_nine": "nine_no_diabetes"}
    for cohort, independent_key in expected.items():
        actual = cohort_evidence["cohorts"][cohort]["after_v2_rules"]
        check = independent["waterfall"][independent_key]
        if (actual["n"], actual["events"]) != (check["n"], check["events"]):
            raise ValueError("Independent HAALSI count reconciliation failed")
    policy = PublicLockPolicy(SCHEMA_VERSIONS["ten_doctor_report"], 30, 0,
        config["target_test_fraction_proposed"],
        config["target_validation_fraction_of_development_proposed"],
        config["test_event_floor_proposed"], config["validation_event_floor_proposed"],
        ((10, 30), (25, 75)))
    keys = {"primary_ten_0_30": "mhas_ten_0_30",
            "timing_ten_0_14": "mhas_ten_0_14",
            "diabetes_omitted_nine_0_30": "mhas_nine_0_30",
            "diabetes_omitted_nine_0_14": "mhas_nine_0_14"}
    scenarios = {}
    for name, key in keys.items():
        item = cohort_evidence["cohorts"][key]["after_v2_rules"]
        scenarios[name] = aggregate_budget_plan(item["events"], item["known_negative"], policy)
    return {"protocol_version": config["protocol_version"],
            "readiness": "NO_PENDING_EXACT_APPROVALS",
            "candidate_source_ten": cohort_evidence["cohorts"]["haalsi_ten_doctor"]["after_v2_rules"],
            "candidate_source_nine": cohort_evidence["cohorts"]["haalsi_nine"]["after_v2_rules"],
            "independent_source_waterfall": independent["waterfall"],
            "independent_medication_counts": independent["medication"],
            "independent_sex_counts": independent["wave1_roster"],
            "independent_diabetes_counts": independent["diabetes"],
            "target_scenarios": scenarios,
            "proposed_adaptation_budgets": [
                {"positive_labels": 25, "negative_labels": 75, "total_labels": 100,
                 "role": "primary_proposed"},
                {"positive_labels": 10, "negative_labels": 30, "total_labels": 40,
                 "role": "low_label_sensitivity_proposed"},
                {"positive_labels": 50, "negative_labels": 150, "total_labels": 200,
                 "role": "exploratory_only_if_feasible"}],
            "test_prevalence_policy": "Stratify one fixed target split to preserve natural prevalence approximately; reserve floors may perturb it; never rebalance test labels.",
            "adaptation_prevalence_policy": "Fixed 1:3 event-to-nonevent sampling enriches events; raw probabilities require separate development-only weighting/calibration review.",
            "sensitivity_partition_warning": "0–14-day sensitivity must inherit the primary 0–30-day immutable test membership by intersection; its independent arithmetic is an upper-level planning screen, not a second publication lock.",
            "actual_target_split_created": False,
            "participant_identifiers_written": False,
            "training_performed": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-evidence", type=Path, required=True)
    parser.add_argument("--independent-haalsi", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = {"cohort_evidence": args.cohort_evidence,
              "independent_haalsi": args.independent_haalsi, "config": args.config}
    data = {name: json.loads(path.read_text()) for name, path in inputs.items()}
    report = build_prelock_feasibility(data["cohort_evidence"], data["independent_haalsi"], data["config"])
    report["created_utc"] = datetime.now(timezone.utc).isoformat()
    report["input_sha256"] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                              for name, path in inputs.items()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as out:
        out.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print("Aggregate-only public prelock feasibility written")


if __name__ == "__main__":
    main()
