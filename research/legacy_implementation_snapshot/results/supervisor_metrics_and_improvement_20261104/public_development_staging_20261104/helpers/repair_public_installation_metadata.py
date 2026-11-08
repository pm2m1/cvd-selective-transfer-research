#!/usr/bin/env python3
"""Human-operated, one-file public bootstrap repair. No clinical/config access.

Original manifests, workflow code, public copies and authorization guards are
never changed. Only a missing root manifest may be installed, without overwrite.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile

MANIFEST = 'PUBLIC_STAGING_MANIFEST.json'
MANIFEST_SHA256 = 'WITHHELD_REFERENCE_BINDING'
HELPER_LEDGER = 'helpers/WORKFLOW_PUBLIC_BINDINGS.json'
HELPER_LEDGER_SHA256 = 'WITHHELD_REFERENCE_BINDING'
CHECKSUMS = 'STAGING_CHECKSUMS.sha256'
CHECKSUMS_SHA256 = 'WITHHELD_REFERENCE_BINDING'


class RepairStop(Exception):
    def __init__(self, code, public_file=None):
        self.code, self.public_file = code, public_file


def need(condition, code, public_file=None):
    if not condition:
        raise RepairStop(code, public_file)


def absolute(value):
    need(isinstance(value, str) and bool(value) and not any(c in value for c in '\x00\r\n<>${}'), 'ABSOLUTE_ROOT_REQUIRED')
    path = Path(value)
    need(path.is_absolute() and '..' not in path.parts and not path.is_symlink(), 'ABSOLUTE_ROOT_REQUIRED')
    need(path.is_dir(), 'PUBLIC_ROOT_DIRECTORY_MISSING')
    return path.resolve(strict=True)


def public_path(root, name):
    rel = PurePosixPath(name)
    need(not rel.is_absolute() and '..' not in rel.parts and '\\' not in name, 'PUBLIC_PATH_REJECTED')
    path = root
    for part in rel.parts:
        path /= part
        need(not path.is_symlink(), 'PUBLIC_SYMLINK_REJECTED', name)
    need(path.resolve().is_relative_to(root), 'PUBLIC_PATH_REJECTED')
    need(path.is_file(), 'REQUIRED_PUBLIC_ASSET_MISSING', name)
    return path


def read_regular(path):
    need(stat.S_ISREG(path.lstat().st_mode), 'EXPECTED_PUBLIC_REGULAR_FILE')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(fd, 'rb') as stream:
        need(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'EXPECTED_PUBLIC_REGULAR_FILE')
        return stream.read()


def verified_bytes(root, name, expected):
    raw = read_regular(public_path(root, name))
    need(hashlib.sha256(raw).hexdigest() == expected, 'PUBLIC_CHECKSUM_MISMATCH', name)
    return raw


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'PUBLIC_JSON_REJECTED')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def verify_source(source):
    """Authenticate the existing public release pins; never fabricate a manifest."""
    payload = verified_bytes(source, MANIFEST, MANIFEST_SHA256)
    m = strict_json(payload)
    sums = verified_bytes(source, CHECKSUMS, CHECKSUMS_SHA256).decode('ascii')
    need(f'{MANIFEST_SHA256}  {MANIFEST}' in sums.splitlines(), 'REGISTERED_MANIFEST_CHECKSUM_MISSING')
    need(len(m['public_source_files']) == 63 and len(m['additional_public_records']) == 5
         and len(m['experiment_tools']) == 25, 'PUBLIC_INVENTORY_REJECTED')
    entries = {}
    for row in m['public_source_files']:
        need(row['path'].startswith('src/dmv_mat_cvd/') and row['path'].endswith('.py'), 'PUBLIC_INVENTORY_REJECTED')
        entries['public_project/'+row['path']] = row['expected_sha256']
    for row in m['additional_public_records']:
        need(row['path'].startswith('configs/') and row['path'].endswith('.json'), 'PUBLIC_INVENTORY_REJECTED')
        entries['public_project/'+row['path']] = row['actual_sha256']
    for row in m['experiment_tools']:
        entries['experiment_tools/'+row['path']] = row['source_sha256']
    need(len(entries) == 93, 'PUBLIC_INVENTORY_REJECTED')
    helper_raw = verified_bytes(source, HELPER_LEDGER, HELPER_LEDGER_SHA256)
    helpers = strict_json(helper_raw)
    need(helpers.get('schema') == 'workflow-public-helper-bindings-v1'
         and len(helpers['files']) == 12, 'PUBLIC_HELPER_INVENTORY_REJECTED')
    entries[HELPER_LEDGER] = HELPER_LEDGER_SHA256
    entries.update({'helpers/'+name: digest for name, digest in helpers['files'].items()})
    need(len(entries) == 106, 'PUBLIC_INVENTORY_REJECTED')
    for name, digest in entries.items():
        verified_bytes(source, name, digest)
    return payload, entries


def require_independent_operator(source):
    # Source verification occurs first; this is the original unchanged guard.
    path = public_path(source, 'experiment_tools/local_execution.py')
    spec = importlib.util.spec_from_file_location('_metadata_repair_original_guard', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.require_local()
    except Exception:
        raise RepairStop('INDEPENDENT_LOCAL_OPERATOR_REQUIRED') from None


def insert_without_overwrite(destination, payload):
    """Atomic no-replace publication by hard link, with temporary mode 0600."""
    temporary = None
    fd = None
    try:
        fd, name = tempfile.mkstemp(prefix='.public-manifest-repair-', suffix='.tmp', dir=destination)
        temporary = Path(name)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            fd = None
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # link() fails if any destination entry exists; replace() is never used.
        try:
            os.link(temporary, destination/MANIFEST, follow_symlinks=False)
        except FileExistsError:
            raise RepairStop('EXISTING_MANIFEST_NOT_OVERWRITTEN') from None
    finally:
        if fd is not None:
            os.close(fd)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def repair(source, destination, payload, entries):
    need(not source.is_relative_to(destination) and not destination.is_relative_to(source), 'PUBLIC_TREES_MUST_BE_SEPARATE')
    need(hashlib.sha256(payload).hexdigest() == MANIFEST_SHA256, 'PUBLIC_CHECKSUM_MISMATCH', MANIFEST)
    # Verify only exact known public names. Never enumerate the destination.
    for name, digest in entries.items():
        verified_bytes(destination, name, digest)
    target = destination/MANIFEST
    if target.exists() or target.is_symlink():
        verified_bytes(destination, MANIFEST, MANIFEST_SHA256)
        installed = False
    else:
        insert_without_overwrite(destination, payload)
        installed = True
    verified_bytes(destination, MANIFEST, MANIFEST_SHA256)
    # Same complete public files remain required after insertion; no relaxed gate.
    for name, digest in entries.items():
        verified_bytes(destination, name, digest)
    return 'PASS: ROOT_PUBLIC_MANIFEST_INSTALLED' if installed else 'PASS: ROOT_PUBLIC_MANIFEST_ALREADY_VERIFIED'


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise RepairStop('ARGUMENTS_REJECTED')


def main(argv=None):
    try:
        parser = Parser(prog='repair_public_installation_metadata.py')
        parser.add_argument('--staging', required=True)
        parser.add_argument('--destination', required=True)
        args = parser.parse_args(argv)
        source = absolute(args.staging)
        payload, entries = verify_source(source)
        require_independent_operator(source)  # No agent/CI bypass, no attestation.
        destination = absolute(args.destination)
        result = repair(source, destination, payload, entries)
        print(result)
        print('PASS: REQUIRED_WORKFLOW_PUBLIC_LAYOUT_VERIFIED')
        return 0
    except BaseException as exc:
        if isinstance(exc, SystemExit) and exc.code == 0:
            return 0
        if isinstance(exc, RepairStop):
            suffix = ' PUBLIC_FILE='+exc.public_file if exc.public_file is not None else ''
            print('STOP ISSUE='+exc.code+suffix)
        else:
            print('STOP ISSUE=PUBLIC_METADATA_REPAIR_NOT_COMPLETED')
        return 2


if __name__ == '__main__':
    sys.exit(main())
