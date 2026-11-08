"""Generate a NEW, still-unapproved count candidate from verified member bytes.

Called inside the separately authorized registration operation only. No cohort imports.
"""
import copy
from pathlib import Path
from local_execution import need, sha, write_json


def generate_count_configuration(template, products, measurements, output):
    candidate = copy.deepcopy(template)
    need(set(products) == set(template['sources']), 'SOURCE_ROLE_SET_MISMATCH')
    for role, source in products.items():
        expected = template['sources'][role]['dataset_basename']
        need(source['dataset_basename'] == expected, 'SOURCE_BASENAME_MISMATCH')
        _verified(source)
    candidate['sources'] = copy.deepcopy(products)
    if measurements is None:
        candidate['measurement_sources'] = None
    else:
        need(set(measurements) == set(template['measurement_sources']), 'MEASUREMENT_ROLE_SET_MISMATCH')
        for role, source in measurements.items():
            need(source['dataset_basename'] == template['measurement_sources'][role]['dataset_basename'], 'SOURCE_BASENAME_MISMATCH')
            _verified(source)
        candidate['measurement_sources'] = copy.deepcopy(measurements)
    # Registration is not count-operation approval; all scientific fields stay frozen.
    need(candidate['source_use_review'] == 'UNRESOLVED_NOT_AUTHORIZED', 'COUNT_REVIEW_MUST_REMAIN_UNRESOLVED')
    write_json(output, candidate)
    return candidate


def _verified(source):
    need(set(source) == {'path', 'sha256', 'dataset_basename', 'claimed_archive_edition'}, 'SOURCE_DESCRIPTOR_INVALID')
    p = Path(source['path'])
    need(p.is_absolute() and not p.is_symlink() and p.is_file(), 'MATERIALIZED_MEMBER_MISSING')
    need(source['claimed_archive_edition'] == 'UNRESOLVED', 'UNSUPPORTED_ARCHIVE_EDITION_CLAIM')
    need(sha(p) == source['sha256'], 'MATERIALIZED_MEMBER_HASH_MISMATCH')
