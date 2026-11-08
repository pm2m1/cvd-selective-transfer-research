"""Catch public reporting drift without clinical inputs, PDFs or private readers."""

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load("scripts/check_result_consistency.py", "consistency")
PLOT = load("examples/plot_public_comparisons.py", "comparison_plot")


def copy_public_evidence(tmp_path):
    paths = [
        "results/aggregate_only_results.json",
        "README.md",
        "docs/phase1/baselines-and-results.md",
        "docs/FINAL_SUBMISSION_MANUSCRIPT.md",
        "docs/SUPPLEMENTARY_AGGREGATE_RESULTS.md",
        "docs/SUPERVISOR_PHASE1_GUIDE.md",
        "docs/PHASE1_RESULTS_GALLERY.md",
        "figures/09_all13_primary_auroc.svg",
        "figures/10_primary_secondary_ap.svg",
    ]
    for name in paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)


def test_all_13_methods_two_budgets_and_public_outputs_agree():
    report = CHECK.check()
    assert report == {
        "budgets": 2,
        "registered_models": 13,
        "metric_summaries": 78,
        "manuscript_rows": 13,
        "supplement_rows": 26,
        "new_figure_points": 21,
    }


@pytest.mark.parametrize(
    "relative,old",
    [
        ("README.md", "0.142664"),
        ("docs/phase1/baselines-and-results.md", "0.140706"),
        ("docs/FINAL_SUBMISSION_MANUSCRIPT.md", "| 0.0946 |"),
        ("docs/SUPPLEMENTARY_AGGREGATE_RESULTS.md", "0.0946 (0.0562, 0.1608)"),
        ("docs/SUPERVISOR_PHASE1_GUIDE.md", "0.702854"),
        ("docs/PHASE1_RESULTS_GALLERY.md", "0.067654"),
        ("figures/09_all13_primary_auroc.svg", "0.702854"),
        ("figures/10_primary_secondary_ap.svg", "0.140706"),
    ],
)
def test_changed_report_or_figure_fails_closed(tmp_path, relative, old):
    copy_public_evidence(tmp_path)
    target = tmp_path / relative
    text = target.read_text()
    assert old in text
    target.write_text(text.replace(old, "0.999999"))
    with pytest.raises(ValueError):
        CHECK.check(tmp_path)


@pytest.mark.parametrize("alteration", ["mean", "draws", "replicates", "model_inventory"])
def test_inconsistent_aggregate_contract_is_detected(alteration):
    result = json.loads((ROOT / "results/aggregate_only_results.json").read_text())
    result = copy.deepcopy(result)
    budget = result["metrics"]["primary_25_75"]
    if alteration == "mean":
        budget["models"]["calibrated_logical"]["ap"]["mean"] += 0.01
    elif alteration == "draws":
        budget["models"]["source_logistic"]["ap"]["per_draw"] *= 10
    elif alteration == "replicates":
        budget["replicates"] = 100
    else:
        del budget["models"]["full_finetune"]
    with pytest.raises(ValueError):
        CHECK.validate_aggregate(result)


@pytest.mark.parametrize("kind,count", [("auroc", 13), ("budgets", 8)])
def test_all_public_plot_records_match_original_means_and_intervals(kind, count):
    result = json.loads((ROOT / "results/aggregate_only_results.json").read_text())
    rows = PLOT.plot_rows(kind)
    assert len(rows) == count
    for row in rows:
        value = result["metrics"][row["budget"]]["models"][row["model"]][row["metric"]]
        assert (row["mean"], row["lower"], row["upper"]) == (
            value["mean"],
            value["interval"]["lower"],
            value["interval"]["upper"],
        )


@pytest.mark.parametrize("kind", ["auroc", "budgets"])
def test_comparison_renderer_preserves_existing_artwork(tmp_path, kind):
    target = tmp_path / "existing.svg"
    target.write_text("INVENTED EXISTING ARTWORK")
    with pytest.raises(ValueError, match="never overwritten"):
        PLOT.render(kind, target)
    assert target.read_text() == "INVENTED EXISTING ARTWORK"


def test_gallery_covers_all_public_figures_and_labels_synthetic_evidence():
    gallery = (ROOT / "docs/PHASE1_RESULTS_GALLERY.md").read_text()
    figures = list((ROOT / "figures").glob("*.svg"))
    assert len(figures) == 11
    for path in figures:
        assert f"../figures/{path.name}" in gallery
    assert "Synthetic illustration only" in gallery
    assert "not cross-validation" in gallery
    assert "ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED" in gallery
