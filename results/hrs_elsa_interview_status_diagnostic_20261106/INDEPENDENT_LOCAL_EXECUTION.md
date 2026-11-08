# Independent local execution — no real diagnostic performed by Codex

## 1. Install this NEW public package

Use the genuine independently controlled Terminal/environment, outside AI tools and indexers. Do not change environment flags to disguise agent/CI operation. These commands are **instructions for the operator**, not commands Codex will run on private paths. Both old registration/count installations and their consumed outputs stay untouched.

Transfer `ELSA_Interview_Status_Diagnostic_20261106_Public.zip` to the independent environment, then extract it into a new, unused **public staging directory**. ZIP entries are rooted at the package files, not an enclosing repository. Do not merge into an existing installation.

```sh
mkdir "/ABSOLUTE/NEW/PUBLIC_STATUS_DIAGNOSTIC_STAGING"
python3 -B -m zipfile -e "/ABSOLUTE/TRANSFER/ELSA_Interview_Status_Diagnostic_20261106_Public.zip" "/ABSOLUTE/NEW/PUBLIC_STATUS_DIAGNOSTIC_STAGING"
cd "/ABSOLUTE/NEW/PUBLIC_STATUS_DIAGNOSTIC_STAGING"
python3 -B verify_public.py
python3 -B verify_public.py --install-to "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_tools"
cd "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_tools"
python3 -B verify_public.py
```

Run extraction only after the `mkdir` succeeds. The installer copies only manifest-enumerated public files, creates restrictive permissions and refuses an existing destination. It never transfers private inputs. If a destination is already present, stop; do not overwrite it or weaken its checks. Package digests verify transfer integrity, not independent publisher authentication or legal rights.

Use an independently controlled Python environment matching the verified Python 3.12.14 / pandas 3.0.6 / NumPy 2.5.3 stack where possible. `python3` below must select that environment. If dependencies are needed, install them locally:

```sh
python3 -B -m pip install -r requirements.txt
```

Do not create a virtual environment inside the fingerprinted tool directory; use a separate environment outside it. Actual runtime versions are saved privately. Other combinations are not claimed verified. Optional public synthetic validation needs `requirements-test.txt`, then `python3 -B -m pytest -q -p no:cacheprovider tests`. No synthetic test opens actual sources.

## 2. Prepare a fresh private configuration

Create a genuinely new private run directory:

```sh
mkdir -m 700 "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_run"
python3 -B verify_public.py --new-config "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_run/status.reviewed.json"
```

The new-config command creates only an unresolved public template, mode `0600`, exclusively. It reads no existing private file, sets no authorization and opens no source. Do not copy or edit the old count configuration. Do not create authorization files manually.

Edit **only this new private configuration locally**, never through Codex. Supply:

- `source_registration`: absolute path and locally verified SHA256 of the existing `source_registration.private.json`, under the independently applicable scope for reading that integrity record. The tool verifies its public registration identities and registered member relationships. It does not inspect registration authorization/receipt files or any failed-count receipt/output.
- `sources`: exactly ten materialized-file descriptors copied byte-for-byte at the JSON-value level from that registration manifest's `members[].materialized_file`, keyed by role. Use the existing registered loose files **in place**. Do not move, rename, rehash-as-new, rewrite or relabel clinical sources to satisfy a check. Do not supply ZIP paths. Optional nurse members in the manifest are not supplied.
- Preserve `schema`, `mode`, `no_models: true`, `no_event_counts: true`, and the template's new diagnostic protocol/mapping fingerprints. Preserve each source's unresolved edition and the original fingerprints. Old count protocol hashes belong to its historical protocol, not this new diagnostic config's `protocol_sha256`.

Independently establish that these are the exact source snapshots relevant to the failed count. Merely finding ten registered files does not prove equivalence to the historical failed operation; this tool will not infer it by opening that operation's artifacts. Any required prior-config metadata review must have its own applicable local permission.

### Distinct source-use review

Before authorization, establish provider/institutional permission and actual isolation covering this **new** status-only operation, including whole-file hashing, selected-column reads and private aggregate reporting. Old research, registration or count authorization is not reused.

Only after that scope is genuinely independently established, record:

