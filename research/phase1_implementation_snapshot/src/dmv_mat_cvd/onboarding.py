"""Aggregate-only release inventory, cohort dry-run, and explicit locked execution."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .config import ExperimentConfig
from .data.adapters import ARICAdapter, MESAAdapter
from .data.cohort_construction import readiness_text
from .data.mapping import mapping_report
from .data.releases import inventory, load_json, read_raw, safe_relative
from .experiments.runner import run_experiment


def save_report(result, directory: str | Path):
    output = Path(directory) / f'{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}'
    output.mkdir(parents=True, exist_ok=False)
    (output / 'readiness.json').write_text(json.dumps(result.report, indent=2, allow_nan=False) + '\n')
    (output / 'readiness.txt').write_text(readiness_text(result.report))
    (output / 'mapping_audit.txt').write_text(mapping_report(result.report['mapping_audit']))
    return output


def run_from_config(config_path: str | Path):
    cfg = ExperimentConfig(**load_json(config_path))
    if not cfg.publication_mode:
        raise ValueError('The onboarding run command requires explicit locked/publication configuration')
    cohorts = []
    for role, adapter_class in (('source', ARICAdapter), ('target', MESAAdapter)):
        item = cfg.cohort_inputs[role]
        manifest = load_json(item['release_manifest'])
        if item.get('raw_file') not in manifest['raw_file_names']:
            raise ValueError('Input raw file must be explicitly listed in the release manifest')
        identifier = next(f.get('raw') for f in load_json(item['mapping_config'])['fields'] if f['canonical'] == 'participant_id')
        raw = read_raw(safe_relative(item['release_directory'], item['raw_file']), identifier)
        adapter = adapter_class(mapping_config=item['mapping_config'], endpoint_crosswalk=item['endpoint_crosswalk'])
        result = adapter.dry_run(raw, manifest=manifest, release_directory=item['release_directory'],
                                 policy=load_json(item['readiness_policy']))
        report_path = save_report(result, Path(cfg.output_dir) / 'onboarding')
        print(f'{role}: COHORT_READY = {"YES" if result.report["ready"] else "NO"}; audit: {report_path}')
        if result.cohort is None or not result.report['ready'] and not cfg.exploratory_override:
            raise ValueError('Readiness gate blocked modeling; inspect the saved aggregate report')
        cohorts.append(result.cohort)
    return run_experiment(*cohorts, cfg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inv = commands.add_parser('inventory')
    inv.add_argument('directory')
    inv.add_argument('--identifier-mapping', help='JSON object: relative filename -> verified raw participant-ID column')
    inv.add_argument('--max-read-mb', type=int, default=256)
    inv.add_argument('--output', required=True)
    dry = commands.add_parser('dry-run', aliases=['readiness'])
    dry.add_argument('--cohort', choices=['aric', 'mesa'], required=True)
    dry.add_argument('--raw-file', required=True)
    dry.add_argument('--mapping', required=True)
    dry.add_argument('--crosswalk', required=True)
    dry.add_argument('--manifest', required=True)
    dry.add_argument('--release-directory', required=True)
    dry.add_argument('--policy', required=True)
    dry.add_argument('--output-dir', default='results/onboarding')
    run = commands.add_parser('run')
    run.add_argument('--config', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'inventory':
            result = inventory(args.directory, load_json(args.identifier_mapping) if args.identifier_mapping else None,
                               args.max_read_mb * 1024 * 1024)
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('x') as handle:
                json.dump(result, handle, indent=2, allow_nan=False)
            print(f'Aggregate inventory written to {destination}; no training performed')
        elif args.command in {'dry-run', 'readiness'}:
            manifest = load_json(args.manifest)
            path = safe_relative(args.release_directory, args.raw_file)
            if args.raw_file not in manifest.get('raw_file_names', []):
                raise ValueError('Raw file must belong to the supplied manifest')
            adapter = (ARICAdapter if args.cohort == 'aric' else MESAAdapter)(
                mapping_config=args.mapping, endpoint_crosswalk=args.crosswalk)
            identifier = next(f.get('raw') for f in load_json(args.mapping)['fields'] if f['canonical'] == 'participant_id')
            result = adapter.dry_run(read_raw(path, identifier), manifest=manifest, release_directory=args.release_directory,
                                     policy=load_json(args.policy))
            output = save_report(result, args.output_dir)
            print(readiness_text(result.report))
            print(f'Aggregate reports: {output}; no training performed')
        else:
            result = run_from_config(args.config)
            print(f'Locked experiment: {result["output_directory"]}')
    except Exception as exc:
        # Third-party parser/conversion exceptions can embed raw row values.
        parser.exit(2, f'Onboarding command stopped ({type(exc).__name__}). No record values emitted; inspect aggregate audits/configuration.\n')


if __name__ == '__main__':
    main()
