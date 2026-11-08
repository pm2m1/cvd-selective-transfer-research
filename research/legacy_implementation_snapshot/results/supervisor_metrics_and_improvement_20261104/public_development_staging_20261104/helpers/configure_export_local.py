#!/usr/bin/env python3
"""Offline configuration editing only; never loads clinical inputs or authorizes work.

Run independently, outside AI-accessible environments. Source bindings are anchored
to the original public template; there is deliberately no CLI override for that pin.
"""
from __future__ import annotations

import argparse
import copy
import getpass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import warnings


EXPECTED_BINDINGS_SHA256 = 'WITHHELD_REFERENCE_BINDING'
SCHEMA = "new-private-development-export-v1"
PATH_FIELDS = ("data_root", "master_file", "questionnaire")
STATUS_LABELS = (
    "DATA_ROOT", "MASTER_FILE", "QUESTIONNAIRE", "ISOLATED_PUBLIC_PROJECT",
    "DEVELOPMENT_ONLY_CONTRACT", "PUBLIC_SOURCE_BINDINGS", "LOCAL_CONFIG_STRUCTURE",
)


class SafeStop(Exception):
    """No user-supplied text or exception context is exposed to the terminal."""


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise SafeStop() from None  # argparse's default error can echo private argv.


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SafeStop()
        result[key] = value
    return result


def _reject_constant(value):
    raise SafeStop()


def _absolute_path(value):
    # No expansion, search, substitution, guessing or rewriting of entered paths.
    if not isinstance(value, str) or not value or value.isspace():
        raise SafeStop()
    if any(c in value for c in ("\x00", "\r", "\n", "<", ">", "{", "}", "$", "%")):
        raise SafeStop()
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise SafeStop()
    lowered = value.lower()
    if lowered.startswith(("/path/to/", "/absolute/path/")):
        raise SafeStop()
    if any(part.upper() in {"TODO", "TBD", "REPLACE_ME", "PLACEHOLDER", "PATH_TO"}
           or part.upper().startswith(("YOUR_", "REPLACE_WITH_")) for part in path.parts):
        raise SafeStop()
    return path


def _existing_path(value, directory=False):
    path = _absolute_path(value)
    info = path.lstat()  # Metadata only: never open master/questionnaire/input contents.
    expected = stat.S_ISDIR if directory else stat.S_ISREG
    if stat.S_ISLNK(info.st_mode) or not expected(info.st_mode):
        raise SafeStop()
    return path