```json
"source_use_review": "INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_STATUS_ONLY_OPERATION",
"reviewed_scope": [
  "READ_REGISTERED_SOURCE_AND_INTEGRITY_METADATA",
  "HASH_REGISTERED_SOURCE_BYTES",
  "READ_LINKAGE_AND_INTERVIEW_STATUS_COLUMNS_ONLY",
  "WRITE_PRIVATE_AGGREGATE_STATUS_DIAGNOSTICS"
]
```

These literals record an independently established fact; they are not a licence or automatic approval. If scope remains unresolved, keep the unresolved template and stop. Configuration metadata itself stays private. The helper does not ask anyone to paste protected paths, hashes or findings into AI.

## 3. Fresh interactive authorization, then one execution

From the NEW tool directory, run these exact supported commands independently. The config is the same new file for both commands. The authorization file and output directory must not already exist; their parent must be private (`0700`).

```sh
python3 -B run_status_diagnostic.py --authorize-local --config "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_run/status.reviewed.json" --authorization "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_run/status.authorization.json" --output "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_run/status_output"
python3 -B run_status_diagnostic.py --execute-local --config "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_run/status.reviewed.json" --authorization "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_run/status.authorization.json" --output "$HOME/ResearchPrivate/hrs_elsa_interview_status_diagnostic_20261106_run/status_output"
```

The original runtime prompts interactively for the independent operator and scope confirmation. Do not pipe names/phrases, automate confirmations, simulate a human, or manually construct an authorization. Purpose is **`elsa_interview_participation_status_only_v1_20261106`**. Authorizations bind that purpose, exact new config, non-test Python source and exact new output destination. Old purpose or changed bindings fail. Authorization success reads no clinical columns and performs no diagnostic.

The execution consumes its new attempt before restricted processing. It verifies public files, new scope, exact registered manifest/source bindings, then reads only the selected columns. It does not invoke the old counting pipeline. Private data files and the registration manifest are opened read-only and reverified; no former research artifact is rewritten.

### Allowlisted Terminal statuses

- Public verification/installation: `PASS ISSUE=PUBLIC_STATUS_DIAGNOSTIC_PACKAGE_VERIFIED` or the same ending `_INSTALLED`.
- New template: `PASS ISSUE=NEW_UNRESOLVED_STATUS_CONFIG_CREATED_NO_AUTHORIZATION`.
- Preauthorization config failure: `STOP ISSUE=STATUS_CONFIG_NOT_READY_NO_AUTHORIZATION_RECORDED`.
- Authorization success: `LOCAL_AUTHORIZATION_RECORDED_NO_DATA_PROCESSING`.
- Diagnostic success: `REVIEW ISSUE=PRIVATE_OUTPUT_REQUIRES_DISCLOSURE_REVIEW`.
- Execution rejected/failed: `REVIEW ISSUE=LOCAL_OPERATION_NOT_COMPLETED_INSPECT_PRIVATE_RECEIPT`.
- Invalid CLI: `STOP ISSUE=INVALID_STATUS_DIAGNOSTIC_COMMAND`.

No success console status reveals which private class occurred or how many observations are affected. A generic failure before output creation may have no receipt; do not invent one.

## 4. Review privately and preserve every attempt

Review the protected output locally using `SCIENTIFIC_INTERPRETATION_GUIDE.md`. A successful result has the private status matrix, integrity record, static operational summary and successful consumed completion. Invalid linkage can leave only the input diagnostic and failed receipt. Incompatible status codes can leave a matrix followed by failed completion; that is not an accepted successful report.

Never delete, overwrite, rename, reset or silently resume any failed/interrupted/consumed destination or authorization. No automatic retry occurs. Any further operation requires a documented reason, fresh appropriate scope/authorization and new destinations. The old count attempt remains `FAILED_NO_RETRY` permanently, and the new diagnostic cannot authorize corrected counts.

Detailed counts, raw-state frequencies, wave combinations, code/context, fingerprints, paths and even data-conditioned interpretations stay restricted pending applicable disclosure review. `operational_summary.json` contains only a static acknowledgment and no empirical verdict. Do not upload private reports/logs to AI, GitHub or other external services merely because they are aggregate-only.

Permissions and environment guards do not prove a volume is inaccessible to AI/indexers, legal scope or scientific approval. Establish those facts independently. No real operation, authorization or private inspection was executed by Codex while preparing this package.
