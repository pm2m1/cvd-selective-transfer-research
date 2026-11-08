"""Verify ONLY explicitly listed public package files. No private file discovery."""
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify():
    root = Path(__file__).resolve().parent
    record = json.loads((root / 'PUBLIC_PACKAGE_MANIFEST.json').read_text())
    for name, expected in record['files'].items():
        rel = PurePosixPath(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name:
            raise ValueError('UNSAFE_PUBLIC_PATH')
        p = root / name
        if p.is_symlink() or not p.resolve().is_relative_to(root) or not p.is_file():
            raise ValueError('PUBLIC_FILE_MISSING')
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError('PUBLIC_HASH_MISMATCH')
    return len(record['files'])


if __name__ == '__main__':
    try:
        count = verify()
    except BaseException:
        print('STOP ISSUE=PUBLIC_PACKAGE_BINDING_INVALID')
        raise SystemExit(2)
    print('PASS ISSUE=PUBLIC_PACKAGE_FILES_VERIFIED')
