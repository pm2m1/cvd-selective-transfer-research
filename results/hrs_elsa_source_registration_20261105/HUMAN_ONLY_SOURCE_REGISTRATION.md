# Independent human-only source registration

This task is prepared, **not run on research data**. Do not execute these commands in Codex, CI, an AI-controlled Terminal or an indexed research workspace. Never paste populated plans, archive paths/hashes, private manifests, authorizations, data members or logs into AI services. All paths below are generic placeholders.

## Install public code without changing the count engine

Transfer the released public ZIP into the independently controlled environment. Create a **new, unused** public tool directory there and extract it. Do not replace the original audit, count tools or any previous installation. The ZIP contains only public source/docs/templates/tests and reference public records. It contains no clinical Stata files.

```sh
mkdir "/ABSOLUTE/NEW/PUBLIC_REGISTRATION_TOOL"
python3 -B -m zipfile -e "/ABSOLUTE/PUBLIC_PACKAGE/ELSA_Source_Registration_20261105_Public.zip" "/ABSOLUTE/NEW/PUBLIC_REGISTRATION_TOOL"
cd "/ABSOLUTE/NEW/PUBLIC_REGISTRATION_TOOL"
python3 -B verify_package.py
```

Execute the extraction only after `mkdir` succeeds. If that directory already exists, stop; choose a genuinely new installation rather than overwriting. Python 3.10+ and its standard library suffice for registration; pytest and pandas are required only for invented-fixture tests. The independent count installation must separately exist at its original registered public release; do not modify it to make a checksum pass.

## Independently review and prepare the private plan

Use a private parent directory already independently controlled, outside this tool's tree, with mode `0700`. New private files must be `0600`. Copy `registration_plan.template.json` to a **new** plan file using a local editor/file workflow that refuses replacement; do not place the populated plan in this public package.

The human must locally supply:

1. `count_tool_root`: absolute path of the unchanged final-count public installation. The registrar verifies the recorded release manifest and every one of its 27 listed public files without executing them.
2. `input_archives`: explicit paths only. No searching or enumeration occurs. Provide an `archive_id`, `archive_path`, `verification_mode`, `expected_archive_sha256`, `study_id: UKDS_SN5050`, and `archive_edition: UNRESOLVED` for each archive. Multiple explicitly supplied archives are supported, but all required basenames must be globally unique. No full ZIP paths have been recovered from historical records.
3. Choose `verify_existing_local_pin` only with an independently reviewed local container hash, never either historical Python hash or the public dictionary ZIP hash. Choose `first_local_registration` only if permitted despite absent historical authentication; its expected hash must remain `null`, and its basename must satisfy the historical `5050stata_*.zip` selector. Do not switch modes to evade a failed pin.
4. `register_measurements: false` for exactly ten history sources. Set it to `true` only if the same review also covers the two named nurse files; all twelve then become required. Missing nurses cannot silently fall back to ten.
5. Only after actual independent review establishes scope for **this new registration operation**, set `source_use_review` to `INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_REGISTRATION_OPERATION` and `reviewed_scope` to exactly:

```json
[
  "READ_AND_HASH_ARCHIVE_BYTES",
  "DECOMPRESS_AND_HASH_SELECTED_MEMBERS",
  "MATERIALIZE_SELECTED_RESTRICTED_FILES_IN_PRIVATE_STORAGE"
]
```

Those settings record an independently established fact; they do not grant permission. If applicable scope, acquisition identity or isolation cannot be established, retain the blocker and do not authorize. The helper does not obtain institutional/provider approval. It will copy full selected clinical files into private storage without interpreting rows; this is itself a protected-data operation.

## Exact fresh authorization → registration sequence

The two commands must use the **same new plan, authorization path and output path**. The authorization file and output directory must not already exist. No human name or confirmation phrase is supplied by a script; the original reused runtime prompts directly in the independent Terminal.

```sh
python3 -B register_sources.py --authorize-local --config "/ABSOLUTE/PRIVATE/NEW/registration.reviewed.json" --authorization "/ABSOLUTE/PRIVATE/NEW/registration.authorization.json" --output "/ABSOLUTE/PRIVATE/NEW/registration_output"
python3 -B register_sources.py --execute-local --config "/ABSOLUTE/PRIVATE/NEW/registration.reviewed.json" --authorization "/ABSOLUTE/PRIVATE/NEW/registration.authorization.json" --output "/ABSOLUTE/PRIVATE/NEW/registration_output"
```

