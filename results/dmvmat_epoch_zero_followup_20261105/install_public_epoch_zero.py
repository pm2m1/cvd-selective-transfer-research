"""Public manifest-allowlist installer; no private input/configuration discovery."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def install(source,destination,expected):
    source=Path(source).absolute();destination=Path(destination).absolute()
    if source.is_symlink() or destination.is_symlink() or destination.exists():raise ValueError('INSTALLATION_DESTINATION_UNAVAILABLE')
    manifest=source/'PUBLIC_PACKAGE_MANIFEST.json'
    if manifest.is_symlink() or digest(manifest)!=expected:raise ValueError('PUBLIC_MANIFEST_MISMATCH')
    inventory=json.loads(manifest.read_text())
    if inventory['schema']!='epoch-zero-public-package-v1':raise ValueError('PUBLIC_MANIFEST_SCHEMA_INVALID')
    files={**inventory['files'],'PUBLIC_PACKAGE_MANIFEST.json':expected}
    # Validate every source before destination creation. Only manifest-listed files.
    for name,h in files.items():
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or rel.suffix not in ['.py','.json','.md','.txt']:raise ValueError('UNSAFE_PUBLIC_FILE')
        current=source
        for part in rel.parts:
            current=current/part
            if current.is_symlink():raise ValueError('PUBLIC_SYMLINK_REJECTED')
        if not current.is_file() or digest(current)!=h:raise ValueError('PUBLIC_FILE_MISMATCH')
    if not destination.parent.is_dir():raise ValueError('DESTINATION_PARENT_REQUIRED')
    # Fail if an ancestor is a symlink; no redirection into an unexpected tree.
    for p in [destination.parent,*destination.parent.parents]:
        if p.is_symlink():raise ValueError('DESTINATION_SYMLINK_REJECTED')
    destination.mkdir(mode=0o700,exist_ok=False)
    for name,h in files.items():
        target=destination/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write((source/name).read_bytes())
        if digest(target)!=h:raise ValueError('COPIED_PUBLIC_FILE_MISMATCH')
    return len(files)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path)
    p.add_argument('--destination',required=True,type=Path);p.add_argument('--expected-manifest-sha256',required=True)
    a=p.parse_args()
    try:install(a.source,a.destination,a.expected_manifest_sha256)
    except BaseException:
        print('STOP ISSUE=PUBLIC_INSTALLATION_NOT_COMPLETED_PRESERVE_DESTINATION');return 2
    print('PASS PUBLIC_EPOCH_ZERO_PACKAGE_INSTALLED_NO_DATA_OPERATION');return 0


if __name__=='__main__':raise SystemExit(main())
