"""Check public reporting against frozen aggregates; never reads private reports."""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import mean
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
METRICS = ("ap", "auroc", "brier")
BUDGETS = ("primary_25_75", "low_label_10_30")
LABELS = {
    "source_logistic": "Source logistic regression",
    "source_xgboost": "Source XGBoost",
    "source_flat_mlp": "Source flat MLP",
    "source_multiview": "Source five-view network",
    "head_only": "Head-only fine-tuning",
    "full_finetune": "Full fine-tuning",
    "target_logistic": "Target logistic regression",
    "target_multiview": "Target-only five-view network",
    "fixed_mask": "Fixed fusion mask",
    "random_calibrated_logical": "Parameter-matched random",
    "legacy_topk": "Legacy top-k",
    "calibrated_threshold": "Calibrated threshold",
    "calibrated_logical": "Calibrated logical",
}


def require(condition, issue):
    if not condition:
        raise ValueError(issue)


def table_rows(text):
    rows = []
    for line in text.splitlines():
        if line.startswith("|"):
            rows.append([v.strip().replace("**", "").replace("`", "") for v in line.strip("|").split("|")])
    return rows


def method_row(text, label):
    found = [r for r in table_rows(text) if r[0] == label]
    require(len(found) == 1, "Missing or duplicate reported model")
    return found[0]


def validate_aggregate(result):
    for budget in BUDGETS:
        data = result["metrics"][budget]
        require(
            (data["participant_count"], data["positive_count"], data["replicates"]) == (283, 21, 2000),
            "Frozen evaluation contract mismatch",
        )
        require(set(data["models"]) == set(LABELS), "Registered model inventory mismatch")
        for name, item in data["models"].items():
            for metric in METRICS:
                value = item[metric]
                require(
                    len(value["per_draw"]) == (1 if name.startswith("source_") else 10),
                    "Source checkpoint or adapted draw count mismatch",
                )
                require(
                    math.isclose(mean(value["per_draw"]), value["mean"], abs_tol=1e-12, rel_tol=0),
                    "Stored per-draw mean mismatch",
                )
                interval = value["interval"]
                require(0 <= interval["lower"] <= interval["upper"] <= 1, "Metric interval mismatch")
                require(
                    (interval["valid_replicates"], interval["discarded_replicates"]) == (2000, 0),
                    "Bootstrap accounting mismatch",
                )
        c = data["contrasts"]["calibrated_logical_minus_full_finetune"]["ap"]
        difference = (
            data["models"]["calibrated_logical"]["ap"]["mean"] - data["models"]["full_finetune"]["ap"]["mean"]
        )
        require(
            math.isclose(difference, c["estimate"], abs_tol=1e-12, rel_tol=0),
            "Paired point estimate mismatch",
        )


def check(root=ROOT):
    result = json.loads((root / "results/aggregate_only_results.json").read_text())
    validate_aggregate(result)
    baseline = (root / "docs/phase1/baselines-and-results.md").read_text()
    primary, secondary = baseline.split("## Secondary 10+30: all registered methods")
    for budget, text in zip(BUDGETS, (primary, secondary)):
        for name, item in result["metrics"][budget]["models"].items():
            require(
                method_row(text, name)[1:] == [f"{item[m]['mean']:.6f}" for m in METRICS],
                "Six-decimal baseline table mismatch",
            )
    manuscript = (root / "docs/FINAL_SUBMISSION_MANUSCRIPT.md").read_text()
    supplement = (root / "docs/SUPPLEMENTARY_AGGREGATE_RESULTS.md").read_text()
    blocks = supplement.split("## Across-draw variation")[0].split("### Secondary 10 + 30 adaptation labels")
    for budget, text in zip(BUDGETS, blocks):
        for name, label in LABELS.items():
            values = result["metrics"][budget]["models"][name]
            row_label = label + (
                ", prespecified primary" if name == "calibrated_logical" and budget == BUDGETS[0] else ""
            )
            row = method_row(text, row_label)
            expected = [
                f"{values['ap']['mean']:.4f} ({values['ap']['interval']['lower']:.4f}, {values['ap']['interval']['upper']:.4f})",
                f"{values['auroc']['mean']:.4f}",
                f"{values['brier']['mean']:.4f}",
            ]
            require(row[1:] == expected, "Frozen supplement table mismatch")
    for name, label in LABELS.items():
        label += ": prespecified primary" if name == "calibrated_logical" else ""
        expected = [f"{result['metrics'][BUDGETS[0]]['models'][name][m]['mean']:.4f}" for m in METRICS]
        require(method_row(manuscript, label)[1:] == expected, "Frozen manuscript table mismatch")
    readme = (root / "README.md").read_text()
    for name, label in {
        "source_multiview": "Source-only five-view network",
        "head_only": "Head-only fine-tuning",
        "full_finetune": "Full fine-tuning",
        "calibrated_logical": "Calibrated logical, prespecified primary",
    }.items():
        expected = [f"{result['metrics'][BUDGETS[0]]['models'][name][m]['mean']:.6f}" for m in METRICS]
        require(method_row(readme, label)[1:] == expected, "README result table mismatch")
    key = result["metrics"][BUDGETS[0]]["models"]["calibrated_logical"]
    contrast = result["metrics"][BUDGETS[0]]["contrasts"]["calibrated_logical_minus_full_finetune"]["ap"]
    for relative in ("README.md", "docs/SUPERVISOR_PHASE1_GUIDE.md", "docs/PHASE1_RESULTS_GALLERY.md"):
        text = (root / relative).read_text()
        for value in [
            *(f"{key[m]['mean']:.6f}" for m in METRICS),
            f"{contrast['estimate']:+.6f}",
            f"−{abs(contrast['interval']['lower']):.6f}",
            f"{contrast['interval']['upper']:+.6f}",
        ]:
            require(value in text, "Public summary value missing or mismatched")
    for figure, kind in (("09_all13_primary_auroc.svg", "auroc"), ("10_primary_secondary_ap.svg", "budgets")):
        text = " ".join(ElementTree.fromstring((root / "figures" / figure).read_text()).itertext())
        pairs = (
            [(BUDGETS[0], name, "auroc") for name in LABELS]
            if kind == "auroc"
            else [
                (b, n, "ap")
                for b in BUDGETS
                for n in ("calibrated_logical", "head_only", "full_finetune", "random_calibrated_logical")
            ]
        )
        for budget, name, metric in pairs:
            require(
                f"{result['metrics'][budget]['models'][name][metric]['mean']:.6f}" in text,
                "Public figure value missing or mismatched",
            )
    return {
        "budgets": 2,
        "registered_models": 13,
        "metric_summaries": 78,
        "manuscript_rows": 13,
        "supplement_rows": 26,
        "new_figure_points": 21,
    }


if __name__ == "__main__":
    try:
        report = check()
    except (ValueError, OSError, KeyError, json.JSONDecodeError, ElementTree.ParseError):
        raise SystemExit("STOP: public result consistency failed; inspect public evidence") from None
    print("PASS: public result consistency " + json.dumps(report, sort_keys=True))
