"""Validate released aggregate files only; never reads participants or private inputs."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path
from statistics import fmean, stdev
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "results/haalsi_mhas_real_threshold_analysis"
GRID = tuple(Decimal(i) / 100 for i in range(5, 51, 5))
MODELS = (
    "calibrated_logical",
    "head_only",
    "full_finetune",
    "random_calibrated_logical",
    "source_multiview",
    "target_logistic",
)
RANKING = ("ap", "auroc", "brier")
CSV_METRICS = (
    "TP",
    "TN",
    "FP",
    "FN",
    "accuracy",
    "precision",
    "recall",
    "specificity",
    "f1",
    "balanced_accuracy",
    "auroc",
    "ap",
    "brier",
)
ALL_METRICS = (
    "threshold",
    "TP",
    "TN",
    "FP",
    "FN",
    "accuracy",
    "precision",
    "recall",
    "sensitivity",
    "specificity",
    "f1",
    "FPR",
    "FNR",
    "NPV",
    "balanced_accuracy",
    "MCC",
    "ap",
    "auroc",
    "brier",
)
POLICY = "FIXED_TEST_GRID_DESCRIPTIVE"
NUM = r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?"


def require(value, message):
    if not value:
        raise ValueError(message)


def equal(got, expected):
    if expected is None:
        require(got is None, "Undefined metric was replaced")
    else:
        require(
            got is not None
            and not isinstance(got, bool)
            and math.isfinite(float(got))
            and math.isclose(float(got), float(expected), abs_tol=1e-8, rel_tol=1e-8),
            "Aggregate metric mismatch",
        )


def number(text):
    return None if text in ("", "N/A", "None", None) else float(text)


def from_counts(tp, tn, fp, fn, threshold):
    require(all(type(n) is int and n >= 0 for n in (tp, tn, fp, fn)), "Noninteger confusion count")
    require(tp + fn == 21 and tn + fp == 262 and tp + tn + fp + fn == 283, "Confusion margins mismatch")

    def div(a, b):
        return a / b if b else None

    recall, specificity = div(tp, tp + fn), div(tn, tn + fp)
    denom = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    return {
        "threshold": float(threshold),
        "TP": tp,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "accuracy": div(tp + tn, 283),
        "precision": div(tp, tp + fp),
        "recall": recall,
        "sensitivity": recall,
        "specificity": specificity,
        "f1": div(2 * tp, 2 * tp + fp + fn),
        "FPR": div(fp, fp + tn),
        "FNR": div(fn, fn + tp),
        "NPV": div(tn, tn + fn),
        "balanced_accuracy": (recall + specificity) / 2,
        "MCC": div(tp * tn - fp * fn, math.sqrt(denom)),
    }


def stats(values):
    valid = [v for v in values if v is not None]
    return {
        "n_defined": len(valid),
        "n_undefined": len(values) - len(valid),
        "mean": fmean(valid) if valid else None,
        "sd": stdev(valid) if len(valid) > 1 else None,
        "min": min(valid) if valid else None,
        "max": max(valid) if valid else None,
    }


def svg_tree(path):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    root = ET.fromstring(path.read_bytes(), parser=parser)
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else "COMMENT"
        require(tag not in {"script", "foreignObject"}, "Active SVG content")
        for attr, value in node.attrib.items():
            if attr.rsplit("}", 1)[-1] in {"href", "src"}:
                require(value.startswith(("#", "data:image/png;base64,")), "External SVG resource")
    comments = [node.text.strip() for node in root.iter() if node.tag is ET.Comment]
    require(
        not any("INVENTED" in s or "SYNTHETIC" in s for s in comments),
        "Synthetic artifact in real collection",
    )
    return root, comments


def validate_matrix(path, model, draw, threshold, row):
    _, comments = svg_tree(path)
    values = [int(s) for s in comments if re.fullmatch(r"\d+", s)]
    require(
        values == [row["TN"], row["FP"], row["FN"], row["TP"]], "SVG confusion orientation/count mismatch"
    )
    require(f"{model}; draw {draw}; cutoff {threshold:.2f}" in comments, "SVG model/draw/cutoff mismatch")
    for label in ("Predicted negative", "Predicted positive", "Observed negative", "Observed positive"):
        require(label in comments, "SVG class-axis label missing")


def plotted_line_groups(axis, width):
    found = []
    for node in axis.iter():
        if not node.attrib.get("id", "").startswith("line2d_"):
            continue
        paths = [c for c in node if isinstance(c.tag, str) and c.tag.endswith("}path")]
        if not any(f"stroke-width:{width}" in c.attrib.get("style", "").replace(" ", "") for c in paths):
            continue
        uses = [c for c in node.iter() if isinstance(c.tag, str) and c.tag.endswith("}use")]
        if uses:
            found.append(uses)
    return found


def axis_transform(axis, coordinate):
    values = []
    for tick in axis.iter():
        if not tick.attrib.get("id", "").startswith(coordinate + "tick_"):
            continue
        comments = [n.text.strip().replace("−", "-") for n in tick.iter() if n.tag is ET.Comment]
        labels = [float(t) for t in comments if re.fullmatch(NUM, t)]
        uses = [
            n
            for n in tick.iter()
            if isinstance(n.tag, str) and n.tag.endswith("}use") and coordinate in n.attrib
        ]
        if labels and uses:
            values.append((labels[-1], float(uses[0].attrib[coordinate])))
    require(len(values) >= 2 and values[0][0] != values[1][0], "Plot tick calibration missing")
    slope = (values[1][1] - values[0][1]) / (values[1][0] - values[0][0])
    offset = values[0][1] - slope * values[0][0]
    require(
        all(abs(slope * data + offset - pixel) < 2e-4 for data, pixel in values), "Plot tick scale mismatch"
    )
    return lambda value: offset + slope * value


def validate_plot_points(axis, uses, thresholds, values):
    xmap, ymap = axis_transform(axis, "x"), axis_transform(axis, "y")
    expected = [(xmap(float(t)), ymap(value)) for t, value in zip(thresholds, values) if value is not None]
    require(len(uses) == len(expected), "Summary plot defined-point count mismatch")
    for marker, (x, y) in zip(uses, expected):
        require(
            abs(float(marker.attrib["x"]) - x) < 2e-4 and abs(float(marker.attrib["y"]) - y) < 2e-4,
            "Summary plot mean geometry mismatch",
        )


def validate_response(path, model, item):
    root, comments = svg_tree(path)
    require(
        f"{model}: {item['draw_count']} fitted score vector(s)" in comments,
        "Response model/draw scope mismatch",
    )
    require(
        any("sample SD" in s and "NOT a confidence interval" in s for s in comments),
        "Response variability label mismatch",
    )
    axes = [n for n in root.iter() if n.attrib.get("id", "").startswith("axes_")]
    require(len(axes) == 6, "Response panel count mismatch")
    for axis, metric in zip(
        axes, ("recall", "specificity", "precision", "f1", "balanced_accuracy", "positive_predictions")
    ):
        conditions = item["fixed_test_thresholds"]
        values = (
            [fmean(row["TP"] + row["FP"] for row in c["per_draw"]) for c in conditions]
            if metric == "positive_predictions"
            else [c["summary"][metric]["mean"] for c in conditions]
        )
        groups = plotted_line_groups(axis, "1.7")
        require(len(groups) == 1, "Response data-series count mismatch")
        validate_plot_points(axis, groups[0], GRID, values)


def validate_comparison(path, report):
    root, comments = svg_tree(path)
    require(all(m.replace("_", " ") in comments for m in report["models"]), "Comparison legend mismatch")
    axes = [n for n in root.iter() if n.attrib.get("id", "").startswith("axes_")]
    require(len(axes) == 4, "Comparison panel count mismatch")
    for axis, metric in zip(axes, ("recall", "specificity", "precision", "f1")):
        groups = plotted_line_groups(axis, "1.5")
        require(len(groups) == len(report["models"]), "Comparison series count mismatch")
        for group, item in zip(groups, report["models"].values()):
            values = [c["summary"][metric]["mean"] for c in item["fixed_test_thresholds"]]
            validate_plot_points(axis, group, GRID, values)


def validate_dashboard(path, expected_rows):
    """Check the separate post-run aggregate dashboard, never participant data."""
    text = path.read_text()
    require(
        not re.search(
            r"fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|https?://|<iframe|<form|<object|<embed|eval\s*\(",
            text,
            re.I,
        ),
        "Dashboard external dependency",
    )
    require(not re.search(r"<(?:script|link|img)[^>]*(?:src|href)\s*=", text, re.I), "Dashboard dependency")
    payloads = re.findall(r'<script\b[^>]*id="dataset"[^>]*>(.*?)</script>', text, re.S)
    require(len(payloads) == 1, "Dashboard dataset missing or ambiguous")
    rows = json.loads(payloads[0])
    schema = {
        "model",
        "draw",
        "threshold",
        "TP",
        "TN",
        "FP",
        "FN",
        "accuracy",
        "precision",
        "recall",
        "specificity",
        "f1",
        "balanced",
        "auroc",
        "ap",
        "brier",
    }
    require(type(rows) is list and len(rows) == 510, "Dashboard row inventory mismatch")
    seen = set()
    for row in rows:
        require(set(row) == schema, "Unexpected dashboard payload")
        key = (row["model"], str(row["draw"]), Decimal(str(row["threshold"])))
        require(key in expected_rows and key not in seen, "Dashboard identity mismatch")
        seen.add(key)
        for metric, value in row.items():
            if metric not in {"model", "draw"}:
                equal(value, expected_rows[key][{"balanced": "balanced_accuracy"}.get(metric, metric)])


def validate(release=RELEASE):
    release = Path(release)
    manifest = json.loads((release / "RELEASE_MANIFEST.json").read_text())
    require(manifest["schema"] == "real-frozen-mhas-aggregate-public-release-v1", "Release schema mismatch")
    basis = manifest["clearance_basis"]
    require(
        basis["type"] == "RESEARCHER_EXPLICIT_ATTESTATION_IN_CONVERSATION"
        and basis["completed_review_attested"] is True
        and basis["independent_legal_or_institutional_approval_verified_by_codex"] is False,
        "Clearance evidence misrepresented",
    )
    for name, binding in manifest["files"].items():
        p = Path(name)
        require(
            not p.is_absolute() and ".." not in p.parts and not (release / p).is_symlink(),
            "Unsafe release file",
        )
        require(p.suffix in {".svg", ".png", ".json", ".csv", ".md"}, "Unapproved release format")
        require(
            hashlib.sha256((release / p).read_bytes()).hexdigest() == binding["sha256"],
            "Original artifact hash mismatch",
        )
    require(len(manifest["files"]) == 528, "Original release count mismatch")
    actual = {p.relative_to(release).as_posix() for p in release.rglob("*") if p.is_file()}
    require(
        actual
        == set(manifest["files"])
        | set(manifest["additional_aggregate_files"])
        | {"RELEASE_MANIFEST.json", "README.md", "VALIDATION_REPORT.json"},
        "Unexpected release file",
    )
    additions = manifest["additional_aggregate_files"]
    require(set(additions) == {"threshold_animation.html"}, "Unexpected additional aggregate")
    dashboard = additions["threshold_animation.html"]
    require(dashboard["source_integrity_bound"] is False, "Post-run provenance misrepresented")
    require(
        hashlib.sha256((release / "threshold_animation.html").read_bytes()).hexdigest()
        == dashboard["sha256"],
        "Dashboard hash mismatch",
    )
    report = json.loads((release / "threshold_sweep.json").read_text())
    require(
        set(report)
        == {
            "schema",
            "analysis",
            "not_new_independent_confirmation",
            "test_threshold_selected",
            "threshold_grid",
            "distinct_test_participants",
            "positive_reports",
            "negative_observations",
            "same_participants_across_draws",
            "probability_ensemble",
            "sd_ddof",
            "ranking_reconciliation",
            "absolute_tolerance",
            "relative_tolerance",
            "validation_status",
            "models",
        },
        "Unexpected report payload",
    )
    require(
        report["probability_ensemble"] is False
        and report["same_participants_across_draws"] is True
        and report["not_new_independent_confirmation"] is True
        and tuple(Decimal(str(t)) for t in report["threshold_grid"]) == GRID,
        "Scientific dependence/grid contract mismatch",
    )
    require(
        report["analysis"] == "SUPPLEMENTARY_DESCRIPTIVE_FROZEN_TEST_THRESHOLD_SWEEP"
        and report["test_threshold_selected"] is False
        and report["sd_ddof"] == 1,
        "Scientific analysis identity mismatch",
    )
    require(
        (report["distinct_test_participants"], report["positive_reports"], report["negative_observations"])
        == (283, 21, 262),
        "Study-population mismatch",
    )
    require(
        report["validation_status"] == "ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED",
        "Validation status mismatch",
    )
    require(set(report["models"]) == set(MODELS), "Real model-family inventory mismatch")
    refs = json.loads(
        (
            ROOT / "results/haalsi_mhas_threshold_sweep_20261107/FROZEN_PUBLIC_METRIC_REFERENCES.json"
        ).read_text()
    )["models"]
    expected_rows, expected_summary = {}, {}
    for model, item in report["models"].items():
        require(
            set(item)
            == {
                "draw_ids",
                "draw_count",
                "fixed_test_thresholds",
                "validation_selected",
                "validation_status",
                "unchanged_ranking",
            },
            "Unexpected model aggregate payload",
        )
        draws = ["source"] if model == "source_multiview" else list(range(10))
        require(
            item["draw_ids"] == draws
            and item["draw_count"] == len(draws)
            and item["validation_selected"] is None,
            "Draw or validation selection mismatch",
        )
        conditions = item["fixed_test_thresholds"]
        require(tuple(Decimal(str(c["threshold"])) for c in conditions) == GRID, "Fixed cutoff grid mismatch")
        previous = {}
        for condition in conditions:
            require(set(condition) == {"threshold", "per_draw", "summary"}, "Unexpected condition payload")
            threshold = Decimal(str(condition["threshold"]))
            require(
                [row["draw_id"] for row in condition["per_draw"]] == draws,
                "Per-condition draw identity mismatch",
            )
            for draw_index, row in enumerate(condition["per_draw"]):
                require(set(row) == {"draw_id", *ALL_METRICS}, "Unexpected aggregate fields")
                calculated = from_counts(row["TP"], row["TN"], row["FP"], row["FN"], threshold)
                for metric, value in calculated.items():
                    equal(row[metric], value)
                for metric in RANKING:
                    equal(row[metric], refs[model][metric]["per_draw"][draw_index])
                key = (model, str(row["draw_id"]), threshold)
                require(key not in expected_rows, "Duplicate operating point")
                expected_rows[key] = row
                if row["draw_id"] in previous:
                    old = previous[row["draw_id"]]
                    require(
                        row["TP"] <= old["TP"] and row["FP"] <= old["FP"], "Threshold monotonicity violated"
                    )
                previous[row["draw_id"]] = row
                validate_matrix(
                    release / f"confusion_matrices/{model}/draw_{row['draw_id']}__fixed_{threshold:.2f}.svg",
                    model,
                    row["draw_id"],
                    threshold,
                    row,
                )
            require(set(condition["summary"]) == set(ALL_METRICS), "Summary metric inventory mismatch")
            for metric in ALL_METRICS:
                summary = stats([row[metric] for row in condition["per_draw"]])
                for name, value in summary.items():
                    equal(condition["summary"][metric][name], value)
                expected_summary[(model, threshold, metric)] = summary
        for metric in RANKING:
            require(
                set(item["unchanged_ranking"][metric]) == {"per_draw", "mean"}
                and len(item["unchanged_ranking"][metric]["per_draw"]) == len(draws),
                "Ranking-vector accounting mismatch",
            )
            for got, expected in zip(
                item["unchanged_ranking"][metric]["per_draw"], refs[model][metric]["per_draw"]
            ):
                equal(got, expected)
            equal(item["unchanged_ranking"][metric]["mean"], refs[model][metric]["mean"])
        validate_response(release / f"summary_plots/{model}_threshold_response.svg", model, item)
    with (release / "threshold_metrics_per_draw.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        require(
            reader.fieldnames == ["model", "policy", "draw_id", "threshold", *CSV_METRICS],
            "Metric CSV schema mismatch",
        )
        rows = list(reader)
    require(len(rows) == len(expected_rows) == 510, "Metric-row count mismatch")
    seen = set()
    for row in rows:
        key = (row["model"], row["draw_id"], Decimal(row["threshold"]))
        require(
            row["policy"] == POLICY and key in expected_rows and key not in seen,
            "CSV operating-point identity mismatch",
        )
        seen.add(key)
        for metric in CSV_METRICS:
            equal(number(row[metric]), expected_rows[key][metric])
    with (release / "threshold_metrics_summary.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        require(
            reader.fieldnames
            == [
                "model",
                "policy",
                "threshold",
                "metric",
                "n_defined",
                "n_undefined",
                "mean",
                "sd",
                "min",
                "max",
            ],
            "Summary CSV schema mismatch",
        )
        rows = list(reader)
    require(len(rows) == len(expected_summary) == 1140, "Summary-row count mismatch")
    seen = set()
    for row in rows:
        key = (row["model"], Decimal(row["threshold"]), row["metric"])
        require(
            row["policy"] == POLICY and key in expected_summary and key not in seen,
            "Summary CSV identity mismatch",
        )
        seen.add(key)
        for metric, value in expected_summary[key].items():
            equal(number(row[metric]), value)
    matrices = list((release / "confusion_matrices").rglob("*.svg"))
    require(len(matrices) == 510, "Matrix-file count mismatch")
    validate_comparison(release / "summary_plots/method_comparison.svg", report)
    validate_dashboard(release / "threshold_animation.html", expected_rows)
    return {
        "original_aggregate_files": 528,
        "additional_post_run_dashboard_files": 1,
        "total_released_aggregate_files": 529,
        "confusion_matrices": 510,
        "model_families": 6,
        "response_plot_files": 12,
        "comparison_plot_files": 2,
        "metric_csv_files": 2,
        "per_draw_rows": 510,
        "summary_rows": 1140,
        "all_matrix_cells_and_svg_plot_means_verified": True,
        "ranking_reconciliation": "MATCHES_ORIGINAL_PUBLIC_PER_DRAW_AND_MEAN_REFERENCES",
        "new_training_or_inference": False,
        "clearance_basis": "RESEARCHER_ATTESTATION_NOT_INDEPENDENT_LEGAL_CERTIFICATION",
        "draw0_selected_counts": [
            {
                "threshold": str(t),
                **{k: expected_rows[("calibrated_logical", "0", t)][k] for k in ("TP", "TN", "FP", "FN")},
            }
            for t in (Decimal(".50"), Decimal(".10"), Decimal(".05"))
        ],
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2, sort_keys=True))
