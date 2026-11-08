"""Render two approved aggregate comparisons; no clinical inputs or new inference."""

from __future__ import annotations

import argparse
import json
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/aggregate_only_results.json"
NAMES = {
    "source_logistic": "Source logistic",
    "source_xgboost": "Source XGBoost",
    "source_flat_mlp": "Source flat MLP",
    "source_multiview": "Source five-view",
    "head_only": "Head-only",
    "full_finetune": "Full fine-tuning",
    "target_logistic": "Target logistic",
    "target_multiview": "Target-only five-view",
    "fixed_mask": "Fixed fusion",
    "random_calibrated_logical": "Matched random",
    "legacy_topk": "Legacy top-k",
    "calibrated_threshold": "Calibrated threshold",
    "calibrated_logical": "Calibrated logical (primary)",
}
BUDGET_METHODS = ("calibrated_logical", "head_only", "full_finetune", "random_calibrated_logical")


def plot_rows(kind):
    result = json.loads(RESULTS.read_text())
    choices = {
        "auroc": [("primary_25_75", name, "auroc") for name in NAMES],
        "budgets": [
            (budget, name, "ap") for budget in ("primary_25_75", "low_label_10_30") for name in BUDGET_METHODS
        ],
    }
    if kind not in choices:
        raise ValueError("Unknown public comparison")
    rows = []
    for budget, name, metric in choices[kind]:
        data = result["metrics"][budget]
        if (data["participant_count"], data["positive_count"], data["replicates"]) != (283, 21, 2000):
            raise ValueError("Unexpected frozen aggregate contract")
        value = data["models"][name][metric]
        rows.append(
            {
                "budget": budget,
                "model": name,
                "metric": metric,
                "mean": value["mean"],
                "lower": value["interval"]["lower"],
                "upper": value["interval"]["upper"],
            }
        )
    return rows


def render(kind, output):
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    rows = plot_rows(kind)
    output = Path(output)
    if output.suffix.lower() != ".svg" or output.exists():
        raise ValueError("Choose a new SVG output; existing artwork is never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"svg.fonttype": "none", "svg.hashsalt": "dmvmat-public-comparisons-v1"}):
        auroc = kind == "auroc"
        fig, ax = plt.subplots(figsize=(10.6, 6.9 if auroc else 4.8))
        methods = tuple(NAMES) if auroc else BUDGET_METHODS
        for row in rows:
            primary_budget = row["budget"] == "primary_25_75"
            y = methods.index(row["model"]) + (0 if auroc else (-0.15 if primary_budget else 0.15))
            color = "#215f88" if primary_budget else "#9a5924"
            if auroc and row["model"] != "calibrated_logical":
                color = "#666666"
            ax.errorbar(
                row["mean"],
                y,
                xerr=[[row["mean"] - row["lower"]], [row["upper"] - row["mean"]]],
                fmt="o" if primary_budget else "s",
                color=color,
                capsize=3,
                markersize=5,
                linewidth=1.3,
                label=("25 + 75" if primary_budget else "10 + 30")
                if not auroc and row["model"] == methods[0]
                else None,
            )
            ax.text(
                1.025,
                y,
                f"{row['mean']:.6f}",
                transform=ax.get_yaxis_transform(),
                va="center",
                fontsize=9,
                color=color,
            )
        ax.set(
            yticks=range(len(methods)),
            yticklabels=[NAMES[m] for m in methods],
            ylim=(len(methods) - 0.4, -0.7),
            xlim=(0, 1 if auroc else 0.3),
            xlabel="AUROC" if auroc else "Average precision (AP)",
        )
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0, labelsize=10)
        ax.grid(axis="x", alpha=0.18)
        if auroc:
            ax.axvline(0.5, color="#333333", linestyle="--", linewidth=1)
        else:
            ax.legend(
                title="Adaptation labels; stopping labels additional",
                loc="upper center",
                bbox_to_anchor=(0.5, -0.18),
                ncol=2,
                frameon=False,
                fontsize=9,
            )
        title = (
            "All 13 registered methods: primary-budget held-out AUROC"
            if auroc
            else "Primary and secondary adaptation budgets: held-out AP"
        )
        fig.suptitle(title, fontsize=13, y=0.97)
        fig.text(
            0.5,
            0.90 if auroc else 0.86,
            "Same 283 MHAS participants / 21 positive reports; adapted methods average ten paired draws",
            ha="center",
            fontsize=9,
        )
        fig.text(
            0.5,
            0.025,
            "Stored descriptive 95% participant-bootstrap intervals; not paired superiority tests."
            if auroc
            else "Two enriched budgets on one shared test: not a learning curve or independent replication.",
            ha="center",
            fontsize=9,
        )
        fig.subplots_adjust(
            left=0.26, right=0.84, top=0.85 if auroc else 0.76, bottom=0.12 if auroc else 0.32
        )
        buffer = StringIO()
        fig.savefig(
            buffer,
            format="svg",
            metadata={
                "Date": None,
                "Title": title,
                "Description": "Approved aggregate visualization only. Source: results/aggregate_only_results.json. "
                "No raw predictions, new bootstrap, threshold selection or clinical inference.",
            },
        )
        with output.open("x") as stream:
            stream.write("\n".join(line.rstrip() for line in buffer.getvalue().splitlines()) + "\n")
        plt.close(fig)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("auroc", "budgets"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.kind, args.output)
    print("APPROVED_AGGREGATE_FIGURE_CREATED")
