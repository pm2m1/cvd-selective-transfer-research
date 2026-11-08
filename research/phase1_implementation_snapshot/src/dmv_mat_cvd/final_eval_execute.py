"""Fail-closed, one-time final evaluation. Import and preparation never read test rows.

The real path requires a separate execution manifest and an explicit CLI flag.
It has no fitting, optimizer, module-selection, split or calibration operation.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
from typing import Mapping

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost  # load native XGBoost before torch on this frozen macOS environment
from xgboost import XGBClassifier
import torch
from sklearn.linear_model import LogisticRegression

from .data.locked_development import load_mhas_locked_development
from .data.public_preprocessing import CATEGORIES, CONTINUOUS, PublicPreprocessor
from .data.public_v2 import VIEWS_TEN, construct_mhas_v2
from .data.releases import file_sha256
from .experiments.baselines import FlatMLP
from .final_eval_preflight import verify_pretest_registration
from .final_eval_stats import fixed_reliability_bins, paired_participant_bootstrap
from .models.multiview_mlp import MultiViewRiskNet
from .public_lock import _verified_evidence
from .real_baselines import CONFIG, EVIDENCE


REGISTRATION_SHA256 = 'WITHHELD_PRIVATE_BINDING'
REGISTRATION_PATH = Path("FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json")
PRIVATE_OUTPUT = Path('WITHHELD_PRIVATE_PATH')
PUBLIC_OUTPUT = Path("results/real_training/m6c_final_test_v1/aggregate_only_results.json")
AUTHORIZATION_SCOPE = "one final MHAS target-test evaluation under frozen public-haalsi-mhas-v2 registration"
AUTHORIZATION_STATEMENT = (
    'I explicitly authorize exactly one final evaluation of the immutable MHAS target test for `public-haalsi-mhas-v2` under `FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json` (SHA256 `WITHHELD_PRIVATE_BINDING`), using only its 184 frozen checkpoint bindings, bootstrap seed `20261026`, and private output directory `WITHHELD_PRIVATE_PATH`. I authorize no retraining, preprocessing fit, changed masks, new split, favorable-draw selection or repeated test evaluation.'
)


def inventory_digest(models: list[dict]) -> str:
    """Bind each model's exact path, hash, preprocessing and draw/mask identity."""
    return hashlib.sha256(json.dumps(models, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _json_private(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def _safe_error(exc: Exception) -> dict:
    # Exception messages may include participant identifiers or raw values.
    return {"status": "FAILED_NO_AUTOMATIC_RETRY", "exception_type": type(exc).__name__,
            "time_utc": datetime.now(timezone.utc).isoformat()}


def verify_registration_hash(path: Path, expected: str = REGISTRATION_SHA256) -> None:
    if file_sha256(path) != expected:
        raise ValueError("Frozen evaluation registration SHA256 changed")


def verify_input_bindings(registration: dict) -> None:
    """Generic hash gate, independently fixture-testable without any cohort read."""
    paths = [(registration["test_lock_path"], registration["test_lock_sha256"]),
             (registration["private_assignments_path"], registration["private_assignments_sha256"]),
             (registration["evaluator_statistic_code"], registration["evaluator_statistic_code_sha256"])]
    paths.extend((m[key], m[digest]) for m in registration["models"] for key, digest in (
        ("checkpoint_path", "checkpoint_sha256"),
        ("preprocessor_path", "preprocessor_sha256")))
    for path, expected in paths:
        if file_sha256(Path(path)) != expected:
            raise ValueError("Frozen lock, assignment, model, preprocessor or statistic code changed")


def claim_private_run(output: Path, *, approved_root: Path = PRIVATE_OUTPUT,
                      allowed_data_root: Path = Path('WITHHELD_PRIVATE_PATH')) -> None:
    """Atomic exclusive ownership. Any partial directory permanently blocks retry."""
    if output != approved_root:
        raise ValueError("Private evaluation destination differs from frozen registration")
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.parent.is_symlink() or not output.parent.resolve().is_relative_to(
            allowed_data_root.resolve()):
        raise ValueError("Private output parent is unsafe")
    os.mkdir(output, 0o700)  # one process succeeds; an existing or partial run fails
    _json_private(output / "attempt.private.json", {
        "status": "CLAIMED_BEFORE_TEST_ACCESS", "time_utc": datetime.now(timezone.utc).isoformat(),
        "registration_sha256": REGISTRATION_SHA256})


def validate_execution_manifest(manifest: dict, registration: dict, *,
                                authorized: bool) -> None:
    expected = {
        "manifest_version": "public-mhas-test-execution-v1",
        "protocol_version": "public-haalsi-mhas-v2",
        "registration_sha256": REGISTRATION_SHA256,
        "executor_sha256": file_sha256(Path(__file__)),
        "statistics_code_sha256": registration["evaluator_statistic_code_sha256"],
        "test_lock_sha256": registration["test_lock_sha256"],
        "private_assignments_sha256": registration["private_assignments_sha256"],
        "model_inventory_sha256": inventory_digest(registration["models"]),
        "model_checkpoint_count": 184,
        "primary_contrast": registration["primary_contrast"],
        "bootstrap_seed": 20261026,
        "bootstrap_replicates": 2000,
        "xgboost_version": xgboost.__version__,
        "private_output_directory": str(PRIVATE_OUTPUT),
        "one_time_execution": True,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("Execution manifest does not bind the frozen scientific inputs/code")
    if manifest.get("evaluation_execution_authorized") is not authorized:
        raise PermissionError("Separate final-test evaluation authorization is absent or inconsistent")
    if authorized:
        if (manifest.get("authorization_source") != "explicit_user_message_in_chatgpt" or
                manifest.get("authorization_scope") != AUTHORIZATION_SCOPE or
                manifest.get("authorization_statement") != AUTHORIZATION_STATEMENT or
                not manifest.get("authorization_received_at_utc") or
                manifest.get("execution_status") != "AUTHORIZED_NOT_EXECUTED"):
            raise PermissionError("Exact separate one-time evaluation authorization is unverified")
    elif (manifest.get("authorization_source") is not None or
          manifest.get("authorization_statement") is not None or
          manifest.get("execution_status") != "PENDING_USER_AUTHORIZATION"):
        raise ValueError("Pending manifest contains unsupported authorization claims")


def _verify_model_record_bindings(registration: dict) -> None:
    """Cross-check registry mapping against both frozen run tables and masks."""
    a = Path("results/real_training/m6a_20261025_dev_baselines_v4")
    b = Path("results/real_training/m6b_20261025_selector_v1")
    with (a / "development_metrics.csv").open(newline="") as stream:
        a_rows = list(csv.DictReader(stream))
    with (b / "per_run.csv").open(newline="") as stream:
        b_rows = list(csv.DictReader(stream))
    with (b / "masks.csv").open(newline="") as stream:
        masks = list(csv.DictReader(stream))
    mask_map = {(r["budget"], r["method"], int(r["repetition"])): json.loads(r["mask_json"])
                for r in masks}
    if len(mask_map) != 100 or len(masks) != 100:
        raise ValueError("Frozen 6B mask inventory is incomplete or duplicate")
    a_map = {(r["budget"], r["method"], None if not r["repetition"] else int(float(r["repetition"]))):
             (r["checkpoint"], r["checkpoint_sha256"]) for r in a_rows}
    b_map = {(r["budget"], r["method"], int(r["repetition"])):
             (r["checkpoint"], r["checkpoint_sha256"]) for r in b_rows}
    if len(b_map) != 100 or len(b_rows) != 100:
        raise ValueError("Frozen 6B checkpoint table is incomplete or duplicate")
    for model in registration["models"]:
        key = (model["budget"], model["method"], model["repetition"])
        rows = a_map if model["run"] == a.name else b_map if model["run"] == b.name else None
        if rows is None or key not in rows or (
                Path(model["checkpoint_path"]).name, model["checkpoint_sha256"]) != rows[key]:
            raise ValueError("Registered checkpoint does not correspond to frozen method/draw")
        if rows is b_map and model.get("mask") != mask_map.get(key):
            raise ValueError("Registered selective mask differs from frozen mask table")
    if len([x for x in registration["models"] if x["run"] == a.name]) != 84:
        raise ValueError("6A model inventory differs from frozen 84 checkpoints")


def prepare(registration_path: Path, manifest_path: Path, *, data_root: Path,
            master_file: Path, questionnaire: Path, authorized: bool = False) -> dict:
    """Hash/code/configuration preflight only. No assignment parsing or test data."""
    verify_registration_hash(registration_path)
    checked = verify_pretest_registration(registration_path)
    registration = json.loads(registration_path.read_text())
    verify_input_bindings(registration)
    manifest = json.loads(manifest_path.read_text())
    validate_execution_manifest(manifest, registration, authorized=authorized)
    _verify_model_record_bindings(registration)
    if PRIVATE_OUTPUT != Path(registration["private_output"]["directory"]) or PUBLIC_OUTPUT != Path(
            registration["public_aggregate_output"]):
        raise ValueError("Registered output paths changed")
    actual_versions = {"python": platform.python_version(), "numpy": np.__version__,
                       "scikit_learn": sklearn.__version__, "torch": torch.__version__,
                       "pandas": pd.__version__}
    if actual_versions != registration["metric_library_versions"]:
        raise ValueError("Final evaluation software environment differs from frozen registration")
    if PUBLIC_OUTPUT.parent.exists():
        raise FileExistsError("Public aggregate evaluation directory already exists or is partial")
    baseline = json.loads(Path("results/real_training/m6a_20261025_dev_baselines_v4/run_manifest.json").read_text())
    evidence = json.loads(EVIDENCE.read_text())
    config = _verified_evidence(evidence, CONFIG, data_root, master_file, questionnaire)
    if (file_sha256(CONFIG) != registration["scientific_config_sha256"] or
            baseline["input_hashes"] != evidence["file_sha256"] or
            baseline["config_sha256"] != registration["scientific_config_sha256"] or
            baseline["evidence_digest"] != registration["aggregate_evidence_digest"] or
            config["protocol_version"] != registration["protocol_version"]):
        raise ValueError("Source/target dataset or public configuration binding changed")
    selector = json.loads(Path("results/real_training/m6b_20261025_selector_v1/experiment_registration.json").read_text())
    code_paths = {
        "runner_code_sha256": Path("src/dmv_mat_cvd/real_baselines.py"),
        "preprocessor_code_sha256": Path("src/dmv_mat_cvd/data/public_preprocessing.py"),
        "development_loader_code_sha256": Path("src/dmv_mat_cvd/data/locked_development.py"),
    }
    if any(file_sha256(path) != baseline[key] for key, path in code_paths.items()):
        raise ValueError("Frozen baseline loader/preprocessor code changed")
    if file_sha256(Path("src/dmv_mat_cvd/models/multiview_mlp.py")) != selector["model_code_sha256"]:
        raise ValueError("Frozen five-view model code changed")
    return {**checked, "dataset_configuration_hashes_verified": True,
            "execution_manifest_authorized": authorized, "test_features_or_labels_read": False}


def frozen_preprocessor(path: Path, expected_sha256: str, dimensions: dict) -> PublicPreprocessor:
    if file_sha256(path) != expected_sha256:
        raise ValueError("Fitted preprocessor changed")
    saved = json.loads(path.read_text())
    if (saved.get("schema_version") != "cvd-public-wave-v2-ten-doctor-report" or
            saved.get("fit_role") not in {"source_train", "target_adaptation"} or
            saved.get("views") != {k: list(v) for k, v in VIEWS_TEN.items()} or
            saved.get("categories") != {k: list(v) + ["unknown"] for k, v in CATEGORIES.items()} or
            set(saved.get("continuous", {})) != set(CONTINUOUS)):
        raise ValueError("Frozen feature schema or preprocessing provenance changed")
    if any(not all(np.isfinite(stats[key]) for key in ("median", "mean", "scale")) or
           stats["scale"] <= 0 for stats in saved["continuous"].values()):
        raise ValueError("Frozen continuous transformation is invalid")
    pp = PublicPreprocessor()
    pp.state = {k: v for k, v in saved.items() if k != "encoded_columns"}
    if pp.encoded_columns != saved.get("encoded_columns") or pp.view_dims != dimensions:
        raise ValueError("Frozen encoded order/dimensions differ")
    return pp


def encode_frozen_features(frame: pd.DataFrame, pp: PublicPreprocessor) -> dict[str, np.ndarray]:
    """Inference-only allowlist transform. Labels and IDs cannot enter tensors."""
    expected = {name for fields in VIEWS_TEN.values() for name in fields}
    if not frame.columns.is_unique or set(frame.columns) != expected or pp.state is None:
        raise ValueError("Test inference requires exactly ten approved predictor columns")
    encoded: dict[str, np.ndarray] = {}
    for name in CONTINUOUS:
        values = pd.to_numeric(frame[name], errors="raise").to_numpy(dtype=float)
        if np.isinf(values).any():
            raise ValueError("Infinite predictor value")
        stats = pp.state["continuous"][name]
        encoded[name] = ((np.where(np.isnan(values), stats["median"], values) -
                          stats["mean"]) / stats["scale"])[:, None]
    for name, categories in pp.state["categories"].items():
        if not frame[name].dropna().isin(CATEGORIES[name]).all():
            raise ValueError("Unmapped test category")
        values = frame[name].fillna("unknown").to_numpy()
        encoded[name] = np.column_stack([values == value for value in categories])
    views = {view: np.concatenate([encoded[name] for name in fields], axis=1).astype(np.float32)
             for view, fields in VIEWS_TEN.items()}
    if any(not np.isfinite(value).all() for value in views.values()):
        raise ValueError("Nonfinite encoded predictor")
    return views


def infer_frozen(entry: dict, frame: pd.DataFrame, dimensions: dict) -> np.ndarray:
    """Predict only; strict checkpoint load, model family and probability checks."""
    path = Path(entry["checkpoint_path"])
    if file_sha256(path) != entry["checkpoint_sha256"]:
        raise ValueError("Frozen model checkpoint changed")
    pp = frozen_preprocessor(Path(entry["preprocessor_path"]), entry["preprocessor_sha256"], dimensions)
    if ((entry["method"].startswith("source_") or entry["method"] in {
            "head_only", "full_finetune", "fixed_mask", "random_calibrated_logical",
            "legacy_topk", "calibrated_threshold", "calibrated_logical"}) and
            pp.state["fit_role"] != "source_train"):
        raise ValueError("Transfer/source model is bound to target-fitted preprocessing")
    if entry["method"].startswith("target_") and pp.state["fit_role"] != "target_adaptation":
        raise ValueError("Target-only model is bound to wrong fitted preprocessing")
    views = encode_frozen_features(frame, pp)
    family = entry["model_family"]
    if family in {"sklearn_logistic", "xgboost"}:
        model = joblib.load(path)
        if family == "sklearn_logistic" and not isinstance(model, LogisticRegression):
            raise ValueError("Checkpoint is not the declared logistic model")
        if family == "xgboost":
            if not isinstance(model, XGBClassifier):
                raise ValueError("Checkpoint is not the declared XGBoost model")
        flat = np.concatenate([views[name] for name in VIEWS_TEN], axis=1)
        probabilities = np.asarray(model.predict_proba(flat))
        if probabilities.shape != (len(frame), 2) or list(model.classes_) != [0, 1]:
            raise ValueError("Frozen tabular model class order/output changed")
        output = probabilities[:, 1]
    elif family in {"flat_mlp", "five_view_net"}:
        model = FlatMLP(dimensions) if family == "flat_mlp" else MultiViewRiskNet(dimensions, 16)
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True), strict=True)
        model.eval()
        with torch.no_grad():
            output = torch.sigmoid(model({k: torch.from_numpy(v) for k, v in views.items()})).numpy()
    else:
        raise ValueError("Unregistered model family")
    output = np.asarray(output, dtype=float)
    if output.shape != (len(frame),) or not np.isfinite(output).all() or (
            (output < 0) | (output > 1)).any():
        raise ValueError("Frozen model returned invalid probabilities")
    return output


def aligned_prediction(ids: tuple[str, ...], expected_ids: tuple[str, ...],
                       probabilities: np.ndarray) -> np.ndarray:
    if (len(ids) != len(set(ids)) or ids != expected_ids or
            len(expected_ids) != len(set(expected_ids))):
        raise ValueError("Missing, duplicate or misordered participant predictions")
    values = np.asarray(probabilities, dtype=float)
    if values.shape != (len(expected_ids),) or not np.isfinite(values).all() or (
            (values < 0) | (values > 1)).any():
        raise ValueError("Missing or invalid probability for a test participant")
    return values


def assemble_prediction_matrices(registration: dict, expected_ids: tuple[str, ...],
                                 records: Mapping[tuple[str, str, int | None],
                                                  tuple[tuple[str, ...], np.ndarray]]) -> dict[str, dict[str, np.ndarray]]:
    """No row-position joins: every model must predict the identical ordered IDs."""
    keys = {(m["budget"], m["method"], m["repetition"]) for m in registration["models"]}
    if len(keys) != len(registration["models"]) or set(records) != keys:
        raise ValueError("Missing, duplicate or unregistered model predictions")
    aligned = {key: aligned_prediction(records[key][0], expected_ids, records[key][1]) for key in keys}
    source = {m["method"]: aligned[("source", m["method"], None)][None, :]
              for m in registration["models"] if m["budget"] == "source"}
    out = {}
    for budget, details in registration["budgets"].items():
        count = details["draws"]
        methods = {m["method"] for m in registration["models"] if m["budget"] == budget}
        if count != 10 or len(methods) != 9:
            raise ValueError("Frozen final method/draw inventory differs")
        out[budget] = {**source, **{method: np.stack([aligned[(budget, method, repetition)]
                              for repetition in range(count)]) for method in methods}}
    return out


def evaluate_aligned_bundle(registration: dict, labels: np.ndarray,
                            matrices: dict[str, dict[str, np.ndarray]], *,
                            replicates: int | None = None) -> dict:
    """Pure registered statistics. A lower replicate count is synthetic-test only."""
    if set(matrices) != set(registration["budgets"]):
        raise ValueError("Both registered label budgets are required")
    seed = registration["uncertainty"]["bootstrap_seed"]
    actual_replicates = registration["uncertainty"]["test_participant_resamples"]
    if replicates is not None:
        if registration.get("registration_version") == "public-mhas-final-test-evaluation-v1":
            raise ValueError("Real frozen registration cannot change bootstrap replicates")
        actual_replicates = replicates
    contrasts = [("calibrated_logical", "full_finetune"),
                 ("calibrated_logical", "head_only"),
                 ("calibrated_logical", "random_calibrated_logical"),
                 ("calibrated_logical", "source_multiview")]
    outcome = {}
    for budget in registration["budgets"]:
        predictions = matrices[budget]
        if any(a not in predictions or b not in predictions for a, b in contrasts):
            raise ValueError("Registered primary/secondary comparator missing")
        statistics = paired_participant_bootstrap(labels, predictions, contrasts,
                                                  seed=seed, replicates=actual_replicates)
        statistics["calibration_exploratory"] = {
            name: {"mean_predicted_by_draw": [float(x) for x in matrix.mean(axis=1)],
                   "fixed_reliability_bins_by_draw": fixed_reliability_bins(labels, matrix)}
            for name, matrix in predictions.items()}
        outcome[budget] = statistics
    return outcome


def aggregate_public_payload(registration: dict, statistics: dict,
                             participants: int, events: int) -> dict:
    """Strict aggregate allowlist; never accepts IDs, labels or predictions."""
    if (set(statistics) != set(registration["budgets"]) or participants < 2 or
            not 0 < events < participants):
        raise ValueError("Aggregate-only final report contract mismatch")
    disclosed = deepcopy(statistics)
    for budget in disclosed.values():
        for model in budget.get("calibration_exploratory", {}).values():
            # A fixed reliability bin can contain one person; its observed
            # fraction would then expose that person's label. Retain the
            # registered bin result only in the private metrics artifact.
            model["fixed_reliability_bins_by_draw"] = "PRIVATE_ONLY_SMALL_CELL_DISCLOSURE_CONTROL"
    return {"status": "COMPLETE_AGGREGATE_ONLY",
            "protocol_version": registration["protocol_version"],
            "registration_sha256": REGISTRATION_SHA256,
            "participant_count": participants, "positive_reports": events,
            "metrics": disclosed}


def _load_locked_test_after_claim(registration: dict, *, data_root: Path,
                                  master_file: Path) -> tuple[tuple[str, ...], pd.DataFrame, np.ndarray]:
    """The sole real test-row access path; call only after authorization and claim."""
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
    # This selected-row reader indexes identifiers first and then reads only
    # explicitly permitted row positions. No development labels are loaded.
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
    expected_predictors = {name for fields in VIEWS_TEN.values() for name in fields}
    if set(ordered.columns) != expected_predictors | {"participant_id", "endpoint_status", "label"}:
        raise ValueError("Metadata or future field entered final test predictors")
    return (tuple(ordered.participant_id), ordered.loc[:, list(expected_predictors)].copy(),
            ordered.label.to_numpy(dtype=int))


def _real_inference(registration: dict, ids: tuple[str, ...], predictors: pd.DataFrame,
                    dimensions: dict) -> tuple[dict, dict]:
    torch.set_num_threads(2)  # same small-CPU policy as frozen 6A/6B runs
    records = {}
    private_arrays = {"participant_ids": np.asarray(ids, dtype=str)}
    for entry in registration["models"]:
        key = entry["budget"], entry["method"], entry["repetition"]
        probabilities = infer_frozen(entry, predictors, dimensions)
        records[key] = (ids, probabilities)
        suffix = "source" if entry["repetition"] is None else f"rep{entry['repetition']}"
        private_arrays[f"{entry['budget']}__{entry['method']}__{suffix}"] = probabilities
    return assemble_prediction_matrices(registration, ids, records), private_arrays


def persist_evaluation_outputs(registration: dict, *, manifest_hash: str,
                               ids: tuple[str, ...], labels: np.ndarray,
                               arrays: dict, statistics: dict,
                               private_output: Path, public_output: Path) -> dict:
    """One-way private predictions then aggregate report; testable with temp fixtures."""
    if not (private_output / "attempt.private.json").is_file():
        raise ValueError("Private evaluation ownership must be claimed first")
    if public_output.parent.exists():
        raise FileExistsError("Aggregate public output already exists or is partial")
    private_predictions = private_output / "predictions.private.npz"
    descriptor = os.open(private_predictions, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        np.savez_compressed(stream, **arrays)
    private_result = {"status": "COMPLETE", "registration_sha256": REGISTRATION_SHA256,
                      "execution_manifest_sha256": manifest_hash,
                      "private_prediction_sha256": file_sha256(private_predictions),
                      "test_participants": len(ids), "test_positive_reports": int(labels.sum()),
                      "bootstrap_seed": 20261026, "bootstrap_replicates": 2000,
                      "model_predictions": len(registration["models"]),
                      "no_fitting_performed": True,
                      "completed_utc": datetime.now(timezone.utc).isoformat()}
    _json_private(private_output / "evaluation_manifest.private.json", private_result)
    _json_private(private_output / "metrics.private.json", statistics)
    public_output.parent.mkdir(parents=True, exist_ok=False)
    _json_private(public_output, aggregate_public_payload(
        registration, statistics, len(ids), int(labels.sum())))
    return private_result


def execute_real_test(registration_path: Path, manifest_path: Path, *, data_root: Path,
                      master_file: Path, questionnaire: Path) -> dict:
    """One attempt only. No retry after claim, even when evaluation fails."""
    prepare(registration_path, manifest_path, data_root=data_root,
            master_file=master_file, questionnaire=questionnaire, authorized=True)
    registration = json.loads(registration_path.read_text())
    manifest_hash = file_sha256(manifest_path)
    manifest_record = json.loads(manifest_path.read_text())
    validate_execution_manifest(manifest_record, registration, authorized=True)
    if file_sha256(registration_path) != REGISTRATION_SHA256:
        raise ValueError("Registration changed during final authorization check")
    claim_private_run(PRIVATE_OUTPUT)
    previous_umask = os.umask(0o077)
    try:
        if (file_sha256(manifest_path) != manifest_hash or
                file_sha256(registration_path) != REGISTRATION_SHA256):
            raise ValueError("Authorization or registration changed after exclusive claim")
        validate_execution_manifest(manifest_record, registration, authorized=True)
        verify_input_bindings(registration)
        _verified_evidence(json.loads(EVIDENCE.read_text()), CONFIG,
                           data_root, master_file, questionnaire)
        _verify_model_record_bindings(registration)
        for key, path in (
                ("baseline_run_manifest_sha256", Path("results/real_training/m6a_20261025_dev_baselines_v4/run_manifest.json")),
                ("selector_registration_sha256", Path("results/real_training/m6b_20261025_selector_v1/experiment_registration.json")),
                ("selector_masks_sha256", Path("results/real_training/m6b_20261025_selector_v1/masks.csv")),
                ("selector_module_scores_sha256", Path("results/real_training/m6b_20261025_selector_v1/module_scores.csv"))):
            if file_sha256(path) != registration[key]:
                raise ValueError("Frozen baseline or selector artifact changed after claim")
        _json_private(PRIVATE_OUTPUT / "authorization.private.json", {
            "manifest_sha256": manifest_hash, "manifest": manifest_record,
            "registration_sha256": REGISTRATION_SHA256, "executor_sha256": file_sha256(Path(__file__))})
        ids, predictors, labels = _load_locked_test_after_claim(
            registration, data_root=data_root, master_file=master_file)
        baseline = json.loads(Path("results/real_training/m6a_20261025_dev_baselines_v4/run_manifest.json").read_text())
        matrices, arrays = _real_inference(registration, ids, predictors, baseline["view_dimensions"])
        arrays["observed_labels"] = labels
        statistics = evaluate_aligned_bundle(registration, labels, matrices)
        persist_evaluation_outputs(registration, manifest_hash=manifest_hash,
            ids=ids, labels=labels, arrays=arrays, statistics=statistics,
            private_output=PRIVATE_OUTPUT, public_output=PUBLIC_OUTPUT)
        return {"status": "COMPLETE", "private_output": str(PRIVATE_OUTPUT),
                "public_aggregate_output": str(PUBLIC_OUTPUT),
                "models_evaluated": len(registration["models"]),
                "test_participants": len(ids), "test_positive_reports": int(labels.sum())}
    except Exception as exc:
        _json_private(PRIVATE_OUTPUT / "failure.private.json", _safe_error(exc))
        raise
    finally:
        os.umask(previous_umask)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true", help="Read-only; no test rows")
    group.add_argument("--execute-real-test", action="store_true", help="Requires separate one-time authorization")
    parser.add_argument("--registration", type=Path, default=REGISTRATION_PATH)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--master-file", type=Path, required=True)
    parser.add_argument("--questionnaire", type=Path, required=True)
    args = parser.parse_args()
    common = dict(data_root=args.data_root, master_file=args.master_file,
                  questionnaire=args.questionnaire)
    if args.prepare:
        print(json.dumps(prepare(args.registration, args.execution_manifest, **common), indent=2))
    else:
        print(json.dumps(execute_real_test(args.registration, args.execution_manifest, **common), indent=2))


if __name__ == "__main__":
    main()