Authorization purpose is `elsa_source_registration_v1_20261105`; old count, diagnostic or other receipts are not accepted. Authorization binds exact plan bytes, all non-test Python source bytes and the new output destination. The registrar also pins public contract, protocol and count-reference bytes. An authorization acknowledgment means **no registration has run yet**.

On execution the consumed start marker is created **before any archive access**. The utility verifies source-use scope, the public count installation and the explicit archives; streams selected bytes; creates private loose files and descriptors; and writes the manifest/candidate. No dataset loader, participant parser, count engine or model is invoked.

### Static public Terminal statuses

- Authorization success: `LOCAL_AUTHORIZATION_RECORDED_NO_DATA_PROCESSING` (RC 0).
- Registration completed: `REVIEW ISSUE=PRIVATE_OUTPUT_REQUIRES_DISCLOSURE_REVIEW` (RC 0). This acknowledges private artifact creation, not authenticity, scientific acceptance or count authorization.
- Local operation failed/rejected: `REVIEW ISSUE=LOCAL_OPERATION_NOT_COMPLETED_INSPECT_PRIVATE_RECEIPT` (RC 2). Before a marker exists there may be no receipt; do not invent one.
- Invalid bundled public references: `STOP ISSUE=PUBLIC_REGISTRATION_REFERENCE_BINDING_INVALID` (RC 2).

Only inspect detailed private receipts/logs locally under the applicable scope. The allowlisted private receipt issue codes include `ARCHIVE_HASH_MISMATCH`, `NON_ARCHIVE_HASH_USED_AS_ARCHIVE_PIN`, `REQUIRED_STATA_MEMBER_MISSING`, `AMBIGUOUS_STATA_MEMBER`, `DUPLICATE_ZIP_MEMBER`, `UNSUPPORTED_ARCHIVE_EDITION_CLAIM`, `REGISTRATION_SOURCE_USE_REVIEW_REQUIRED`, `ARCHIVE_CORRUPT_OR_UNREADABLE`, `MEMBER_CORRUPT_OR_UNREADABLE`, `UNSAFE_ZIP_MEMBER`, and `ARCHIVE_CHANGED_DURING_REGISTRATION`. Unanticipated errors stay `UNEXPECTED_IMPLEMENTATION_EXCEPTION`; no arbitrary error is printed publicly.

## Private outputs and no-retry rules

Within the **new** private output only:

- `operation_started.private.json`: consumed marker.
- `runtime.private.log`: captured stdout/stderr; never share unrestricted context.
- `registered_inputs/<role>/<exact_basename>.dta`: full selected protected bytes, mode `0600`.
- `source_registration.private.json`: container/member hashes, private paths, full member names, code/public-contract/scientific bindings and unresolved-authentication labels.
- `count_config.candidate.private.json`: ten verified loose-file source descriptors; optional two nurse descriptors only if requested. `source_use_review` remains `UNRESOLVED_NOT_AUTHORIZED`.
- `completion.private.json`: completed, `FAILED_NO_RETRY`, or `INTERRUPTED_NO_RETRY`; all consumed. Partial data copies remain private evidence.

Never delete, rename, overwrite, reuse or silently resume a failed destination or authorization. No automatic retry occurs. Resolve any cause under a fresh independently justified protocol/authorization/destination. Original archives are opened read-only and rehashed for mutation detection; they are never rewritten. OS access timestamps may change.

## Count configuration generation and next boundary

`config_generation.py` is the generation utility, called automatically **inside this authorized operation**. It rechecks actual materialized-file hashes and uses the exact frozen template, changing only source descriptors and explicit measurement selection. It has no separate private-data CLI, avoiding duplicate inspection of protected outputs.

The count engine accepts honest `claimed_archive_edition: UNRESOLVED`; no invented edition or engine patch is needed. The generated candidate is **source-complete, not authorized for counting**. Review the private lineage and source compatibility locally. Preserve the candidate byte-for-byte; if a reviewed count configuration is later justified, create a new reviewed copy under the original count protocol, establish that distinct scope, and obtain fresh count authorization with new destinations. Do not reuse registration authorization. The unchanged count engine verifies its own file/protocol/mapping bindings; it does not independently verify this new lineage manifest, which must be retained/reviewed as additional provenance evidence.

No count command is executed or authorized here. No event-count, endpoint feasibility or modeling conclusion is implied. If the original archives cannot be supplied legitimately or a required exact revision is absent, stop with the precise missing-source blocker.
