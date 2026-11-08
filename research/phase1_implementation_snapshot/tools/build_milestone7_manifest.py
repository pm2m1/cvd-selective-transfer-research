"""Hash the frozen experiment and Milestone 7 aggregate reporting artifacts.

The only private reads are SHA256 byte streams for the pre-existing lock,
assignment and incident/metadata files. No private JSON is parsed, and no
prediction, feature, outcome or participant row is read or regenerated.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = ROOT / "FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json"
REGISTRATION_SHA = 'WITHHELD_REFERENCE_BINDING'
RESULT = ROOT / "results/real_training/m6c_final_test_v2_recovery/aggregate_only_results.json"
RESULT_SHA = 'WITHHELD_REFERENCE_BINDING'
OUTPUT = ROOT / "FINAL_REPRODUCIBILITY_MANIFEST.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked(path: Path, expected: str) -> str:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"Frozen hash mismatch: {path}")
    return actual


def project_path(relative: str) -> Path:
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Non-project model binding: {relative}")
    return path


def main() -> None:
    checked(REGISTRATION, REGISTRATION_SHA)
    checked(RESULT, RESULT_SHA)
    registration = json.loads(REGISTRATION.read_text())
    result = json.loads(RESULT.read_text())
    assert registration["protocol_version"] == "public-haalsi-mhas-v2"
    assert result["registration_sha256"] == REGISTRATION_SHA
    assert result["participant_count"] == 283 and result["positive_reports"] == 21
    primary = result["metrics"]["primary_25_75"]["contrasts"]["calibrated_logical_minus_full_finetune"]["ap"]
    assert abs(primary["estimate"] - 0.0018192160502534082) < 1e-15
    assert registration["model_checkpoint_count"] == len(registration["models"]) == 184

    bindings = []
    preprocessors = {}
    for model in registration["models"]:
        checkpoint = project_path(model["checkpoint_path"])
        preprocessor = project_path(model["preprocessor_path"])
        checked(checkpoint, model["checkpoint_sha256"])
        checked(preprocessor, model["preprocessor_sha256"])
        prior = preprocessors.setdefault(model["preprocessor_path"], model["preprocessor_sha256"])
        assert prior == model["preprocessor_sha256"]
        bindings.append({key: model.get(key) for key in
                         ("method", "budget", "repetition", "model_family", "checkpoint_path",
                          "checkpoint_sha256", "preprocessor_path", "preprocessor_sha256",
                          "adaptation_draw", "reporting_role")})

    lock_sha = checked(Path(registration["test_lock_path"]), registration["test_lock_sha256"])
    assignments_sha = checked(Path(registration["private_assignments_path"]),
                              registration["private_assignments_sha256"])
    failed_private = Path('WITHHELD_PRIVATE_PATH')
    failed_hashes = {
        "attempt.private.json": 'WITHHELD_REFERENCE_BINDING',
        "authorization.private.json": 'WITHHELD_REFERENCE_BINDING',
        "failure.private.json": 'WITHHELD_REFERENCE_BINDING',
    }
    for filename, expected in failed_hashes.items():
        checked(failed_private / filename, expected)

    files = [
        "METHOD_SPEC.md", "PUBLIC_FINAL_PROTOCOL_V2.md", "PUBLIC_EXPERIMENT_ANALYSIS_PLAN.md",
        "configs/public_haalsi_mhas_v2.ready_pending_execution_m5l.json",
        "configs/public_features_ten_v2.lock_candidate.json",
        "configs/public_features_nine_v2.lock_candidate.json",
        "results/real_training/m6a_20261025_dev_baselines_v4/run_manifest.json",
        "results/real_training/m6a_20261025_dev_baselines_v4/development_metrics.csv",
        "results/real_training/m6b_20261025_selector_v1/experiment_registration.json",
        "results/real_training/m6b_20261025_selector_v1/masks.csv",
        "results/real_training/m6b_20261025_selector_v1/module_scores.csv",
        "results/real_training/m6b_20261025_selector_v1/per_run.csv",
        "results/real_training/m6b_20261025_selector_v1/summary.json",
        "FINAL_MHAS_TEST_EVALUATION_REGISTRATION.json",
        "FINAL_TEST_EXECUTION_MANIFEST.authorized.json",
        "FINAL_TEST_RECOVERY_EXECUTION_MANIFEST.authorized.json",
        "MILESTONE6C2_FINAL_TEST_ATTEMPT_REPORT.md",
        "MILESTONE6C3_RUNTIME_FAILURE_INVESTIGATION.md",
        "MILESTONE6C4_RECOVERY_EXECUTOR_REPORT.md",
        "MILESTONE6C5_REAL_TEST_RECOVERY_EXECUTION_REPORT.md",
        "src/dmv_mat_cvd/final_eval_execute.py",
        "src/dmv_mat_cvd/final_eval_recovery_execute.py",
        "src/dmv_mat_cvd/final_eval_runtime_v2.py",
        "src/dmv_mat_cvd/final_eval_recovery_worker.py",
        "src/dmv_mat_cvd/final_eval_recovery_stats_worker.py",
        "src/dmv_mat_cvd/final_eval_stats.py",
        "results/real_training/m6c_final_test_v2_recovery/aggregate_only_results.json",
        "FINAL_HAALSI_MHAS_RESULTS.md", "DMV_MAT_CVD_RESEARCH_MANUSCRIPT.md",
        "tools/build_milestone7_figures.py", "tools/build_milestone7_manifest.py",
    ]
    public_hashes = {relative: sha256(project_path(relative)) for relative in files}
    expected = {
        "results/real_training/m6a_20261025_dev_baselines_v4/run_manifest.json":
            registration["baseline_run_manifest_sha256"],
        "results/real_training/m6b_20261025_selector_v1/experiment_registration.json":
            registration["selector_registration_sha256"],
        "results/real_training/m6b_20261025_selector_v1/masks.csv": registration["selector_masks_sha256"],
        "results/real_training/m6b_20261025_selector_v1/module_scores.csv":
            registration["selector_module_scores_sha256"],
        "src/dmv_mat_cvd/final_eval_stats.py": registration["evaluator_statistic_code_sha256"],
    }
    for relative, expected_hash in expected.items():
        assert public_hashes[relative] == expected_hash, relative

    figure_dir = ROOT / "results/final_research/m7_aggregate_figures"
    figures = {str(p.relative_to(ROOT)): sha256(p) for p in sorted(figure_dir.iterdir())
               if p.suffix in {".svg", ".png"}}
    assert len(figures) == 14
    recovery_private_manifest = Path(
        'WITHHELD_PRIVATE_PATH'
    )
    recovery_manifest_sha = checked(
        recovery_private_manifest,
        'WITHHELD_REFERENCE_BINDING',
    )
    config = json.loads(project_path("configs/public_haalsi_mhas_v2.ready_pending_execution_m5l.json").read_text())
    assert public_hashes["configs/public_haalsi_mhas_v2.ready_pending_execution_m5l.json"] == (
        registration["scientific_config_sha256"])
    payload = {
        "manifest_version": "m7-final-aggregate-reproducibility-v1",
        "reporting_date": "2026-10-26",
        "study_protocol": registration["protocol_version"],
        "method_spec_version": registration["method_spec_version"],
        "schema_version": registration["schema_version"],
        "experimental_phase": "CLOSED_NO_MORE_TEST_ACCESS_AUTHORIZED",
        "private_test_rows_parsed_by_this_script": False,
        "private_checkpoint_inference_performed_by_this_script": False,
        "frozen_registration_sha256": REGISTRATION_SHA,
        "frozen_test_lock_sha256": lock_sha,
        "frozen_assignments_sha256": assignments_sha,
        "scientific_config_sha256": registration["scientific_config_sha256"],
        "approved_release_and_mapping_hashes_from_config": config["expected_input_sha256"],
        "checkpoint_binding_count": len(bindings),
        "checkpoint_method_counts": dict(sorted(Counter(x["method"] for x in bindings).items())),
        "checkpoint_inventory": bindings,
        "unique_preprocessor_inventory": preprocessors,
        "selector_registration_sha256": registration["selector_registration_sha256"],
        "selector_masks_sha256": registration["selector_masks_sha256"],
        "selector_module_scores_sha256": registration["selector_module_scores_sha256"],
        "first_failed_attempt": {
            "status": "FAILED_AFTER_TEST_ACCESS_NO_PERFORMANCE_RESULTS",
            "private_artifact_sha256": failed_hashes,
            "report_sha256": public_hashes["MILESTONE6C2_FINAL_TEST_ATTEMPT_REPORT.md"],
        },
        "authorized_recovery": {
            "status": "RECOVERY_COMPLETE_AFTER_FAILED_ORIGINAL_ATTEMPT",
            "authorization_manifest_sha256": public_hashes["FINAL_TEST_RECOVERY_EXECUTION_MANIFEST.authorized.json"],
            "executor_sha256": public_hashes["src/dmv_mat_cvd/final_eval_recovery_execute.py"],
            "isolated_runtime_sha256": public_hashes["src/dmv_mat_cvd/final_eval_runtime_v2.py"],
            "model_worker_sha256": public_hashes["src/dmv_mat_cvd/final_eval_recovery_worker.py"],
            "statistics_worker_sha256": public_hashes["src/dmv_mat_cvd/final_eval_recovery_stats_worker.py"],
            "private_evaluation_manifest_sha256": recovery_manifest_sha,
            "public_aggregate_sha256": RESULT_SHA,
        },
        "primary_result": {"budget": "25+75", "paired_ap_difference": primary["estimate"],
                           "bootstrap_interval": primary["interval"],
                           "bootstrap_seed": registration["uncertainty"]["bootstrap_seed"],
                           "bootstrap_replicates": registration["uncertainty"]["test_participant_resamples"]},
        "public_artifact_sha256": public_hashes,
        "aggregate_only_figure_sha256": figures,
        "figure_generator_sha256": public_hashes["tools/build_milestone7_figures.py"],
        "manuscript_sha256": public_hashes["DMV_MAT_CVD_RESEARCH_MANUSCRIPT.md"],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"Verified {len(bindings)} checkpoint bindings, {len(preprocessors)} preprocessors, "
          f"{len(figures)} figures; wrote {OUTPUT.name}")


if __name__ == "__main__":
    main()
