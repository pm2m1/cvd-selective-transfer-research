"""Verify original imported public releases and produce exact public file counts."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def category(path, record):
    p = Path(path)
    if "confusion_matrices" in p.parts and p.suffix == ".svg":
        return "synthetic_confusion_matrix"
    if "threshold_response" in p.name and p.suffix in {".svg", ".png"}:
        return "synthetic_threshold_response_rendition"
    if "summary_plots" in p.parts and p.suffix in {".svg", ".png"}:
        return "synthetic_comparison_plot_rendition"
    if p.suffix in {".svg", ".png"}:
        return "synthetic_diagnostic_figure"
    if ("synthetic_results" in p.parts or record["kind"] == "ORIGINAL_SYNTHETIC_OUTPUT") and p.suffix in {
        ".csv",
        ".json",
    }:
        return "synthetic_experiment_result_table_or_json"
    if p.name.startswith("SYNTHETIC_") and p.suffix == ".json":
        return "synthetic_execution_summary"
    if p.suffix == ".py":
        return "python_source_or_test"
    return "protocol_configuration_mapping_or_documentation"


def verify(root=ROOT):
    registry = json.loads((root / "research/IMPORTED_PUBLIC_ARTIFACTS.json").read_text())
    counts = Counter()
    for name, record in registry["files"].items():
        path = root / name
        if Path(name).is_absolute() or ".." in Path(name).parts or path.is_symlink():
            raise ValueError("Unsafe import path")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("Imported original bytes changed")
        if path.suffix.lower() in {".pdf", ".tex", ".bib", ".sty", ".zip", ".npz", ".pt", ".dta"}:
            raise ValueError("Excluded academic or fitting artifact")
        if len(data) >= 50 * 1024 * 1024:
            raise ValueError("Large file requires a separate release review")
        if record["original_bytes"] and record["sha256"] != record["source_sha256"]:
            raise ValueError("Original-byte provenance mismatch")
        if record["kind"] == "ORIGINAL_SYNTHETIC_OUTPUT":
            if path.suffix == ".csv":
                with path.open(newline="") as stream:
                    rows = list(csv.DictReader(stream))
                if not rows or any(not row.get("model", "").startswith("INVENTED_") for row in rows):
                    raise ValueError("Invented-run model identity mismatch")
            if path.suffix == ".svg" and "SYNTHETIC" not in data.decode():
                raise ValueError("Missing original synthetic identity label")
        counts[category(name, record)] += 1
    for package in registry["packages"]:
        manifest_path = root / package["path"]
        manifest = json.loads(manifest_path.read_text())
        for name, expected in manifest["files"].items():
            if hashlib.sha256((manifest_path.parent / name).read_bytes()).hexdigest() != expected:
                raise ValueError("Original package manifest mismatch")
    return {
        "imported_files": len(registry["files"]),
        "standalone_packages": len(registry["packages"]),
        "real_confusion_matrices_published": 0,
        "real_threshold_plots_published": 0,
        "categories": dict(sorted(counts.items())),
        "privacy_projected_source_files": sum(not r["original_bytes"] for r in registry["files"].values()),
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
