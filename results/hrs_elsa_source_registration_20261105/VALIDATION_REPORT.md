# Synthetic validation — ELSA source registration V1

Date: 5 November 2026. **Public engineering completed; no real registration, clinical count or training executed.**

## Actual verification

- Python 3.12.14, pytest 9.1.1, pandas 3.0.6 in the existing project virtual environment.
- Command: `.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_source_registration_20261105/tests` from repository root.
- **60 passed, 0 failed** (last source-tree run: 0.43 seconds). All ZIPs and Stata tables were invented in temporary directories. They contain invented numeric columns, not real participant information.
- Unchanged public count release: 27/27 manifest-listed files verified; release-manifest SHA256 `e1026e76d8d96560eb6973cbf13a3d528ea30ed9356c60dd72febfc60faa4373`.
- Prior public evidence preservation: 11/11 fingerprints in `PRIOR_PUBLIC_BINDINGS.json` matched. No old file was rewritten. This assertion concerns those explicit public files, not any private volume or uninspected historical outputs.
- Copied independent runtime SHA256 matches the original count runtime exactly: `d1227f629eaaf727c3ca41195c7ab1dccd1da3a15040168752b1f2cbbc3b2e02`.

## Coverage

The 60 cases cover complete ten-member configuration generation, twelve-member optional nurse registration, member/container hash distinction, distinct per-role contents, correct private file/directory permissions, first registration versus a reviewed local pin, wrong/missing pins, historical code hashes rejected as archive pins, five unsupported edition claims, missing independent scope before archive access, missing/relative/symlinked sources, wrong study/name/mode, missing members, duplicate full names/basenames/across archives, valid multiple explicit containers, unrelated containers refused, corrupt containers/CRC, non-Stata contents, unsafe ZIP paths/symlinks, resource limits, concurrent archive mutation, modified public count bindings, refusal to overwrite configurations/destinations, failed/interrupted consumed attempts, four invalid authorization bindings, agent rejection before private configuration reading, absence of cohort/row-reader imports, unchanged scientific fields and unchanged unresolved count review.

Pandas generated legitimate **invented** Stata-format 114, 118 and 119 tables. These format releases remain distinct from study editions. Registration itself uses only standard-library ZIP/binary streaming/header checks; no pandas, pyreadstat or count-engine import occurs. A header check does not establish actual clinical-variable compatibility.

Authorization rejection tests use invented receipts and mock the local boundary only inside unit tests. No real authorization was created, read or confirmed. Production agent/TTY checks remain intact. Real input presence, acquisition identity, permissions and successful local registration are **not verified** by these tests.

## Source and protocol SHA256

| Public file | SHA256 |
|---|---|
| `register_sources.py` | `6400235afa59406ead390a6260f83b5a2ce0e05f25e872f032fb69b15720b9ea` |
| `registration.py` | `e4f2cc64190b220af41e6af5f7161d0f18f147d4a6c4177656cf87e1f0c4ccc9` |
| `config_generation.py` | `93aadb9a98d80e867656f4b894f9c72109591e07439188acf2d4f0b3d13d58ab` |
| `local_execution.py` | `d1227f629eaaf727c3ca41195c7ab1dccd1da3a15040168752b1f2cbbc3b2e02` |
| `verify_package.py` | `0ead93c16b33ea94d1f9e18345b4ea948b60bc04de1e4b23aa9d6e5eef13bc32` |
| `PUBLIC_SOURCE_CONTRACT.json` | `f92f18d41f4b57d74f11977f64cca0ca8882be4e49baf5d25502edf4b6870b26` |
| `REGISTRATION_PROTOCOL.json` | `3d5b3554763ee6bf3f2c92a606c86d1539f16be1e0e527c0acde3b9f67e33e79` |

The package manifest fingerprints all distributed public files except itself; compare the separate ZIP SHA256 before independent transfer. This checks transfer integrity, not publisher origin. `PACKAGE_REBUILD_VERIFICATION.md` records the exact ZIP extraction test separately.

## Empirical limitation

The public historical records are insufficient to authenticate the ten required inputs. They supply no clinical archive/member pins; Core 1–5 presence and actual acquired edition are not proven. Existing source-use and independent count authorization gates remain unresolved until independently established in the separate local environment. No empirical event or feasibility claim follows from 60 synthetic tests.
