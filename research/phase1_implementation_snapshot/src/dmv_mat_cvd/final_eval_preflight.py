"""Read-only pretest inventory check; never opens participant-level test rows."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .data.releases import file_sha256


EXPECTED_METHODS_PER_BUDGET = {
    "head_only", "full_finetune", "target_logistic", "target_multiview",
    "fixed_mask", "random_calibrated_logical", "legacy_topk",
    "calibrated_threshold", "calibrated_logical",
}


def verify_pretest_registration(path: Path) -> dict:
    """Verify only hashes, counts, identities and authorization state."""
    record = json.loads(path.read_text())
    if (record.get("registration_version") != "public-mhas-final-test-evaluation-v1" or
            record.get("protocol_version") != "public-haalsi-mhas-v2" or
            record.get("schema_version") != "cvd-public-wave-v2-ten-doctor-report" or
            record.get("primary_method") != "calibrated_logical" or
            record.get("primary_budget") != "primary_25_75" or
            record.get("primary_contrast", {}).get("right") != "full_finetune" or
            record.get("evaluation_authorized") is not False or
            record.get("real_test_accessed_for_this_registration") is not False or
            record.get("model_checkpoint_count") != 184 or
            record.get("uncertainty", {}).get("test_participant_resamples") != 2000 or
            record.get("uncertainty", {}).get("bootstrap_seed") != 20261026):
        raise ValueError("Final evaluation registration is not the frozen pending version")
    if file_sha256(Path(record["test_lock_path"])) != record["test_lock_sha256"]:
        raise ValueError("Private target lock hash changed")
    if file_sha256(Path(record["private_assignments_path"])) != record["private_assignments_sha256"]:
        raise ValueError("Private partition/draw manifest hash changed")
    bindings = {
        "evaluator_statistic_code_sha256": Path(record["evaluator_statistic_code"]),
        "baseline_run_manifest_sha256": Path("results/real_training/m6a_20261025_dev_baselines_v4/run_manifest.json"),
        "selector_registration_sha256": Path("results/real_training/m6b_20261025_selector_v1/experiment_registration.json"),
        "selector_masks_sha256": Path("results/real_training/m6b_20261025_selector_v1/masks.csv"),
        "selector_module_scores_sha256": Path("results/real_training/m6b_20261025_selector_v1/module_scores.csv"),
    }
    if any(file_sha256(file) != record[key] for key, file in bindings.items()):
        raise ValueError("Frozen scientific or statistic-code artifact changed")
    models = record["models"]
    if len(models) != 184 or len({(m["run"], m["method"], m["budget"], m["repetition"])
                                   for m in models}) != 184:
        raise ValueError("Final model inventory is incomplete or duplicated")
    for model in models:
        for path_key, digest_key in (("checkpoint_path", "checkpoint_sha256"),
                                     ("preprocessor_path", "preprocessor_sha256")):
            if file_sha256(Path(model[path_key])) != model[digest_key]:
                raise ValueError("Frozen checkpoint or preprocessing artifact changed")
        if model["budget"] != "source" and model["adaptation_draw"] != {
                "budget": model["budget"], "repetition": model["repetition"]}:
            raise ValueError("Checkpoint/draw binding changed")
    for budget in ("primary_25_75", "low_label_10_30"):
        for method in EXPECTED_METHODS_PER_BUDGET:
            repetitions = {m["repetition"] for m in models
                           if m["budget"] == budget and m["method"] == method}
            if repetitions != set(range(10)):
                raise ValueError("Final comparator repetitions missing or substituted")
    if len([m for m in models if m["budget"] == "source"]) != 4:
        raise ValueError("Source-only baselines missing")
    if Path(record["private_output"]["directory"]).exists():
        raise FileExistsError("Final private evaluation output already exists or is partial")
    return {"registration_sha256": file_sha256(path),
            "lock_sha256": record["test_lock_sha256"],
            "assignment_sha256": record["private_assignments_sha256"],
            "checkpoint_bindings_verified": len(models),
            "real_test_rows_read": False,
            "evaluation_authorized": False,
            "private_output_absent": True,
            "status": "PRETEST_INVENTORY_VALID_AUTHORIZATION_PENDING"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_pretest_registration(args.registration), indent=2))


if __name__ == "__main__":
    main()
