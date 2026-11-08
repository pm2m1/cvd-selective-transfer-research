"""Verify/install only manifest-enumerated public files; no clinical discovery."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError('INVALID_PUBLIC_COMMAND')


def verify(root=ROOT):
    root = Path(root).resolve()
    ledger = json.loads((root/'RELEASE_MANIFEST.json').read_text())
    for name, expected in ledger['files'].items():
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name:
            raise ValueError('UNSAFE_PUBLIC_PATH')
        p = root/name
        if p.is_symlink() or not p.resolve().is_relative_to(root) or not p.is_file():
            raise ValueError('PUBLIC_FILE_MISSING_OR_UNSAFE')
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError('PUBLIC_FILE_BINDING_MISMATCH')
    return ledger


def install(destination):
    ledger = verify()
    out = Path(destination)
    if not out.is_absolute() or os.path.lexists(out) or not out.parent.is_dir():
        raise ValueError('NEW_PUBLIC_INSTALLATION_REQUIRED')
    out.mkdir(mode=0o700)
    for name in [*ledger['files'], 'RELEASE_MANIFEST.json']:
        target = out/name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write((ROOT/name).read_bytes())
    verify(out)


def new_config(destination):
    verify()
    out = Path(destination)
    if (not out.is_absolute() or os.path.lexists(out) or not out.parent.is_dir()
        or out.resolve().is_relative_to(ROOT) or out.parent.stat().st_mode & 0o077):
        raise ValueError('NEW_PRIVATE_CONFIG_DESTINATION_REQUIRED')
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write((ROOT/'config.template.json').read_bytes())


def main():
    try:
        parser = SafeParser(description=__doc__)
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--install-to', type=Path)
        group.add_argument('--new-config', type=Path)
        args = parser.parse_args()
        if args.new_config:
            new_config(args.new_config)
            print('PASS ISSUE=NEW_UNRESOLVED_STATUS_CONFIG_CREATED_NO_AUTHORIZATION')
            return 0
        install(args.install_to) if args.install_to else verify()
        print('PASS ISSUE=PUBLIC_STATUS_DIAGNOSTIC_PACKAGE_VERIFIED' + ('_INSTALLED' if args.install_to else ''))
        return 0
    except SystemExit as exc:
        return exc.code
    except BaseException:
        print('STOP ISSUE=PUBLIC_STATUS_DIAGNOSTIC_PACKAGE_INVALID_OR_DESTINATION_USED')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
