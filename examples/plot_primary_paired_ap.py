"""Replot approved stored contrasts only; no input-data, inference or bootstrap CLI."""

from __future__ import annotations

import argparse
import json
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results/aggregate_only_results.json"
COMPARATORS = (
    ("full_finetune", "Full fine-tuning (primary)"),
    ("head_only", "Head-only (secondary)"),
    ("random_calibrated_logical", "Matched random (secondary)"),
    ("source_multiview", "Source five-view (secondary)"),
)


def plot_rows():
    """Read the four original primary-budget paired AP estimates/intervals."""
    result = json.loads(RESULTS.read_text())
    budget = result["metrics"]["primary_25_75"]
    if budget["participant_count"] != 283 or budget["positive_count"] != 21:
        raise ValueError("Unexpected approved aggregate contract")
    rows = []
    for identifier, label in COMPARATORS:
        value = budget["contrasts"]["calibrated_logical_minus_" + identifier]["ap"]
        rows.append(
            {
                "comparator": identifier,
                "label": label,
                "estimate": value["estimate"],
                "lower": value["interval"]["lower"],
                "upper": value["interval"]["upper"],
                "primary": identifier == "full_finetune",
            }
        )
    return rows


def render(output):
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    rows = plot_rows()
    output = Path(output)
    if output.suffix.lower() != ".svg" or output.exists():
        raise ValueError("Choose a new SVG output; existing artwork is never overwritten")
    output.parent.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"svg.fonttype": "none", "svg.hashsalt": "dmvmat-public-paired-ap-v1"}):
        fig, ax = plt.subplots(figsize=(11, 4.3))
        for y, row in enumerate(rows):
            color = "#215f88" if row["primary"] else "#666666"
            ax.errorbar(
                row["estimate"],
                y,
                xerr=[[row["estimate"] - row["lower"]], [row["upper"] - row["estimate"]]],
                fmt="o",
                capsize=4,
                markersize=6 if row["primary"] else 5,
                linewidth=1.8 if row["primary"] else 1.2,
                color=color,
            )
            ax.text(
                1.025,
                y,
                f"{row['estimate']:+.6f} [{row['lower']:+.6f}, {row['upper']:+.6f}]",
                transform=ax.get_yaxis_transform(),
                va="center",
                fontsize=10,
                color=color,
            )
        ax.axvline(0, color="#333333", linestyle="--", linewidth=1)
        ax.set(
            yticks=range(len(rows)),
            yticklabels=[r["label"] for r in rows],
            xlim=(-0.035, 0.04),
            ylim=(3.5, -0.65),
            xticks=[-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03, 0.04],
            xlabel="Paired AP difference: calibrated logical minus comparator",
        )
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0, labelsize=10)
        ax.grid(axis="x", alpha=0.18)
        ax.text(
            1.025,
            -0.6,
            "Estimate [descriptive 95% interval]",
            transform=ax.get_yaxis_transform(),
            fontsize=10,
        )
        fig.suptitle(
            "Primary 25 + 75 adaptation budget: paired average-precision contrasts", fontsize=13, y=0.97
        )
        fig.text(
            0.5,
            0.875,
            "Ten paired adaptation draws on the same 283 MHAS participants / 21 positive reports",
            ha="center",
            fontsize=10,
        )
        fig.text(
            0.5,
            0.025,
            "Joint participant-bootstrap intervals from approved stored results; every interval includes zero. Superiority is not established.",
            ha="center",
            fontsize=9,
        )
        fig.subplots_adjust(left=0.22, right=0.67, top=0.79, bottom=0.20)
        buffer = StringIO()
        fig.savefig(
            buffer,
            format="svg",
            bbox_inches="tight",
            metadata={
                "Date": None,
                "Title": "Approved primary paired AP contrasts: not a new analysis",
                "Description": "Source: results/aggregate_only_results.json, metrics.primary_25_75.contrasts. Four stored paired AP estimates and joint participant-bootstrap intervals; no private inputs or new bootstrap.",
            },
        )
        with output.open("x") as stream:
            stream.write("\n".join(line.rstrip() for line in buffer.getvalue().splitlines()) + "\n")
        plt.close(fig)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.output)
    print("Approved public paired-contrast visualization created; no clinical processing")
