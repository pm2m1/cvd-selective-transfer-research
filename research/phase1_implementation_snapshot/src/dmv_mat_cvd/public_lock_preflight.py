"""Read-only public-study lock preflight: real aggregates, synthetic partitions.

This command never calls target_partition_in_memory or execute_real_lock on
real cohorts. It does not create an adaptation draw, a lock file, or training
data. Its report contains aggregate counts and whole-file digests only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .data.public_v2 import (PUBLIC_V2_VERSION, SCHEMA_VERSIONS,
    construct_haalsi_v2, construct_mhas_v2)
from .data.releases import file_sha256
from .public_lock import (REPORTED_DECISION_IDS, REQUIRED_DOCUMENTS, PublicLockPolicy,
    _validate_approval, _verified_evidence, aggregate_budget_plan,
    public_runner_review_valid, validate_public_inputs, validate_public_use_records)
from .public_v2_readiness import (_haalsi_raw, _mhas_raw, readiness_evidence)


def _reported_decision_check(approval: dict) -> dict:
    decisions = approval.get("reported_supervisor_decisions", [])
    ids = [item.get("id") for item in decisions if isinstance(item, dict)]
    return {"all_ten_recorded": len(ids) == 10 and set(ids) == REPORTED_DECISION_IDS and
            all(item.get("response") == "YES (student-reported)" for item in decisions),
            "provenance_is_student_report": "Student reported" in approval.get("provenance", ""),
            "signed_approval_claimed": bool(approval.get("written_supervisor_approval_received")),
            "execution_authorized": bool(approval.get("lock_execution_authorized"))}


def preflight_public_lock(manifest_path: Path, *, data_root: Path,
                          output_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get("mode") != "read_only_preflight" or
            manifest.get("protocol_version") != PUBLIC_V2_VERSION or
            manifest.get("execute_real_lock") is not False):
        raise ValueError("Public preflight manifest must explicitly prohibit execution")
    config_path = Path(manifest["config_path"])
    evidence_path = Path(manifest["cohort_evidence_path"])
    independent_path = Path(manifest["independent_haalsi_path"])
    approval_path = Path(manifest["approval_record_path"])
    master_file = Path(manifest["master_file"])
    questionnaire = Path(manifest["questionnaire_file"])
    evidence = json.loads(evidence_path.read_text())
    config = _verified_evidence(evidence, config_path, data_root,
                                master_file, questionnaire)
    approval = json.loads(approval_path.read_text())
    independent = json.loads(independent_path.read_text())
    if (manifest.get("config_sha256") != file_sha256(config_path) or
            manifest.get("approval_record_sha256") != file_sha256(approval_path) or
            manifest.get("evidence_digest") != evidence["evidence_digest"]):
        raise ValueError("Preflight execution manifest is stale")
    policy_data = manifest["policy"]
    policy = PublicLockPolicy(policy_data["schema_version"],
        policy_data["target_window_days"], policy_data["seed"],
        policy_data["test_fraction"],
        policy_data["validation_fraction_of_development"],
        policy_data["test_event_floor"], policy_data["validation_event_floor"],
        tuple(tuple(pair) for pair in policy_data["adaptation_budgets"]))
    if (config.get("source") != "HAALSI Wave 1" or
            config.get("target") != "MHAS Wave 3/2012 examination" or
            config.get("endpoint_version") != "public-wave-doctor-reported-ha-or-stroke-v2" or
            policy.schema_version != config.get("proposed_primary_schema") or
            policy.target_window_days != 30 or
            policy.seed != config.get("target_partition_seed") or
            set(policy.adaptation_budgets) != {tuple(x) for x in config.get("target_adaptation_labeled_budgets", [])} or
            policy.test_fraction != config.get("target_test_fraction_proposed") or
            policy.validation_fraction_of_development != config.get("target_validation_fraction_of_development_proposed") or
            policy.test_event_floor != config.get("test_event_floor_proposed") or
            policy.validation_event_floor != config.get("validation_event_floor_proposed")):
        raise ValueError("Public preflight policy differs from frozen candidate configuration")
    documented = approval.get("documentation", {})
    documentation_valid = (isinstance(documented, dict) and
        REQUIRED_DOCUMENTS.issubset(documented) and all(
            isinstance(item, dict) and item.get("version") and item.get("path") and
            item.get("sha256") and file_sha256(Path(item["path"])) == item["sha256"]
            for item in documented.values()))
    if not documentation_valid:
        raise ValueError("Official documentation inventory is incomplete or changed")
    hmap = json.loads(Path(config["source_mapping"]).read_text())
    mmap = json.loads(Path(config["target_mapping"]).read_text())
    if (hmap.get("public_model_mapping_version") != config.get("source_public_mapping_version") or
            mmap.get("public_model_mapping_version") != config.get("target_public_mapping_version")):
        raise ValueError("Frozen public model mapping overlays do not match configuration")
    hraw, hlabels, hload = _haalsi_raw(data_root, hmap)
    mraw, mlabels, mload = _mhas_raw(data_root, master_file, mmap)
    source = construct_haalsi_v2(hraw, hmap, hlabels, schema="ten_doctor_report")
    target = construct_mhas_v2(mraw, mmap, mlabels,
                               schema="ten_doctor_report", max_days=30)
    h_nine = construct_haalsi_v2(hraw, hmap, hlabels, schema="nine_no_diabetes")
    m_nine = construct_mhas_v2(mraw, mmap, mlabels,
                               schema="nine_no_diabetes", max_days=30)
    m_short = construct_mhas_v2(mraw, mmap, mlabels,
                                schema="ten_doctor_report", max_days=14)
    m_short_nine = construct_mhas_v2(mraw, mmap, mlabels,
                                     schema="nine_no_diabetes", max_days=14)
    identity = validate_public_inputs(source, target, policy)
    cohorts = {"haalsi_ten_doctor": source, "haalsi_nine": h_nine,
               "mhas_ten_0_30": target, "mhas_nine_0_30": m_nine,
               "mhas_ten_0_14": m_short, "mhas_nine_0_14": m_short_nine}
    for key, cohort in cohorts.items():
        if cohort.report["after_v2_rules"] != evidence["cohorts"][key]["after_v2_rules"]:
            raise ValueError(f"Fresh public cohort differs from frozen aggregate evidence: {key}")
    if (independent["waterfall"]["doctor_diabetes"] != {
            k: source.report["after_v2_rules"][k] for k in ("n", "events")} or
            independent["waterfall"]["nine_no_diabetes"] != {
            k: h_nine.report["after_v2_rules"][k] for k in ("n", "events")}):
        raise ValueError("Independent HAALSI reconciliation differs from constructor")
    primary_ids = set(target.canonical.participant_id)
    timing_ids = set(m_short.canonical.participant_id)
    nine_ids = set(m_nine.canonical.participant_id)
    short_nine_ids = set(m_short_nine.canonical.participant_id)
    if not timing_ids <= primary_ids or not short_nine_ids <= nine_ids or not primary_ids <= nine_ids:
        raise ValueError("Stricter examination-window cohort is not nested")
    reserve = {}
    for name, cohort in (("primary_ten_0_30", target),
                         ("timing_ten_0_14", m_short),
                         ("nine_0_30", m_nine),
                         ("nine_0_14", m_short_nine)):
        item = cohort.report["after_v2_rules"]
        reserve[name] = aggregate_budget_plan(item["events"], item["known_negative"], policy)
    reported = _reported_decision_check(approval)
    if not reported["all_ten_recorded"] or not reported["provenance_is_student_report"]:
        raise ValueError("Ten reported supervisor decisions are not accurately recorded")
    data_use = validate_public_use_records(approval)
    runner_reviewed = public_runner_review_valid(approval)
    executable_error = None
    try:
        _validate_approval(approval, evidence, config, policy)
    except (ValueError, FileNotFoundError) as exc:
        executable_error = str(exc)
    readiness = readiness_evidence(config, source.report, target.report,
                                   provenance_ok=True, locked_runner_reviewed=runner_reviewed)
    lock_root = data_root / manifest["lock_root_relative_to_data_root"]
    if not lock_root.resolve().is_relative_to(data_root.resolve()):
        raise ValueError("Planned private lock root escapes declared external data root")
    prior_lock = lock_root / PUBLIC_V2_VERSION / "target_lock.json"
    report = {"report_version": "public-lock-preflight-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_version": PUBLIC_V2_VERSION,
        "endpoint_version": config["endpoint_version"],
        "source_public_mapping_version": config["source_public_mapping_version"],
        "target_public_mapping_version": config["target_public_mapping_version"],
        "config_sha256": file_sha256(config_path),
        "approval_record_sha256": file_sha256(approval_path),
        "cohort_evidence_digest": evidence["evidence_digest"],
        "independent_audit_sha256": file_sha256(independent_path),
        "release_mapping_schema_code_hashes_valid": True,
        "official_documentation_count_verified": len(documented),
        "cohort_counts": {name: cohort.report["after_v2_rules"] for name, cohort in cohorts.items()},
        "independent_haalsi_reconciliation": independent["waterfall"],
        "participant_checks": {"source_unique": bool(source.canonical.participant_id.is_unique),
                               "target_unique_and_isolated": bool(target.canonical.participant_id.is_unique),
                               "source_target_overlap": False,
                               "mhas_master_join": mload["master_join"],
                               "model_metadata_excluded": True},
        "sensitivity_membership": {"timing_0_14_subset_of_primary_0_30": True,
            "primary_ten_inside_nine_0_30": primary_ids <= nine_ids,
            "nine_extra_0_30_n": len(nine_ids - primary_ids),
            "short_nine_inside_nine_0_30": True},
        "event_reserve_arithmetic": reserve,
        "reported_supervisor_decisions": reported,
        "release_use_evidence": data_use,
        "public_runner_review_record_valid": runner_reviewed,
        "approval_for_real_execution": {"runner_manifest_validated": executable_error is None,
            "failure_reason": executable_error,
            "written_supervisor_approval_recorded": bool(approval.get("written_supervisor_approval_received")),
            "clinical_review_disposition": approval.get("clinical_review_disposition"),
            "institutional_approval_or_exemption_verified": bool(approval.get("institutional_approval_or_exemption_verified")),
            "explicit_lock_execution_authorized": bool(approval.get("lock_execution_authorized")),
            "protocol_stage_approved_for_lock": config.get("protocol_stage") == "approved_for_lock",
            "planned_private_lock_already_exists": prior_lock.exists()},
        "readiness": readiness,
        "real_target_partition_created": False,
        "real_adaptation_subset_created": False,
        "real_lock_file_written": False,
        "training_or_fitted_preprocessing_performed": False,
        "participant_ids_written": False}
    report["status"] = ("READY_FOR_SEPARATE_AUTHORIZED_LOCK" if
        readiness["COHORT_READY"] == "YES" and executable_error is None and
        approval.get("lock_execution_authorized") is True and
        config.get("protocol_stage") == "approved_for_lock" and not prior_lock.exists()
        else "BLOCKED_PENDING_APPROVAL_OR_EXECUTION_AUTHORIZATION")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x") as output:
        output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = preflight_public_lock(args.manifest, data_root=args.data_root,
                                   output_path=args.output)
    print(f"Public preflight: {report['status']}; no real split or lock executed")


if __name__ == "__main__":
    main()
