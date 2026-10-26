"""Scientific method identifiers, independent of package/build version."""
METHOD_SPEC_VERSION = 'dmv-mat-cvd-method-v1'
SELECTOR_VERSIONS = {
    'legacy_topk': 'legacy-topk-m2-v1',
    'calibrated_threshold': 'calibrated-threshold-m3-v1',
    'calibrated_logical': 'calibrated-logical-m3-v1',
}
PRIMARY_SELECTOR = 'calibrated_logical'
REQUIRED_COMPARATORS = ('source_only', 'head_only', 'full', 'fixed_mask',
                       'random_calibrated_logical', 'legacy_topk',
                       'calibrated_threshold', 'calibrated_logical')
