"""Run each authentic public package's synthetic suite in an isolated process."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    registry = json.loads((ROOT / "research/IMPORTED_PUBLIC_ARTIFACTS.json").read_text())
    for package in registry["packages"]:
        root = ROOT / Path(package["path"]).parent
        external = package.get("external_public_documentation", [])
        base = ROOT / package.get("external_documentation_base", ".")
        if any(not (base / name).is_file() for name in external):
            print("NOT_RUN_EXTERNAL_DOCUMENTATION_NOT_DISTRIBUTED " + root.name, flush=True)
            continue
        print("PUBLIC_SYNTHETIC_PACKAGE " + root.name, flush=True)
        subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
            cwd=root,
            check=True,
            timeout=180,
        )
    print("ALL_AVAILABLE_IMPORTED_PUBLIC_SYNTHETIC_SUITES_PASSED", flush=True)
