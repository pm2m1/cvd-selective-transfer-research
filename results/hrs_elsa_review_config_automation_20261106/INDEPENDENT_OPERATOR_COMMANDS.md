# Independent Mac Terminal commands

Run only in the independently controlled environment. Do not paste private files, paths, hashes, findings or error context into AI. Before Command A, independently establish permission for **metadata preparation itself**: reading/hashing the ten historical JSON records, original configuration/authorization/completion/registration metadata, and writing a fresh backup/binding record for the unused review configuration. Controlled discovery additionally needs permission to list the named run directories shallowly and read candidate authorization/reviewed-configuration JSON metadata. The user's request and file ownership alone do not establish provider/institutional scope.

## Transfer only this new helper

The original review tool is already installed. **Do not reinstall it or recreate the existing review template.** Verify the new public package with `python3 -B verify_release.py`, then independently transfer `prepare_offline_review_config.py` to a new, separate helper directory:

`$HOME/ResearchPrivate/hrs_elsa_review_config_automation_20261106/`

This is an operator-side destination reference, not a directory Codex accessed. Do not overwrite an existing helper, place files in the frozen review-tools tree, or place them beside the private review configuration. No dependency installation is needed. Use the existing independent Python environment; synthetic verification used Python3.12.14.

## A — Bind the historical JSON metadata

```sh
python3 -B "$HOME/ResearchPrivate/hrs_elsa_review_config_automation_20261106/prepare_offline_review_config.py" --bind --private-root "$HOME/ResearchPrivate" --config "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_run/review.reviewed.json" --review-tools "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_tools" --discover-known-layout
```

This one command uses the three named historical run directories supplied in the task. It does not guess a successful output folder: it derives output paths from the original authorization's `output_binding` and chooses the matching original configuration by its recorded SHA256 and schema. Authorization filenames may use public documented dot/underscore/dash naming, case-insensitively; configuration names must identify configuration/reviewed JSON. It never picks among multiple authorization candidates. Source registration is the descriptor recorded by the diagnostic, not a newly located archive.

Expected mechanical success: `PASS ISSUE=METADATA_BOUND_SCOPE_UNCHANGED`. This has **not** been observed on real inputs by Codex. Existing sources, receipts, authorizations and outputs are never modified. The existing new review configuration alone is replaced after backup/staging/fsync checks.

If known-layout discovery cannot resolve the records, stop. A qualified operator may explicitly identify all ten paths in an owner-only JSON map **outside the review-run directory** and use `--evidence-map "/ABSOLUTE/PRIVATE/REVIEWED_METADATA_PATHS.json"` instead of `--discover-known-layout`. Its format is:

```json
{
  "schema": "elsa-review-evidence-paths-v1",
  "evidence": {
    "diagnostic_config": {"path": "/ABSOLUTE/ORIGINAL/CONFIG.json"}
  }
}
```

The example shows one role only; a real map must contain exactly all ten roles listed below. Each entry has `path` and optionally a previously reviewed lowercase64-character `sha256`; if supplied, it must match. Paths alone cause hashes to be calculated locally. An explicit map is an operator selection, never automatic resolution of competing authorizations. Do not edit original hashes to obtain a match.

Required roles: diagnostic_config, diagnostic_authorization, diagnostic_completion, diagnostic_integrity, diagnostic_report, diagnostic_input_validation, failed_count_config, failed_count_authorization, failed_count_completion, source_registration.

## B — Verify the bound configuration without displaying descriptors

```sh
python3 -B "$HOME/ResearchPrivate/hrs_elsa_review_config_automation_20261106/prepare_offline_review_config.py" --check --private-root "$HOME/ResearchPrivate" --config "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_run/review.reviewed.json" --review-tools "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_tools"
```

Expected success: `PASS ISSUE=METADATA_CONFIGURATION_VERIFIED_NO_AUTHORIZATION`. The check is read-only. It verifies all ten references, backup integrity, bound configuration core, metadata identities and unchanged original public-tool bytes. It does not inspect disease outcomes or confer scientific approval.

## C — Independently establish and record actual review scope

Before changing declarations, establish provider/institutional permission for the **distinct offline scientific-review operation**, authentic provenance of the existing protected records, permission to inspect their private classifications, competence/role of the reviewer, and an environment inaccessible to AI/indexers/external services. Scope must cover historical authorization/configuration/completion and registration metadata as well as the status report and new private worksheets. Original registration, counting and diagnostic authorizations cannot authorize the new review. This helper cannot establish any of those facts.

Only when true, edit the existing new configuration locally to record the original documented values:

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

The helper does not set these fields. Do not record them merely to pass software checks. Preserve all descriptors/pins/prohibitions. Keep the configuration0600 and do not add editor backups or unrelated files inside the run directory. Command B may be repeated read-only before any authorization; it permits this exact independently recorded declaration change and rejects changes to the bound configuration core.

## D — Original preflight

```sh
python3 -B "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_tools/offline_scientific_review.py" --preflight --config "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_run/review.reviewed.json"
printf 'PREFLIGHT_EXIT=%s\n' "$?"
```

The original prints `NO_EXECUTION` in both cases: **exit0** means its preparatory configuration checks passed; **exit2** means STOP. With unchanged unresolved declarations, exit2 is expected. Neither status is scientific acceptance or a private empirical verdict. It does not generate a worksheet or consume a review attempt.

## E — Original offline review once, after all requirements are satisfied

```sh
python3 -B "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_tools/offline_scientific_review.py" --review --config "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_run/review.reviewed.json" --authorization "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_run/review.authorization.json" --output "$HOME/ResearchPrivate/hrs_elsa_private_review_20261106_run/review_output"
```

The original interactive authorization prompts must be completed personally and truthfully. No helper supplies responses, creates authorization, starts review or retries. Authorization/output must not exist. Failures and interrupted/consumed attempts remain permanent. Keep the resulting worksheet private; an independently competent scientific determination and any required adoption remain necessary before a justified fresh count release. Actual event/feature/partition feasibility and separate export/training/evaluation permissions are later gates.

## Failures and retained artifacts

Binding requires the run directory to contain **only the original unused configuration**. Successful preparation leaves that configuration, `.prebinding.backup.json` and `.binding.record.json` suffix files. A staging suffix file is renamed away on success. Any existing authorization, output, marker, backup, staging, partial record or unrelated entry blocks binding. No artifact is deleted automatically.

A pre-write missing/ambiguous-path failure does not consume a research operation; an independent operator may correct the explicit selection after checking no preparation artifacts were created. If any backup/staging/record exists after a failure, stop and preserve it. Do not delete it to force a retry, restore an old template automatically, reset an operation, or upload it to Codex. The read-only check also refuses a partial preparation or a run that already contains an authorization/output.
