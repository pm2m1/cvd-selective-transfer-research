"""Synthetic-only full-inventory CPU inference probe; never loads cohort rows.

Run from a fresh process with an external timeout. The saved output contains
only invented-predictor probabilities, with no participant identifiers.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd


def invented_frame(count: int) -> pd.DataFrame:
    if count != 283:
        raise ValueError("The probe reproduces the registered 283-row batch")
    row = np.arange(count)
    return pd.DataFrame({
        "age": 45.0 + row % 39,
        "sex": np.where(row % 2, "female", "male"),
        "sbp": 104.0 + row % 61,
        "dbp": 62.0 + row % 37,
        "bmi": 20.0 + (row % 19) * .7,
        "total_cholesterol": 145.0 + row % 105,
        "hdl": 30.0 + row % 39,
        "smoking_status": np.asarray(("never", "former", "current"), dtype=object)[row % 3],
        "diabetes": np.where(row % 5 == 0, "yes", "no"),
        "antihypertensive_treatment": np.where(row % 4 == 0, "yes", "no"),
    })


def run(mode: str, destination: Path) -> None:
    # The original executor imports XGBoost before PyTorch. Keep that order.
    isolated = mode in {"isolated_torch", "isolated_tabular"}
    if isolated:
        from dmv_mat_cvd.final_eval_runtime_v2 import initialize_isolated_cpu, infer_frozen_isolated
        group = "torch" if mode == "isolated_torch" else "tabular"
        initialize_isolated_cpu(group)
        infer_frozen = lambda entry, frame, dims: infer_frozen_isolated(entry, frame, dims, group)
    else:
        from dmv_mat_cvd.final_eval_execute import infer_frozen
    if not isolated or group == "torch":
        import torch
    from threadpoolctl import threadpool_info

    if mode == "original_late_two":
        torch.set_num_threads(2)  # original executor timing, after imports
    elif mode in {"single_early", "two_early"}:
        requested = 1 if mode == "single_early" else 2
        torch.set_num_threads(requested)
        torch.set_num_interop_threads(1)
    elif not isolated:
        raise ValueError("Unknown synthetic runtime condition")
    print(json.dumps({"stage": "initialized", "mode": mode,
        "env": {key: os.environ.get(key) for key in (
            "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS", "KMP_DUPLICATE_LIB_OK")},
        "torch_intra": torch.get_num_threads() if not isolated or group == "torch" else None,
        "torch_interop": torch.get_num_interop_threads() if not isolated or group == "torch" else None,
        "loaded_stacks": {name: name in sys.modules for name in ("torch", "sklearn", "xgboost")},
        "threadpools": [{"filepath": item.get("filepath"), "user_api": item.get("user_api"),
                         "num_threads": item.get("num_threads")}
                        for item in threadpool_info()]}, sort_keys=True), flush=True)

    registration = json.loads(Path("FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json").read_text())
    manifest = json.loads(Path("results/real_training/m6a_20261025_dev_baselines_v4/run_manifest.json").read_text())
    predictors = invented_frame(283)
    outputs = []
    indices = []
    started = time.monotonic()
    for index, entry in enumerate(registration["models"]):
        if isolated and ((group == "torch") !=
                         (entry["model_family"] in {"flat_mlp", "five_view_net"})):
            continue
        probabilities = infer_frozen(entry, predictors, manifest["view_dimensions"])
        if probabilities.shape != (283,) or not np.isfinite(probabilities).all():
            raise ValueError("Synthetic inference output contract failed")
        outputs.append(probabilities)
        indices.append(index)
        print(json.dumps({"stage": "completed_model", "index": index,
            "family": entry["model_family"], "elapsed_seconds": round(time.monotonic() - started, 3)}),
            flush=True)
    result = np.stack(outputs)
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination, synthetic_predictions=result,
                        model_indices=np.asarray(indices, dtype=int))
    print(json.dumps({"stage": "complete", "models": len(outputs), "rows": result.shape[1],
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "minimum_probability": float(result.min()),
        "maximum_probability": float(result.max())}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("original_late_two", "single_early", "two_early",
                                           "isolated_torch", "isolated_tabular"), required=True)
    parser.add_argument("--synthetic-output", type=Path, required=True)
    args = parser.parse_args()
    run(args.mode, args.synthetic_output)


if __name__ == "__main__":
    main()
