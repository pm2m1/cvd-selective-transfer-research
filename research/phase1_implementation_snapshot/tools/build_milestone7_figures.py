"""Render Milestone 7 figures from frozen public aggregates only.

This script has no cohort loader, model import, private path, or command-line
input. Input SHA256 values are pinned to the completed development/final runs.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "results/final_research/m7_aggregate_figures"
INPUTS = {
    "final": ("results/real_training/m6c_final_test_v2_recovery/aggregate_only_results.json",
              'WITHHELD_REFERENCE_BINDING'),
    "baseline": ("results/real_training/m6a_20261025_dev_baselines_v4/development_metrics.csv",
                 'WITHHELD_REFERENCE_BINDING'),
    "selector_runs": ("results/real_training/m6b_20261025_selector_v1/per_run.csv",
                      'WITHHELD_REFERENCE_BINDING'),
    "selector_summary": ("results/real_training/m6b_20261025_selector_v1/summary.json",
                         'WITHHELD_REFERENCE_BINDING'),
    "masks": ("results/real_training/m6b_20261025_selector_v1/masks.csv",
              'WITHHELD_REFERENCE_BINDING'),
}


def verified_path(key: str) -> Path:
    relative, expected = INPUTS[key]
    path = ROOT / relative
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError(f"Frozen aggregate changed: {relative}")
    return path


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUTPUT / f"{name}.svg", bbox_inches="tight", facecolor="white")
    fig.savefig(OUTPUT / f"{name}.png", dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def box(ax: plt.Axes, xy: tuple[float, float], size: tuple[float, float],
        text: str, color: str = "#ecf3f8", fontsize: int = 11) -> None:
    x, y = xy
    w, h = size
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                facecolor=color, edgecolor="#41576c", linewidth=1))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize)


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float]) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=12,
                                 linewidth=1.2, color="#41576c"))


def cohort_flow() -> None:
    fig, ax = plt.subplots(figsize=(12, 4.3))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.set_title("Frozen public-study cohorts and target partitions", loc="left", fontsize=15)
    box(ax, (.02, .63), (.23, .23), "HAALSI Wave 1 source\n2,906 / 107 reports", "#e8f2e8")
    box(ax, (.02, .14), (.23, .23), "MHAS 2012 target\n1,133 / 83 reports", "#e7f0fa")
    for x, text in [(.32, "Source train\n1,744 / 65"),
                    (.54, "Source validation\n581 / 21"),
                    (.76, "Source held-out\n581 / 21 (unused)")]:
        box(ax, (x, .63), (.20, .23), text, "#e8f2e8")
    for x, text, color in [(.32, "Target adaptation pool\n679 / 49", "#e7f0fa"),
                           (.54, "Target validation\n171 / 13", "#fff2d7"),
                           (.76, "Immutable target test\n283 / 21", "#fbe8e7")]:
        box(ax, (x, .14), (.20, .23), text, color)
    arrow(ax, (.25, .745), (.31, .745))
    arrow(ax, (.25, .255), (.31, .255))
    ax.text(.01, .01, "Values are participants / positive reports. Test performance was produced by one authorized recovery after a failed first access.",
            fontsize=9, color="#485768")
    save(fig, "01_cohort_flow")


def architecture_workflow() -> None:
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.set_title("Five-view network and frozen module-selection workflow", loc="left", fontsize=15)
    views = ["Background\nage · sex", "Haemodynamic\nSBP · DBP",
             "Metabolic\nBMI · total cholesterol\nHDL", "Behaviour\nsmoking",
             "Comorbidity / medication\ndiabetes · treatment"]
    for i, label in enumerate(views):
        x = .01 + i * .195
        box(ax, (x, .70), (.18, .19), label, "#e7f0fa", 9)
        arrow(ax, (x + .09, .70), (x + .09, .55))
        box(ax, (x, .44), (.18, .11), f"Encoder {i + 1}", "#eff5e8", 9)
        arrow(ax, (x + .09, .44), (.46, .33))
    box(ax, (.37, .23), (.25, .10), "Fusion 1 → Fusion 2", "#fff2d7")
    arrow(ax, (.62, .28), (.70, .28))
    box(ax, (.70, .23), (.25, .10), "Binary prediction head", "#fbe8e7")
    box(ax, (.10, .01), (.80, .14),
        "Detached source/target representations → calibrated MMD + class geometry\n"
        "→ SHARE / ADAPT mask", "#f1ecf8", 9)
    ax.text(.12, .18, "MMD selects modules; optimization uses classification loss only.",
            fontsize=9, color="#485768")
    save(fig, "02_architecture_selector")


def validation_chart(baseline: list[dict[str, str]], selector: list[dict[str, str]]) -> None:
    by_method: dict[str, list[float]] = defaultdict(list)
    for row in baseline:
        if row["budget"] == "primary_25_75" and row["method"] in {"head_only", "full_finetune"}:
            by_method[row["method"]].append(float(row["ap"]))
    for row in selector:
        if row["budget"] == "primary_25_75":
            by_method[row["method"]].append(float(row["ap"]))
    names = ["head_only", "full_finetune", "fixed_mask", "random_calibrated_logical",
             "legacy_topk", "calibrated_threshold", "calibrated_logical"]
    names = [n for n in names if n in by_method]
    labels = [n.replace("_", " ") for n in names]
    values = [mean(by_method[n]) for n in names]
    errs = [stdev(by_method[n]) for n in names]
    fig, ax = plt.subplots(figsize=(10, 4.7))
    ax.barh(labels[::-1], values[::-1], xerr=errs[::-1], color="#54789c", ecolor="#20394e", capsize=3)
    ax.set_xlabel("Validation average precision, mean ± SD across ten overlapping draws")
    ax.set_title("Development validation: 25 + 75 target labels, 171 participants / 13 reports", loc="left")
    ax.set_xlim(0, max(v + e for v, e in zip(values, errs)) * 1.18)
    ax.grid(axis="x", alpha=.22)
    save(fig, "03_validation_ap")


def final_ap_chart(final: dict) -> None:
    b = final["metrics"]["primary_25_75"]
    names = ["source_multiview", "head_only", "full_finetune", "fixed_mask",
             "random_calibrated_logical", "legacy_topk", "calibrated_threshold", "calibrated_logical"]
    y = list(range(len(names)))
    vals = [b["models"][n]["ap"]["mean"] for n in names]
    low = [b["models"][n]["ap"]["interval"]["lower"] for n in names]
    high = [b["models"][n]["ap"]["interval"]["upper"] for n in names]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.errorbar(vals, y, xerr=[[v - l for v, l in zip(vals, low)],
                            [h - v for h, v in zip(high, vals)]], fmt="o", capsize=3,
                color="#24567d", ecolor="#7895aa")
    ax.set_yticks(y, [n.replace("_", " ") for n in names])
    ax.set_xlim(.05, .28)
    ax.set_xlabel("Locked-test average precision (joint participant-bootstrap 95% interval)")
    ax.set_title("Held-out MHAS test: 25 + 75 labels, 283 participants / 21 reports", loc="left")
    ax.grid(axis="x", alpha=.22)
    ax.text(.05, len(names) + .35,
            "Intervals resample the same test participants jointly across all frozen draws; methods are correlated.",
            fontsize=9, color="#485768")
    ax.set_ylim(-.7, len(names) + .7)
    save(fig, "04_final_test_ap")


def parameter_tradeoff(final: dict, selector: list[dict[str, str]]) -> None:
    b = final["metrics"]["primary_25_75"]["models"]
    sizes: dict[str, list[float]] = defaultdict(list)
    for row in selector:
        if row["budget"] == "primary_25_75":
            sizes[row["method"]].append(float(row["adapted_fraction"]))
    sizes.update({"head_only": [33 / 8033], "full_finetune": [1.0],
                  "source_multiview": [0.0]})
    fig, ax = plt.subplots(figsize=(10, 5.3))
    annotations = {
        "source_multiview": (8, 0, "source only"),
        "head_only": (8, -18, "head only"),
        "random_calibrated_logical": (8, -5, "matched random"),
        "calibrated_logical": (8, 17, "logical = threshold"),
        "fixed_mask": (-75, 16, "fixed mask"),
        "legacy_topk": (-80, -12, "legacy top-k"),
        "full_finetune": (-80, -18, "full fine-tuning"),
    }
    for name in annotations:
        x = mean(sizes[name]) * 100
        y = b[name]["ap"]["mean"]
        ax.scatter(x, y, s=65, color="#24567d" if name == "calibrated_logical" else "#7591a7")
        dx, dy, label = annotations[name]
        ax.annotate(label, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8)
    ax.set(xlabel="Trainable fraction of 8,033-parameter multiview network (%)",
           ylabel="Locked-test mean AP",
           title="Parameter economy does not establish a predictive advantage")
    ax.set_xlim(-4, 110)
    ax.set_ylim(.128, .150)
    ax.grid(alpha=.22)
    save(fig, "05_parameters_vs_test_ap")


def selection_frequency(summary: dict) -> None:
    freq = summary["module_selection_frequency"]
    modules = ["view:background", "view:haemodynamic", "view:metabolic", "view:behaviour",
               "view:comorbidity_medication", "fusion1", "fusion2"]
    methods = ["calibrated_logical", "calibrated_threshold", "legacy_topk", "fixed_mask"]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    data = [[freq[f"primary_25_75:{method}"][module] for module in modules] for method in methods]
    image = ax.imshow(data, vmin=0, vmax=1, cmap="Blues", aspect="auto")
    for i, row in enumerate(data):
        for j, value in enumerate(row):
            ax.text(j, i, f"{value:.0%}", ha="center", va="center", fontsize=9,
                    color="white" if value >= .6 else "#20394e")
    ax.set_xticks(range(len(modules)), [m.replace("view:", "").replace("_", " ") for m in modules],
                  rotation=30, ha="right")
    ax.set_yticks(range(len(methods)), [m.replace("_", " ") for m in methods])
    ax.set_title("Primary-budget module selection frequency across ten development draws", loc="left")
    fig.colorbar(image, ax=ax, label="Fraction of draws selected")
    save(fig, "06_module_selection_frequency")


def audit_timeline() -> None:
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    ax.set_title("Frozen experiment and disclosed final-test recovery", loc="left", fontsize=15)
    steps = [("Protocol + lock", "fixed target split"),
             ("6A / 6B", "frozen checkpoints"),
             ("6C-0", "184 bindings\n2,000 bootstraps"),
             ("6C-2", "failed test access\nno metrics"),
             ("6C-5", "authorized recovery\none result")]
    for i, (title, subtitle) in enumerate(steps):
        x = .01 + i * .20
        box(ax, (x, .37), (.18, .35), title + "\n" + subtitle,
            "#fbe8e7" if i == 3 else ("#e8f2e8" if i == 4 else "#e7f0fa"), 8)
        if i < len(steps) - 1:
            arrow(ax, (x + .18, .545), (x + .20, .545))
    ax.text(.01, .19, "Recovery retained the original test membership, models, masks and registered estimands.",
            fontsize=10, color="#485768")
    save(fig, "07_audit_timeline")


def main() -> None:
    paths = {key: verified_path(key) for key in INPUTS}
    final = json.loads(paths["final"].read_text())
    summary = json.loads(paths["selector_summary"].read_text())
    with paths["baseline"].open(newline="") as handle:
        baseline = list(csv.DictReader(handle))
    with paths["selector_runs"].open(newline="") as handle:
        selector = list(csv.DictReader(handle))
    with paths["masks"].open(newline="") as handle:
        masks = list(csv.DictReader(handle))
    assert final["participant_count"] == 283 and final["positive_reports"] == 21
    assert len(selector) == 100 and len(masks) == 100
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cohort_flow()
    architecture_workflow()
    validation_chart(baseline, selector)
    final_ap_chart(final)
    parameter_tradeoff(final, selector)
    selection_frequency(summary)
    audit_timeline()
    print(f"Created seven SVG and seven PNG aggregate-only figures in {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
