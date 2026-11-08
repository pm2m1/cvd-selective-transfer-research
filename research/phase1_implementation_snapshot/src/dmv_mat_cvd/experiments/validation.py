"""Repeated-seed controlled selector benchmark; no changes to the clinical design."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable
import uuid

import numpy as np

from ..config import ALL_MODES, ExperimentConfig
from ..data.budgets import InsufficientBudgetData
from ..data.controlled import SCENARIOS, generate_controlled_cohort
from ..transfer.scores import InsufficientDiscriminability, multi_kernel_mmd, normalize_representations
from ..transfer.selector import select_adaptation_mask
from .runner import run_experiment
from .validation_metrics import describe, pairwise_mask_jaccard, recovery_metrics, transfer_metrics

VALIDATION_METHODS = ("source_only", "head_only", "full", "fixed_mask", "random_mask", "dmv_mat")


@dataclass(frozen=True)
class ValidationConfig:
    seeds: tuple[int, ...] = tuple(range(10))
    event_budgets: tuple[int, ...] = (10, 25, 50, 100)
    scenarios: tuple[str, ...] = tuple(SCENARIOS)
    methods: tuple[str, ...] = VALIDATION_METHODS
    source_n: int = 1200
    target_n: int = 1600
    epochs_source: int = 20
    epochs_target: int = 12
    learning_rate_target: float = 7e-4
    mmd_max_samples: int = 128
    device: str = "cpu"
    output_dir: str = "results/synthetic_validation"

    def __post_init__(self) -> None:
        if not self.seeds or len(set(self.seeds)) != len(self.seeds) or any(type(seed) is not int or seed < 0 for seed in self.seeds):
            raise ValueError("Provide unique nonnegative integer seeds")
        if not self.event_budgets or len(set(self.event_budgets)) != len(self.event_budgets) or any(type(b) is not int or b < 2 for b in self.event_budgets):
            raise ValueError("Provide unique event budgets >= 2")
        if not self.scenarios or set(self.scenarios) - set(SCENARIOS) or len(set(self.scenarios)) != len(self.scenarios):
            raise ValueError("Provide unique known scenarios")
        if (set(VALIDATION_METHODS) - set(self.methods) or set(self.methods) - set(ALL_MODES)
                or len(set(self.methods)) != len(self.methods)):
            raise ValueError("The six required validation methods must be included; additional baseline modes are optional")
        if min(self.source_n, self.target_n) < 20:
            raise ValueError("Validation cohort sizes must be at least 20")
        # Reuse the existing training configuration validation.
        ExperimentConfig(epochs_source=self.epochs_source, epochs_target=self.epochs_target,
                         lr_selective=self.learning_rate_target, mmd_max_samples=self.mmd_max_samples)


def mmd_comparability_audit(seed: int = 90210, replicates: int = 10, n: int = 64) -> dict:
    """Controlled diagnostics, not a new selector or a permutation significance test.

    All dimensions have unit per-coordinate variance; shifted means have a
    fixed Euclidean displacement relative to the reference RMS radius.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for dimension in (4, 16, 32, 64):
        for replicate in range(replicates):
            source, target = rng.normal(size=(2, n, dimension))
            for shifted in (False, True):
                comparison = target.copy()
                if shifted:
                    comparison[:, 0] += .8 * np.sqrt(dimension)
                for scale in (.1, 1., 10.):
                    left, right = source * scale, comparison * scale
                    normalized_left, normalized_right, _ = normalize_representations(left, right)
                    rows.append({"dimension": dimension, "replicate": replicate, "shifted": shifted,
                                 "scale": scale, "raw_mmd": multi_kernel_mmd(left, right),
                                 "radius_mmd": multi_kernel_mmd(normalized_left, normalized_right)})
    groups = defaultdict(list)
    invariance = defaultdict(list)
    for row in rows:
        groups[row["dimension"], row["shifted"], row["scale"]].append(row)
        invariance[row["dimension"], row["replicate"], row["shifted"]].append(row["radius_mmd"])
    return {
        "seed": seed, "replicates": replicates, "samples_per_domain": n,
        "maximum_radius_mmd_difference_under_rescaling": max(max(values) - min(values) for values in invariance.values()),
        "groups": [{"dimension": dim, "shifted": shifted, "scale": scale,
                    "raw_mmd": describe(row["raw_mmd"] for row in values),
                    "radius_mmd": describe(row["radius_mmd"] for row in values)}
                   for (dim, shifted, scale), values in groups.items()],
        "interpretation": "Source RMS corrects common scale and coordinate duplication; it does not equalize arbitrary layer null distributions or sample-size bias. No policy was tuned using this audit.",
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value
                          for key, value in row.items()} for row in rows)


