# Independent Mac Terminal runbook

Codex must not execute these commands against private artifacts. Do not paste paths, hashes, matrices, findings, configurations or receipts into AI. Keep private outputs outside AI-accessible/indexed workspaces. Permissions alone do not establish isolation or lawful scope.

## 1. Establish this distinct review scope

Independently verify provider/institutional permission for reading the existing aggregate diagnostic **and** historical configuration, authorization, completion and registration **metadata** listed below, and writing a new private scientific-review worksheet. Permission for the diagnostic itself is not automatically permission for this new review. No raw source-byte hashing, Stata reads, disease counts or training is included. No old authorization is reused. If any required metadata is outside permitted scope, stop; do not fabricate an equivalence record.

## 2. Verify and install public files once

Extract the public ZIP into a new public staging directory and run from its root:

```sh
python3 -B verify_public.py
python3 -B verify_public.py --install-to "/ABSOLUTE/NEW/ISOLATED_REVIEW_TOOLS"
```

The installer copies only manifest-enumerated files, refuses existing destinations, preserves old installations and verifies copied bytes. It creates restrictive modes. No private files are transferred. A failed partial install is retained; use a documented fresh destination rather than overwriting it. Python3.10+ on macOS is supported by the source interfaces; actual testing uses the existing project Python environment. No pip installation is needed for the review program.

## 3. Prepare a fresh private review configuration locally

Create a new private run directory in the independently approved private workspace, outside all historical outputs and tool trees, then create an unresolved template:

```sh
mkdir -m 700 "/ABSOLUTE/PRIVATE/NEW_REVIEW_RUN"
python3 -B verify_public.py --new-config "/ABSOLUTE/PRIVATE/NEW_REVIEW_RUN/review.reviewed.json"
```

Edit only that new JSON with an ordinary local editor. Do not edit Python. Supply `private_root`: a permission-restricted, operator-owned common ancestor of all metadata and the new run. It must not itself be an old operation's output or lie inside the tool installation. The public tools may be a sibling directory within this private workspace; private inputs/outputs must remain outside their tree. All input JSON files must be regular nonsymlink files with mode0600, in owner-only directories within that root. Symbolic-link components are refused. Do not move/rewrite original artifacts to satisfy this helper; resolve scope/location problems independently or remain blocked.

Supply the explicit absolute path and independently recorded SHA256 for each of these **existing JSON records**. Never select a dataset, ZIP, NPZ, model checkpoint or log:

| Configuration key | Existing record |
|---|---|
| diagnostic_config | Original reviewed status-diagnostic configuration |
| diagnostic_authorization | Original status authorization, read only for lineage |
| diagnostic_completion | Original successful status output `completion.private.json` |
| diagnostic_integrity | Same output `diagnostic_integrity.private.json` |
| diagnostic_report | Same output `status_diagnostic.private.json` |
| diagnostic_input_validation | Same output `input_validation.private.json` |
| failed_count_config | Original failed count's reviewed configuration |
| failed_count_authorization | Original failed count authorization, read only for lineage |
| failed_count_completion | Original consumed failed count `completion.private.json` |
| source_registration | Existing `source_registration.private.json` used by the diagnostic |

Obtain these descriptors using the independently permitted local metadata process; do not ask Codex to find or hash them. The helper checks reviewed descriptor hashes, completion/integrity links, historical purpose/code/config/output bindings, exact ten history products and registered member descriptors. Source paths inside those records are compared as metadata only; no clinical file is opened, statted or rehashed. Equal descriptor hashes are evidence of recorded content identity, not proof of current bytes, authentic distributor edition or legal entitlement. Reviewed hashes/receipts are not digital signatures; the operator must establish their authentic provenance.

Preserve the template's public contract pin and all three prohibition flags. Only after actual independent scope and isolation are established, record:

