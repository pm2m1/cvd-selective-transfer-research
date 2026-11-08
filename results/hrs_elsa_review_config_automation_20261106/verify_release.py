"""Read-only verification of this new public helper package."""
import hashlib
import json
from pathlib import Path


def verify(root):
    root=Path(root).resolve();m=json.loads((root/'RELEASE_MANIFEST.json').read_text())
    if m.get('scope')!='PUBLIC_CODE_DOCUMENTATION_AND_INVENTED_TEST_FIXTURES_ONLY':raise ValueError('PUBLIC_SCOPE_INVALID')
    entries=list(root.rglob('*'))
    if any(p.is_symlink() for p in entries):raise ValueError('PUBLIC_LAYOUT_INVALID')
    actual={p.relative_to(root).as_posix() for p in entries if p.is_file()}
    if actual != set(m['files'])|{'RELEASE_MANIFEST.json'}:raise ValueError('PUBLIC_INVENTORY_INVALID')
    for n,h in m['files'].items():
        p=Path(n)
        if p.is_absolute() or '..' in p.parts or hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:raise ValueError('PUBLIC_BINDING_INVALID')
    return len(m['files'])


if __name__=='__main__':
    try:
        verify(Path(__file__).resolve().parent)
        print('PASS ISSUE=PUBLIC_CONFIG_HELPER_PACKAGE_VERIFIED')
    except BaseException:
        print('STOP ISSUE=PUBLIC_CONFIG_HELPER_PACKAGE_INVALID');raise SystemExit(2)
