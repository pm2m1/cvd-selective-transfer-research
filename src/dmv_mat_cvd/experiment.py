"""Backward-compatible synthetic CLI backed by the common cohort runner."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import ALL_MODES, ExperimentConfig
from .data.synthetic import SyntheticDomainConfig, generate_cohort
from .experiments.runner import choose_device, loader, run_experiment


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical synthetic DMV-MAT-CVD experiment")
    parser.add_argument("--config", type=Path, help="JSON object of ExperimentConfig settings")
    parser.add_argument("--source-n", type=int, default=8000)
    parser.add_argument("--target-n", type=int, default=3000)
    for name in ("seed", "epochs-source", "epochs-target", "batch-size", "patience", "target-event-budget"):
        parser.add_argument(f"--{name}", type=int)
    for name in ("adapt-fraction", "target-test-fraction", "target-adaptation-fraction", "threshold"):
        parser.add_argument(f"--{name}", type=float)
    parser.add_argument("--preprocessing-policy", choices=["source_fitted", "target_adaptation"])
    parser.add_argument("--threshold-policy", choices=["fixed", "validation_f1"])
    parser.add_argument("--selector-policy", choices=["legacy_topk", "calibrated_threshold", "calibrated_logical"])
    parser.add_argument("--selector-scope", choices=["all", "views"])
    parser.add_argument("--device")
    parser.add_argument("--output-dir")
    parser.add_argument("--modes", nargs="+", choices=ALL_MODES)
    parser.add_argument("--fixed-mask", nargs="*")
    parser.add_argument("--legacy-mmd", action="store_true", help="Use original unnormalized MMD for ablation")
    args = parser.parse_args()
    options = json.loads(args.config.read_text()) if args.config else {}
    for name, value in vars(args).items():
        if name not in {"config", "source_n", "target_n", "legacy_mmd"} and value is not None:
            options[name] = tuple(value) if name in {"modes", "fixed_mask"} else value
    if args.legacy_mmd:
        options["mmd_normalize"] = False
    cfg = ExperimentConfig(**options)
    result = run_experiment(
        generate_cohort(SyntheticDomainConfig(args.source_n, "source", cfg.seed)),
        generate_cohort(SyntheticDomainConfig(args.target_n, "target", cfg.seed + 100)), cfg,
    )
    print(f"Experiment: {result['experiment_id']}  Device: {result['device']}")
    print(f"View dimensions: {result['model_configuration']['view_dims']}")
    def fmt(value):
        return "undefined" if value is None else f"{value:.4f}"
    for name, values in result["target_metrics"].items():
        print(f"{name:20s} AP={fmt(values['ap'])}  AUROC={fmt(values['auroc'])}  Brier={fmt(values['brier'])}")
    for name, values in result["module_scores"].items():
        print(f"{name:30s} disc={fmt(values['discriminability'])} MMD={values['mmd']:.4f} -> {values['decision']}")
    for name, values in result["transfer_gains"].items():
        detail = result["methods"][name]
        print(f"{name}: gain AP={fmt(values['transfer_gain_ap'])}, gain AUROC={fmt(values['transfer_gain_auroc'])}, "
              f"adapted={detail['adapted_parameter_fraction']:.1%}, frozen integrity={detail['frozen_integrity']['ok']}")
    print(f"Results: {result['output_directory']}/results.json")


if __name__ == "__main__":
    main()
