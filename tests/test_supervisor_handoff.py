"""Public evidence/navigation checks; no academic identifiers or clinical inputs."""

import ast
import importlib.util
import json
from pathlib import Path

import pytest

from dmv_mat_cvd.models.multiview_mlp import MultiViewRiskNet

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("paired_plot", ROOT / "examples/plot_primary_paired_ap.py")
PLOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLOT)
CHECK_SPEC = importlib.util.spec_from_file_location("release_check", ROOT / "scripts/check_public_release.py")
CHECK = importlib.util.module_from_spec(CHECK_SPEC)
CHECK_SPEC.loader.exec_module(CHECK)


def test_clinical_architecture_parameter_count():
    # These are published encoded widths, not clinical records or fitted weights.
    model = MultiViewRiskNet(dict(background=4, haemodynamic=2, metabolic=3, behaviour=4, comorbidity=6))
    assert sum(p.numel() for p in model.parameters()) == 8033
    assert sum(p.numel() for p in model.head.parameters()) == 33
    assert len(model.selectable_modules()) == 7


def test_paired_plot_rows_match_approved_contrasts():
    approved = json.loads((ROOT / "results/aggregate_only_results.json").read_text())
    contrasts = approved["metrics"]["primary_25_75"]["contrasts"]
    rows = PLOT.plot_rows()
    assert len(rows) == 4 and sum(r["primary"] for r in rows) == 1
    assert rows[0]["comparator"] == "full_finetune"
    svg = (ROOT / "figures/08_primary_paired_ap_contrasts.svg").read_text()
    for row in rows:
        value = contrasts["calibrated_logical_minus_" + row["comparator"]]["ap"]
        assert row["estimate"] == value["estimate"]
        assert row["lower"] == value["interval"]["lower"]
        assert row["upper"] == value["interval"]["upper"]
        assert row["lower"] <= 0 <= row["upper"]
        assert f"{row['estimate']:+.6f} [{row['lower']:+.6f}, {row['upper']:+.6f}]" in svg
    assert "Superiority is not established" in svg and "not a new analysis" in svg


def test_paired_plot_refuses_overwriting_reviewed_artwork(tmp_path):
    path = tmp_path / "existing.svg"
    path.write_text("INVENTED EXISTING FILE")
    with pytest.raises(ValueError, match="never overwritten"):
        PLOT.render(path)
    assert path.read_text() == "INVENTED EXISTING FILE"


def test_supervisor_summary_keeps_publication_gaps_explicit():
    guide = (ROOT / "docs/SUPERVISOR_PHASE1_GUIDE.md").read_text()
    approved = json.loads((ROOT / "results/aggregate_only_results.json").read_text())
    for name in approved["metrics"]["primary_25_75"]["models"]:
        assert "`" + name + "`" in guide
    for value in ("0.142664", "0.702854", "0.067654", "+0.001819", "−0.024809", "+0.032340"):
        assert value in guide
    assert "not 3-fold, 5-fold or 10-fold cross-validation" in guide
    assert "ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED" in guide
    mapping = (ROOT / "docs/PHASE1_REPORT_TO_CODE_MAP.md").read_text()
    assert "Original clinical joint-test bootstrap executor is not released" in mapping
    assert "not a complete clinical replay" in mapping


@pytest.mark.parametrize(
    "relative,symbols",
    [
        (
            "src/dmv_mat_cvd/models/multiview_mlp.py",
            ["MultiViewRiskNet", "ViewEncoder", "selectable_modules"],
        ),
        ("src/dmv_mat_cvd/training.py", ["train_model"]),
        ("src/dmv_mat_cvd/data/preprocessing.py", ["Preprocessor", "fit", "transform"]),
        ("src/dmv_mat_cvd/data/cohort_construction.py", ["construct_cohort", "row_endpoint"]),
        ("src/dmv_mat_cvd/data/splitting.py", ["split_source", "split_target", "assert_disjoint"]),
        ("src/dmv_mat_cvd/data/budgets.py", ["sample_event_budget"]),
        (
            "src/dmv_mat_cvd/transfer/calibration.py",
            ["permutation_mmd", "relative_geometry", "calibrated_mask"],
        ),
        (
            "src/dmv_mat_cvd/transfer/adapt.py",
            ["adapt_model", "set_selective_trainability", "frozen_unchanged"],
        ),
        (
            "src/dmv_mat_cvd/transfer/selector.py",
            ["select_adaptation_mask", "random_budget_mask", "diverse_random_budget_mask"],
        ),
        ("src/dmv_mat_cvd/experiments/runner.py", ["run_experiment", "parameter_summary", "seed_everything"]),
        (
            "src/dmv_mat_cvd/thresholds.py",
            ["operating_point", "summarize_draws", "reconcile_ranking", "descriptive_sweep"],
        ),
    ],
)
def test_mapped_public_symbols_exist(relative, symbols):
    tree = ast.parse((ROOT / relative).read_text())
    names = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert set(symbols) <= names
    assert relative.removeprefix("src/") in (ROOT / "docs/PHASE1_REPORT_TO_CODE_MAP.md").read_text()


@pytest.mark.parametrize("relative", ["latex/main.tex", "REPORT.pdf", "unreviewed.svg"])
def test_academic_report_directory_remains_publication_gated(tmp_path, relative):
    p = tmp_path / "reports/nitw-btech-phase1" / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("INVENTED UNAPPROVED ACADEMIC FILE")
    with pytest.raises(ValueError, match="publication review is pending"):
        CHECK.check_file(tmp_path, p.relative_to(tmp_path).as_posix())


def test_report_status_readme_is_allowed_without_manuscript(tmp_path):
    p = tmp_path / "reports/nitw-btech-phase1/README.md"
    p.parent.mkdir(parents=True)
    p.write_text("Report publication pending; no academic identifiers or signatures.")
    assert CHECK.check_file(tmp_path, p.relative_to(tmp_path).as_posix())
