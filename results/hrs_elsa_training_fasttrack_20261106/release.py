"""Enumerated public-only verification and exclusive installation."""
from pathlib import Path,PurePosixPath
import hashlib,json,os
ROOT=Path(__file__).resolve().parent


def verify(root=ROOT):
    root=Path(root).resolve();m=json.loads((root/'RELEASE_MANIFEST.json').read_text())
    for name,pin in m['files'].items():
        r=PurePosixPath(name);p=root/name
        if r.is_absolute() or '..' in r.parts or p.is_symlink() or not p.resolve().is_relative_to(root) or not p.is_file():raise ValueError('UNSAFE_OR_MISSING_PUBLIC_FILE')
        if hashlib.sha256(p.read_bytes()).hexdigest()!=pin:raise ValueError('PUBLIC_INTEGRITY_FAILURE')
    return m


def install(destination):
    m=verify();out=Path(destination)
    if not out.is_absolute() or os.path.lexists(out) or not out.parent.is_dir():raise ValueError('NEW_PUBLIC_DESTINATION_REQUIRED')
    out.mkdir(mode=0o700)
    for n in [*m['files'],'RELEASE_MANIFEST.json']:
        p=out/n;p.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'wb') as f:f.write((ROOT/n).read_bytes())
    verify(out)
