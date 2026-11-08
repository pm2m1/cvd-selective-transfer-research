# Epoch-zero follow-up validation report

**PUBLIC IMPLEMENTATION READY FOR SEPARATE INDEPENDENT LOCAL AUTHORIZATION. No clinical experiment was executed.**

## Synthetic verification

- Final focused suite: **32 tests passed, zero failures**. Exact log: SYNTHETIC_RELEASE_UNIT_TEST_LOG.txt.
- Full synthetic CLI smoke: all45 registered split/budget cells,90 adapted fits,one shared source fit,three arms. RC0; terminal SYNTHETIC_ONLY COMPLETED.
- Five invented conditions selected epoch0. All five restored the exact initial model state and produced source-only-equivalent raw probabilities.
- All45 paired conditions passed optimizer initialization, update/RNG prefix and common checkpoint-score equality checks.
- Demo settings explicitly differ only for synthetic speed: invented90-person target pool, source2/target3 epochs,20 bootstrap repetitions. Real protocol remains source30/target20 and1,000 bootstrap repetitions.
- Missing calibration support remains unavailable; no class support or event values were invented to force eligibility.
- Tests demonstrate later-epoch selection, exact zero restoration, BCE improvement with worse outer AP, unchanged budgets, label isolation, distinct fold/pooled estimands, old-authorization rejection, cancelled authorization, private file modes, interrupted/failed no-retry lifecycle, manifest tamper/traversal rejection and no-overwrite installation.
- One early installer test failed because the test used the macOS /var symlink. The fixture was moved to its real /private/tmp location; symlink protection was not weakened. All final tests pass.

## Source preservation and dependency identity

- 18/18 explicitly copied public dependencies match their original registered SHA256 values. No original public implementation or protocol was modified.
- Original ArmA calls the unchanged vendored fit. A direct synthetic comparison confirms matching curves and restored weights against that function.
- The unchanged retained-export verifier accepts only the original bound completed development export, never a dataset path or new arbitrary prediction file.
- The unchanged local runtime retains agent/CI rejection, interactive scope confirmation, separate purpose/output/code/config binding and exclusive consumed output markers.
- Runtime versions are reviewed in the new local config and checked before authorization/execution. Hash equality is not provider permission, dataset authenticity or scientific acceptance.

## Architecture and protocol scope

Exactly three arms, one original8,033-parameter architecture, fixed.001 target LR/BCE and the inherited three-fold/three-seed/five-budget design. Source-only C is raw-forward equivalent to B epoch0 for this LayerNorm/no-dropout network. Calibration differs intentionally: B may spend calibration labels; C does not.
Primary equal-fold paired AP is distinct from secondary pooled OOF AP. Conditional participant-cluster uncertainty accounts for participant reuse across repeats, but not retraining, survey clusters or historical model/design selection. No scientific winner is assigned automatically.

## Actual validation runtime

```json
{
  "python": "3.12.14",
  "numpy": "2.5.3",
  "pandas": "3.0.6",
  "torch": "2.14.0",
  "scikit-learn": "1.9.1",
  "scipy": "1.18.1",
  "matplotlib": "3.11.2",
  "joblib": "1.6.0"
}
```

## New code/protocol SHA256 values

| File | SHA256 |
|---|---|
| checkpoints.py | `0e3aee8e20dbc8e8f01e518a06b39f4a7b129dd82a0eda0accc2e469a71f0eeb` |
| experiment.py | `6fd3cce1afb1f7d58cab34ffd231c378619e7bf7213f676a34ba7f63c3f3e439` |
| paired_report.py | `6994370d42b82f2e85684b4adb3379bf9ddaa2fd2c95886ffd13cb7675fa8fea` |
| epoch_zero.py | `b9579210065d23bbaebb38637d08ab8d2791e14bf4979919fbfc59558792fb29` |
| package_integrity.py | `84e751c0f463b7902571c570ed10eda99a1b792d3324540bc1bc4e51026552ff` |
| install_public_epoch_zero.py | `ea2098f0df1ee77b04a0814188d857b06e1bb5cd5a45ccf0807315f2cb6acdf0` |
| EXPERIMENT_CONFIG.json | `efd80898ce5d9f95f6751972711bafc3f30abd438fc37d9bc88ab2f41971f088` |
| SCIENTIFIC_PROTOCOL.md | `5d8d7d52986c243c08be64f59930c05f7522ced141ecea107bda5eb7244cbf42` |
| tests/test_epoch_zero.py | `4ee13ba8a7d8c3cf0c4687ecb98274fabd25624c7104f03f8ae517253ff0756d` |

## Standalone public release

PUBLIC_PACKAGE_MANIFEST.json is the explicit installation allowlist; RELEASE_SHA256.txt separately records its digest to avoid self-referential hashing. The release ZIP contains the allowlisted public files plus that manifest and release-digest file. It excludes all invented execution outputs/checkpoints as well as any real private artifact. No private records were accessed to prepare it.
Installation and standalone revalidation results are recorded in STANDALONE_VALIDATION.json. Existing destination rejection, checksum failure, unrelated-file exclusion and marker preservation are tested. The installer must be run independently by the actual operator for the real installation; no such installation or clinical execution is claimed here.

## Remaining prerequisites

Independent verification of actual processing permission and isolation; a new reviewed private configuration containing the existing four retained-artifact bindings; reviewed exact runtime; a fresh operator authorization and unused private output destination. The package supplies none of these approvals automatically.
All real metrics remain unavailable to this session. INDEPENDENT_TEST_NOT_AVAILABLE. No real export, training, test inference or previous-artifact modification occurred.

## Standalone result

The public-only installer succeeded in a fresh temporary installation. All32 tests passed there (zero failures), followed by RC0 for the complete invented-data CLI smoke. Every invented output file checked had no group/other permissions. No sibling repository or private input was required. Final release extraction is independently verified before delivery; see the adjacent release verification record.
