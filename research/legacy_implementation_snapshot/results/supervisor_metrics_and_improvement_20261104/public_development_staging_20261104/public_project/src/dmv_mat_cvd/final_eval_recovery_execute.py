"""Fail-closed recovery evaluator. Preparation never opens a target-test row.

The real path requires a NEW explicit recovery authorization and a distinct
atomic private claim. It must never be invoked under the consumed first-attempt
authorization. Model inference and statistics execute in separate processes.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
from typing import Mapping


REGISTRATION = Path("FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json")
REGISTRATION_SHA256 = 'WITHHELD_REFERENCE_BINDING'
ORIGINAL_EXECUTOR_SHA256 = 'WITHHELD_REFERENCE_BINDING'
ORIGINAL_AUTHORIZATION_SHA256 = 'WITHHELD_REFERENCE_BINDING'
ORIGINAL_REPORT = Path("MILESTONE6C2_FINAL_TEST_ATTEMPT_REPORT.md")
ORIGINAL_PRIVATE = Path('WITHHELD_PRIVATE_PATH')
RECOVERY_PRIVATE = Path('WITHHELD_PRIVATE_PATH')
RECOVERY_PUBLIC = Path("results/real_training/m6c_final_test_v2_recovery/aggregate_only_results.json")
MANIFEST = Path("FINAL_TEST_RECOVERY_EXECUTION_MANIFEST.pending.json")
INTENDED_COMMAND = (
    'PYTHONPATH=src .venv/bin/python -m dmv_mat_cvd.final_eval_recovery_execute --execute-real-recovery --registration FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json --execution-manifest FINAL_TEST_RECOVERY_EXECUTION_MANIFEST.authorized.json --data-root WITHHELD_PRIVATE_PATH --master-file WITHHELD_PRIVATE_PATH --questionnaire WITHHELD_PRIVATE_PATH'
)
RUNTIME = Path("src/dmv_mat_cvd/final_eval_runtime_v2.py")
WORKER = Path("src/dmv_mat_cvd/final_eval_recovery_worker.py")
STATS_WORKER = Path("src/dmv_mat_cvd/final_eval_recovery_stats_worker.py")
STATISTICS = Path("src/dmv_mat_cvd/final_eval_stats.py")
BASELINE = Path("results/real_training/m6a_20261025_dev_baselines_v4/run_manifest.json")
SELECTOR = Path("results/real_training/m6b_20261025_selector_v1")
CONFIG = Path("configs/public_haalsi_mhas_v2.ready_pending_execution_m5l.json")
EVIDENCE = Path("results/public_governance/20261025/m5l_pending_execution/20261025T105836Z-2542127c/aggregate_public_v2.json")
ORIGINAL_ATTEMPT_HASHES = {
    "attempt.private.json": 'WITHHELD_REFERENCE_BINDING',
    "authorization.private.json": 'WITHHELD_REFERENCE_BINDING',
    "failure.private.json": 'WITHHELD_REFERENCE_BINDING',
}
AUTHORIZATION_SCOPE = "one documented recovery evaluation of the same immutable MHAS test after the failed first attempt"
FAILURE_DISCLOSURE = ("The original final-test attempt accessed target-test rows but did not produce "
                      "performance results. A proposed recovery would reaccess the same frozen "
                      "target-test participants under a separate authorization.")
FAMILY_COUNTS = {"torch": 162, "tabular": 22}
SOURCE_METHODS = ("source_logistic", "source_xgboost", "source_flat_mlp", "source_multiview")
ADAPTED_METHODS = ("head_only", "full_finetune", "target_logistic", "target_multiview",
                   "fixed_mask", "random_calibrated_logical", "legacy_topk",
                   "calibrated_threshold", "calibrated_logical")
FEATURE_ORDER = ("age", "sex", "sbp", "dbp", "bmi", "total_cholesterol", "hdl",
                 "smoking_status", "diabetes", "antihypertensive_treatment")
CONTINUOUS = frozenset({"age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl"})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inventory_digest(models: list[dict]) -> str:
    return hashlib.sha256(json.dumps(models, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def private_json_exclusive(path: Path, value: dict) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def recovery_authorization_statement(manifest: dict) -> str:
    return (
        "I explicitly authorize exactly one documented recovery evaluation of the same immutable "
        "MHAS target test for public-haalsi-mhas-v2. I acknowledge that the first authorized attempt "
        "accessed test rows, failed without predictions or performance results, and remains preserved. "
        f"Use frozen registration SHA256 {manifest['scientific_registration_sha256']}, "
        f"recovery executor SHA256 {manifest['recovery_executor_sha256']}, "
        f"isolated runtime SHA256 {manifest['recovery_runtime_sha256']}, "
        f"worker SHA256 {manifest['recovery_worker_sha256']}, "
        f"statistics worker SHA256 {manifest['statistics_worker_sha256']}, "
        f"fixed bootstrap seed 20261026, and private output {manifest['private_recovery_directory']}. "
        "I authorize no retraining, changed masks, new split, favorable-draw selection, "
        "automatic retry or reuse of the first attempt's authorization."
    )


def verify_original_failure() -> None:
    if not ORIGINAL_PRIVATE.is_dir():
        raise ValueError("Original failed attempt directory is missing")
    if set(path.name for path in ORIGINAL_PRIVATE.iterdir()) != set(ORIGINAL_ATTEMPT_HASHES):
        raise ValueError("Original failed attempt files changed")
    if any(sha256(ORIGINAL_PRIVATE / name) != value
           for name, value in ORIGINAL_ATTEMPT_HASHES.items()):
        raise ValueError("Original failed attempt hash changed")
    if sha256(Path("src/dmv_mat_cvd/final_eval_execute.py")) != ORIGINAL_EXECUTOR_SHA256:
        raise ValueError("Original failed executor changed")
    if sha256(Path("FINAL_TEST_EXECUTION_MANIFEST.authorized.json")) != ORIGINAL_AUTHORIZATION_SHA256:
        raise ValueError("Original consumed authorization changed")


def validate_manifest(manifest: dict, registration: dict, *, authorized: bool) -> None:
    expected = {
        "manifest_version": "public-mhas-final-test-recovery-v1",
        "protocol_version": "public-haalsi-mhas-v2",
        "scientific_registration_sha256": REGISTRATION_SHA256,
        "original_failed_attempt_report_sha256": sha256(ORIGINAL_REPORT),
        "original_executor_sha256": ORIGINAL_EXECUTOR_SHA256,
        "original_consumed_authorization_sha256": ORIGINAL_AUTHORIZATION_SHA256,
        "original_attempt_files_sha256": ORIGINAL_ATTEMPT_HASHES,
        "original_attempt_status": "FAILED_AFTER_TEST_ACCESS_NO_PERFORMANCE_RESULTS",
        "failure_disclosure": FAILURE_DISCLOSURE,
        "test_lock_sha256": registration["test_lock_sha256"],
        "private_assignments_sha256": registration["private_assignments_sha256"],
        "model_inventory_sha256": inventory_digest(registration["models"]),
        "model_checkpoint_count": 184,
        "registered_statistics_sha256": registration["evaluator_statistic_code_sha256"],
        "recovery_runtime_sha256": sha256(RUNTIME),
        "recovery_executor_sha256": sha256(Path(__file__)),
        "recovery_worker_sha256": sha256(WORKER),
        "statistics_worker_sha256": sha256(STATS_WORKER),
        "private_recovery_directory": str(RECOVERY_PRIVATE),
        "public_aggregate_output": str(RECOVERY_PUBLIC),
        "intended_recovery_command": INTENDED_COMMAND,
        "recovery_attempt_number": 1,
        "one_time_execution": True,
        "bootstrap_seed": 20261026,
        "bootstrap_replicates": 2000,
        "primary_contrast": registration["primary_contrast"],
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("Recovery manifest does not bind the unchanged science and new code")
    if manifest.get("recovery_execution_authorized") is not authorized:
        raise PermissionError("Separate recovery authorization is absent or inconsistent")
    if authorized:
        if (manifest.get("authorization_source") != "explicit_user_message_in_chatgpt" or
                manifest.get("authorization_scope") != AUTHORIZATION_SCOPE or
                manifest.get("authorization_statement") != recovery_authorization_statement(manifest) or
                not manifest.get("authorization_received_at_utc") or
                manifest.get("execution_status") != "AUTHORIZED_NOT_EXECUTED"):
            raise PermissionError("New exact one-time recovery authorization is unverified")
    elif (manifest.get("authorization_source") is not None or
          manifest.get("authorization_statement") is not None or
          manifest.get("authorization_received_at_utc") is not None or
          manifest.get("execution_status") != "PENDING_NEW_USER_AUTHORIZATION"):
        raise ValueError("Pending recovery manifest falsely claims authorization")


def verify_registration_and_models(registration_path: Path) -> dict:
    if sha256(registration_path) != REGISTRATION_SHA256:
        raise ValueError("Frozen scientific registration changed")
    registration = json.loads(registration_path.read_text())
    if (registration.get("registration_version") != "public-mhas-final-test-evaluation-v1" or
            registration.get("protocol_version") != "public-haalsi-mhas-v2" or
            registration.get("schema_version") != "cvd-public-wave-v2-ten-doctor-report" or
            registration.get("primary_method") != "calibrated_logical" or
            registration.get("primary_budget") != "primary_25_75" or
            registration.get("primary_contrast", {}).get("right") != "full_finetune" or
            registration.get("uncertainty", {}).get("bootstrap_seed") != 20261026 or
            registration.get("uncertainty", {}).get("test_participant_resamples") != 2000 or
            registration.get("model_checkpoint_count") != 184):
        raise ValueError("Frozen scientific identity differs")
    if len(registration["models"]) != 184 or len({(m["budget"], m["method"], m["repetition"])
                                                   for m in registration["models"]}) != 184:
        raise ValueError("Frozen model inventory is incomplete or duplicated")
    if len([m for m in registration["models"] if m["budget"] == "source"]) != 4:
        raise ValueError("Frozen source-only inventory differs")
    for budget in ("primary_25_75", "low_label_10_30"):
        for method in ADAPTED_METHODS:
            if {m["repetition"] for m in registration["models"]
                    if m["budget"] == budget and m["method"] == method} != set(range(10)):
                raise ValueError("Frozen adaptation model/draw inventory differs")
    if inventory_digest(registration["models"]) != (
            'WITHHELD_REFERENCE_BINDING'):
        raise ValueError("Frozen model order or binding changed")
    bindings = [(Path(registration["test_lock_path"]), registration["test_lock_sha256"]),
                (Path(registration["private_assignments_path"]), registration["private_assignments_sha256"]),
                (Path(registration["evaluator_statistic_code"]), registration["evaluator_statistic_code_sha256"]),
                (BASELINE, registration["baseline_run_manifest_sha256"]),
                (SELECTOR / "experiment_registration.json", registration["selector_registration_sha256"]),
                (SELECTOR / "masks.csv", registration["selector_masks_sha256"]),
                (SELECTOR / "module_scores.csv", registration["selector_module_scores_sha256"])]
    bindings.extend((Path(model[name]), model[digest]) for model in registration["models"]
                    for name, digest in (("checkpoint_path", "checkpoint_sha256"),
                                         ("preprocessor_path", "preprocessor_sha256")))
    if any(not path.is_file() or sha256(path) != expected for path, expected in bindings):
        raise ValueError("Frozen lock, assignment, model, preprocessor or statistic hash changed")
    verify_model_record_bindings(registration)
    return registration


def verify_model_record_bindings(registration: dict) -> None:
    baseline_dir = BASELINE.parent
    with (baseline_dir / "development_metrics.csv").open(newline="") as stream:
        baseline = list(csv.DictReader(stream))
    with (SELECTOR / "per_run.csv").open(newline="") as stream:
        selector = list(csv.DictReader(stream))
    with (SELECTOR / "masks.csv").open(newline="") as stream:
        masks = list(csv.DictReader(stream))
    a_map = {(row["budget"], row["method"], None if not row["repetition"] else
              int(float(row["repetition"]))): (row["checkpoint"], row["checkpoint_sha256"])
             for row in baseline}
    b_map = {(row["budget"], row["method"], int(row["repetition"])):
             (row["checkpoint"], row["checkpoint_sha256"]) for row in selector}
    mask_map = {(row["budget"], row["method"], int(row["repetition"])): json.loads(row["mask_json"])
                for row in masks}
    if len(b_map) != len(mask_map) or len(b_map) != len(selector) or len(mask_map) != len(masks) or len(b_map) != 100:
        raise ValueError("Frozen selective rows or masks are incomplete")
    for model in registration["models"]:
        key = (model["budget"], model["method"], model["repetition"])
        table = a_map if model["run"] == baseline_dir.name else b_map if model["run"] == SELECTOR.name else None
        if table is None or key not in table or (
                Path(model["checkpoint_path"]).name, model["checkpoint_sha256"]) != table[key]:
            raise ValueError("Frozen checkpoint/draw binding differs")
        if table is b_map and model.get("mask") != mask_map.get(key):
            raise ValueError("Frozen selective mask binding differs")


def verify_release_evidence(data_root: Path, master_file: Path, questionnaire: Path,
                            registration: dict) -> None:
    evidence = json.loads(EVIDENCE.read_text())
    stable = {k: v for k, v in evidence.items() if k not in {"created_utc", "evidence_digest"}}
    digest = hashlib.sha256(json.dumps(stable, sort_keys=True, allow_nan=False).encode()).hexdigest()
    config = json.loads(CONFIG.read_text())
    if (digest != evidence.get("evidence_digest") or
            evidence.get("protocol_version") != "public-haalsi-mhas-v2" or
            config != evidence.get("configuration") or
            sha256(CONFIG) != registration["scientific_config_sha256"]):
        raise ValueError("Frozen public release/configuration evidence changed")
    source_map = Path(config["source_mapping"])
    target_map = Path(config["target_mapping"])
    source, target = json.loads(source_map.read_text()), json.loads(target_map.read_text())
    paths = {
        "haalsi": data_root / source["files"]["main"],
        "mhas_harmonized": data_root / target["files"]["main"],
        "mhas_biomarker": data_root / target["files"]["biomarker"],
        "mhas_eol": data_root / target["files"]["eol"],
        "mhas_master_2024": master_file,
        "source_mapping": source_map, "target_mapping": target_map,
        "public_config": CONFIG,
        "primary_feature_schema": Path(config["primary_feature_schema_config"]),
        "sensitivity_feature_schema": Path(config["sensitivity_feature_schema_config"]),
        "haalsi_baseline_questionnaire": questionnaire,
    }
    module_dir = Path("src/dmv_mat_cvd")
    paths.update({
        "code_public_v2": module_dir / "data/public_v2.py",
        "code_public_cohorts": module_dir / "data/public_cohorts.py",
        "code_public_reconciliation": module_dir / "data/public_reconciliation.py",
        "code_wave_endpoint": module_dir / "data/wave_endpoint.py",
        "code_real_cohorts": module_dir / "data/real_cohorts.py",
        "code_public_v2_readiness": module_dir / "public_v2_readiness.py",
        "code_public_lock": module_dir / "public_lock.py",
    })
    hashes = evidence.get("file_sha256", {})
    if set(paths) - set(hashes) or any(not path.is_file() or sha256(path) != hashes[name]
                                        for name, path in paths.items()):
        raise ValueError("Dataset, mapping, questionnaire or frozen construction code changed")
    if config.get("expected_input_sha256") is not None and any(
            hashes.get(name) != expected for name, expected in config["expected_input_sha256"].items()):
        raise ValueError("Expected frozen public input hashes differ")
    baseline = json.loads(BASELINE.read_text())
    if (baseline["input_hashes"] != hashes or
            baseline["config_sha256"] != registration["scientific_config_sha256"] or
            baseline["evidence_digest"] != registration["aggregate_evidence_digest"] or
            config["protocol_version"] != registration["protocol_version"]):
        raise ValueError("Frozen baseline input provenance changed")
    selector = json.loads((SELECTOR / "experiment_registration.json").read_text())
    code_paths = {
        "runner_code_sha256": module_dir / "real_baselines.py",
        "preprocessor_code_sha256": module_dir / "data/public_preprocessing.py",
        "development_loader_code_sha256": module_dir / "data/locked_development.py",
    }
    if any(sha256(path) != baseline[key] for key, path in code_paths.items()) or (
            sha256(module_dir / "models/multiview_mlp.py") != selector["model_code_sha256"]):
        raise ValueError("Frozen training/preprocessing/model code changed")


def verify_environment(registration: dict) -> None:
    actual = {"python": platform.python_version(),
              "numpy": importlib.metadata.version("numpy"),
              "pandas": importlib.metadata.version("pandas"),
              "scikit_learn": importlib.metadata.version("scikit-learn"),
              "torch": importlib.metadata.version("torch")}
    if actual != registration["metric_library_versions"] or (
            importlib.metadata.version("xgboost") != "3.4.1"):
        raise ValueError("Frozen software environment changed")


def preflight(registration_path: Path, manifest_path: Path, *, data_root: Path,
              master_file: Path, questionnaire: Path, authorized: bool = False,
              allow_claimed_output: bool = False) -> dict:
    """Read-only hash and governance checks; no test row or feature is parsed."""
    registration = verify_registration_and_models(registration_path)
    verify_original_failure()
    if Path(registration["public_aggregate_output"]).exists():
        raise ValueError("Original failed attempt unexpectedly produced a public result")
    manifest = json.loads(manifest_path.read_text())
    validate_manifest(manifest, registration, authorized=authorized)
    verify_environment(registration)
    verify_release_evidence(data_root, master_file, questionnaire, registration)
    if RECOVERY_PRIVATE == ORIGINAL_PRIVATE or RECOVERY_PRIVATE != Path(manifest["private_recovery_directory"]):
        raise ValueError("Recovery destination collides with the failed attempt")
    if (not allow_claimed_output and RECOVERY_PRIVATE.exists()) or RECOVERY_PUBLIC.parent.exists():
        raise FileExistsError("Recovery private/public output already exists or is partial")
    if allow_claimed_output and not RECOVERY_PRIVATE.is_dir():
        raise ValueError("Exclusive recovery claim disappeared")
    return {"status": "RECOVERY_PREFLIGHT_VALID_AUTHORIZATION_PENDING" if not authorized
            else "RECOVERY_PREFLIGHT_VALID_AUTHORIZED",
            "registration_sha256": REGISTRATION_SHA256,
            "model_bindings_verified": len(registration["models"]),
            "failed_original_attempt_preserved": True,
            "release_and_mapping_hashes_verified": True,
            "new_authorization_present": authorized,
            "test_rows_read": False,
            "recovery_output_absent": not allow_claimed_output}


def claim_recovery_private(output: Path, *, approved_root: Path = RECOVERY_PRIVATE,
                           allowed_data_root: Path = Path('WITHHELD_PRIVATE_PATH')) -> None:
    """Atomic exclusive ownership; a partial directory permanently bars retry."""
    if output != approved_root or output == ORIGINAL_PRIVATE:
        raise ValueError("Recovery output is not the separately approved destination")
    if output.parent.is_symlink() or not output.parent.resolve().is_relative_to(
            allowed_data_root.resolve()):
        raise ValueError("Recovery private parent is unsafe")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.mkdir(output, 0o700)
    private_json_exclusive(output / "attempt.private.json", {
        "status": "CLAIMED_BEFORE_RECOVERY_TEST_ACCESS",
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "registration_sha256": REGISTRATION_SHA256,
        "original_attempt_preserved": True})


def write_feature_payload(frame, path: Path) -> str:
    """Write only ten approved predictors, in fixed row order, to private IPC."""
    import numpy as np
    import pandas as pd
    if not frame.columns.is_unique or set(frame.columns) != set(FEATURE_ORDER):
        raise ValueError("Private IPC requires exactly ten frozen predictors")
    arrays = {}
    for name in FEATURE_ORDER:
        values = frame[name].to_numpy()
        missing = pd.isna(values)
        if name in CONTINUOUS:
            numeric = pd.to_numeric(frame[name], errors="raise").to_numpy(dtype=np.float64)
            arrays[f"feature_{name}"] = numeric
        else:
            canonical = np.asarray(["" if absent else str(value)
                                    for value, absent in zip(values, missing)], dtype=str)
            arrays[f"feature_{name}"] = canonical
        arrays[f"missing_{name}"] = np.asarray(missing, dtype=np.bool_)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        np.savez_compressed(stream, **arrays)
    return sha256(path)


def run_bounded_process(command: list[str], *, timeout_seconds: int,
                        environment: Mapping[str, str] | None = None) -> dict:
    """Start a fresh interpreter; terminate its whole process group on timeout."""
    env = dict(os.environ if environment is None else environment)
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                 "VECLIB_MAXIMUM_THREADS"):
        env[name] = "1"
    env["KMP_DUPLICATE_LIB_OK"] = "FALSE"
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True,
                               start_new_session=True)
    try:
        stdout, _stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=5)
        raise TimeoutError("Isolated recovery process exceeded its fixed watchdog")
    except BaseException:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
        raise
    if process.returncode != 0:
        # Never echo native stderr: it may contain paths or participant data.
        raise RuntimeError(f"Isolated recovery process failed with exit status {process.returncode}")
    lines = stdout.splitlines()
    if len(lines) != 1:
        raise ValueError("Isolated recovery worker returned ambiguous progress output")
    try:
        result = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ValueError("Isolated recovery worker returned non-JSON status") from exc
    if result.get("status") != "COMPLETE":
        raise ValueError("Isolated recovery worker did not report completion")
    return result


def run_frozen_workers(registration_path: Path, feature_path: Path, feature_sha256: str,
                       private_dir: Path, *, worker_timeout_seconds: int = 90,
                       process_runner=run_bounded_process) -> dict[int, object]:
    """Return one aligned probability vector per registered model index."""
    import numpy as np
    registration = json.loads(registration_path.read_text())
    output_by_index = {}
    for group in ("tabular", "torch"):
        output = private_dir / f"{group}_predictions.private.npz"
        command = [sys.executable, "-m", "dmv_mat_cvd.final_eval_recovery_worker",
                   "--family-group", group, "--registration", str(registration_path),
                   "--registration-sha256", REGISTRATION_SHA256,
                   "--features", str(feature_path), "--features-sha256", feature_sha256,
                   "--baseline-manifest", str(BASELINE), "--output", str(output)]
        status = process_runner(command, timeout_seconds=worker_timeout_seconds)
        if (status.get("family_group") != group or
                status.get("models_completed") != FAMILY_COUNTS[group] or
                status.get("feature_sha256") != feature_sha256):
            raise ValueError("Isolated family count or feature binding changed")
        loaded = status.get("native_stacks_loaded")
        expected_loaded = {"torch": group == "torch", "sklearn": group == "tabular",
                           "xgboost": group == "tabular"}
        if loaded != expected_loaded:
            raise ValueError("Isolated worker loaded an incompatible native model family")
        if not output.is_file() or output.stat().st_mode & 0o077:
            raise ValueError("Isolated prediction file missing or insufficiently private")
        with np.load(output, allow_pickle=False) as saved:
            if set(saved.files) != {"model_indices", "probabilities", "feature_sha256"} or (
                    str(saved["feature_sha256"]) != feature_sha256):
                raise ValueError("Worker output lacks exact input binding")
            indices, values = saved["model_indices"], saved["probabilities"]
            if (indices.shape != (FAMILY_COUNTS[group],) or
                    values.shape != (FAMILY_COUNTS[group],
                                     registration["test_integrity_metadata_only"]["participants"]) or
                    not np.isfinite(values).all() or ((values < 0) | (values > 1)).any()):
                raise ValueError("Worker predictions have wrong size or range")
            expected = [i for i, entry in enumerate(registration["models"])
                        if (entry["model_family"] in {"flat_mlp", "five_view_net"}) == (group == "torch")]
            if list(indices) != expected:
                raise ValueError("Worker model indices are missing, duplicate or out of order")
            for index, value in zip(indices, values):
                if int(index) in output_by_index:
                    raise ValueError("Model predicted by multiple isolated workers")
                output_by_index[int(index)] = value.copy()
    if set(output_by_index) != set(range(184)):
        raise ValueError("At least one frozen model prediction is missing")
    return output_by_index


def assemble_registered_matrices(registration: dict, predictions: dict[int, object],
                                 expected_participants: int) -> dict:
    """Assemble the exact frozen budget/method/draw inventory in input row order."""
    import numpy as np
    if set(predictions) != set(range(184)):
        raise ValueError("Missing or extra registered prediction")
    by_key = {}
    for index, entry in enumerate(registration["models"]):
        key = (entry["budget"], entry["method"], entry["repetition"])
        values = np.asarray(predictions[index], dtype=float)
        if key in by_key or values.shape != (expected_participants,) or (
                not np.isfinite(values).all() or ((values < 0) | (values > 1)).any()):
            raise ValueError("Duplicate, misaligned or invalid registered prediction")
        by_key[key] = values
    source = {method: by_key[("source", method, None)][None, :] for method in SOURCE_METHODS}
    result = {}
    for budget, details in registration["budgets"].items():
        if details["draws"] != 10:
            raise ValueError("Frozen adaptation draw count changed")
        result[budget] = {**source, **{method: np.stack([
            by_key[(budget, method, repetition)] for repetition in range(10)])
            for method in ADAPTED_METHODS}}
    return result


def write_private_bundle(path: Path, labels, matrices: dict) -> str:
    import numpy as np
    arrays = {"observed_labels": np.asarray(labels, dtype=np.int8)}
    arrays.update({f"{budget}__{method}": values for budget, methods in matrices.items()
                   for method, values in methods.items()})
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        np.savez_compressed(stream, **arrays)
    return sha256(path)


def run_frozen_statistics(registration_path: Path, bundle_path: Path, bundle_sha256: str,
                          private_dir: Path, *, process_runner=run_bounded_process,
                          synthetic_replicates: int | None = None) -> dict:
    metrics = private_dir / "metrics.private.json"
    payload = private_dir / "aggregate_payload.private.json"
    registration_hash = REGISTRATION_SHA256
    if synthetic_replicates is not None:
        fixture_registration = json.loads(registration_path.read_text())
        if fixture_registration.get("registration_version") == "public-mhas-final-test-evaluation-v1":
            raise ValueError("Frozen registration cannot use synthetic bootstrap override")
        registration_hash = sha256(registration_path)
    command = [sys.executable, "-m", "dmv_mat_cvd.final_eval_recovery_stats_worker",
               "--registration", str(registration_path),
               "--registration-sha256", registration_hash,
               "--bundle", str(bundle_path), "--bundle-sha256", bundle_sha256,
               "--private-metrics", str(metrics),
               "--private-public-payload", str(payload)]
    if synthetic_replicates is not None:
        command.extend(("--synthetic-replicates", str(synthetic_replicates)))
    status = process_runner(command, timeout_seconds=3600)
    if status.get("native_stacks_loaded") != {"torch": False, "sklearn": True,
                                               "xgboost": False}:
        raise ValueError("Statistics process loaded an incompatible native model family")
    if not metrics.is_file() or not payload.is_file() or any(
            path.stat().st_mode & 0o077 for path in (metrics, payload)):
        raise ValueError("Private registered statistics were not securely completed")
    if status.get("participants") != 283 or status.get("positive_reports") != 21:
        raise ValueError("Frozen test aggregate count changed during statistics")
    return {"private_metrics_sha256": sha256(metrics),
            "aggregate_payload_sha256": sha256(payload)}


def load_locked_test_after_recovery_claim(registration: dict, *, data_root: Path,
                                          master_file: Path):
    """The sole real test-row loader; never called from preparation."""
    import numpy as np
    from .data.locked_development import load_mhas_locked_development
    from .data.public_v2 import VIEWS_TEN, construct_mhas_v2

    assignments = json.loads(Path(registration["private_assignments_path"]).read_text())
    lock = json.loads(Path(registration["test_lock_path"]).read_text())
    parts = assignments["target_partitions"]
    test_ids = set(parts["target_test"])
    others = set(parts["target_validation"]) | set(parts["target_adaptation_pool"])
    source_ids = set().union(*(set(x) for x in assignments["source_partitions"].values()))
    if (test_ids & others or test_ids & source_ids or len(test_ids) != len(parts["target_test"]) or
            set(parts) != {"target_test", "target_validation", "target_adaptation_pool"} or
            len(test_ids) != registration["test_integrity_metadata_only"]["participants"]):
        raise ValueError("Private target-test assignment is nonunique, overlapping or incomplete")
    config = json.loads(CONFIG.read_text())
    mapping = json.loads(Path(config["target_mapping"]).read_text())
    raw, loading = load_mhas_locked_development(data_root, master_file, mapping, test_ids, others)
    cohort = construct_mhas_v2(raw, mapping, loading["labels"])
    frame = cohort.canonical
    if (set(frame.participant_id) != test_ids or frame.participant_id.duplicated().any() or
            len(frame) != lock["partition_counts"]["target_test"]["n"] or
            int(frame.label.sum()) != lock["partition_counts"]["target_test"]["events"] or
            cohort.report["schema_version"] != registration["schema_version"] or
            cohort.report["diagnostics"]["landmark"]["window_days"] != 30):
        raise ValueError("Canonical locked test differs from approved count, endpoint or landmark")
    ordered = frame.sort_values("participant_id").reset_index(drop=True)
    expected = {name for fields in VIEWS_TEN.values() for name in fields}
    if set(ordered.columns) != expected | {"participant_id", "endpoint_status", "label"}:
        raise ValueError("Metadata or future field entered final test predictors")
    ids = tuple(ordered.participant_id)
    labels = ordered.label.to_numpy(dtype=np.int8)
    return ids, ordered.loc[:, list(FEATURE_ORDER)].copy(), labels


def persist_recovery(private_dir: Path, public_output: Path, *,
                     registration: dict, manifest_sha256: str, ids: tuple[str, ...],
                     labels, worker_outputs: dict, statistic_hashes: dict,
                     registration_sha256: str = REGISTRATION_SHA256) -> dict:
    if public_output.parent.exists() or not (private_dir / "attempt.private.json").is_file():
        raise FileExistsError("Recovery output already exists or exclusive claim is missing")
    if len(ids) != len(set(ids)) or len(ids) != 283 or int(labels.sum()) != 21:
        raise ValueError("Frozen test participant or event integrity differs")
    saved_ids = json.loads((private_dir / "participant_ids.private.json").read_text())
    if tuple(saved_ids.get("ordered_participant_ids", ())) != ids:
        raise ValueError("Private participant ordering changed before reporting")
    payload = json.loads((private_dir / "aggregate_payload.private.json").read_text())
    if (set(payload) != {"status", "protocol_version", "registration_sha256",
                         "participant_count", "positive_reports", "metrics"} or
            payload["status"] != "COMPLETE_AGGREGATE_ONLY" or
            payload["protocol_version"] != registration["protocol_version"] or
            payload["registration_sha256"] != registration_sha256 or
            payload["participant_count"] != len(ids) or
            payload["positive_reports"] != int(labels.sum()) or
            set(payload["metrics"]) != set(registration["budgets"])):
        raise ValueError("Private aggregate payload differs from frozen reporting contract")
    record = {
        "status": "RECOVERY_COMPLETE_AFTER_FAILED_ORIGINAL_ATTEMPT",
        "registration_sha256": registration_sha256,
        "execution_manifest_sha256": manifest_sha256,
        "original_failed_attempt_preserved": True,
        "test_participants": len(ids), "test_positive_reports": int(labels.sum()),
        "model_predictions": len(registration["models"]),
        "bootstrap_seed": 20261026, "bootstrap_replicates": 2000,
        "private_feature_sha256": sha256(private_dir / "features.private.npz"),
        "private_prediction_bundle_sha256": sha256(private_dir / "prediction_bundle.private.npz"),
        "private_ids_sha256": sha256(private_dir / "participant_ids.private.json"),
        "worker_outputs": worker_outputs, **statistic_hashes,
        "no_fitting_performed": True,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
    }
    private_json_exclusive(private_dir / "evaluation_manifest.private.json", record)
    public_output.parent.mkdir(parents=True, exist_ok=False)
    private_json_exclusive(public_output, payload)
    return record


def execute_one_recovery(registration_path: Path, manifest_path: Path, *,
                         data_root: Path, master_file: Path, questionnaire: Path) -> dict:
    """One authorized claim only. A failed or interrupted claim forbids retry."""
    preflight(registration_path, manifest_path, data_root=data_root, master_file=master_file,
              questionnaire=questionnaire, authorized=True)
    manifest_sha = sha256(manifest_path)
    claim_recovery_private(RECOVERY_PRIVATE)
    old_umask = os.umask(0o077)
    try:
        if sha256(manifest_path) != manifest_sha:
            raise ValueError("Recovery authorization changed after exclusive claim")
        preflight(registration_path, manifest_path, data_root=data_root, master_file=master_file,
                  questionnaire=questionnaire, authorized=True, allow_claimed_output=True)
        registration = json.loads(registration_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        private_json_exclusive(RECOVERY_PRIVATE / "authorization.private.json", {
            "manifest_sha256": manifest_sha, "manifest": manifest,
            "registration_sha256": REGISTRATION_SHA256,
            "recovery_executor_sha256": sha256(Path(__file__))})
        ids, predictors, labels = load_locked_test_after_recovery_claim(
            registration, data_root=data_root, master_file=master_file)
        private_json_exclusive(RECOVERY_PRIVATE / "participant_ids.private.json",
                               {"ordered_participant_ids": ids})
        features = RECOVERY_PRIVATE / "features.private.npz"
        feature_sha = write_feature_payload(predictors, features)
        by_index = run_frozen_workers(registration_path, features, feature_sha, RECOVERY_PRIVATE)
        matrices = assemble_registered_matrices(registration, by_index, len(ids))
        bundle = RECOVERY_PRIVATE / "prediction_bundle.private.npz"
        bundle_sha = write_private_bundle(bundle, labels, matrices)
        statistic_hashes = run_frozen_statistics(registration_path, bundle, bundle_sha,
                                                 RECOVERY_PRIVATE)
        worker_outputs = {group: sha256(RECOVERY_PRIVATE / f"{group}_predictions.private.npz")
                          for group in ("torch", "tabular")}
        persist_recovery(RECOVERY_PRIVATE, RECOVERY_PUBLIC, registration=registration,
                         manifest_sha256=manifest_sha, ids=ids, labels=labels,
                         worker_outputs=worker_outputs, statistic_hashes=statistic_hashes)
        return {"status": "RECOVERY_COMPLETE", "private_output": str(RECOVERY_PRIVATE),
                "public_aggregate_output": str(RECOVERY_PUBLIC),
                "models_evaluated": 184, "test_participants": len(ids),
                "test_positive_reports": int(labels.sum())}
    except BaseException as exc:
        if not (RECOVERY_PRIVATE / "failure.private.json").exists():
            private_json_exclusive(RECOVERY_PRIVATE / "failure.private.json", {
                "status": "FAILED_NO_AUTOMATIC_RETRY",
                "exception_type": type(exc).__name__,
                "time_utc": datetime.now(timezone.utc).isoformat()})
        raise
    finally:
        os.umask(old_umask)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true", help="Hash-only; no target-test rows")
    mode.add_argument("--prepare-authorized", action="store_true",
                      help="Read-only hash and exact new authorization check")
    mode.add_argument("--execute-real-recovery", action="store_true",
                      help="Requires a NEW exact one-time recovery authorization")
    parser.add_argument("--registration", type=Path, default=REGISTRATION)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--master-file", type=Path, required=True)
    parser.add_argument("--questionnaire", type=Path, required=True)
    args = parser.parse_args()
    common = {"data_root": args.data_root, "master_file": args.master_file,
              "questionnaire": args.questionnaire}
    if args.prepare or args.prepare_authorized:
        print(json.dumps(preflight(args.registration, args.execution_manifest,
                                   authorized=args.prepare_authorized, **common), indent=2))
    else:
        print(json.dumps(execute_one_recovery(args.registration, args.execution_manifest,
                                              **common), indent=2))


if __name__ == "__main__":
    main()
