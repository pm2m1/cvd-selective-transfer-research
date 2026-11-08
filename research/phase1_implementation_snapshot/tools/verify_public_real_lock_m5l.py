"""Verify the single public real lock and persist assignments only in its private directory.

This command performs no fitting or test-performance evaluation. Public output
contains aggregates and whole-file hashes, never participant identifiers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from dmv_mat_cvd.data.public_v2 import PUBLIC_V2_VERSION, construct_haalsi_v2, construct_mhas_v2
from dmv_mat_cvd.data.releases import file_sha256
from dmv_mat_cvd.public_lock import (
    PublicLockPolicy, _validate_approval, _verified_evidence, adaptation_draw,
    aggregate_partition_metadata, comparator_adaptation_sets,
    project_sensitivity_on_primary_lock, source_partition_in_memory,
    validate_public_inputs, verify_locked_target,
)
from dmv_mat_cvd.public_v2_readiness import _haalsi_raw, _mhas_raw


def verify(*, data_root: Path, lock_path: Path, config_path: Path,
           evidence_path: Path, approval_path: Path, authorization_path: Path,
           master_file: Path, questionnaire: Path, output_path: Path) -> dict:
    expected_lock = data_root / "private_locks" / PUBLIC_V2_VERSION / "target_lock.json"
    if lock_path.resolve() != expected_lock.resolve() or not lock_path.is_file():
        raise ValueError("Single approved private lock is absent or at the wrong path")
    private_dir = lock_path.parent
    assignments_path = private_dir / "participant_assignments.private.json"
    if assignments_path.exists() or output_path.exists():
        raise FileExistsError("Verification artifacts already exist; do not overwrite")

    snapshot = json.loads(lock_path.read_text())
    evidence = json.loads(evidence_path.read_text())
    config = _verified_evidence(evidence, config_path, data_root, master_file, questionnaire)
    approval = json.loads(approval_path.read_text())
    authorization = json.loads(authorization_path.read_text())
    policy = PublicLockPolicy(config["proposed_primary_schema"], 30, 20261025,
                              .25, .20, 15, 10, ((25, 75), (10, 30)))
    _validate_approval(approval, evidence, config, policy)
    if (authorization.get("authorization_status") !=
            "AUTHORIZED_FOR_ONE_REAL_LOCK_NOT_YET_EXECUTED" or
            authorization.get("lock_execution_authorized") is not True or
            authorization.get("real_lock_executed") is not False or
            authorization.get("current_candidate_config_sha256") != file_sha256(config_path) or
            authorization.get("current_candidate_approval_record_sha256") != file_sha256(approval_path) or
            authorization.get("current_aggregate_evidence_digest") != evidence["evidence_digest"] or
            authorization.get("authorization_record_sha256") !=
                file_sha256(Path(authorization["authorization_record_path"]))):
        raise ValueError("One-time user authorization is stale or misbound")
    if (snapshot.get("protocol_version") != PUBLIC_V2_VERSION or
            snapshot.get("source") != "HAALSI Wave 1" or
            snapshot.get("target") != "MHAS Wave 3/2012 examination" or
            snapshot.get("endpoint_version") != config["endpoint_version"] or
            snapshot.get("seed") != policy.seed or
            snapshot.get("schema_version") != policy.schema_version or
            snapshot.get("config_sha256") != file_sha256(config_path) or
            snapshot.get("evidence_digest") != evidence["evidence_digest"] or
            snapshot.get("raw_mapping_document_sha256") != evidence["file_sha256"] or
            snapshot.get("release_identities") != config["release_identities"] or
            snapshot.get("test_event_floor") != 15 or
            snapshot.get("validation_event_floor") != 10 or
            snapshot.get("adaptation_budgets") != [[25, 75], [10, 30]] or
            snapshot.get("target_window_days") != 30 or
            snapshot.get("participant_ids_serialized") is not False or
            snapshot.get("training_performed") is not False):
        raise ValueError("Private lock identity, hashes or policy differ from authorization")

    source_map = json.loads(Path(config["source_mapping"]).read_text())
    target_map = json.loads(Path(config["target_mapping"]).read_text())
    source_raw, source_labels, _ = _haalsi_raw(data_root, source_map)
    target_raw, target_labels, _ = _mhas_raw(data_root, master_file, target_map)
    source = construct_haalsi_v2(source_raw, source_map, source_labels,
                                 schema="ten_doctor_report")
    target = construct_mhas_v2(target_raw, target_map, target_labels,
                               schema="ten_doctor_report", max_days=30)
    timing = construct_mhas_v2(target_raw, target_map, target_labels,
                               schema="ten_doctor_report", max_days=14)
    nine = construct_mhas_v2(target_raw, target_map, target_labels,
                             schema="nine_no_diabetes", max_days=30)
    checks = validate_public_inputs(source, target, policy)
    if checks != snapshot["cohort_counts"]:
        raise ValueError("Reconstructed source/target cohort differs from lock")
    target_parts = verify_locked_target(snapshot, source, target, policy)
    source_parts = source_partition_in_memory(source, policy.seed)
    if aggregate_partition_metadata(source, source_parts) != snapshot["source_partition_counts"]:
        raise ValueError("Source split reconstruction differs from lock")
    target_ids = set(target.canonical.participant_id.astype(str))
    if (set().union(*target_parts.values()) != target_ids or
            sum(map(len, target_parts.values())) != len(target_ids) or
            set(source.canonical.participant_id.astype(str)) & target_ids):
        raise ValueError("Target exclusivity or source/target isolation failed")
    counts = aggregate_partition_metadata(target, target_parts)
    if (counts["target_test"]["events"] < 15 or
            counts["target_validation"]["events"] < 10 or
            counts["target_adaptation_pool"]["events"] < 25 or
            counts["target_adaptation_pool"]["nonevents"] < 75):
        raise ValueError("Prespecified reserve or adaptation pool failed")

    timing_ids = set(timing.canonical.participant_id.astype(str))
    if not timing_ids <= target_ids:
        raise ValueError("Timing sensitivity contains a new primary participant")
    timing_parts = project_sensitivity_on_primary_lock(target_parts, timing)
    if set().union(*timing_parts.values()) != timing_ids:
        raise ValueError("Timing sensitivity partition inheritance failed")
    nine_ids = set(nine.canonical.participant_id.astype(str))
    if not target_ids <= nine_ids:
        raise ValueError("Nine-feature common-population comparison invalid")
    nine_parts = project_sensitivity_on_primary_lock(target_parts, nine)
    if nine_parts != target_parts:
        raise ValueError("Nine-feature shared population changed the primary partition")

    labels = target.canonical.set_index("participant_id")["label"]
    draws: dict[str, dict[str, list[str]]] = {}
    for repetition in range(config["adaptation_subset_repetitions"]):
        primary = adaptation_draw(target, target_parts, positives=25, negatives=75,
                                  seed=policy.seed, repetition=repetition)
        low = adaptation_draw(target, target_parts, positives=10, negatives=30,
                              seed=policy.seed, repetition=repetition)
        if (not low <= primary or not primary <= target_parts["target_adaptation_pool"] or
                len(primary) != 100 or len(low) != 40 or
                int(labels.loc[list(primary)].sum()) != 25 or
                int(labels.loc[list(low)].sum()) != 10):
            raise ValueError("Nested adaptation labels differ from approved budgets")
        shared = comparator_adaptation_sets(primary)
        if (shared["source_only"] is not None or
                any(value != frozenset(primary) for name, value in shared.items()
                    if name != "source_only")):
            raise ValueError("Transfer comparators do not share the adaptation records")
        draws[str(repetition)] = {"primary_25_75": sorted(primary),
                                  "low_label_10_30": sorted(low)}

    # All participant-level assignments remain inside the controlled private
    # lock directory. Exclusive creation refuses a second verification write.
    os.chmod(private_dir, 0o700)
    os.chmod(lock_path, 0o600)
    private_payload = {"protocol_version": PUBLIC_V2_VERSION,
                       "lock_sha256": file_sha256(lock_path),
                       "target_partitions": {k: sorted(v) for k, v in target_parts.items()},
                       "source_partitions": {k: sorted(v) for k, v in source_parts.items()},
                       "adaptation_draws": draws,
                       "participant_level_private": True,
                       "target_test_labels_included": False}
    data = (json.dumps(private_payload, indent=2, allow_nan=False) + "\n").encode()
    descriptor = os.open(assignments_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())

    report = {"verification_version": "public-real-lock-m5l-v1",
              "protocol_version": PUBLIC_V2_VERSION,
              "lock_identifier_sha256": file_sha256(lock_path),
              "private_assignments_sha256": file_sha256(assignments_path),
              "config_sha256": file_sha256(config_path),
              "evidence_digest": evidence["evidence_digest"],
              "approval_sha256": file_sha256(approval_path),
              "authorization_manifest_sha256": file_sha256(authorization_path),
              "source_counts": snapshot["source_partition_counts"],
              "target_counts": counts,
              "timing_sensitivity_partition_counts": aggregate_partition_metadata(
                  timing, timing_parts),
              "nine_feature_common_population_n": len(target_ids),
              "nine_feature_expanded_only_n": len(nine_ids - target_ids),
              "adaptation_repetitions_verified": len(draws),
              "nested_low_label_draws_verified": True,
              "shared_comparator_adaptation_verified": True,
              "source_target_disjoint": True,
              "participants_exclusive_and_complete": True,
              "metadata_or_post_index_predictors_excluded": True,
              "real_test_performance_evaluated": False,
              "model_or_preprocessing_fitted": False,
              "participant_ids_in_public_report": False,
              "private_lock_nonoverwriting": True}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x") as output:
        output.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--master-file", type=Path, required=True)
    parser.add_argument("--questionnaire", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(data_root=args.data_root, lock_path=args.lock,
                    config_path=args.config, evidence_path=args.evidence,
                    approval_path=args.approval, authorization_path=args.authorization,
                    master_file=args.master_file, questionnaire=args.questionnaire,
                    output_path=args.output)
    print(f"Private public lock verified; target test N={result['target_counts']['target_test']['n']}")


if __name__ == "__main__":
    main()
