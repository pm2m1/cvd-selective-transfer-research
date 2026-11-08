"""Aggregate-only SHA256 preservation check. Never opens participant rows."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_one(path: Path, expected: str) -> bool:
    return path.is_file() and digest(path) == expected


def main() -> None:
    historical = json.loads((ROOT / "results/onboarding/m4_verification_20260925T162406Z/protected_file_hashes.json").read_text())
    baseline_dir = ROOT / "results/real_training/m6a_20261025_dev_baselines_v4"
    baseline = json.loads((ROOT / "results/real_training/m6b_20261025_selector_v1/baseline_artifact_inventory.json").read_text())
    registered = json.loads((ROOT / "FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json").read_text())
    old_private = Path('WITHHELD_PRIVATE_PATH')
    old_artifacts = {
        "attempt.private.json": 'WITHHELD_REFERENCE_BINDING',
        "authorization.private.json": 'WITHHELD_REFERENCE_BINDING',
        "failure.private.json": 'WITHHELD_REFERENCE_BINDING',
    }
    selective = [item for item in registered["models"] if item["run"] == "m6b_20261025_selector_v1"]
    groups = {
        "historical_25444": {name: verify_one(ROOT / name, expected) for name, expected in historical.items()},
        "baseline_110": {name: verify_one(baseline_dir / name, expected)
                         for name, expected in baseline["files"].items()},
        "selector_100": {str(i): verify_one(ROOT / item["checkpoint_path"], item["checkpoint_sha256"])
                         for i, item in enumerate(selective)},
        "failed_attempt_3": {name: verify_one(old_private / name, expected)
                             for name, expected in old_artifacts.items()},
        "frozen_core": {
            "registration": verify_one(ROOT / "FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json",
                'WITHHELD_REFERENCE_BINDING'),
            "old_executor": verify_one(ROOT / "src/dmv_mat_cvd/final_eval_execute.py",
                'WITHHELD_REFERENCE_BINDING'),
            "original_consumed_authorization": verify_one(ROOT / "FINAL_TEST_EXECUTION_MANIFEST.authorized.json",
                'WITHHELD_REFERENCE_BINDING'),
            "registered_statistics_code": verify_one(ROOT / "src/dmv_mat_cvd/final_eval_stats.py",
                'WITHHELD_REFERENCE_BINDING'),
            "test_lock": verify_one(Path(registered["test_lock_path"]), registered["test_lock_sha256"]),
            "assignments": verify_one(Path(registered["private_assignments_path"]), registered["private_assignments_sha256"]),
        },
    }
    summary = {name: {"checked": len(values), "changed_or_missing": sum(not ok for ok in values.values())}
               for name, values in groups.items()}
    summary["original_attempt_blocks_retry"] = old_private.is_dir()
    summary["original_attempt_has_no_results"] = not any((old_private / name).exists() for name in (
        "predictions.private.npz", "metrics.private.json", "evaluation_manifest.private.json"))
    print(json.dumps(summary, indent=2))
    if any(value["changed_or_missing"] for value in summary.values() if isinstance(value, dict)):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