```json
"source_use_review": "INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OFFLINE_REVIEW",
"isolation_review": "INDEPENDENTLY_REVIEWED_OUTSIDE_AI_AND_INDEXERS",
"reviewed_scope": [
  "READ_EXISTING_STATUS_DIAGNOSTIC_AND_INTEGRITY_METADATA",
  "READ_HISTORICAL_CONFIGURATION_AUTHORIZATION_AND_COMPLETION_METADATA_ONLY",
  "READ_EXISTING_SOURCE_REGISTRATION_METADATA_ONLY",
  "WRITE_NEW_PRIVATE_REVIEW_WORKSHEET_NO_ELIGIBILITY_CHANGE"
]
```

These entries record externally established facts, not software-issued permission. They do not adopt a scientific rule or create authorization. Keep the configuration mode0600. Empty paths/hashes, unresolved scope or unsafe locations stop the operation.

Optional nonprocessing config preflight:

```sh
python3 -B offline_scientific_review.py --preflight --config "/ABSOLUTE/PRIVATE/NEW_REVIEW_RUN/review.reviewed.json"
```

This checks the new configuration, public contract and metadata-file types/permissions/existence, **not existing report contents or hashes**. `NO_EXECUTION` with exit0 means only that those preparatory checks passed; exit2 means preparation stopped. No scientific status is printed. Original runtime rules require subsequent integrity/content verification inside the consumed authorized operation; preflight cannot promise that it will succeed.

## 4. One local review command

From the installed review tools directory:

```sh
python3 -B offline_scientific_review.py --review --config "/ABSOLUTE/PRIVATE/NEW_REVIEW_RUN/review.reviewed.json" --authorization "/ABSOLUTE/PRIVATE/NEW_REVIEW_RUN/review.authorization.json" --output "/ABSOLUTE/PRIVATE/NEW_REVIEW_RUN/review_output"
```

This is implemented and synthetic-tested. It first invokes the unchanged runtime's interactive authorization. The operator must personally enter the original name/scope confirmation prompts; no response is supplied automatically. It then invokes execution under the new purpose `elsa_existing_status_scientific_review_v1_20261106`. Authorization and output must both be unused. A cancellation stops before execution. Separate original-style `--authorize-local` and `--execute-local` modes are also supported with identical arguments if deliberately staged; do not use `--review` to reuse an existing authorization.

The original runtime consumes an attempt before protected report processing, creates private start/completion receipts and redirects execution output into a private log. Any failure/interruption remains permanently consumed; never reset, overwrite, silently resume or automatically retry. A documented genuinely new review operation needs fresh scope/authorization/destinations. Original count/diagnostic artifacts remain read-only.

Console output is static operational acknowledgment only: original authorization/runtime statuses, `PRIVATE_REVIEW_ARTIFACT_CREATED`, `INDEPENDENT_SCIENTIFIC_DECISION_REQUIRED`, or `NO_EXECUTION`. Do not interpret generic failure as an empirical category. Arbitrary exceptions, paths, counts and findings are not printed. No network/telemetry/upload exists.

## 5. Complete the scientific worksheet locally

Examine `scientific_evidence_worksheet.private.json` and the separate `reviewer_decision.UNRESOLVED.private.json`. They distinguish mechanical verification from **UNRESOLVED** scientific acceptance. Inspect every wave and every observed family, zero versus missing, direct outcome versus fallback, missing/unmatched Core coverage and raw marginal limits. A completed diagnostic with invalid/duplicate linkage or domain errors is incompatible and refused; it is not promoted into evidence.

Create a **new** reviewer-authored completed-decision file; preserve the generated originals and integrity record. Use local JSON editing, not Python changes. For each family record authoritative evidence, exact interpretation, remaining uncertainty, A/B/C category and effects on lifetime history, baseline, intervals, censoring and selection. Record actual reviewer expertise/role and any genuinely required independent adoption. Do not invent a reviewer, signature or institution. Review all checklist acceptance fields; pass/fail metadata checks do not answer them. The generation schema describes unresolved software output; a completed human determination is a separate record, not a file this helper automatically approves.

No command in this package accepts a completed worksheet as permission or starts counting. If any scientific determination is absent, maintain NO_EXECUTION. See `CONDITIONAL_COUNT_RELEASE.md`. Only an independently justified new count release, fresh count authorization, empirical feasibility acceptance, permitted canonical export and separate modeling authorizations can lead to real training. Keep all detailed worksheets and decisions private pending applicable disclosure review.
