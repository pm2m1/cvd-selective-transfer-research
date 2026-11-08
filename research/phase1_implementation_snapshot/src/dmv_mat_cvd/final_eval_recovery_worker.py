"""One family-isolated frozen-inference worker; no cohort loader or labels."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from .final_eval_runtime_v2 import VIEWS, file_sha256, infer_frozen_isolated, initialize_isolated_cpu


FAMILIES = {"torch": frozenset({"flat_mlp", "five_view_net"}),
            "tabular": frozenset({"sklearn_logistic", "xgboost"})}


def read_private_features(path: Path, expected_sha256: str) -> pd.DataFrame:
    if file_sha256(path) != expected_sha256:
        raise ValueError("Private frozen feature payload changed")
    names = [field for fields in VIEWS.values() for field in fields]
    with np.load(path, allow_pickle=False) as saved:
        if set(saved.files) != {f"feature_{name}" for name in names} | {
                f"missing_{name}" for name in names}:
            raise ValueError("Private feature payload has unexpected fields")
        columns = {}
        lengths = set()
        for name in names:
            values = saved[f"feature_{name}"]
            missing = saved[f"missing_{name}"]
            if values.ndim != 1 or missing.shape != values.shape or missing.dtype != np.bool_:
                raise ValueError("Invalid private feature column shape")
            lengths.add(len(values))
            if name in {"age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl"}:
                if values.dtype.kind != "f":
                    raise ValueError("Continuous private feature must be floating-point")
                column = values.copy()
                column[missing] = np.nan
            else:
                if values.dtype.kind != "U":
                    raise ValueError("Categorical private feature must be Unicode")
                column = values.astype(object)
                column[missing] = np.nan
            columns[name] = column
    if len(lengths) != 1:
        raise ValueError("Private feature columns have different participant counts")
    return pd.DataFrame(columns, columns=names)


def run_worker(*, family_group: str, registration_path: Path, registration_sha256: str,
               features_path: Path, features_sha256: str, baseline_manifest_path: Path,
               output_path: Path) -> dict:
    if family_group not in FAMILIES:
        raise ValueError("Unknown isolated family")
    if file_sha256(registration_path) != registration_sha256:
        raise ValueError("Frozen registration changed")
    registration = json.loads(registration_path.read_text())
    if len(registration["models"]) != 184:
        raise ValueError("Frozen model inventory changed")
    frame = read_private_features(features_path, features_sha256)
    if len(frame) != registration["test_integrity_metadata_only"]["participants"]:
        raise ValueError("Frozen test batch size changed")
    dimensions = json.loads(baseline_manifest_path.read_text())["view_dimensions"]
    initialize_isolated_cpu(family_group)
    indices, predictions = [], []
    for index, entry in enumerate(registration["models"]):
        if entry["model_family"] not in FAMILIES[family_group]:
            continue
        values = infer_frozen_isolated(entry, frame, dimensions, family_group)
        if values.shape != (len(frame),):
            raise ValueError("Frozen prediction count changed")
        indices.append(index)
        predictions.append(values)
    if len(indices) != (162 if family_group == "torch" else 22):
        raise ValueError("Frozen family inventory differs")
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        np.savez_compressed(stream, model_indices=np.asarray(indices, dtype=np.int64),
                            probabilities=np.stack(predictions),
                            feature_sha256=np.asarray(features_sha256))
    return {"family_group": family_group, "models_completed": len(indices),
            "participants": len(frame), "feature_sha256": features_sha256,
            "native_stacks_loaded": {name: name in sys.modules
                                     for name in ("torch", "sklearn", "xgboost")}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family-group", required=True, choices=tuple(FAMILIES))
    parser.add_argument("--registration", required=True, type=Path)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--features", required=True, type=Path)
    parser.add_argument("--features-sha256", required=True)
    parser.add_argument("--baseline-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        result = run_worker(family_group=args.family_group,
            registration_path=args.registration, registration_sha256=args.registration_sha256,
            features_path=args.features, features_sha256=args.features_sha256,
            baseline_manifest_path=args.baseline_manifest, output_path=args.output)
    except BaseException as exc:
        # Exception text can contain participant values; only the type is exposed.
        print(json.dumps({"status": "FAILED", "exception_type": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
    print(json.dumps({"status": "COMPLETE", **result}), flush=True)


if __name__ == "__main__":
    main()
