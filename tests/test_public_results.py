"""Documentation numbers must come from the existing approved aggregate JSON."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_documented_primary_table_matches_approved_values():
    result = json.loads((ROOT / "results/aggregate_only_results.json").read_text())
    models = result["metrics"]["primary_25_75"]["models"]
    text = (ROOT / "docs/phase1/baselines-and-results.md").read_text()
    for name, item in models.items():
        assert (
            "| "
            + name
            + " | "
            + " | ".join(f"{item[k]['mean']:.6f}" for k in ("ap", "auroc", "brier"))
            + " |"
            in text
        )


def test_registered_contrast_and_scope_remain_explicit():
    result = json.loads((ROOT / "results/aggregate_only_results.json").read_text())
    contrast = result["metrics"]["primary_25_75"]["contrasts"]["calibrated_logical_minus_full_finetune"]["ap"]
    readme = (ROOT / "README.md").read_text()
    assert f"+{contrast['estimate']:.6f}" in readme
    assert f"−{abs(contrast['interval']['lower']):.6f}" in readme
    assert f"+{contrast['interval']['upper']:.6f}" in readme
    assert "Statistically established superiority was not demonstrated" in readme
    assert "ORIGINAL_VALIDATION_OPTIMAL_THRESHOLD_NOT_ESTABLISHED" in readme
