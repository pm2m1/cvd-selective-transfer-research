"""Verify/install only enumerated public package bytes; no clinical file access."""
from pathlib import Path
import argparse,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root=ROOT):
    root=Path(root).resolve();manifest=json.loads((root/'RELEASE_MANIFEST.json').read_text())
    for name,expected in manifest['files'].items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('UNSAFE_PUBLIC_MANIFEST_PATH')
        p=root/rel
        if p.is_symlink() or not p.resolve().is_relative_to(root) or not p.is_file() or digest(p)!=expected:
            raise ValueError('PUBLIC_PACKAGE_BINDING_MISMATCH')
    return manifest

def install(destination):
    manifest=verify();out=Path(destination).expanduser()
    if out.exists() or out.is_symlink() or not out.parent.is_dir():raise ValueError('INSTALL_DESTINATION_NOT_NEW')
    # Only explicitly enumerated public files. Never recurse over a research repo.
    out.mkdir(mode=0o700)
    for name in [*manifest['files'],'RELEASE_MANIFEST.json']:
        target=out/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write((ROOT/name).read_bytes())
    verify(out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--install-to',type=Path);args=p.parse_args()
    try:
        install(args.install_to) if args.install_to else verify()
        print('PASS PUBLIC_COUNT_PACKAGE_VERIFIED'+('_INSTALLED' if args.install_to else ''));return 0
    except Exception:
        print('STOP PUBLIC_COUNT_PACKAGE_NOT_VERIFIED_OR_INSTALLED');return 2

if __name__=='__main__':sys.exit(main())
