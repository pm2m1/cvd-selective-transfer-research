"""Read-only, aggregate-only prelock validation of the separate public protocol."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

import pandas as pd

from .data.public_v2 import (PUBLIC_V2_VERSION, SCHEMA_VERSIONS, VIEWS_NINE, VIEWS_TEN,
    construct_haalsi_v2, construct_mhas_v2)
from .data.public_cohorts import audit_public_cohort
from .data.real_cohorts import HAALSIAdapter, MHASAdapter, join_mhas_master_followup
from .data.releases import file_sha256
from .public_evidence_reconciliation import MASTER_COLUMNS


DELEGATED_GOVERNANCE_VERSION = "public-haalsi-mhas-governance-amendment-v1"
_DELEGATED_DOCUMENTS = {
    "governance_amendment_sha256": "PUBLIC_GOVERNANCE_AMENDMENT_V1.adopted.md",
    "methodology_review_sha256": "PUBLIC_CVD_ENDPOINT_METHODOLOGY_REVIEW.md",
    "supervisor_direction_sha256": "PUBLIC_SUPERVISOR_DIRECTION_M5J.md",
}


def delegated_review_documents_valid(record: dict) -> bool:
    """Verify a documented internal review; this grants no lock authorization."""
    repo = Path(__file__).resolve().parents[2]
    return (record.get("governance_amendment_version") == DELEGATED_GOVERNANCE_VERSION and
            record.get("governance_amendment_status") == "adopted_internal_only" and
            all((repo / name).is_file() and record.get(field) == file_sha256(repo / name)
                for field, name in _DELEGATED_DOCUMENTS.items()))


def event_reserve_plan(events: int, nonevents: int, budget: int, *,
                       test_fraction: float = .25, validation_fraction: float = .2,
                       test_floor: int = 15, validation_floor: int = 10) -> dict:
    """Conservative event arithmetic only; this never assigns participants."""
    if min(events, nonevents, budget, test_floor, validation_floor) < 0 or budget == 0:
        raise ValueError("Event plan counts/budget invalid")
    if not (0 < test_fraction < 1 and 0 < validation_fraction < 1):
        raise ValueError("Event plan fractions invalid")
    import math
    test = max(test_floor, math.ceil(events * test_fraction))
    validation = max(validation_floor, math.ceil((events - test) * validation_fraction))
    available = max(0, events - test - validation)
    # Controls are counted before any split; each future partition needs both
    # classes. Do not claim a test set exists from this arithmetic.
    controls_feasible = nonevents >= 6
    return {"events_total": events, "nonevents_total": nonevents,
            "test_events_reserved": test, "validation_events_reserved": validation,
            "adaptation_events_available": available, "requested_adaptation_events": budget,
            "arithmetic_feasible": available >= budget and controls_feasible,
            "actual_split_created": False,
            "limits": "Proposed floors are not a power calculation; actual seeded lock may differ."}


def readiness_evidence(config: dict, source: dict, target: dict, *,
                       provenance_ok: bool, locked_runner_reviewed: bool = False) -> dict:
    """Technical evidence and outstanding approvals are kept separate."""
    if config.get("protocol_version") != PUBLIC_V2_VERSION:
        raise ValueError("Public v2 identity required; primary ARIC/MESA identity forbidden")
    if config.get("source") != "HAALSI Wave 1" or config.get("target") != "MHAS Wave 3/2012 examination":
        raise ValueError("Public source/target identities are fixed")
    gates = {
        "unique_wave1_respondent_roster_match": source["diagnostics"]["sex"]["unmatched"] == 0 and
                                            source["diagnostics"]["sex"]["multiple"] == 0,
        "source_endpoint_rule_applied": source["protocol_version"] == PUBLIC_V2_VERSION,
        "target_exam_landmark_applied": target["diagnostics"]["landmark"]["window_days"] == 30,
        "same_five_view_contract": source["schema_version"] == target["schema_version"],
        "aggregate_release_provenance_recorded": provenance_ok,
        "public_locked_runner_reviewed": locked_runner_reviewed,
        "no_model_or_publication_split": not source["training_performed"] and
                                        not target["training_performed"] and
                                        not source["publication_split_created"] and
                                        not target["publication_split_created"],
    }
    pending = {
        "ten_feature_diabetes_comparability_final_choice": config.get("final_schema_signoff") == "approved",
        "clinical_or_governance_endpoint_review_if_required": (
            config.get("clinical_endpoint_signoff") == "approved" or
            (config.get("clinical_endpoint_signoff") == "not_required_documented" and
             delegated_review_documents_valid(config))),
        "event_floors_and_one_time_test_governance": config.get("statistical_event_reserve_signoff") == "approved",
        "separate_public_locked_execution_review": config.get("public_publication_lock") == "approved",
    }
    ready = all(gates.values()) and all(pending.values())
    return {"technical_gates": gates, "approval_gates": pending,
            "COHORT_READY": "YES" if ready else "NO",
            "status": "READY" if ready else "BLOCKED_PENDING_PROTOCOL_REVIEW",
            "aric_mesa_primary_gate": "UNCHANGED_SEPARATE"}


def require_public_v2_ready(report: dict) -> None:
    """Future public locked runner must call this; no override is defined."""
    if report.get("readiness", {}).get("COHORT_READY") != "YES":
        raise ValueError("Public COHORT_READY = NO; publication split and training prohibited")


def _haalsi_raw(root: Path, mapping: dict) -> tuple[pd.DataFrame, dict, dict]:
    raw, loading = HAALSIAdapter(mapping).load(root)
    path = root / mapping["files"]["main"]
    labels = pd.read_stata(path, iterator=True, convert_categoricals=False).value_labels()
    columns = pd.read_stata(path, iterator=True, convert_categoricals=False).variable_labels()
    slot_keys = {name for name in columns if re.fullmatch(r"W1HHMEMBERPRIMKEY_\d+_", name)}
    slot_sex = {name for name in columns if re.fullmatch(r"W1HHMEMBERSEX_\d+_", name)}
    extras = sorted(slot_keys | slot_sex | {"PRIM_KEY", "W1CM004", "W1CM007_MALES",
                                            "W1CM007_FEMALES", "W3CM321", "W3CM324"})
    extra = pd.read_stata(path, columns=extras, convert_categoricals=False)
    if extra.PRIM_KEY.isna().any() or extra.PRIM_KEY.duplicated().any():
        raise ValueError("HAALSI Wave-1 extra fields have invalid IDs")
    return raw.merge(extra, on="PRIM_KEY", how="left", validate="one_to_one"), labels, loading


def _mhas_raw(root: Path, master_file: Path, mapping: dict) -> tuple[pd.DataFrame, dict, dict]:
    raw, loading = MHASAdapter(mapping).load(root)
    bio = root / mapping["files"]["biomarker"]
    extra = pd.read_stata(bio, columns=["cunicah", "np", "date_12"], convert_categoricals=False)
    extra["__join_id"] = extra.cunicah.astype("int64") * 100 + extra.np.astype("int64")
    raw = raw.merge(extra[["__join_id", "date_12"]], on="__join_id", how="left", validate="one_to_one")
    master = pd.read_stata(master_file, columns=list(MASTER_COLUMNS) + ["tipent_12", "tipne_12"],
                           convert_categoricals=False)
    joined, join = join_mhas_master_followup(raw, master,
                                             additional_metadata=("tipent_12", "tipne_12"))
    labels = pd.read_stata(root / mapping["files"]["main"], iterator=True,
                           convert_categoricals=False).value_labels()
    labels.update(pd.read_stata(bio, iterator=True, convert_categoricals=False).value_labels())
    return joined, labels, {**loading, "master_join": join}


def _cohort_overlap(first, second) -> dict[str, int]:
    """Aggregate membership comparison; no IDs or per-person hashes leave memory."""
    a = first.canonical.set_index("participant_id").label
    b = second.canonical.set_index("participant_id").label
    left, right = a.index.difference(b.index), b.index.difference(a.index)
    return {"shared_n": int(len(a.index.intersection(b.index))),
            "first_only_n": int(len(left)), "first_only_events": int(a.loc[left].sum()),
            "second_only_n": int(len(right)), "second_only_events": int(b.loc[right].sum())}


def run_public_v2(root: Path, master_file: Path, config_path: Path,
                  output_root: Path, *, questionnaire: Path | None = None) -> Path:
    config = json.loads(config_path.read_text())
    if config.get("protocol_version") != PUBLIC_V2_VERSION:
        raise ValueError("Explicit public v2 protocol required")
    root, master_file = root.resolve(), master_file.resolve()
    if not master_file.is_file():
        raise FileNotFoundError("MHAS 2024 Master file required")
    source_path = Path(config["source_mapping"])
    target_path = Path(config["target_mapping"])
    mapping_h, mapping_m = json.loads(source_path.read_text()), json.loads(target_path.read_text())
    if mapping_h.get("cohort_name") != "HAALSI" or mapping_m.get("cohort_name") != "MHAS":
        raise ValueError("Public mapping identities mismatch")
    if config.get("source_public_mapping_version") is not None and (
            mapping_h.get("public_model_mapping_version") != config["source_public_mapping_version"] or
            mapping_m.get("public_model_mapping_version") != config.get("target_public_mapping_version") or
            config.get("endpoint_version") != "public-wave-doctor-reported-ha-or-stroke-v2"):
        raise ValueError("Frozen public endpoint/mapping versions differ from release configuration")
    schema_paths = {"primary": Path(config["primary_feature_schema_config"]),
                    "sensitivity": Path(config["sensitivity_feature_schema_config"])}
    for role, version, views in (("primary", SCHEMA_VERSIONS["ten_doctor_report"], VIEWS_TEN),
                                 ("sensitivity", SCHEMA_VERSIONS["nine_no_diabetes"], VIEWS_NINE)):
        candidate = json.loads(schema_paths[role].read_text())
        if (candidate.get("protocol_version") != PUBLIC_V2_VERSION or
                candidate.get("schema_version") != version or
                candidate.get("views") != {k: list(v) for k, v in views.items()}):
            raise ValueError("Public feature schema configuration drift")
    hraw, hlabels, hload = _haalsi_raw(root, mapping_h)
    mraw, mlabels, mload = _mhas_raw(root, master_file, mapping_m)
    old_h = audit_public_cohort(hraw, mapping_h, value_labels=hlabels)
    no_route_mapping = json.loads(json.dumps(mapping_h))
    no_route_mapping["hypertension_field"] = None
    no_route_h = audit_public_cohort(hraw, no_route_mapping, value_labels=hlabels)
    h_doctor = construct_haalsi_v2(hraw, mapping_h, hlabels, schema="ten_doctor_report")
    h_broad = construct_haalsi_v2(hraw, mapping_h, hlabels, schema="ten_broad_diagnostic")
    h_nine = construct_haalsi_v2(hraw, mapping_h, hlabels, schema="nine_no_diabetes")
    m_doctor = construct_mhas_v2(mraw, mapping_m, mlabels, schema="ten_doctor_report", max_days=30)
    m_nine = construct_mhas_v2(mraw, mapping_m, mlabels, schema="nine_no_diabetes", max_days=30)
    m_short = construct_mhas_v2(mraw, mapping_m, mlabels, schema="ten_doctor_report", max_days=14)
    m_short_nine = construct_mhas_v2(mraw, mapping_m, mlabels, schema="nine_no_diabetes", max_days=14)
    for src, tgt in ((h_doctor, m_doctor), (h_nine, m_nine)):
        if src.views != tgt.views or set(src.canonical.columns) != set(tgt.canonical.columns):
            raise ValueError("Cross-cohort public predictor contract mismatch")
        if src.canonical.participant_id.str.startswith("MHAS:").any() or \
           tgt.canonical.participant_id.str.startswith("HAALSI:").any():
            raise ValueError("Source/target identity leakage")
    budget = {}
    for name, cohort in (("primary_0_30", m_doctor), ("sensitivity_0_14", m_short),
                         ("nine_0_30", m_nine), ("nine_0_14", m_short_nine)):
        events = int(cohort.canonical.label.sum())
        controls = len(cohort.canonical) - events
        budget[name] = {str(b): event_reserve_plan(events, controls, b,
            test_fraction=config["target_test_fraction_proposed"],
            validation_fraction=config["target_validation_fraction_of_development_proposed"],
            test_floor=config["test_event_floor_proposed"],
            validation_floor=config["validation_event_floor_proposed"]) for b in (10, 25, 50)}
    paths = {"haalsi": root / mapping_h["files"]["main"],
             "mhas_harmonized": root / mapping_m["files"]["main"],
             "mhas_biomarker": root / mapping_m["files"]["biomarker"],
             "mhas_eol": root / mapping_m["files"]["eol"],
             "mhas_master_2024": master_file,
             "source_mapping": source_path, "target_mapping": target_path,
             "public_config": config_path,
             "primary_feature_schema": schema_paths["primary"],
             "sensitivity_feature_schema": schema_paths["sensitivity"]}
    module_dir = Path(__file__).resolve().parent
    paths.update({
        "code_public_v2": module_dir / "data/public_v2.py",
        "code_public_cohorts": module_dir / "data/public_cohorts.py",
        "code_public_reconciliation": module_dir / "data/public_reconciliation.py",
        "code_wave_endpoint": module_dir / "data/wave_endpoint.py",
        "code_real_cohorts": module_dir / "data/real_cohorts.py",
        "code_public_v2_readiness": module_dir / "public_v2_readiness.py",
        "code_public_lock": module_dir / "public_lock.py",
    })
    if questionnaire is not None:
        if not questionnaire.is_file():
            raise FileNotFoundError("Official HAALSI baseline questionnaire unavailable")
        paths["haalsi_baseline_questionnaire"] = questionnaire
    hashes = {name: file_sha256(path) for name, path in paths.items()}
    expected_hashes = config.get("expected_input_sha256")
    if expected_hashes is not None:
        if not isinstance(expected_hashes, dict) or any(
                hashes.get(name) != digest for name, digest in expected_hashes.items()):
            raise ValueError("Frozen public input SHA256 differs from actual release/mapping/schema/document")
    report = {"protocol_version": PUBLIC_V2_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": config, "file_sha256": hashes,
        "source_load": hload, "target_load": mload,
        "cohorts": {"haalsi_ten_doctor": h_doctor.report,
                    "haalsi_ten_broad_diagnostic": h_broad.report,
                    "haalsi_nine": h_nine.report,
                    "mhas_ten_0_30": m_doctor.report,
                    "mhas_nine_0_30": m_nine.report,
                    "mhas_ten_0_14": m_short.report,
                    "mhas_nine_0_14": m_short_nine.report},
        "historical_public_v1_comparison": {
            "haalsi_current_5f_mapping": {"n": len(old_h.canonical),
                "events": int(old_h.canonical.label.sum())},
            "haalsi_without_any_medication_skip_derivation": {"n": len(no_route_h.canonical),
                "events": int(no_route_h.canonical.label.sum())}},
        "schema_membership_comparison": {
            "haalsi_broad_vs_doctor": _cohort_overlap(h_broad, h_doctor),
            "haalsi_doctor_vs_nine": _cohort_overlap(h_doctor, h_nine),
            "mhas_ten_vs_nine_0_30": _cohort_overlap(m_doctor, m_nine)},
        "event_reserve_plans": budget,
        "publication_split_created": False, "training_performed": False,
        "statistical_preprocessing_performed": False,
        "participant_level_records_written": False}
    report["readiness"] = readiness_evidence(config, h_doctor.report, m_doctor.report,
                                               provenance_ok=all(hashes.values()))
    # A stable digest covers all evidence except the run timestamp and output path.
    stable = {k: v for k, v in report.items() if k != "created_utc"}
    report["evidence_digest"] = hashlib.sha256(json.dumps(stable, sort_keys=True,
        allow_nan=False).encode()).hexdigest()
    output = output_root / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    (output / "aggregate_public_v2.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--master-file", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/public_haalsi_mhas_v2.proposed.json"))
    parser.add_argument("--questionnaire", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("results/public_protocol_v2"))
    args = parser.parse_args()
    print(f"Aggregate public v2 evidence: {run_public_v2(args.data_root, args.master_file, args.config, args.output_root, questionnaire=args.questionnaire)}")


if __name__ == "__main__":
    main()
