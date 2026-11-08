"""Aggregate-only HAALSI/MHAS onboarding audit. Does not fit or train models."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from .data.real_cohorts import HAALSIAdapter, MHASAdapter
from .data.releases import file_sha256, load_json, safe_relative
from .data.splitting import split_target


def _reference_counts(path: Path) -> dict:
    """Parse prior *aggregate* audit only for reconciliation, never as input to labels."""
    content = path.read_text()
    result = {}
    for name in ("HAALSI", "MHAS"):
        block = re.search(rf"\n{name}\n-+\n(.*?)(?=\n(?:MHAS|DOMAIN SHIFT)\n|\Z)", content, re.S)
        if block is None:
            raise ValueError("Reference audit format is unrecognized")
        n = re.search(r"Final usable (?:source|target) N: ([\d,]+)", block.group(1))
        events = re.search(r"Incident heart attack/stroke events: ([\d,]+)", block.group(1))
        months = re.search(r"follow-up: median ([\d.]+) months", block.group(1))
        if not all((n, events, months)):
            raise ValueError("Reference audit is incomplete")
        result[name] = {"eligible": int(n.group(1).replace(",", "")),
                        "events": int(events.group(1).replace(",", "")),
                        "followup_median_months": float(months.group(1))}
    return result


def run_audit(root: str | Path, output_root: str | Path, *, seed: int = 7,
              target_test_fraction: float = .25,
              reference_path: str | Path = "artifacts/real_data_audit/2026-10-04/cumulative_endpoint_audit.txt") -> Path:
    if not isinstance(seed, int) or not 0 < target_test_fraction < 1:
        raise ValueError("Explicit integer seed and test fraction in (0,1) required")
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("DMVMAT_CVD_DATA_ROOT is not an available directory")
    output = Path(output_root) / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    reference = _reference_counts(Path(reference_path))
    reports = {}
    for name, adapter_class, config_name in (
        ("HAALSI", HAALSIAdapter, "haalsi_wave_m5.provisional.json"),
        ("MHAS", MHASAdapter, "mhas_wave_m5.provisional.json"),
    ):
        config_path = Path("configs/mappings") / config_name
        config = load_json(config_path)
        adapter = adapter_class(config)
        raw, load_counts = adapter.load(root)
        audit = adapter.audit(raw, load_accounting=load_counts)
        report = audit.report
        actual = {"eligible": report["counts"]["historical_reference_eligible"],
                  "events": report["counts"]["historical_reference_events"],
                  "followup_median_months": report["diagnostics"]["followup_months_median"]}
        report["historical_reconciliation"] = {"previous_aggregate": reference[name],
                                                 "independent_recalculation": actual,
                                                 "matches": actual == reference[name]}
        report["gates"]["historical_audit_reconciled"] = actual == reference[name]
        report["ready"] = all(report["gates"].values())
        files = {}
        for role, relative in config["files"].items():
            path = safe_relative(root, relative)
            files[role] = {"file_name": relative, "bytes": path.stat().st_size, "sha256": file_sha256(path)}
        report["provenance"] = {"mapping_file": str(config_path), "mapping_sha256": file_sha256(config_path),
                                "raw_files": files, "audit_source_sha256": file_sha256(reference_path),
                                "release_version": None, "date_received": None,
                                "authorized_user_context": None,
                                "documentation_complete": False,
                                "note": "Checksummed local inputs; release metadata and clinical documentation remain unverified."}
        if name == "MHAS":
            parts = split_target(audit.cohort, test_fraction=target_test_fraction, seed=seed)
            report["target_split"] = {
                "split_seed": seed, "locked_test_fraction": target_test_fraction,
                "split_status": "provisional_audit_only; not a publication test lock because cohort readiness is NO",
                "policy": "participant-only seeded split before any statistical preprocessing; no per-participant rows written",
                "partitions": {role: {"participants": len(partition),
                    "membership_sha256": hashlib.sha256("\n".join(sorted(partition.participant_ids)).encode()).hexdigest()}
                    for role, partition in parts.items()},
                "all_participants_accounted": sum(len(partition) for partition in parts.values()) == len(audit.cohort),
                "no_overlap": sum(len(partition.participant_ids) for partition in parts.values()) == len(audit.cohort),
            }
        reports[name] = report
    combined_ready = all(report["ready"] for report in reports.values())
    summary = {"COHORT_READY": "YES" if combined_ready else "NO", "analysis": "provisional HAALSI-to-MHAS wave-onboarding audit",
               "not_frozen_primary_design": "Frozen method-v1 remains ARIC Visit 1 to MESA Exam 1 with 1826-day first clinical MI/stroke.",
               "training_performed": False, "statistical_preprocessing_performed": False,
               "followup_median_difference_months_source_minus_target":
                   reports["HAALSI"]["diagnostics"]["followup_months_median"] - reports["MHAS"]["diagnostics"]["followup_months_median"],
               "source": reports["HAALSI"], "target": reports["MHAS"],
               "required_sensitivity_analyses": [
                   "Intermediate-positive persistence versus final-wave-only endpoint; report reversal counts",
                   "Missing final-wave outcomes: complete-case versus explicit unknown/attrition analysis",
                   "Compare follow-up length and 60-month observed status by cohort before any fixed-horizon inference",
                   "Assess death before final interview and competing loss once death linkage is validated",
                   "Assess fasting-glucose availability and measurement timing without substituting diabetes/HbA1c",
                   "Reconcile month-level wave timing with exact event dates or retain a separately named wave endpoint"],
               "mandatory_blockers": {name: [gate for gate, passed in report["gates"].items() if not passed]
                                      for name, report in reports.items()}}
    (output / "readiness.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    manifest = {"manifest_status": "incomplete_release_metadata", "method_spec_version": reports["HAALSI"]["method_spec_version"],
                "schema_version": reports["HAALSI"]["schema_version"],
                "cohorts": {name: {"cohort_name": name, **reports[name]["provenance"]} for name in reports},
                "no_participant_records": True}
    (output / "provenance_manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    (output / "audit_config.json").write_text(json.dumps({"seed": seed, "target_test_fraction": target_test_fraction,
        "source_mapping": "configs/mappings/haalsi_wave_m5.provisional.json",
        "target_mapping": "configs/mappings/mhas_wave_m5.provisional.json",
        "reference_aggregate_audit": str(reference_path), "training_performed": False}, indent=2) + "\n")
    lines = [f"COHORT_READY = {summary['COHORT_READY']}", summary["not_frozen_primary_design"]]
    for name, report in reports.items():
        lines += [f"{name}: historical reference {report['counts']['historical_reference_eligible']} eligible / "
                  f"{report['counts']['historical_reference_events']} events; median follow-up "
                  f"{report['diagnostics']['followup_months_median']} months; reference match "
                  f"{report['historical_reconciliation']['matches']}"]
        lines += [f"  [{'x' if passed else ' '}] {gate}" for gate, passed in report["gates"].items()]
        lines += [f"  {key}: {value}" for key, value in report["diagnostics"].items()]
    lines += ["No model training or statistical preprocessing occurred."]
    (output / "readiness.txt").write_text("\n".join(lines) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("DMVMAT_CVD_DATA_ROOT"))
    parser.add_argument("--output-root", default="results/real_onboarding")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--target-test-fraction", type=float, default=.25)
    args = parser.parse_args()
    if not args.data_root:
        parser.error("DMVMAT_CVD_DATA_ROOT or --data-root is required")
    try:
        destination = run_audit(args.data_root, args.output_root, seed=args.seed,
                                target_test_fraction=args.target_test_fraction)
    except Exception as exc:
        parser.exit(2, f"Real-data audit stopped ({type(exc).__name__}); no raw values emitted.\n")
    print(f"Aggregate readiness report: {destination}; no training performed")


if __name__ == "__main__":
    main()
