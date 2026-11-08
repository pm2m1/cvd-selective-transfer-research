"""Explicit public inventory verification/installation; no private input reads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def verify(root=ROOT):
    root=Path(root).resolve()
    m=json.loads((root/'RELEASE_MANIFEST.json').read_text())
    if m.get('scope') != 'PUBLIC_CODE_DOCUMENTATION_AND_INVENTED_TESTS_ONLY': raise ValueError('PUBLIC_SCOPE_INVALID')
    entries=list(root.rglob('*'))
    if any(p.is_symlink() for p in entries): raise ValueError('PUBLIC_LAYOUT_INVALID')
    actual={p.relative_to(root).as_posix() for p in entries if p.is_file()}
    if actual != set(m['files'])|{'RELEASE_MANIFEST.json'}: raise ValueError('PUBLIC_INVENTORY_INVALID')
    for name,h in m['files'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:
            raise ValueError('PUBLIC_BINDING_INVALID')
    return m


def install(destination):
    m=verify(); p=Path(destination)
    if not p.is_absolute() or any(x.is_symlink() for x in (p,*p.parents)) or p.exists() or not p.parent.is_dir():
        raise ValueError('PUBLIC_INSTALLATION_REFUSED')
    p.mkdir(mode=0o700)
    # Exclusive files; partial installation is retained and never silently retried.
    for name in [*m['files'],'RELEASE_MANIFEST.json']:
        target=p/name;target.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write((ROOT/name).read_bytes())
    verify(p)


def new_config(destination):
    verify()
    p=Path(destination)
    if not p.is_absolute() or any(x.is_symlink() for x in (p,*p.parents)) or p.exists() or p.suffix!='.json':
        raise ValueError('NEW_CONFIG_REFUSED')
    s=p.parent.stat()
    if s.st_mode&0o077 or s.st_uid!=os.getuid() or p.is_relative_to(ROOT):raise ValueError('PRIVATE_PARENT_REQUIRED')
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write((ROOT/'review_config.template.json').read_bytes())


class Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('PUBLIC_COMMAND_INVALID')


def main():
    try:
        p=Parser();g=p.add_mutually_exclusive_group()
        g.add_argument('--install-to',type=Path);g.add_argument('--new-config',type=Path)
        a=p.parse_args()
        if a.install_to:install(a.install_to)
        elif a.new_config:new_config(a.new_config)
        else:verify()
        print('PASS PUBLIC_PACKAGE_VERIFIED_NO_SCIENTIFIC_APPROVAL');return 0
    except BaseException:
        print('NO_EXECUTION');return 2


if __name__=='__main__':raise SystemExit(main())
