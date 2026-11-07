"""Public checkout checks. Never reads data directories or paths outside this tree."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_SUFFIXES = {
    ".dta",
    ".sav",
    ".sas7bdat",
    ".xpt",
    ".npz",
    ".npy",
    ".pt",
    ".pth",
    ".ckpt",
    ".pkl",
    ".pickle",
    ".joblib",
    ".zip",
    ".parquet",
    ".ipynb",
    ".xlsx",
    ".xls",
    ".pdf",
    ".jsonl",
    ".db",
    ".sqlite",
    ".tsv",
}
HOME_PATH = re.compile(r"/(?:Users|home)/[^/\s]+")
SECRET = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)


def check_file(root, relative):
    path = root / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
        or any(p.is_symlink() for p in path.parents if p.is_relative_to(root))
    ):
        raise ValueError("Unsafe public file")
    # Aggregate approval does not authorize an identifiable institutional report.
    # Only its status README is reviewed until a separate report-release decision.
    if (
        relative.startswith("reports/nitw-btech-phase1/")
        and relative != "reports/nitw-btech-phase1/README.md"
    ):
        raise ValueError("Academic report publication review is pending")
    lower = relative.lower()
    if (
        path.suffix.lower() in PRIVATE_SUFFIXES
        or ".private." in lower
        or Path(relative).parts[0].lower() in {"data", "datasets", "raw", "controlled", "private_data"}
        or path.name.startswith(".env")
        or path.suffix in {".pem", ".key"}
    ):
        raise ValueError("Prohibited artifact")
    if path.suffix == ".csv" and not relative.startswith(
        "results/synthetic_validation/20260924T222643Z-da0fe9b3/"
    ):
        raise ValueError("Unreviewed table")
    text = path.read_text(encoding="utf-8")
    if HOME_PATH.search(text) or SECRET.search(text):
        raise ValueError("Private path or recognizable credential")
    if path.suffix == ".svg":
        svg = ElementTree.fromstring(text)
        for node in svg.iter():
            if node.tag.rsplit("}", 1)[-1] in {"script", "foreignObject"}:
                raise ValueError("Active SVG content")
            for attr, value in node.attrib.items():
                if attr.rsplit("}", 1)[-1] in {"href", "src"} and not value.startswith(
                    ("#", "data:image/png;base64,")
                ):
                    raise ValueError("External SVG dependency")
    return text


def check_links(root, path, text):
    """Check local Markdown path targets; external availability is not inferred."""
    count = 0
    for target in re.findall(r"\]\(([^\s)]+)(?:\s+\"[^\"]*\")?\)", text):
        if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        value = unquote(target.split("#", 1)[0])
        resolved = (path.parent / value).resolve()
        if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
            raise ValueError("Broken or escaping documentation link")
        count += 1
    return count


def run(root=ROOT):
    inventory = json.loads((root / ".public-files.json").read_text())
    listed = inventory["files"]
    if len(set(listed)) != len(listed) or any(Path(p).is_absolute() or ".." in Path(p).parts for p in listed):
        raise ValueError("Invalid public allowlist")
    tracked = set(
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().strip("\0").split("\0")
    )
    if tracked != set(listed):
        raise ValueError("Tracked files differ from reviewed allowlist")
    links, svgs = 0, 0
    for relative in listed:
        text = check_file(root, relative)
        path = root / relative
        if path.suffix == ".md":
            links += check_links(root, path, text)
        svgs += path.suffix == ".svg"
    frozen = json.loads((root / "docs/phase1/frozen-public-bindings.json").read_text())
    fixes = frozen.get("reviewed_implementation_fixes", {})
    if not set(fixes) <= set(frozen["sha256"]):
        raise ValueError("Invalid reviewed implementation fix")
    for relative, expected in frozen["sha256"].items():
        if relative in fixes:
            fix = fixes[relative]
            if fix["base_sha256"] != expected or not fix["reason"]:
                raise ValueError("Missing compatibility-fix provenance")
            expected = fix["reviewed_sha256"]
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError("Historical public artifact changed")
    print(
        f"PASS: {len(listed)} allowlisted files; {len(frozen['sha256']) - len(fixes)} preserved; "
        f"{len(fixes)} reviewed compatibility fixes; {links} local links; {svgs} SVGs"
    )


if __name__ == "__main__":
    try:
        run()
    except (
        ValueError,
        OSError,
        KeyError,
        json.JSONDecodeError,
        ElementTree.ParseError,
        subprocess.SubprocessError,
    ):
        raise SystemExit("STOP: public release check failed; inspect the public diff locally") from None
