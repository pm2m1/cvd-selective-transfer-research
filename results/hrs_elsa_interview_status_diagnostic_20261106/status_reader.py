"""New-operation selected-column reader. No count-engine/endpoint imports."""
from pathlib import Path
import math
import warnings
from local_execution import need, require_local, Rejected


def normalized(value):
    if type(value).__name__ == 'StataMissingValue':
        return str(value)
    if hasattr(value, 'item'):
        value = value.item()
    return value


def key_class(value):
    if value is None or type(value).__name__ == 'StataMissingValue':
        return None, 'MISSING_LINKAGE'
    if isinstance(value, (str, bool)):
        return None, 'INVALID_LINKAGE_STORAGE'
    try:
        x = float(value)
    except (ValueError, TypeError, OverflowError):
        return None, 'INVALID_LINKAGE_STORAGE'
    if not math.isfinite(x):
        return None, 'MISSING_LINKAGE'
    if not x.is_integer() or not 0 < x < 2**53:
        return None, 'INVALID_LINKAGE_VALUE'
    return int(x), None


def columns(role):
    if role == 'harmonized':
        return {'idauniq'} | {'inw'+str(w) for w in range(1, 10)}
    w = int(role[4:])
    return {'idauniq', 'indoc' if w == 1 else f'w{w}indout', 'askpx1' if w < 3 else 'askpx'}


def read_status(path, role):
    require_local()  # Also guards direct calls; tests mock only invented fixtures.
    import pandas as pd
    required = columns(role)
    quality = {'MISSING_LINKAGE': 0, 'INVALID_LINKAGE_STORAGE': 0,
               'INVALID_LINKAGE_VALUE': 0, 'DUPLICATE_LINKAGE': 0}
    rows = {}
    try:
        # Warning text can contain source context; turn it into a sanitized input
        # failure instead of allowing participant/scalar details into any log.
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with pd.io.stata.StataReader(path, convert_categoricals=False, convert_missing=True) as reader:
                names = {}
                for original in reader.variable_labels():
                    lower = original.lower()
                    need(lower not in names, 'STATUS_COLUMN_CASE_COLLISION')
                    names[lower] = original
                need(required <= set(names), 'REQUIRED_STATUS_FIELDS_MISSING')
                frame = reader.read(columns=[names[n] for n in sorted(required)])
        frame.columns = [n.lower() for n in frame.columns]
        for row in frame.to_dict('records'):
            raw_key = row.pop('idauniq')
            key, issue = key_class(raw_key)
            if issue:
                quality[issue] += 1
                continue
            if key in rows:
                quality['DUPLICATE_LINKAGE'] += 1
                continue  # Never silently use a duplicate for a completed diagnostic.
            rows[key] = {n: normalized(x) for n, x in row.items()}
    except Rejected:
        raise
    except Exception:
        raise Rejected('STATUS_SOURCE_UNREADABLE_OR_CORRUPT') from None
    return rows, quality