def summarize_runs(rows: list[dict], masks: list[dict]) -> dict:
    groups, stability = defaultdict(list), defaultdict(list)
    for row in rows:
        groups[row["scenario"], row["target_event_budget"], row["method"]].append(row)
    metrics = ("ap", "auroc", "brier", "transfer_gain_ap", "transfer_gain_auroc",
               "negative_transfer_ap", "negative_transfer_auroc", "selection_precision", "selection_recall",
               "selection_f1", "exact_mask_accuracy", "false_adaptation_rate", "missed_adaptation_rate",
               "selection_jaccard", "adapted_parameter_fraction", "adaptation_size", "adaptation_events",
               "parameter_budget_error", "candidate_count", "same_as_adaptive")
    summaries = []
    for (scenario, budget, method), values in groups.items():
        valid = [row for row in values if row["status"] == "valid"]
        summaries.append({"scenario": scenario, "target_event_budget": budget, "method": method,
                          "requested_runs": len(values), "valid_runs": len(valid),
                          "statistics": {key: describe(row.get(key) for row in valid) for key in metrics}})
    for row in masks:
        stability[row["scenario"], row["target_event_budget"], row["method"]].append(row["module_mask"])
    return {"groups": summaries,
            "mask_stability": [{"scenario": s, "target_event_budget": b, "method": m,
                                "seeds": len(values),
                                "mean_pairwise_jaccard_all_modules": pairwise_mask_jaccard(values),
                                "mean_pairwise_jaccard_views": pairwise_mask_jaccard(values, views_only=True)}
                               for (s, b, m), values in stability.items()]}


