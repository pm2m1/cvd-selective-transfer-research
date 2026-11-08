"""Bounded fresh-process trials of invented-input final inference only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np


def trial(condition: str, repetition: int, directory: Path, timeout: int) -> dict:
    env = os.environ.copy()
    if condition != "inherited_two":
        env.pop("KMP_DUPLICATE_LIB_OK", None)
        for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                     "VECLIB_MAXIMUM_THREADS"):
            env[name] = "1" if condition in {"clean_one", "remediated_one"} else "2"
    mode = {"inherited_two": "original_late_two", "clean_one": "single_early",
            "clean_two": "two_early", "isolated_torch": "isolated_torch",
            "isolated_tabular": "isolated_tabular"}[condition]
    output = directory / f"{condition}_{repetition}.npz"
    command = [sys.executable, "tools/final_eval_runtime_probe.py", "--mode", mode,
               "--synthetic-output", str(output)]
    started = time.monotonic()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate(timeout=5)
    records = []
    for line in stdout.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    completed = [x for x in records if x.get("stage") == "completed_model"]
    initialized = next((x for x in records if x.get("stage") == "initialized"), {})
    result = {"condition": condition, "repetition": repetition, "exit_code": proc.returncode,
              "timed_out": timed_out, "elapsed_seconds": round(time.monotonic()-started, 3),
              "models_completed": len(completed),
              "last_completed_index": completed[-1]["index"] if completed else None,
              "last_completed_family": completed[-1]["family"] if completed else None,
              "complete": any(x.get("stage") == "complete" for x in records),
              "synthetic_output": str(output) if output.exists() else None,
              "thread_initialization": initialized,
              "error_tail": stderr[-800:]}
    (directory / f"{condition}_{repetition}.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--conditions", nargs="+", choices=("inherited_two", "clean_one",
                        "clean_two", "isolated_torch", "isolated_tabular"),
                        default=("inherited_two", "clean_one", "clean_two"))
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    results = []
    for condition in args.conditions:
        for repetition in range(args.repetitions):
            result = trial(condition, repetition, args.directory, args.timeout)
            results.append(result)
            print(json.dumps({k: v for k, v in result.items() if k not in {
                "thread_initialization", "error_tail"}}), flush=True)
    completed = [(x, np.load(x["synthetic_output"])["synthetic_predictions"])
                 for x in results if x["complete"] and x["synthetic_output"]]
    comparisons = []
    if completed:
        reference = completed[0][1]
        for result, predictions in completed[1:]:
            if predictions.shape != reference.shape:
                continue
            comparisons.append({"condition": result["condition"],
                "repetition": result["repetition"],
                "max_abs_difference": float(np.max(np.abs(reference-predictions))),
                "shape": list(predictions.shape)})
    (args.directory / "aggregate.json").write_text(json.dumps({
        "trials": results, "comparisons": comparisons}, indent=2) + "\n")


if __name__ == "__main__":
    main()
