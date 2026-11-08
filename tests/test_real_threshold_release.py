"""Released aggregates and explicit temporary corruption fixtures; no private IO."""

import hashlib
import importlib.util
import json
import re
import shutil
from decimal import Decimal
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "real_aggregate_validation", ROOT / "scripts/validate_real_threshold_release.py"
)
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)
RELEASE = ROOT / "results/haalsi_mhas_real_threshold_analysis"


def test_complete_original_real_release_reconciles():
    report = V.validate()
    assert report["original_aggregate_files"] == 528
    assert report["confusion_matrices"] == report["per_draw_rows"] == 510
    assert report["summary_rows"] == 1140
    assert report["response_plot_files"] == 12
    assert report["all_matrix_cells_and_svg_plot_means_verified"] is True
    assert report["new_training_or_inference"] is False
    assert report["additional_post_run_dashboard_files"] == 1
    assert report["total_released_aggregate_files"] == 529


def rebind_fixture(root, relative):
    # Corruption fixtures deliberately rebind the test copy to exercise semantic
    # checks beyond hashes. No production source/manifest or approval is changed.
    manifest = json.loads((root / "RELEASE_MANIFEST.json").read_text())
    manifest["files"][relative]["sha256"] = hashlib.sha256((root / relative).read_bytes()).hexdigest()
    (root / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest))


@pytest.mark.parametrize(
    "case", ["count", "undefined_precision", "ranking", "summary", "test_selection", "participant_payload"]
)
def test_rebound_corruption_still_fails_semantic_checks(tmp_path, case):
    target = tmp_path / "INVENTED_CORRUPTION_FIXTURE"
    shutil.copytree(RELEASE, target)
    report = json.loads((target / "threshold_sweep.json").read_text())
    condition = report["models"]["calibrated_logical"]["fixed_test_thresholds"][0]
    if case == "count":
        condition["per_draw"][0]["TP"] += 1
    elif case == "undefined_precision":
        report["models"]["calibrated_logical"]["fixed_test_thresholds"][-1]["per_draw"][0]["precision"] = 0
    elif case == "ranking":
        condition["per_draw"][0]["ap"] += 0.01
    elif case == "summary":
        condition["summary"]["recall"]["sd"] += 0.1
    elif case == "test_selection":
        report["test_threshold_selected"] = True
    else:
        report["participant_ids"] = ["INVENTED_FOR_REJECTION_ONLY"]
    (target / "threshold_sweep.json").write_text(json.dumps(report))
    rebind_fixture(target, "threshold_sweep.json")
    with pytest.raises(ValueError):
        V.validate(target)


def test_duplicate_csv_operating_point_rejected_even_with_rebound_hash(tmp_path):
    target = tmp_path / "INVENTED_DUPLICATE_FIXTURE"
    shutil.copytree(RELEASE, target)
    p = target / "threshold_metrics_per_draw.csv"
    lines = p.read_text().splitlines()
    lines[-1] = lines[1]
    p.write_text("\n".join(lines) + "\n")
    rebind_fixture(target, p.name)
    with pytest.raises(ValueError, match="identity"):
        V.validate(target)


def test_zero_denominators_are_unavailable_not_zero():
    negative = V.from_counts(0, 262, 0, 21, Decimal(".50"))
    assert negative["precision"] is None and negative["MCC"] is None
    assert negative["recall"] == negative["f1"] == 0
    positive = V.from_counts(21, 0, 262, 0, Decimal(".05"))
    assert positive["NPV"] is None and positive["recall"] == 1 and positive["specificity"] == 0


def test_svg_identity_and_synthetic_substitution_rejected(tmp_path):
    p = RELEASE / "confusion_matrices/calibrated_logical/draw_0__fixed_0.10.svg"
    target = tmp_path / "INVENTED_WRONG_LABEL.svg"
    target.write_text(p.read_text().replace("calibrated_logical; draw 0", "full_finetune; draw 0"))
    with pytest.raises(ValueError, match="model/draw"):
        V.validate_matrix(
            target, "calibrated_logical", 0, Decimal(".10"), {"TN": 238, "FP": 24, "FN": 17, "TP": 4}
        )
    target.write_text(
        p.read_text().replace("PRIVATE POST-HOC DESCRIPTIVE ANALYSIS", "INVENTED SYNTHETIC EXAMPLE")
    )
    with pytest.raises(ValueError, match="Synthetic"):
        V.svg_tree(target)


def test_plot_marker_tampering_rejected(tmp_path):
    p = RELEASE / "summary_plots/calibrated_logical_threshold_response.svg"
    root, _ = V.svg_tree(p)
    axis = next(n for n in root.iter() if n.attrib.get("id") == "axes_1")
    marker = V.plotted_line_groups(axis, "1.7")[0][0]
    marker.attrib["y"] = str(float(marker.attrib["y"]) + 1)
    target = tmp_path / "INVENTED_CHANGED_MARKER.svg"
    target.write_bytes(ET.tostring(root))
    report = json.loads((RELEASE / "threshold_sweep.json").read_text())
    with pytest.raises(ValueError, match="geometry"):
        V.validate_response(target, "calibrated_logical", report["models"]["calibrated_logical"])


def test_clearance_basis_is_transparent_and_not_an_invented_receipt():
    manifest = json.loads((RELEASE / "RELEASE_MANIFEST.json").read_text())
    basis = manifest["clearance_basis"]
    assert basis["type"] == "RESEARCHER_EXPLICIT_ATTESTATION_IN_CONVERSATION"
    assert basis["separate_documentary_record_provided"] is False
    assert basis["independent_legal_or_institutional_approval_verified_by_codex"] is False
    assert len(manifest["excluded_files"]) == 7
    assert all(not Path(record["source_name"]).is_absolute() for record in manifest["files"].values())
    assert not any(
        "provenance" in name or "completion" in name or "authorization" in name for name in manifest["files"]
    )


@pytest.mark.parametrize("case", ["participant_payload", "count", "network"])
def test_dashboard_corruption_rejected(tmp_path, case):
    original = (RELEASE / "threshold_animation.html").read_text()
    path = tmp_path / "INVENTED_DASHBOARD_FIXTURE.html"
    report = json.loads((RELEASE / "threshold_sweep.json").read_text())
    expected = {
        (model, str(row["draw_id"]), Decimal(str(c["threshold"]))): row
        for model, item in report["models"].items()
        for c in item["fixed_test_thresholds"]
        for row in c["per_draw"]
    }
    match = re.search(r'<script\b[^>]*id="dataset"[^>]*>(.*?)</script>', original, re.S)
    rows = json.loads(match[1])
    if case == "participant_payload":
        rows[0]["participant_id"] = "INVENTED_REJECTION_FIXTURE"
    elif case == "count":
        rows[0]["TP"] += 1
    changed = original[: match.start(1)] + json.dumps(rows) + original[match.end(1) :]
    if case == "network":
        changed += '<script>fetch("https://invalid.example")</script>'
    path.write_text(changed)
    with pytest.raises(ValueError):
        V.validate_dashboard(path, expected)
