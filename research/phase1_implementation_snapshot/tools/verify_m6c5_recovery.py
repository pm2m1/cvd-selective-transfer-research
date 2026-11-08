"""Aggregate-only verification of the single authorized private recovery output.

Reads completed private artifacts only. Never runs inference or metrics.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path('WITHHELD_PRIVATE_PATH')
PUBLIC = ROOT / "results/real_training/m6c_final_test_v2_recovery/aggregate_only_results.json"
ORIGINAL = PRIVATE.with_name("final_test_v1")
REGISTRATION_SHA256 = 'WITHHELD_REFERENCE_BINDING'
LOCK_SHA256 = 'WITHHELD_REFERENCE_BINDING'
ASSIGNMENTS_SHA256 = 'WITHHELD_REFERENCE_BINDING'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify() -> dict:
    registration_path = ROOT / "FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json"
    authorization_path = ROOT / "FINAL_TEST_RECOVERY_EXECUTION_MANIFEST.authorized.json"
    if sha256(registration_path) != REGISTRATION_SHA256:
        raise ValueError("Frozen registration changed")
    registration = json.loads(registration_path.read_text())
    authorization = json.loads(authorization_path.read_text())
    if (authorization.get("recovery_execution_authorized") is not True or
            authorization.get("execution_status") != "AUTHORIZED_NOT_EXECUTED" or
            authorization.get("authorization_source") != "explicit_user_message_in_chatgpt"):
        raise ValueError("New recovery authorization record differs")
    if sha256(Path(registration["test_lock_path"])) != LOCK_SHA256 or (
            sha256(Path(registration["private_assignments_path"])) != ASSIGNMENTS_SHA256):
        raise ValueError("Immutable target lock or assignments changed")
    if PRIVATE == ORIGINAL or not PRIVATE.is_dir() or not ORIGINAL.is_dir():
        raise ValueError("Separate original and recovery attempts are required")
    if stat.S_IMODE(PRIVATE.stat().st_mode) != 0o700:
        raise ValueError("Recovery directory permissions changed")
    expected_files = {
        "attempt.private.json", "authorization.private.json", "participant_ids.private.json",
        "features.private.npz", "tabular_predictions.private.npz",
        "torch_predictions.private.npz", "prediction_bundle.private.npz",
        "metrics.private.json", "aggregate_payload.private.json",
        "evaluation_manifest.private.json",
    }
    if {item.name for item in PRIVATE.iterdir()} != expected_files:
        raise ValueError("Private recovery output is partial or has extra files")
    if any(stat.S_IMODE((PRIVATE / name).stat().st_mode) != 0o600 for name in expected_files):
        raise ValueError("Private recovery file permissions changed")
    run = json.loads((PRIVATE / "evaluation_manifest.private.json").read_text())
    private_auth = json.loads((PRIVATE / "authorization.private.json").read_text())
    if (run.get("status") != "RECOVERY_COMPLETE_AFTER_FAILED_ORIGINAL_ATTEMPT" or
            run.get("model_predictions") != 184 or run.get("test_participants") != 283 or
            run.get("test_positive_reports") != 21 or
            run.get("bootstrap_seed") != 20261026 or run.get("bootstrap_replicates") != 2000 or
            run.get("no_fitting_performed") is not True or
            run.get("registration_sha256") != REGISTRATION_SHA256 or
            run.get("execution_manifest_sha256") != sha256(authorization_path) or
            private_auth.get("manifest_sha256") != sha256(authorization_path) or
            private_auth.get("manifest") != authorization):
        raise ValueError("Recovery completion or authorization binding differs")
    binding_paths = {
        "private_feature_sha256": "features.private.npz",
        "private_prediction_bundle_sha256": "prediction_bundle.private.npz",
        "private_ids_sha256": "participant_ids.private.json",
        "private_metrics_sha256": "metrics.private.json",
        "aggregate_payload_sha256": "aggregate_payload.private.json",
    }
    if any(run.get(key) != sha256(PRIVATE / name) for key, name in binding_paths.items()):
        raise ValueError("A completed private artifact changed")
    if any(run["worker_outputs"].get(group) != sha256(
            PRIVATE / f"{group}_predictions.private.npz") for group in ("torch", "tabular")):
        raise ValueError("Frozen worker output changed")
    assignments = json.loads(Path(registration["private_assignments_path"]).read_text())
    ids = json.loads((PRIVATE / "participant_ids.private.json").read_text())["ordered_participant_ids"]
    test_ids = assignments["target_partitions"]["target_test"]
    if (len(ids) != 283 or len(set(ids)) != 283 or ids != sorted(ids) or
            set(ids) != set(test_ids)):
        raise ValueError("Private participant identity/order differs from locked test")
    with np.load(PRIVATE / "features.private.npz", allow_pickle=False) as features:
        if len(features.files) != 20 or any(features[name].shape != (283,)
                                             for name in features.files) or (
                any("label" in name or "participant" in name for name in features.files)):
            raise ValueError("Private IPC feature contract differs")
    all_indices = []
    for group, families, count in (
            ("tabular", {"sklearn_logistic", "xgboost"}, 22),
            ("torch", {"flat_mlp", "five_view_net"}, 162)):
        with np.load(PRIVATE / f"{group}_predictions.private.npz", allow_pickle=False) as worker:
            expected = [i for i, item in enumerate(registration["models"])
                        if item["model_family"] in families]
            indices = worker["model_indices"]
            values = worker["probabilities"]
            if (list(indices) != expected or len(indices) != count or
                    values.shape != (count, 283) or not np.isfinite(values).all() or
                    ((values < 0) | (values > 1)).any() or
                    str(worker["feature_sha256"]) != run["private_feature_sha256"]):
                raise ValueError("Frozen worker predictions are misaligned or invalid")
            all_indices.extend(map(int, indices))
    if sorted(all_indices) != list(range(184)):
        raise ValueError("At least one registered model is missing or duplicated")
    source = {"source_logistic", "source_xgboost", "source_flat_mlp", "source_multiview"}
    adapted = {"head_only", "full_finetune", "target_logistic", "target_multiview",
               "fixed_mask", "random_calibrated_logical", "legacy_topk",
               "calibrated_threshold", "calibrated_logical"}
    expected_keys = {"observed_labels"} | {f"{budget}__{method}"
        for budget in registration["budgets"] for method in source | adapted}
    with np.load(PRIVATE / "prediction_bundle.private.npz", allow_pickle=False) as bundle:
        if set(bundle.files) != expected_keys:
            raise ValueError("Registered method/budget bundle is incomplete")
        labels = bundle["observed_labels"]
        if labels.shape != (283,) or int(labels.sum()) != 21 or (
                not np.isin(labels, [0, 1]).all()):
            raise ValueError("Frozen test-label count changed")
        for budget in registration["budgets"]:
            for method in source | adapted:
                values = bundle[f"{budget}__{method}"]
                if values.shape != ((1 if method in source else 10), 283) or (
                        not np.isfinite(values).all() or ((values < 0) | (values > 1)).any()):
                    raise ValueError("Registered method/draw bundle differs")
    metrics = json.loads((PRIVATE / "metrics.private.json").read_text())
    payload = json.loads(PUBLIC.read_text())
    private_payload = json.loads((PRIVATE / "aggregate_payload.private.json").read_text())
    if payload != private_payload or set(metrics) != set(registration["budgets"]) or (
            payload.get("status") != "COMPLETE_AGGREGATE_ONLY" or
            payload.get("participant_count") != 283 or
            payload.get("positive_reports") != 21 or
            payload.get("registration_sha256") != REGISTRATION_SHA256 or
            payload.get("protocol_version") != "public-haalsi-mhas-v2"):
        raise ValueError("Public aggregate differs from private registered result")
    for budget in registration["budgets"]:
        record = metrics[budget]
        if (record.get("bootstrap_seed") != 20261026 or
                record.get("replicates") != 2000 or
                "calibrated_logical_minus_full_finetune" not in record.get("contrasts", {})):
            raise ValueError("Frozen statistic or primary contrast changed")
    public_text = PUBLIC.read_text()
    if any(marker in public_text for marker in ("MHAS:", "participant_ids",
                                               "observed_labels", "probabilities",
                                               '"fixed_reliability_bins_by_draw": [')):
        raise ValueError("Participant-level information entered public output")
    if not all(value == "PRIVATE_ONLY_SMALL_CELL_DISCLOSURE_CONTROL"
               for budget in payload["metrics"].values()
               for model in budget["calibration_exploratory"].values()
               for value in (model["fixed_reliability_bins_by_draw"],)):
        raise ValueError("Small-cell calibration output was disclosed")
    return {
        "status": "VERIFIED_RECOVERY_COMPLETE",
        "registration_sha256": REGISTRATION_SHA256,
        "authorized_manifest_sha256": sha256(authorization_path),
        "private_evaluation_manifest_sha256": sha256(PRIVATE / "evaluation_manifest.private.json"),
        "public_aggregate_sha256": sha256(PUBLIC),
        "private_artifact_sha256": {name: sha256(PRIVATE / name) for name in sorted(expected_files)},
        "test_participants": 283, "positive_reports": 21,
        "frozen_model_outputs": 184, "bootstrap_replicates": 2000,
        "original_failure_preserved": True, "second_recovery_run_allowed": False,
        "no_new_training": True, "public_participant_rows": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
