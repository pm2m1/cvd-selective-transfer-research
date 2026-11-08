"""Human-only metadata inventory; no file contents, hashes or uploads.

Only run independently after applicable permission for filesystem metadata review
has been established. This tool creates no scientific/disclosure authorization.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path


def in_agent():
    return bool(os.environ.get("CI") or any(k.startswith("CODEX") for k in os.environ))


def classify(relative):
    path = Path(relative)
    if "confusion_matrices" in path.parts and path.suffix.lower() == ".svg":
        return "CONFUSION_MATRIX_SVG"
    if "summary_plots" in path.parts and path.suffix.lower() in {".svg", ".png", ".pdf"}:
        return "SUMMARY_PLOT_RENDITION"
    return "OTHER_ARTIFACT"


def inventory_metadata(root, output):
    """Unit-tested only on invented directories; never reads any input payload."""
    root, output = Path(root).absolute(), Path(output).absolute()
    if any(p.is_symlink() for p in (root, *root.parents, output.parent, *output.parent.parents)):
        raise ValueError("UNSAFE_SYMLINK")
    if not root.is_dir() or root.stat().st_uid != os.getuid() or stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise ValueError("PRIVATE_ROOT_PERMISSIONS_REQUIRED")
    if output.exists() or output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("NEW_SEPARATE_OUTPUT_REQUIRED")
    if output.parent.stat().st_uid != os.getuid() or stat.S_IMODE(output.parent.stat().st_mode) & 0o077:
        raise ValueError("PRIVATE_OUTPUT_PARENT_REQUIRED")
    rows = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(directory) / name
            if p.is_symlink():
                raise ValueError("UNSAFE_SYMLINK")
        for name in files:
            p = Path(directory) / name
            info = p.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError("UNSAFE_FILE_OWNER_OR_TYPE")
            relative = p.relative_to(root).as_posix()
            rows.append(
                {
                    "relative_path": relative,
                    "bytes": info.st_size,
                    "category": classify(relative),
                    "publication_status": "NOT_PUBLISHED",
                    "reason": "EXACT_ARTIFACT_PUBLIC_DISCLOSURE_NOT_ESTABLISHED",
                }
            )
    output.mkdir(mode=0o700)
    data = {
        "scope": "FILENAMES_AND_STAT_ONLY_NO_PAYLOAD_ACCESS",
        "scientific_approval": "NOT_GRANTED",
        "source_root": str(root),
        "files": sorted(rows, key=lambda r: r["relative_path"]),
        "counts": {
            kind: sum(row["category"] == kind for row in rows)
            for kind in ("CONFUSION_MATRIX_SVG", "SUMMARY_PLOT_RENDITION", "OTHER_ARTIFACT")
        },
    }
    fd = os.open(output / "UNPUBLISHED_FILES.private.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
    return data["counts"]


def main():
    if in_agent():
        raise SystemExit("STOP: INDEPENDENT_LOCAL_OPERATOR_REQUIRED")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not __import__("sys").stdin.isatty():
        raise SystemExit("STOP: INDEPENDENT_LOCAL_OPERATOR_REQUIRED")
    answer = input(
        "Applicable metadata-review permission independently established? Type INVENTORY METADATA ONLY: "
    )
    if answer != "INVENTORY METADATA ONLY":
        raise SystemExit("STOP: NO_OPERATION")
    try:
        inventory_metadata(args.root.expanduser(), args.output.expanduser())
    except (ValueError, OSError):
        raise SystemExit("STOP: PRIVATE_METADATA_INVENTORY_FAILED") from None
    print("PRIVATE_METADATA_INVENTORY_CREATED_NO_DISCLOSURE_APPROVAL")


if __name__ == "__main__":
    main()
