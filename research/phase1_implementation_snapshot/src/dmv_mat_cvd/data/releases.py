"""Controlled release metadata and aggregate-only local inventory. No training."""
from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import re

import pandas as pd


def load_json(path: str | Path) -> dict:
    def unique(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise ValueError("Duplicate JSON key; configuration is ambiguous")
            output[key] = value
        return output
    value = json.loads(Path(path).read_text(), object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def digest_json(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def file_sha256(path: str | Path) -> str:
    result = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def safe_relative(root: str | Path, name: str) -> Path:
    base = Path(root).resolve()
    path = (base / name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(base):
        raise ValueError("Release paths must stay within the supplied directory")
    return path


MANIFEST_FIELDS = {'cohort_name', 'release_version', 'date_received', 'source_repository',
                   'authorized_user_context', 'raw_file_names', 'raw_file_checksums',
                   'documentation_files', 'codebooks', 'manuals', 'notes', 'synthetic_fixture'}


def validate_manifest(manifest: dict, directory: str | Path | None = None) -> dict:
    errors = []
    if set(manifest) - MANIFEST_FIELDS:
        errors.append('Unsupported manifest fields; credentials and participant data are prohibited')
    for field in ('cohort_name', 'release_version', 'date_received', 'source_repository', 'authorized_user_context'):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip() or manifest[field].startswith('TODO'):
            errors.append(f'{field}: required release metadata')
    try:
        date.fromisoformat(manifest.get('date_received', ''))
    except (ValueError, TypeError):
        errors.append('date_received: ISO date required')
    for field in ('raw_file_names', 'documentation_files', 'codebooks', 'manuals'):
        value = manifest.get(field)
        if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value):
            errors.append(f'{field}: nonempty relative filename list required')
        elif len(set(value)) != len(value):
            errors.append(f'{field}: duplicate filenames')
        else:
            for name in value:
                try:
                    path = safe_relative(directory or '.', name)
                    if directory is not None and not path.is_file():
                        errors.append(f'{field}: declared file is unavailable')
                except ValueError:
                    errors.append(f'{field}: unsafe path')
    if not isinstance(manifest.get('notes', ''), str):
        errors.append('notes must be plain release metadata text, never nested records')
    if 'synthetic_fixture' in manifest and type(manifest['synthetic_fixture']) is not bool:
        errors.append('synthetic_fixture must be an explicit boolean')
    raw_names = manifest.get('raw_file_names')
    raw_names = raw_names if isinstance(raw_names, list) and all(isinstance(x, str) for x in raw_names) else []
    checksums = manifest.get('raw_file_checksums', {})
    if not isinstance(checksums, dict) or set(checksums) != set(raw_names):
        errors.append('raw_file_checksums: exactly one SHA256 per raw file required')
    else:
        for name, checksum in checksums.items():
            if not isinstance(checksum, str) or not re.fullmatch('[0-9a-f]{64}', checksum):
                errors.append('raw_file_checksums: invalid SHA256')
            elif directory is not None:
                try:
                    path = safe_relative(directory, name)
                    if not path.is_file() or file_sha256(path) != checksum:
                        errors.append('raw_file_checksums: file missing or checksum mismatch')
                except ValueError:
                    errors.append('raw_file_checksums: unsafe path')
    # Metadata must describe authorization, never contain authentication material.
    text = json.dumps(manifest).lower()
    if re.search(r'(bearer\s+|access_token|api_key|password|secret_key|token=|://[^/\s]+:[^/\s]+@)', text):
        errors.append('Authentication material is prohibited in release manifests')
    return {'valid': not errors, 'files_verified': directory is not None and not errors,
            'errors': sorted(set(errors)), 'manifest_hash': digest_json(manifest)}


READABLE = {'.csv', '.tsv', '.sas7bdat', '.xpt', '.dta'}


def read_raw(path: str | Path, identifier_column: str | None = None) -> pd.DataFrame:
    path = Path(path)
    extension = path.suffix.lower()
    if extension in {'.csv', '.tsv'}:
        return pd.read_csv(path, sep='\t' if extension == '.tsv' else ',',
                           dtype={identifier_column: 'string'} if identifier_column else None)
    if extension in {'.sas7bdat', '.xpt'}:
        return pd.read_sas(path, format='sas7bdat' if extension == '.sas7bdat' else 'xport', encoding='utf-8')
    if extension == '.dta':
        return pd.read_stata(path, convert_categoricals=False)
    raise ValueError('Unsupported local tabular format')


def inventory(directory: str | Path, participant_columns: dict[str, str] | None = None,
              max_read_bytes: int = 256 * 1024 * 1024) -> dict:
    """Read only bounded files; large/unsupported files are explicitly skipped.

    Names/types/counts only, no values, examples, distinct values, min/max dates,
    participant IDs or raw reader exception messages are emitted.
    """
    root = Path(directory).resolve()
    if not root.is_dir() or max_read_bytes < 1:
        raise ValueError('Supply an existing directory and positive read-size limit')
    rows = []
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        name = str(path.relative_to(root))
        if not path.resolve().is_relative_to(root):
            rows.append({'file_name': name, 'status': 'skipped_external_symlink'})
            continue
        item = {'file_name': name, 'file_type': path.suffix.lower(), 'bytes': path.stat().st_size}
        if not path.resolve().is_relative_to(root):
            item['status'] = 'skipped_external_symlink'
        elif path.suffix.lower() not in READABLE:
            item['status'] = 'unsupported_metadata_only'
        elif path.stat().st_size > max_read_bytes:
            item['status'] = 'too_large_metadata_only'
        else:
            try:
                frame = read_raw(path, (participant_columns or {}).get(name))
                item.update(status='read', row_count=len(frame), column_count=len(frame.columns),
                            columns=[str(c) for c in frame.columns],
                            dtypes={str(c): str(t) for c, t in frame.dtypes.items()},
                            missing_counts={str(c): int(v) for c, v in frame.isna().sum().items()},
                            date_like_fields=[str(c) for c in frame if pd.api.types.is_datetime64_any_dtype(frame[c]) or re.search(r'date|time|dob', str(c), re.I)],
                            candidate_identifier_fields=[str(c) for c in frame if re.search(r'(^id$|_id$|^id_|participant|subject|identifier)', str(c), re.I)])
                identifier = (participant_columns or {}).get(name)
                if identifier is not None:
                    if identifier not in frame:
                        item['identifier_status'] = 'mapped_column_missing'
                    else:
                        ids = frame[identifier]
                        item.update(identifier_status='mapped', missing_participant_ids=int(ids.isna().sum()),
                                    duplicate_participant_id_rows=int(ids.notna().mul(ids.duplicated(keep=False)).sum()),
                                    duplicate_participant_id_excess=int(ids.dropna().duplicated().sum()))
            except Exception as exc:
                item.update(status='read_failed', error_type=type(exc).__name__)
        rows.append(item)
    return {'aggregate_only': True, 'training_performed': False, 'maximum_read_bytes': max_read_bytes,
            'identifier_candidates_are_not_mappings': True, 'files': rows}
