#!/usr/bin/env python3
"""Public allowlist-only installation into a new independent tool directory."""
import argparse
import json
import os
from pathlib import Path
import sys
from package_runtime import ROOT,verify_package,safe_relative


def install(destination):
    if not destination.is_absolute() or destination.exists() or destination.is_symlink() or not destination.parent.is_dir():
        raise ValueError('NEW_EXPLICIT_DESTINATION_REQUIRED')
    source=ROOT.resolve();target=destination.resolve()
    if target.is_relative_to(source) or source.is_relative_to(target):raise ValueError('SEPARATE_TREE_REQUIRED')
    inventory=verify_package();files={**inventory['files'],'PUBLIC_PACKAGE_MANIFEST.json':None}
    destination.mkdir(mode=0o700)
    for name in files:
        rel=safe_relative(name);p=destination/rel;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write((source/rel).read_bytes())
    verify_package(destination)


class Parser(argparse.ArgumentParser):
    def error(self,message):raise ValueError('ARGUMENTS_INVALID')


def main(argv=None):
    try:
        p=Parser(prog='install_public_followup.py')
        p.add_argument('--destination',required=True);args=p.parse_args(argv)
        install(Path(args.destination));print('PASS: PUBLIC_FOLLOWUP_INSTALLED_NO_AUTHORIZATION');return 0
    except Exception:
        print('STOP: PUBLIC_FOLLOWUP_INSTALLATION_NOT_COMPLETED');return 2


if __name__=='__main__':sys.exit(main())
