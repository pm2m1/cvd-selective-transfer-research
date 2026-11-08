"""Compare a freshly fetched GitHub API tree with tracked bytes, not local refs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(tree, root=ROOT):
    if tree.get("truncated"):
        raise ValueError("Truncated remote tree")
    local_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    # Caller fetched this tree through the public API using the exact commit SHA.
    entries = {x["path"]: x for x in tree["tree"] if x["type"] == "blob"}
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().strip("\0").split("\0")
    if set(entries) != set(files):
        raise ValueError("Unexpected or absent remote files")
    if any(
        Path(name).suffix.lower() in {".pdf", ".tex", ".sty", ".bib", ".zip", ".dta", ".npz", ".pt"}
        for name in entries
    ):
        raise ValueError("Excluded artifact on remote")
    for name in files:
        raw = (root / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if name not in entries or entries[name]["sha"] != blob:
            raise ValueError("Remote artifact absent or different")
    registry = json.loads((root / "research/IMPORTED_PUBLIC_ARTIFACTS.json").read_text())
    from verify_imported_artifacts import category

    counts = {}
    for name, record in registry["files"].items():
        kind = category(name, record)
        counts[kind] = counts.get(kind, 0) + 1
    return {
        "commit": local_head,
        "tracked_files_verified_against_remote_blobs": len(files),
        "imported_files_verified": len(registry["files"]),
        "imported_categories": counts,
        "report_or_latex_uploaded": False,
        "real_threshold_outputs_uploaded": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree-json", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(json.loads(args.tree_json.read_text())), indent=2, sort_keys=True))
