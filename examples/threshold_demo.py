"""Invented-data-only threshold demonstration. No clinical file input accepted."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from dmv_mat_cvd.thresholds import RANKING, descriptive_sweep, operating_point


def confusion_svg(row):
    """Rows are actual negative/positive; columns predicted negative/positive."""
    if any(type(row[k]) is not int or row[k] < 0 for k in ("TN", "FP", "FN", "TP")):
        raise ValueError("A confusion matrix requires integer counts from one draw")
    cells = (("TN", 0, 0), ("FP", 1, 0), ("FN", 0, 1), ("TP", 1, 1))
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" viewBox="0 0 640 420">',
        '<rect width="640" height="420" fill="white"/>',
        '<g font-family="sans-serif" fill="#172b3a" text-anchor="middle">',
        '<text x="320" y="30" font-size="20">SYNTHETIC ONLY — invented observations</text>',
        '<text x="320" y="58" font-size="14">One draw; probability threshold 0.50; no clinical evidence</text>',
        '<text x="370" y="92" font-size="18">Predicted label</text>',
        '<text x="270" y="122">Negative (0)</text><text x="450" y="122">Positive (1)</text>',
        '<text x="78" y="250" font-size="18" transform="rotate(-90 78 250)">Actual label</text>',
        '<text x="150" y="200">Negative (0)</text><text x="150" y="310">Positive (1)</text>',
    ]
    for label, col, row_index in cells:
        x, y = 185 + col * 180, 145 + row_index * 110
        parts.extend(
            [
                f'<rect x="{x}" y="{y}" width="170" height="100" fill="#e8f0f5" stroke="#38576b"/>',
                f'<text x="{x + 85}" y="{y + 57}" font-size="23">{label} = {row[label]}</text>',
            ]
        )
    parts.append(
        '<text x="320" y="400" font-size="14">Each cell is an integer count in one invented population.</text></g></svg>'
    )
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New unused synthetic output directory")
    args = parser.parse_args()
    rng = np.random.default_rng(20261107)
    labels = np.r_[np.ones(12, dtype=int), np.zeros(68, dtype=int)]
    scores = rng.uniform(0, 0.6, (10, len(labels)))
    baseline = [operating_point(labels, p) for p in scores]
    reference = {
        key: {"per_draw": [r[key] for r in baseline], "mean": float(np.mean([r[key] for r in baseline]))}
        for key in RANKING
    }
    report = descriptive_sweep(labels, scores, reference=reference)
    report["analysis"] = "SYNTHETIC_ONLY_NO_CLINICAL_FINDING"
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "SYNTHETIC_summary.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    (args.output / "SYNTHETIC_confusion.svg").write_text(confusion_svg(baseline[0]))
    print("SYNTHETIC_ONLY_COMPLETE: 10 invented draws, 10 fixed thresholds; no clinical inputs")


if __name__ == "__main__":
    main()
