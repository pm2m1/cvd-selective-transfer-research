"""Verify this public review package only; no dataset/configuration interfaces."""
import hashlib
import json
from pathlib import Path


def verify(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'RELEASE_MANIFEST.json').read_text())
    if manifest.get('scope') != 'PUBLIC_DOCUMENTATION_TESTS_AND_INVENTED_AGGREGATES_ONLY':
        raise ValueError('PUBLIC_SCOPE_INVALID')
    for name, expected in manifest['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('PUBLIC_LAYOUT_INVALID')
        p = root / relative
        if p.is_symlink() or not p.resolve().is_relative_to(root) or not p.is_file():
            raise ValueError('PUBLIC_FILE_UNSAFE_OR_MISSING')
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError('PUBLIC_CHECKSUM_MISMATCH')
    entries = list(root.rglob('*'))
    if any(p.is_symlink() for p in entries):
        raise ValueError('PUBLIC_LAYOUT_INVALID')
    actual = {str(p.relative_to(root)) for p in entries if p.is_file()}
    if actual != set(manifest['files']) | {'RELEASE_MANIFEST.json'}:
        raise ValueError('UNREGISTERED_PUBLIC_PACKAGE_FILE')
    return len(manifest['files'])


if __name__ == '__main__':
    try:
        count = verify(Path(__file__).resolve().parent)
        print(f'PASS PUBLIC_FILES_VERIFIED={count} NO_SCIENTIFIC_APPROVAL')
    except BaseException:
        print('STOP ISSUE=PUBLIC_PACKAGE_VERIFICATION_FAILED')
        raise SystemExit(2)
