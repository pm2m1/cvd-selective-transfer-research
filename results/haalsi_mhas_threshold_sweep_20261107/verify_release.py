"""Verify/install only explicitly enumerated public supplementary source files."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def verify(root=ROOT):
    root=Path(root).resolve();m=json.loads((root/'RELEASE_MANIFEST.json').read_text())
    if m.get('scope')!='PUBLIC_CODE_CLEARED_REFERENCES_AND_INVENTED_TESTS_ONLY':raise ValueError('PUBLIC_SCOPE_INVALID')
    entries=list(root.rglob('*'))
    if any(p.is_symlink() for p in entries):raise ValueError('PUBLIC_LAYOUT_INVALID')
    if {p.relative_to(root).as_posix() for p in entries if p.is_file()}!=set(m['files'])|{'RELEASE_MANIFEST.json'}:
        raise ValueError('PUBLIC_INVENTORY_INVALID')
    for n,h in m['files'].items():
        p=Path(n)
        if p.is_absolute() or '..' in p.parts or hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:raise ValueError('PUBLIC_HASH_MISMATCH')
    return m


def install(destination):
    m=verify();p=Path(destination)
    if not p.is_absolute() or '..' in p.parts or p.exists() or any(x.is_symlink() for x in (p,*p.parents)) or not p.parent.is_dir():
        raise ValueError('FRESH_PUBLIC_INSTALLATION_REQUIRED')
    p.mkdir(mode=0o700)
    for n in [*m['files'],'RELEASE_MANIFEST.json']:
        target=p/n;target.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write((ROOT/n).read_bytes())
    verify(p)


class Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('INVALID_PUBLIC_COMMAND')


if __name__=='__main__':
    try:
        p=Parser();p.add_argument('--install-to',type=Path);a=p.parse_args()
        if a.install_to:install(a.install_to)
        else:verify()
        print('PASS ISSUE=PUBLIC_THRESHOLD_SWEEP_PACKAGE_VERIFIED')
    except BaseException:
        print('STOP ISSUE=PUBLIC_THRESHOLD_SWEEP_PACKAGE_INVALID');raise SystemExit(2)