def run_validation(config: ValidationConfig, progress: Callable[[str], None] | None = None) -> dict:
    started = datetime.now(timezone.utc)
    output = Path(config.output_dir) / f"{started:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    # Save the declared grid before any training or outcomes are observed.
    (output / "configuration.json").write_text(json.dumps(asdict(config), indent=2) + "\n")
    rows, module_rows, mask_rows, failures = [], [], [], []
    total = len(config.scenarios) * len(config.seeds) * len(config.event_budgets)
    completed = 0
    for scenario_name in config.scenarios:
        scenario = SCENARIOS[scenario_name]
        for seed in config.seeds:
            source = generate_controlled_cohort(config.source_n, "source", seed, scenario)
            target = generate_controlled_cohort(config.target_n, "target", seed + 100, scenario)
            for budget in config.event_budgets:
                identifiers = {"scenario": scenario_name, "seed": seed, "target_event_budget": budget}
                cfg = ExperimentConfig(
                    seed=seed, target_event_budget=budget, epochs_source=config.epochs_source,
                    epochs_target=config.epochs_target, lr_head=config.learning_rate_target,
                    lr_full=config.learning_rate_target, lr_selective=config.learning_rate_target,
                    lr_target_only=config.learning_rate_target, modes=config.methods,
                    mmd_max_samples=config.mmd_max_samples, device=config.device, output_dir=str(output / "runs"),
                )
                try:
                    result = run_experiment(source, target, cfg)
                except (InsufficientBudgetData, InsufficientDiscriminability) as exc:
                    failure = {**identifiers, "status": "invalid", "reason": str(exc)}
                    failures.append(failure)
                    for method in config.methods:
                        rows.append({**failure, "method": method, "ap": None, "auroc": None, "brier": None,
                                     "transfer_gain_ap": None, "transfer_gain_auroc": None,
                                     "negative_transfer_ap": None, "negative_transfer_auroc": None,
                                     "module_mask": None, "adapted_parameter_count": None,
                                     "adapted_parameter_fraction": None})
                else:
                    raw_scores = {name: {"mmd": value["raw_mmd"], "discriminability": value["discriminability"]}
                                  for name, value in result["module_scores"].items()}
                    raw_mask, raw_adapt_scores = select_adaptation_mask(raw_scores, cfg.discrepancy_weight, cfg.adapt_fraction)
                    mask_rows.append({**identifiers, "method": "raw_mmd_diagnostic", "diagnostic_only": True,
                                      "module_mask": raw_mask, **recovery_metrics(raw_mask, scenario.ground_truth)})
                    for name, value in result["module_scores"].items():
                        truth = scenario.ground_truth[name]
                        module_rows.append({**identifiers, "module": name,
                                            "discriminability": value["discriminability"], "discriminability_status": "valid",
                                            "raw_mmd": value["raw_mmd"], "radius_normalized_mmd": value["mmd"],
                                            "minmax_mmd": value["normalized_mmd"],
                                            "minmax_discriminability": value["normalized_discriminability"],
                                            "normalization_scale": value["normalization_scale"],
                                            "adapt_score": value["adapt_score"], "decision": value["decision"],
                                            "ground_truth": "UNDEFINED" if truth is None else "ADAPT" if truth else "SHARE",
                                            "ground_truth_basis": "teacher_local_predictive_mapping",
                                            "raw_mmd_adapt_score": raw_adapt_scores[name],
                                            "raw_mmd_decision": "ADAPT" if raw_mask[name] else "SHARE",
                                            "mmd_source_samples": min(config.mmd_max_samples, result["splits"]["source_validation"]["observed_rows"]),
                                            "mmd_target_samples": min(config.mmd_max_samples, result["adaptation_size"])})
                    for method, scores in result["target_metrics"].items():
                        detail = result["methods"][method]
                        mask = {name: state == "ADAPT" for name, state in detail["mask"].items()} if "mask" in detail else None
                        recovery = recovery_metrics(mask, scenario.ground_truth) if mask is not None else {}
                        row = {**identifiers, "method": method, "status": "valid", "reason": None,
                               "ap": scores["ap"], "auroc": scores["auroc"], "brier": scores["brier"],
                               **transfer_metrics(scores, result["target_metrics"]["source_only"]),
                               "module_mask": mask, "adapted_parameter_count": detail.get("adapted_parameter_count"),
                               "adapted_parameter_fraction": detail.get("adapted_parameter_fraction"),
                               "adaptation_size": result["adaptation_size"], "adaptation_events": result["adaptation_events"],
                               "target_validation_size": result["splits"]["target_validation"]["observed_rows"],
                               "adaptation_participant_fingerprint": detail.get("adaptation_participant_fingerprint"),
                               "frozen_integrity": detail.get("frozen_integrity", {}).get("ok"),
                               "parameter_budget_error": detail.get("parameter_budget_error"),
                               "candidate_count": detail.get("candidate_count"), "same_as_adaptive": detail.get("same_as_adaptive"),
                               "experiment_id": result["experiment_id"], **recovery}
                        rows.append(row)
                        if mask is not None:
                            mask_rows.append({**identifiers, "method": method, "diagnostic_only": False,
                                              "module_mask": mask, **recovery})
                completed += 1
                # Flush summaries per cell for inspectable progress and interrupted runs.
                write_csv(output / "per_run.csv", rows)
                write_csv(output / "module_scores.csv", module_rows)
                write_csv(output / "masks.csv", mask_rows)
                if progress:
                    progress(f"[{completed}/{total}] {scenario_name} seed={seed} events={budget}")
    summary = {
        "config": asdict(config), "started": started.isoformat(),
        "finished": datetime.now(timezone.utc).isoformat(), "output_directory": str(output),
        "total_cells": total, "valid_cells": total - len(failures), "invalid_cells": failures,
        "scenarios": {name: {**asdict(SCENARIOS[name]), "ground_truth": SCENARIOS[name].ground_truth}
                      for name in config.scenarios},
        "selector_policy": "unchanged Milestone 1 min-max/top-k re-engineered DMV-MAT-style selector",
        "recovery_basis": "view-local teacher mechanism changes; fusion ground truth undefined; learned encoder updates are not uniquely identifiable",
        "negative_transfer_definition": "strictly lower AP/AUROC than the paired source-only model; reported separately",
        "standard_deviation": "sample standard deviation (ddof=1); 0 for one valid observation",
        "empty_set_convention": "Jaccard and F1 are 1 if both ADAPT sets are empty; precision/recall and error rates with zero denominators are null",
        "sampling": "nested random adaptation-pool prefix ending at E-th event; >=2 controls required; separate validation supervision is additional",
        "mmd_comparability_audit": mmd_comparability_audit(),
        **summarize_runs(rows, mask_rows),
    }
    # Raw-MMD ablation concerns mask recovery only; no predictive results are implied.
    diagnostics = defaultdict(list)
    for row in mask_rows:
        if row["diagnostic_only"]:
            diagnostics[row["scenario"], row["target_event_budget"]].append(row)
    summary["raw_mmd_recovery_diagnostic"] = [
        {"scenario": s, "target_event_budget": b,
         "selection_f1": describe(row["selection_f1"] for row in values),
         "exact_mask_accuracy": describe(row["exact_mask_accuracy"] for row in values)}
        for (s, b), values in diagnostics.items()]
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(10)))
    parser.add_argument("--event-budgets", nargs="+", type=int, default=[10, 25, 50, 100])
    parser.add_argument("--scenarios", nargs="+", choices=list(SCENARIOS), default=list(SCENARIOS))
    parser.add_argument("--methods", nargs="+", choices=ALL_MODES, default=list(VALIDATION_METHODS))
    parser.add_argument("--source-n", type=int, default=1200)
    parser.add_argument("--target-n", type=int, default=1600)
    parser.add_argument("--epochs-source", type=int, default=20)
    parser.add_argument("--epochs-target", type=int, default=12)
    parser.add_argument("--mmd-max-samples", type=int, default=128)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output-dir", default="results/synthetic_validation")
    options = vars(parser.parse_args())
    for name in ("seeds", "event_budgets", "scenarios", "methods"):
        options[name] = tuple(options[name])
    summary = run_validation(ValidationConfig(**options), progress=lambda message: print(message, flush=True))
    print(f"Completed {summary['valid_cells']}/{summary['total_cells']} valid cells. Results: {summary['output_directory']}")


if __name__ == "__main__":
    main()