def _read_config(path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    # Reject a symlink leaf even on platforms lacking O_NOFOLLOW.
    if not stat.S_ISREG(path.lstat().st_mode):
        raise SafeStop()
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise SafeStop()
        raw = stream.read()
    fingerprint = (info.st_dev, info.st_ino, hashlib.sha256(raw).digest())
    return raw, fingerprint


def load_config(value):
    path = _absolute_path(value)
    raw, fingerprint = _read_config(path)
    config = json.loads(raw, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    return path, config, fingerprint


def _bindings_are_original(bindings):
    if not isinstance(bindings, dict) or len(bindings) != 63:
        return False
    for name, digest in bindings.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            return False
        rel = PurePosixPath(name)
        if (rel.is_absolute() or ".." in rel.parts or "\\" in name
                or not name.startswith("src/dmv_mat_cvd/") or rel.suffix != ".py"
                or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            return False
    canonical = json.dumps(bindings, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True, allow_nan=False).encode("ascii")
    return hashlib.sha256(canonical).hexdigest() == EXPECTED_BINDINGS_SHA256


def _base_checks(config):
    if not isinstance(config, dict):
        return False, False
    contract = (config.get("schema") == SCHEMA
                and config.get("mode") == "independent_local_only"
                and config.get("no_test_rows") is True)
    required = {"schema", "mode", "no_test_rows", "isolated_public_project",
                "public_source_bindings", *PATH_FIELDS}
    shape = (required <= config.keys()
             and isinstance(config.get("isolated_public_project"), str)
             and all(config.get(k) is None or isinstance(config.get(k), str) for k in PATH_FIELDS))
    structure = bool(shape and contract and _bindings_are_original(config.get("public_source_bindings")))
    return contract, structure


def _public_source_hash(project, relative):
    """Read only an allowlisted .py leaf, with no followed source-tree symlinks.

    Fail closed where descriptor-relative no-follow directory traversal is absent.
    The actual master/questionnaire/data-root inputs never pass through this code.
    """
    if not hasattr(os, "O_NOFOLLOW") or os.open not in os.supports_dir_fd:
        raise SafeStop()
    root = project.resolve(strict=True)
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(root, directory_flags)
    try:
        parts = PurePosixPath(relative).parts
        for part in parts[:-1]:
            child = os.open(part, directory_flags, dir_fd=fd)
            os.close(fd)
            fd = child
        leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=fd)
        with os.fdopen(leaf, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise SafeStop()
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(fd)


def assess(config):
    result = dict.fromkeys(STATUS_LABELS, False)
    contract, structure = _base_checks(config)
    result["DEVELOPMENT_ONLY_CONTRACT"] = contract
    result["LOCAL_CONFIG_STRUCTURE"] = structure
    if not structure:
        return result
    for field, label in zip(PATH_FIELDS, STATUS_LABELS[:3]):
        try:
            _existing_path(config[field], directory=field == "data_root")
            result[label] = True
        except (SafeStop, OSError, ValueError, TypeError):
            pass
    try:
        project = _existing_path(config["isolated_public_project"], directory=True)
        result["ISOLATED_PUBLIC_PROJECT"] = True
        result["PUBLIC_SOURCE_BINDINGS"] = all(
            _public_source_hash(project, name) == digest
            for name, digest in config["public_source_bindings"].items())
    except (SafeStop, OSError, ValueError, TypeError):
        pass
    return result


def atomic_save(path, config, original_fingerprint):
    """0600 same-directory temporary file, then atomic replacement of the original."""
    payload = (json.dumps(config, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
    temporary = None
    fd = None
    try:
        fd, name = tempfile.mkstemp(prefix=".export-config-", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Refuse changes detected before commit; independent use must be serial.
        _, current_fingerprint = _read_config(path)
        if current_fingerprint != original_fingerprint:
            raise SafeStop()
        os.replace(temporary, path)
        temporary = None  # Rename consumed the temporary name; no second copy remains.
    finally:
        if fd is not None:
            os.close(fd)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _hidden_paths():
    if not sys.stdin.isatty():
        raise SafeStop()
    # If getpass cannot disable terminal echo, abort rather than use its fallback.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return {field: getpass.getpass(f"Enter {field} (hidden): ") for field in PATH_FIELDS}


def _print_status(result):
    try:
        for label in STATUS_LABELS:
            print(f"{label}: {'PASS' if result[label] else 'STOP'}")
        return True
    except Exception:
        return False


def main(argv=None):
    result = dict.fromkeys(STATUS_LABELS, False)
    try:
        parser = SafeParser(prog="configure_export_local.py",
                            description="Independent local configuration editing; no data loading or authorization.")
        parser.add_argument("configuration", metavar="CONFIG_JSON")
        parser.add_argument("--validate-only", action="store_true",
                            help="Read-only structure, path-type and public-source hash checks.")
        args = parser.parse_args(argv)
        path, config, fingerprint = load_config(args.configuration)
        contract, structure = _base_checks(config)
        if not structure:
            result["DEVELOPMENT_ONLY_CONTRACT"] = contract
            raise SafeStop()
        if args.validate_only:
            result = assess(config)
        else:
            _existing_path(config["isolated_public_project"], directory=True)
            completed = copy.deepcopy(config)
            completed.update(_hidden_paths())
            result = assess(completed)
            if not all(result.values()):
                raise SafeStop()
            if any(completed[k] != value for k, value in config.items() if k not in PATH_FIELDS):
                raise SafeStop()
            atomic_save(path, completed, fingerprint)
        printed = _print_status(result)
        return 0 if printed and all(result.values()) else 2
    except (Exception, KeyboardInterrupt):
        # No repr/str(exception), traceback, argv, config fields or path values.
        result["LOCAL_CONFIG_STRUCTURE"] = False
        _print_status(result)
        return 2


if __name__ == "__main__":
    sys.exit(main())
