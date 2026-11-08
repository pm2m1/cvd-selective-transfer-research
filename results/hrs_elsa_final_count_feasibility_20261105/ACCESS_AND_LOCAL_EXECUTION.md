# Independent local installation and execution

This package is public preparation. **No new protected-data operation has been authorized or executed here.** Previous downloads, Stage C permissions, results and consumed attempts do not establish scope for this operation. No account, licence, human signature or approval has been created on the researcher's behalf.

## Public installation

Transfer the public-only release ZIP manually into an approved environment inaccessible to AI tools/indexers. Extract it to a new tools directory. Its runtime needs no project files outside the package, no network access, commercial statistics package or ML libraries. The documentation-rebuild helper is optional and requires the original public documentation ZIP; counting uses the bundled verified mapping directly.

From the extracted package:

```sh
python3 -B verify_public.py
```

Alternatively, from the public preparation source, independently install only the manifest-enumerated public files into a **new** destination:

```sh
python3 -B verify_public.py --install-to /ABSOLUTE/NEW/ISOLATED/PUBLIC/TOOLS
```

This installer never recursively copies a repository, transfers private inputs, overwrites an existing destination, edits original tools or creates an authorization. Its permissions do not prove environmental isolation. If installation fails, preserve its files; do not silently overwrite them. Use the verified ZIP/exclusive destination after understanding the failure.

Python3.12.14, pandas3.0.6, NumPy2.5.3 and pytest9.1.1 were used for public synthetic verification. `requirements.txt` pins the tested libraries. Use an appropriate independent environment, ideally with approved offline wheels. Do not alter a frozen experiment environment to make this run. The operator should run the public synthetic suite there before authorization:

```sh
python3 -B -m pytest -q -p no:cacheprovider tests
```

No protected input is used by that suite; its Stata files are invented. Do not run real input through Codex, even if a synthetic demonstration succeeds.

## Inputs: explicit paths and original registered hashes only

Copy `config.template.json` **outside the immutable public tool tree** into approved private configuration storage. Populate actual paths and original registered SHA256 bindings locally, never paste them into AI. The template deliberately has unset paths/hashes and unresolved scope. It is not executable approval.

The count reader requires Harmonized ELSA H and original Core1–9 products matching `OFFICIAL_VARIABLE_DICTIONARY.md`. Every source descriptor has an absolute local path, registered expected SHA256, exact product basename and truthful claimed archive edition. Unknown edition remains unknown. Do not replace an old registered checksum with the hash of an unexplained changed file. Do not rename or substitute another clinical release to satisfy a product name. Missing required tables, fields, label codes, or incompatible revisions fail closed.

For automatic eight-role availability, supply `measurement_sources` for `wave_4_nurse_data.dta` and `wave_6_elsa_nurse_data_v2.dta`. Their source hashes are checked before and after reading. Only mapped selected columns are read. If measurement inputs are not supplied, set that optional block to null and retain NOT_COMPUTED availability. An optional separately reviewed feature/exposure evidence file can refine baseline reconstruction or establish prior model-use history; its schema is documented in `BASELINE_PREDICTOR_CONTRACT.md`. It must not contain future measurements or manufactured no-prior-use declarations.

The original sources are read-only. All histories are linked by exact numeric IDAUNIQ; string/fuzzy joins and duplicate person rows reject. The new source population and source/measurement choices must be covered by applicable provider/institutional permissions. The public dictionary authenticates documentary bytes, not the clinical archive's distributor origin. Existing qualified provenance remains qualified.

## Fresh scope and original independent-operator boundary

Independently establish permission for this distinct original-table count, measurement availability and private planning operation. Only then record `source_use_review=INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION` locally. This string is a record of a fact established elsewhere, **not** software permission or a replacement for a provider/institutional condition. No sign-off is supplied in this package.

Choose new private authorization and output destinations. Output's parent must already be approved private storage with mode0700. The original runtime remains byte-identical; a new purpose binds this operation. Source/configuration/code/map/protocol hashes are verified; actual runtime versions and output hashes are recorded. Existing old authorizations or output/attempt destinations cannot be reused.

Ordinary independent Terminal commands, replacing the uppercase placeholder paths locally:

```sh
python3 -B run_counts.py --authorize-local --config /ABSOLUTE/PRIVATE/NEW_COUNT_CONFIG.json --authorization /ABSOLUTE/PRIVATE/NEW_COUNT_AUTHORIZATION.json --output /ABSOLUTE/PRIVATE/NEW_COUNT_OUTPUT
python3 -B run_counts.py --execute-local --config /ABSOLUTE/PRIVATE/NEW_COUNT_CONFIG.json --authorization /ABSOLUTE/PRIVATE/NEW_COUNT_AUTHORIZATION.json --output /ABSOLUTE/PRIVATE/NEW_COUNT_OUTPUT
```

The application verifies public package/config readiness before invoking the existing interactive operator prompt. Invalid configuration stops before creating authorization or consuming an execution destination. Complete the prompt personally only when its statements are true. Never pipe answers, impersonate an operator, unset agent markers to defeat detection, or reuse a completed operation. Codex has not executed either command with clinical inputs. Agent/CI rejection and TTY checks precede config/data access. Authorization issuance itself performs no cohort count.

Execution creates an exclusive consumed start record before restricted processing. Failures/interruptions retain receipts; an abrupt termination may leave only the consumed start record. In every case the existing output directory prevents automatic retry. Do not delete/rename markers or overwrite receipts. Any justified recovery is a separately assessed new operation, not a silent retry.

## Review and disclosure

Success prints only `REVIEW ISSUE=PRIVATE_OUTPUT_REQUIRES_DISCLOSURE_REVIEW`, regardless of actual scientific support. Read the new private counts/planning files locally under applicable permission; do not upload them to Codex, ChatGPT, GitHub or cloud editors. Public statuses do not publish counts, small cells, individual values, paths, unrestricted exceptions or a data-conditioned scientific verdict.

Review unknown histories and censoring, fixed-versus-variable horizon differences, component joint accounting, feature chronology, original input bindings, and separate adaptation/stopping/calibration/evaluation reserves. Potential unused-evaluation support is not an independent-test guarantee. All aggregate cells and feasibility conclusions require disclosure review, considering differencing and joint small cells. No operation automatically extracts a modeling dataset or authorizes training.
