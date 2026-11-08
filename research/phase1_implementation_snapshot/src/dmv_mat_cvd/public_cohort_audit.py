"""Aggregate-only proposed HAALSI/MHAS protocol audit; never trains or locks a test split."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

from .data.public_cohorts import PUBLIC_PROTOCOL_VERSION, audit_release
from .data.releases import file_sha256, safe_relative


def _provenance(root: Path, mapping_path: Path, mapping: dict) -> dict:
    files = {}
    for role, relative in mapping["files"].items():
        path = safe_relative(root, relative)
        files[role] = {"relative_file": relative, "bytes": path.stat().st_size,
                       "sha256": file_sha256(path)}
    return {"mapping_file": str(mapping_path), "mapping_sha256": file_sha256(mapping_path),
            "raw_files": files, "source_repository_catalog": (
                "https://www.icpsr.umich.edu/web/NACDA/studies/36633" if mapping["cohort_name"] == "HAALSI"
                else "https://www.mhasweb.org/DataProducts/HarmonizedData.aspx"),
            "source_repository_verified_for_local_copy": False,
            "release_version_verified_for_local_copy": None,
            "date_received": None, "authorized_user_context": None,
            "local_codebooks_or_manuals": [],
            "verified_join_key": ("unique direct PRIM_KEY" if mapping["cohort_name"] == "HAALSI"
                                  else "biomarker cunicah*100+np to harmonized unhhidnp; EOL unhhidnp"),
            "join_key_semantics_documentation_reviewed": False}


def _criterion(passed: bool, reason: str) -> dict:
    return {"met": bool(passed), "reason": reason}


def public_readiness(reports: dict, config: dict, provenance: dict) -> dict:
    """Independent proposed-protocol assessment; no M4 primary gate is changed."""
    source, target = reports["HAALSI"], reports["MHAS"]
    criteria = {
        "canonical_counts_reconciled": _criterion(
            all(r["waterfall"]["eligible"] + r["waterfall"]["unknown_endpoint_after_predictors"]
                == r["waterfall"]["complete_predictors"] for r in reports.values()),
            "Field-level sentinel normalization and sequential waterfalls reconcile; counts remain candidates pending clinical flags."),
        "predictor_baseline_timing_verified": _criterion(config["baseline_timing_reviewed"],
            "HAALSI Wave 1/2 combined sex and MHAS harmonized/biomarker timing need source-document review."),
        "outcome_semantics_approved": _criterion(config["outcome_semantics_reviewed"],
            "Doctor-reported wave outcome, HAALSI reversals and correction field are not adjudicated clinical MI/stroke."),
        "death_attrition_policy_approved": _criterion(config["attrition_death_policy_reviewed"],
            "Substantial unknown follow-up; MHAS EOL is diagnostic and HAALSI mortality linkage is unverified."),
        "unit_transformations_explicit": _criterion(True,
            "HAALSI mmol/L lipids are multiplied by 38.67; MHAS biomarker lipids are declared mg/dL; source method still requires review."),
        "release_provenance_complete": _criterion(config["release_documentation_reviewed"] and
            all(p["release_version_verified_for_local_copy"] and p["date_received"] and p["authorized_user_context"]
                for p in provenance.values()),
            "Local SHA256s verified; release delivery/version, receipt/context, local manuals/codebooks and join-key documentation are missing."),
        "outlier_decisions_reviewed": _criterion(config["measurement_outliers_reviewed"],
            "Extreme positive BMI/HDL/cholesterol and sparse missing interview months require field-specific review."),
        "leakage_risks_resolved": _criterion(config["baseline_timing_reviewed"] and config["publication_split_authorized"],
            "No fitted preprocessing/training occurred; possible cross-wave predictors and a publication test lock remain unresolved."),
        "target_budget_feasibility_reviewed": _criterion(False,
            "103 observed target events before a publication split. Budgets 10/25/50 may be feasible; 100 cannot be guaranteed after a held-out test and validation allocation."),
        "protocol_scientifically_approved": _criterion(config["scientific_protocol_approved"],
            "PUBLIC_HAALSI_MHAS_PROTOCOL.md is proposed and distinct from the frozen ARIC/MESA clinical protocol."),
    }
    return {"status": "READY" if all(x["met"] for x in criteria.values()) else "BLOCKED",
            "protocol_version": PUBLIC_PROTOCOL_VERSION,
            "primary_aric_mesa_status": "BLOCKED_SEPARATELY_UNCHANGED",
            "criteria": criteria,
            "target_event_budgets": {"10": "candidate_feasible_not_split",
                                     "25": "candidate_feasible_not_split",
                                     "50": "candidate_feasible_not_split",
                                     "100": "not_demonstrated_after_holdout_validation"},
            "target_publication_split_created": False,
            "training_performed": False, "statistical_preprocessing_performed": False,
            "source_candidate": source["waterfall"], "target_candidate": target["waterfall"]}


def run_public_audit(root: str | Path, output_root: str | Path,
                     config_path: str | Path = "configs/public_wave_audit.proposed.json") -> Path:
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("Data root is unavailable")
    config_path = Path(config_path)
    config = json.loads(config_path.read_text())
    if config["protocol_version"] != PUBLIC_PROTOCOL_VERSION:
        raise ValueError("Proposed public protocol version mismatch")
    destination = Path(output_root) / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    destination.mkdir(parents=True, exist_ok=False)
    reports, provenance = {}, {}
    for name, key in (("HAALSI", "source_mapping"), ("MHAS", "target_mapping")):
        mapping_path = Path(config[key])
        mapping = json.loads(mapping_path.read_text())
        if mapping["cohort_name"] != name:
            raise ValueError("Cohort mapping identity mismatch")
        result = audit_release(root, mapping, stroke_correction_field=(
            config["haalsi_stroke_correction_field"] if name == "HAALSI" else None))
        reports[name] = result.report
        provenance[name] = _provenance(root, mapping_path, mapping)
    readiness = public_readiness(reports, config, provenance)
    payload = {"public_readiness": readiness, "cohorts": reports, "provenance": provenance,
               "audit_config_sha256": file_sha256(config_path), "raw_participant_rows_saved": False}
    (destination / "public_readiness.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    (destination / "audit_config.json").write_text(json.dumps(config, indent=2) + "\n")
    lines = [f"PUBLIC_STUDY_STATUS = {readiness['status']}",
             f"Proposed protocol: {PUBLIC_PROTOCOL_VERSION}; ARIC/MESA primary readiness remains separate and blocked."]
    for name, report in reports.items():
        w = report["waterfall"]
        lines.append(f"{name}: raw {w['raw']}; baseline free {w['baseline_free']}; "
                     f"complete predictors {w['complete_predictors']}; unknown endpoint "
                     f"{w['unknown_endpoint_after_predictors']}; candidate {w['eligible']}/{w['incident_events']} events")
    lines.extend(f"[{'x' if item['met'] else ' '}] {name}: {item['reason']}"
                 for name, item in readiness["criteria"].items())
    lines.append("No model training, statistical preprocessing or publication target split occurred.")
    (destination / "public_readiness.txt").write_text("\n".join(lines) + "\n")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=os.environ.get("DMVMAT_CVD_DATA_ROOT"))
    parser.add_argument("--output-root", default="results/public_cohort_audit")
    parser.add_argument("--config", default="configs/public_wave_audit.proposed.json")
    args = parser.parse_args()
    if not args.data_root:
        parser.error("DMVMAT_CVD_DATA_ROOT or --data-root required")
    path = run_public_audit(args.data_root, args.output_root, args.config)
    print(f"Aggregate public-protocol audit: {path}; no training performed")


if __name__ == "__main__":
    main()
