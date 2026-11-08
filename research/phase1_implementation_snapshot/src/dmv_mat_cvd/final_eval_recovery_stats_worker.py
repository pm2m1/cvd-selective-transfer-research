"""Isolated frozen-statistics worker; reads only a private prediction bundle."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import numpy as np

from .final_eval_runtime_v2 import file_sha256
from .final_eval_stats import fixed_reliability_bins, paired_participant_bootstrap


CONTRASTS = (("calibrated_logical", "full_finetune"),
             ("calibrated_logical", "head_only"),
             ("calibrated_logical", "random_calibrated_logical"),
             ("calibrated_logical", "source_multiview"))


def evaluate_private_bundle(bundle: Path, bundle_sha256: str, registration: dict,
                            *, synthetic_replicates: int | None = None) -> dict:
    if file_sha256(bundle) != bundle_sha256:
        raise ValueError("Private prediction bundle changed")
    budgets = registration["budgets"]
    expected = {f"{budget}__{method}" for budget in budgets for method in (
        "source_logistic", "source_xgboost", "source_flat_mlp", "source_multiview",
        "head_only", "full_finetune", "target_logistic", "target_multiview",
        "fixed_mask", "random_calibrated_logical", "legacy_topk",
        "calibrated_threshold", "calibrated_logical")}
    with np.load(bundle, allow_pickle=False) as stored:
        if set(stored.files) != expected | {"observed_labels"}:
            raise ValueError("Private model inventory differs from registration")
        labels = stored["observed_labels"].copy()
        matrices = {budget: {method: stored[f"{budget}__{method}"].copy()
                  for method in ("source_logistic", "source_xgboost", "source_flat_mlp", "source_multiview",
                      "head_only", "full_finetune", "target_logistic", "target_multiview",
                      "fixed_mask", "random_calibrated_logical", "legacy_topk",
                      "calibrated_threshold", "calibrated_logical")}
                  for budget in budgets}
    if len(labels) != registration["test_integrity_metadata_only"]["participants"]:
        raise ValueError("Private label count differs from frozen test")
    seed = registration["uncertainty"]["bootstrap_seed"]
    replicates = registration["uncertainty"]["test_participant_resamples"]
    if synthetic_replicates is not None:
        if synthetic_replicates < 20:
            raise ValueError("Synthetic bootstrap must have at least 20 replicates")
        replicates = synthetic_replicates
    result = {}
    for budget, models in matrices.items():
        statistics = paired_participant_bootstrap(labels, models, CONTRASTS,
                                                  seed=seed, replicates=replicates)
        statistics["calibration_exploratory"] = {
            name: {"mean_predicted_by_draw": [float(x) for x in matrix.mean(axis=1)],
                   "fixed_reliability_bins_by_draw": fixed_reliability_bins(labels, matrix)}
            for name, matrix in models.items()}
        result[budget] = statistics
    return result


def public_aggregate(registration: dict, statistics: dict, participants: int, events: int,
                     registration_sha256: str) -> dict:
    if set(statistics) != set(registration["budgets"]) or participants < 2 or not 0 < events < participants:
        raise ValueError("Aggregate-only report contract mismatch")
    disclosed = deepcopy(statistics)
    for budget in disclosed.values():
        for model in budget["calibration_exploratory"].values():
            model["fixed_reliability_bins_by_draw"] = "PRIVATE_ONLY_SMALL_CELL_DISCLOSURE_CONTROL"
    return {"status": "COMPLETE_AGGREGATE_ONLY",
            "protocol_version": registration["protocol_version"],
            "registration_sha256": registration_sha256,
            "participant_count": participants, "positive_reports": events,
            "metrics": disclosed}


def write_json_exclusive(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", required=True, type=Path)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--bundle-sha256", required=True)
    parser.add_argument("--private-metrics", required=True, type=Path)
    parser.add_argument("--private-public-payload", required=True, type=Path)
    parser.add_argument("--synthetic-replicates", type=int, default=None,
                        help="Invented fixture only; forbidden for the frozen registration")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if file_sha256(args.registration) != args.registration_sha256:
            raise ValueError("Frozen registration changed")
        registration = json.loads(args.registration.read_text())
        if args.synthetic_replicates is not None and (
                registration.get("registration_version") == "public-mhas-final-test-evaluation-v1"):
            raise ValueError("Frozen registration forbids bootstrap override")
        statistics = evaluate_private_bundle(args.bundle, args.bundle_sha256, registration,
                                             synthetic_replicates=args.synthetic_replicates)
        with np.load(args.bundle, allow_pickle=False) as saved:
            labels = saved["observed_labels"]
            participants, events = len(labels), int(labels.sum())
        write_json_exclusive(args.private_metrics, statistics)
        write_json_exclusive(args.private_public_payload,
            public_aggregate(registration, statistics, participants, events,
                             args.registration_sha256))
    except BaseException as exc:
        print(json.dumps({"status": "FAILED", "exception_type": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
    print(json.dumps({"status": "COMPLETE", "participants": participants,
                      "positive_reports": events,
                      "native_stacks_loaded": {name: name in sys.modules
                          for name in ("torch", "sklearn", "xgboost")}}), flush=True)


if __name__ == "__main__":
    main()
