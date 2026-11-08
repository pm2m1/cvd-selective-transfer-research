"""Predeclared development, freeze, then held-out selector evaluation.

Run with python -m dmv_mat_cvd.experiments.selector_validation.
No predictive outcome participates in selector choice.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid

import numpy as np
import pandas as pd
import torch

from ..config import ExperimentConfig, SELECTOR_POLICIES
from ..data.budgets import InsufficientBudgetData
from ..data.controlled import SCENARIOS, ShiftScenario, VIEWS, generate_controlled_cohort
from ..transfer.calibration import CalibrationConfig
from ..transfer.scores import InsufficientDiscriminability
from .runner import run_experiment
from .validation_metrics import describe, pairwise_mask_jaccard, recovery_metrics, transfer_metrics

METHODS = ("source_only", "head_only", "full", "fixed_mask", *SELECTOR_POLICIES,
           *("random_" + name for name in SELECTOR_POLICIES))


@dataclass(frozen=True)
class Condition:
    phase: str
    family: str
    level: str
    scenario: ShiftScenario

    @property
    def key(self) -> str:
        return self.scenario.name


def condition_grid() -> tuple[tuple[Condition, ...], tuple[Condition, ...]]:
    """Grid fixed before outcomes. Existing M2 cases appear only in development."""
    development = [Condition("DEVELOPMENT", family, level, scenario) for family, level, scenario in zip(
        ("no_shift", "single_view", "two_view", "behaviour", "broad", "concept", "nuisance"),
        ("none", "medium", "medium", "medium", "high", "high", "medium"), SCENARIOS.values())]
    for level, angle in (("low", .4), ("medium", 1.), ("high", 2.2)):
        development.append(Condition("DEVELOPMENT", "rotation", level,
            ShiftScenario(f"dev_rotation_{level}", "rotation", ("haemodynamic",), angle)))
    for level, multiplier in (("low", .5), ("medium", 0.)):
        development.append(Condition("DEVELOPMENT", "concept", level,
            ShiftScenario(f"dev_concept_{level}", "concept", ("haemodynamic",), concept_multiplier=multiplier)))
    for level, magnitude in (("low", .25), ("high", 2.5)):
        development.append(Condition("DEVELOPMENT", "nuisance", level,
            ShiftScenario(f"dev_nuisance_{level}", "nuisance", ("haemodynamic",), magnitude)))
    heldout = [
        Condition("HELD_OUT", "no_shift", "none", ShiftScenario("held_no_shift", teacher_variant="saturating")),
        Condition("HELD_OUT", "single_view", "medium", ShiftScenario("held_metabolic", "measurement", ("metabolic",), .7)),
        Condition("HELD_OUT", "two_view", "medium", ShiftScenario("held_background_behaviour", "measurement", ("background", "behaviour"), 1.3)),
        Condition("HELD_OUT", "broad", "high", ShiftScenario("held_broad", "measurement", VIEWS, 1.8, "saturating")),
    ]
    for level, angle, multiplier, nuisance in (("low", .65, .7, .55), ("medium", 1.4, -.35, 1.6), ("high", 2.7, -1.6, 3.5)):
        heldout.extend((
            Condition("HELD_OUT", "rotation", level, ShiftScenario(f"held_rotation_{level}", "rotation", ("haemodynamic", "metabolic"), angle, "saturating")),
            Condition("HELD_OUT", "concept", level, ShiftScenario(f"held_concept_{level}", "concept", ("metabolic",), teacher_variant="saturating", concept_multiplier=multiplier)),
            Condition("HELD_OUT", "nuisance", level, ShiftScenario(f"held_nuisance_{level}", "nuisance", ("haemodynamic",), nuisance, "saturating")),
        ))
    return tuple(development), tuple(heldout)


def validate_isolation(development: tuple[Condition, ...], heldout: tuple[Condition, ...],
                       development_seeds: tuple[int, ...], heldout_seeds: tuple[int, ...]) -> None:
    if set(development_seeds) & set(heldout_seeds):
        raise ValueError("Development and held-out seeds overlap")
    if not development or not heldout or any(c.phase != "DEVELOPMENT" for c in development) or any(c.phase != "HELD_OUT" for c in heldout):
        raise ValueError("Declare nonempty separate phases")
    def signatures(conditions):
        return {json.dumps({k: v for k, v in asdict(c.scenario).items() if k != "name"}, sort_keys=True) for c in conditions}
    if signatures(development) & signatures(heldout) or {c.key for c in development} & {c.key for c in heldout}:
        raise ValueError("Held-out conditions must differ beyond name or RNG seed")


def choose_on_development(rows: list[dict]) -> dict:
    if not rows or any(row["phase"] != "DEVELOPMENT" for row in rows):
        raise ValueError("Selector choice accepts DEVELOPMENT rows only")
    # Primary scope is all modules. Views-only runs are a sensitivity analysis.
    # Objective weights are declared before any run: recovery, controls, concept,
    # then parsimony. Predictive AP/AUROC/Brier and transfer gains are not read.
    objectives = {}
    for policy in SELECTOR_POLICIES:
        data = [r for r in rows if r["method"] == policy and r["scope"] == "all" and r["status"] == "valid"]
        if not data:
            raise ValueError("All candidate policies need valid development rows")
        controls = [r["false_adaptation_rate"] for r in data if r["family"] in {"no_shift", "nuisance"}]
        concepts = [r["selection_f1"] for r in data if r["family"] == "concept"]
        if not controls or not concepts:
            raise ValueError("Development choice requires controls and concept conditions")
        macro_f1 = float(np.mean([r["selection_f1"] for r in data]))
        false_control = float(np.mean(controls))
        concept_f1 = float(np.mean(concepts))
        fraction = float(np.mean([r["adapted_parameter_fraction"] for r in data]))
        value = macro_f1 - .5 * false_control + .25 * concept_f1 - .05 * fraction
        objectives[policy] = dict(objective=value, mean_f1=macro_f1, control_false_adaptation=false_control,
                                  concept_f1=concept_f1, adapted_parameter_fraction=fraction)
    selected = sorted(objectives, key=lambda p: (-objectives[p]["objective"], p))[0]
    return {"selected_policy": selected, "objectives": objectives,
            "rule": "mean_F1 - 0.5*control_FAR + 0.25*concept_F1 - 0.05*parameter_fraction; all-module scope; lexical ties"}


METRIC_KEYS = ("ap", "auroc", "brier", "transfer_gain_ap", "transfer_gain_auroc", "negative_transfer_ap",
               "negative_transfer_auroc", "selection_precision", "selection_recall", "selection_f1",
               "exact_mask_accuracy", "selection_jaccard", "false_adaptation_rate", "missed_adaptation_rate",
               "adapted_module_count", "adapted_parameter_fraction", "adapted_parameter_count", "false_adaptations", "missed_adaptations")


def summarize(rows: list[dict]) -> dict:
    frame = pd.DataFrame(rows)
    valid = frame[frame.status == "valid"]
    def groups(keys):
        result = []
        for values, part in valid.groupby(keys, sort=True, dropna=False):
            if len(keys) == 1:
                values = (values,) if not isinstance(values, tuple) else values
            item = dict(zip(keys, values))
            item["statistics"] = {key: describe([None if pd.isna(v) else v for v in part[key]]) for key in METRIC_KEYS}
            stability = []
            view_stability = []
            for _, cell in part.groupby(["scenario", "scope", "target_event_budget", "method"]):
                masks = [json.loads(value) for value in cell.module_mask]
                stability.append(pairwise_mask_jaccard(masks))
                view_stability.append(pairwise_mask_jaccard(masks, views_only=True))
            item["mask_stability"] = describe(stability)["mean"]
            item["view_mask_stability"] = describe(view_stability)["mean"]
            result.append(item)
        return result
    return {"valid_rows": len(valid), "invalid_rows": len(frame) - len(valid),
            "groups": groups(["scenario", "family", "level", "scope", "target_event_budget", "method"]),
            "by_family": groups(["family", "scope", "method"]),
            "by_budget": groups(["scope", "target_event_budget", "method"]),
            "pooled": groups(["scope", "method"]),
            "stability_note": "Pairwise across seeds within scenario/budget/scope/method; aggregates average those within-condition stabilities."}


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def legacy_audit(directory: Path, output: Path) -> dict:
    """Read-only reproduction of the M2 audit; hash every preserved artifact."""
    if not directory.exists():
        raise FileNotFoundError(f"Milestone-2 results absent: {directory}")
    rows = pd.read_csv(directory / "per_run.csv")
    scores = pd.read_csv(directory / "module_scores.csv")
    selected = rows[rows.method == "dmv_mat"].copy()
    def counts(row):
        truth = SCENARIOS[row.scenario].ground_truth
        mask = json.loads(row.module_mask)
        return pd.Series({"false_adaptations": sum(mask[k] and v is False for k, v in truth.items()),
                          "missed_adaptations": sum(not mask[k] and v is True for k, v in truth.items())})
    selected = pd.concat([selected, selected.apply(counts, axis=1)], axis=1)
    columns = ["selection_precision", "selection_recall", "selection_f1", "exact_mask_accuracy",
               "false_adaptation_rate", "missed_adaptation_rate", "false_adaptations", "missed_adaptations"]
    selected.groupby(["scenario", "target_event_budget"])[columns].mean().to_csv(output / "legacy_recovery_audit.csv")
    scores["selection_frequency"] = (scores.decision == "ADAPT").astype(float)
    scores.groupby(["scenario", "target_event_budget", "module"])[["selection_frequency", "raw_mmd",
        "radius_normalized_mmd", "discriminability", "adapt_score"]].mean().to_csv(output / "legacy_module_audit.csv")
    random = rows[rows.method == "random_mask"]
    random.groupby(["adapted_parameter_count", "candidate_count"]).agg(
        cells=("seed", "size"), empirical_equality=("same_as_adaptive", "mean")).to_csv(output / "legacy_random_audit.csv")
    manifest = {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(directory.rglob('*')) if p.is_file()}
    result = {"directory": str(directory), "sha256": manifest,
              "random_expected_equality": float((1 / random.candidate_count).mean()),
              "random_empirical_equality": float(random.same_as_adaptive.mean()),
              "unique_budget_cells": int((random.candidate_count == 1).sum()), "cells": len(random)}
    write_json(output / "legacy_artifact_manifest.json", result)
    return result


@dataclass(frozen=True)
class SelectorValidationConfig:
    development_seeds: tuple[int, ...] = tuple(range(5))
    heldout_seeds: tuple[int, ...] = tuple(range(100, 110))
    event_budgets: tuple[int, ...] = (10, 25, 50, 100)
    scopes: tuple[str, ...] = ("all", "views")
    source_n: int = 1200
    target_n: int = 1600
    epochs_source: int = 20
    epochs_target: int = 12
    mmd_max_samples: int = 128
    permutations: int = 199
    bootstraps: int = 199
    output_dir: str = "results/selector_validation"
    legacy_results: str = "results/synthetic_validation/20260924T222643Z-da0fe9b3"

    def __post_init__(self):
        for values in (self.development_seeds, self.heldout_seeds, self.event_budgets, self.scopes):
            if not values or len(set(values)) != len(values):
                raise ValueError("Seeds, budgets and scopes must be nonempty and unique")
        if set(self.scopes) - {"all", "views"} or any(type(x) is not int or x < 2 for x in self.event_budgets):
            raise ValueError("Invalid scopes or event budgets")
        if min(self.source_n, self.target_n, self.epochs_source, self.epochs_target) < 1:
            raise ValueError("Positive cohort sizes and epoch counts required")
        CalibrationConfig(permutations=self.permutations, bootstraps=self.bootstraps)
        validate_isolation(*condition_grid(), self.development_seeds, self.heldout_seeds)


def verify_frozen(protocol: dict, package: Path) -> None:
    if protocol.get("status") != "FROZEN_BEFORE_HELD_OUT" or not protocol.get("development_choice"):
        raise ValueError("Freeze a development choice before held-out access")
    unsigned = {k: v for k, v in protocol.items() if k != "freeze_sha256"}
    if hashlib.sha256(json.dumps(unsigned, sort_keys=True).encode()).hexdigest() != protocol.get("freeze_sha256"):
        raise ValueError("Frozen selector protocol was changed")
    for relative, digest in protocol["code_sha256"].items():
        if hashlib.sha256((package / relative).read_bytes()).hexdigest() != digest:
            raise ValueError("Selector implementation changed after protocol declaration")


def run_selector_validation(cfg: SelectorValidationConfig | None = None) -> dict:
    cfg = cfg or SelectorValidationConfig()
    torch.set_num_threads(1)
    output = Path(cfg.output_dir) / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    development, heldout = condition_grid()
    calibration = CalibrationConfig(permutations=cfg.permutations, bootstraps=cfg.bootstraps)
    package = Path(__file__).parents[1]
    code_hashes = {str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in sorted(package.rglob('*.py'))}
    protocol = {"configuration": asdict(cfg), "calibration": asdict(calibration),
                "development_conditions": [asdict(c) for c in development],
                "heldout_conditions": [asdict(c) for c in heldout], "code_sha256": code_hashes,
                "selection_objective": "mean_F1 - 0.5*control_FAR + 0.25*concept_F1 - 0.05*parameter_fraction",
                "random_tolerance_fraction": .005, "source_preprocessing": "source_fitted",
                "fixed_policy_forms": {"calibrated_threshold": "(R<.5 and U<1) or (domain_p<=.05 and R<.8 and U<1)",
                                       "calibrated_logical": "U<.75 or (domain_p<=.05 and R<.8 and U<1)"},
                "status": "DEVELOPMENT", "created": datetime.now(timezone.utc).isoformat()}
    write_json(output / "selector_config.json", protocol)
    audit = legacy_audit(Path(cfg.legacy_results), output)
    rows, modules, masks = [], [], []
    def flush():
        for name, data in (("per_run.csv", rows), ("module_scores.csv", modules), ("masks.csv", masks)):
            pd.DataFrame(data).to_csv(output / name, index=False)
    def phase(conditions, seeds):
        if conditions[0].phase == "HELD_OUT":
            frozen = json.loads((output / "selector_config.json").read_text())
            verify_frozen(frozen, package)
        for condition in conditions:
            for seed in seeds:
                source = generate_controlled_cohort(cfg.source_n, "source", seed, condition.scenario)
                target = generate_controlled_cohort(cfg.target_n, "target", seed + 10000, condition.scenario)
                for budget in cfg.event_budgets:
                    for scope in cfg.scopes:
                        identity = dict(phase=condition.phase, scenario=condition.key, family=condition.family,
                                        level=condition.level, magnitude=condition.scenario.magnitude,
                                        concept_multiplier=condition.scenario.concept_multiplier,
                                        teacher=condition.scenario.teacher_variant, seed=seed,
                                        target_event_budget=budget, scope=scope)
                        try:
                            result = run_experiment(source, target, ExperimentConfig(
                                seed=seed, target_event_budget=budget, modes=METHODS, selector_scope=scope,
                                epochs_source=cfg.epochs_source, epochs_target=cfg.epochs_target,
                                lr_head=.0007, lr_full=.0007, lr_selective=.0007,
                                calibration=calibration, mmd_max_samples=cfg.mmd_max_samples,
                                device="cpu", output_dir=str(output / "runs")))
                        except (InsufficientBudgetData, InsufficientDiscriminability) as exc:
                            rows.extend({**identity, "method": method, "status": "invalid", "reason": str(exc)} for method in METHODS)
                            continue
                        for method, metrics in result["target_metrics"].items():
                            detail = result["methods"][method]
                            mask = {k: v == "ADAPT" for k, v in detail["mask"].items()}
                            truth = condition.scenario.ground_truth
                            row = {**identity, "method": method, "status": "valid", "reason": "",
                                   **{k: metrics[k] for k in ("ap", "auroc", "brier")},
                                   **transfer_metrics(metrics, result["target_metrics"]["source_only"]),
                                   **recovery_metrics(mask, truth),
                                   "false_adaptations": sum(mask[k] and v is False for k, v in truth.items()),
                                   "missed_adaptations": sum(not mask[k] and v is True for k, v in truth.items()),
                                   "module_mask": json.dumps(mask, sort_keys=True), "adapted_module_count": sum(mask.values()),
                                   **{k: detail[k] for k in ("adapted_parameter_count", "adapted_parameter_fraction")},
                                   "adaptation_size": result["adaptation_size"], "adaptation_events": result["adaptation_events"],
                                   "adaptation_fingerprint": detail.get("adaptation_participant_fingerprint"),
                                   "target_validation_size": result["splits"]["target_validation"]["observed_rows"],
                                   "frozen_integrity": detail["frozen_integrity"]["ok"],
                                   **{k: detail.get(k) for k in ("candidate_count", "exact_candidate_count", "parameter_budget_error",
                                                               "equality_probability", "same_as_adaptive")}}
                            rows.append(row)
                            masks.append({**identity, "method": method, "module_mask": row["module_mask"],
                                          "adapted_parameter_fraction": row["adapted_parameter_fraction"]})
                        for name, score in result["module_scores"].items():
                            for policy in SELECTOR_POLICIES:
                                modules.append({**identity, "selector": policy, "module": name, **score,
                                    **result["calibration_scores"][name], "ground_truth": truth[name],
                                    "legacy_adapt_score": score["adapt_score"],
                                    "decision": "ADAPT" if result["policy_masks"][policy][name] else "SHARE",
                                    "selected": result["policy_masks"][policy][name],
                                    "selection_reason": result["policy_reasons"][policy][name]})
            flush()
            print(f"{condition.phase} {condition.key}: completed {len(seeds)} seeds; {output}", flush=True)
    phase(development, cfg.development_seeds)
    development_summary = summarize(rows)
    choice = choose_on_development(rows)
    write_json(output / "development_summary.json", {**development_summary, "choice": choice})
    protocol.update(status="FROZEN_BEFORE_HELD_OUT", development_choice=choice,
                    frozen_at=datetime.now(timezone.utc).isoformat())
    protocol["freeze_sha256"] = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    write_json(output / "selector_config.json", protocol)
    write_json(output / "frozen_selector_config.json", protocol)
    # The choice and policy source hashes are now persisted. Held-out metrics
    # cannot flow back into the choice function, and all policies stay frozen.
    phase(heldout, cfg.heldout_seeds)
    heldout_summary = summarize([row for row in rows if row["phase"] == "HELD_OUT"])
    heldout_summary.update(selected_policy=choice["selected_policy"], freeze_sha256=protocol["freeze_sha256"],
                           finished_at=datetime.now(timezone.utc).isoformat())
    write_json(output / "heldout_summary.json", heldout_summary)
    for relative, digest in audit["sha256"].items():
        if hashlib.sha256((Path(cfg.legacy_results) / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError("A preserved Milestone-2 artifact changed")
    return {"output_directory": str(output), "choice": choice, "heldout_summary": heldout_summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development-seeds', type=int, nargs='+', default=list(range(5)))
    parser.add_argument('--heldout-seeds', type=int, nargs='+', default=list(range(100, 110)))
    parser.add_argument('--event-budgets', type=int, nargs='+', default=[10, 25, 50, 100])
    for name, default in (("epochs-source", 20), ("epochs-target", 12), ("permutations", 199), ("bootstraps", 199)):
        parser.add_argument('--' + name, type=int, default=default)
    parser.add_argument('--output-dir', default='results/selector_validation')
    args = vars(parser.parse_args())
    for key in ('development_seeds', 'heldout_seeds', 'event_budgets'):
        args[key] = tuple(args[key])
    result = run_selector_validation(SelectorValidationConfig(**args))
    print(json.dumps({"output_directory": result["output_directory"], "choice": result["choice"]}, indent=2))


if __name__ == '__main__':
    main()
