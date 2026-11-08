"""Imported public originals and invented-only metadata inventory tests."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


VERIFY = module("imported_verify", "scripts/verify_imported_artifacts.py")
INVENTORY = module("private_names", "scripts/inventory_protected_filenames_local.py")


def test_imported_original_packages_are_intact_and_real_results_not_substituted():
    counts = VERIFY.verify()
    assert counts["standalone_packages"] == 13
    assert counts["categories"]["synthetic_confusion_matrix"] == 300
    assert counts["real_confusion_matrices_published"] == 0
    assert counts["real_threshold_plots_published"] == 0
    assert counts["privacy_projected_source_files"] == 16


def test_inventory_reads_no_input_payloads_and_retains_exact_names(tmp_path, monkeypatch):
    root = tmp_path / "INVENTED_SOURCE"
    root.mkdir(mode=0o700)
    (root / "confusion_matrices/INVENTED_MODEL").mkdir(parents=True)
    (root / "confusion_matrices/INVENTED_MODEL/draw_0__fixed_0.50.svg").write_text("DO NOT OPEN")
    (root / "summary_plots").mkdir()
    (root / "summary_plots/INVENTED_MODEL_threshold_response.svg").write_text("DO NOT OPEN")
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **kw: pytest.fail("Payload read"))
    result = INVENTORY.inventory_metadata(root, tmp_path / "NEW_PRIVATE_OUTPUT")
    assert result == {"CONFUSION_MATRIX_SVG": 1, "SUMMARY_PLOT_RENDITION": 1, "OTHER_ARTIFACT": 0}
    report = json.loads((tmp_path / "NEW_PRIVATE_OUTPUT/UNPUBLISHED_FILES.private.json").read_text())
    assert len(report["files"]) == 2
    assert all(row["publication_status"] == "NOT_PUBLISHED" for row in report["files"])
    assert (tmp_path / "NEW_PRIVATE_OUTPUT/UNPUBLISHED_FILES.private.json").stat().st_mode & 0o777 == 0o600


def test_inventory_refuses_existing_destination(tmp_path):
    root = tmp_path / "INVENTED_SOURCE"
    root.mkdir(mode=0o700)
    output = tmp_path / "EXISTING"
    output.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="NEW_SEPARATE"):
        INVENTORY.inventory_metadata(root, output)


def test_inventory_refuses_symlinks(tmp_path):
    root = tmp_path / "INVENTED_SOURCE"
    root.mkdir(mode=0o700)
    (root / "link").symlink_to(tmp_path / "OUTSIDE")
    with pytest.raises(ValueError, match="SYMLINK"):
        INVENTORY.inventory_metadata(root, tmp_path / "NEW")


def test_agent_inventory_gate_stops_before_argument_or_path_access(monkeypatch):
    monkeypatch.setattr(INVENTORY, "in_agent", lambda: True)
    monkeypatch.setattr(Path, "stat", lambda *a, **kw: pytest.fail("Filesystem inspection"))
    with pytest.raises(SystemExit, match="INDEPENDENT_LOCAL_OPERATOR_REQUIRED"):
        INVENTORY.main()


def test_academic_documents_are_absent_from_imported_collection():
    files = json.loads((ROOT / "research/IMPORTED_PUBLIC_ARTIFACTS.json").read_text())["files"]
    assert not any(Path(p).suffix in {".pdf", ".tex", ".sty", ".bib", ".zip"} for p in files)


def test_original_joint_bootstrap_reference_on_invented_identical_models():
    import numpy as np

    stats = module(
        "original_bootstrap_reference",
        "research/phase1_implementation_snapshot/src/dmv_mat_cvd/final_eval_stats.py",
    )
    labels = np.array([0, 1] * 20)
    scores = np.tile(np.linspace(0.1, 0.8, len(labels)), (2, 1))
    result = stats.paired_participant_bootstrap(
        labels,
        {"INVENTED_A": scores, "INVENTED_B": scores.copy()},
        [("INVENTED_A", "INVENTED_B")],
        seed=7,
        replicates=20,
    )
    assert result["participant_count"] == 40
    assert result["estimand"] == "mean_per_draw_metric_with_shared_test_participants"
    for metric in ("ap", "auroc", "brier"):
        row = result["contrasts"]["INVENTED_A_minus_INVENTED_B"][metric]
        assert row["estimate"] == row["interval"]["lower"] == row["interval"]["upper"] == 0
