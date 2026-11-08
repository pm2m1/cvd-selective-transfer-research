# ELSA registration-plan path helper

Public engineering completed on 6 November 2026 in the requested `20261105` directory. **No actual private plan, Downloads directory, archive, authorization or output has been inspected by Codex.** This helper does not register sources, run counts or authorize anything.

Python 3.9+; standard library only. The separate tests use pytest and invented temporary files. Keep these helpers outside both fingerprinted installed tool directories. There is no need to reinstall or modify either original package.

## One copy-paste update command — independent Mac Terminal only

Run this yourself in an ordinary, independently operated Terminal outside Codex/CI. Codex must not execute it. The command supplies an explicit **local metadata-only pattern** because the complete archive basename was not supplied in the public record. It accepts exactly one `5050stata_*_V1.zip` match in Downloads; `_V1(1).zip` does not match. Zero or multiple matches stop without changing the plan; no archive contents are opened and no release edition is inferred.

```sh
python3 -B "$HOME/Desktop/dmv-mat-cvd-prototype/results/hrs_elsa_source_registration_plan_helper_20261105/prepare_plan.py" --plan "$HOME/ResearchPrivate/hrs_elsa_registration_20261105_run/registration.reviewed.json" --count-tools "$HOME/ResearchPrivate/hrs_elsa_counts_20261105_tools" --archive-pattern "$HOME/Downloads/5050stata_*_V1.zip"
```

The helper asks no questions. If the full verified archive path is locally known, `--archive "/ABSOLUTE/LOCALLY_VERIFIED/5050stata_EXACT_NAME_V1.zip"` can replace `--archive-pattern`; that example is a placeholder, not a claimed filename. Do not select a different file merely to make a check pass.

Expected success: `PLAN_ARCHIVE_PATH_UPDATED`. A repeat with the same path, no operation evidence and unchanged unresolved fields gives `PLAN_ALREADY_CONFIGURED` without rewriting the file or backup. Exit code 0 means path preparation only. All failures give a static `STOP ISSUE=...` and exit code 2; no paths, hashes, source contents or unrestricted exceptions are printed.

## Read-only local readiness command

```sh
python3 -B "$HOME/Desktop/dmv-mat-cvd-prototype/results/hrs_elsa_source_registration_plan_helper_20261105/check_readiness.py" --plan "$HOME/ResearchPrivate/hrs_elsa_registration_20261105_run/registration.reviewed.json" --count-tools "$HOME/ResearchPrivate/hrs_elsa_counts_20261105_tools"
```

After a successful path-only update, **if** the remaining state is exactly as described, the expected output is:

```text
REGISTRATION_PLAN: INCOMPLETE
ARCHIVE_PATH: CONFIGURED
ARCHIVE_FILE: PRESENT
SOURCE_REVIEW: UNRESOLVED
AUTHORIZATION: NOT_RECORDED
CONSUMED_ATTEMPT: NO
```

These are conditional expectations, not measurements made by Codex. Readiness exits 0 only when the plan's recorded structure, source-review fields, path/file metadata and count-tool presence are ready with no output/consumption blocker. It exits 2 while incomplete. `READY` does not mean authorized execution, authenticated source identity or independent scientific approval.

`SOURCE_REVIEW: ESTABLISHED` means the exact expected review value **and** scope list are already recorded; the checker never sets them or verifies provider/institutional approval. `AUTHORIZATION: RECORDED` means an authorization-named artifact is present, not that its content or signature is valid; receipt contents are never read. `CONSUMED_ATTEMPT: YES` means a known start/completion marker exists. `NO` is scoped to the checked locations, not an assertion about all private storage.

## Scope and safety behavior

- The existing plan must be a regular, non-symlink file in a private run directory (no group/other access). The archive and count-tool paths must be absolute and have no symlink components. The archive must be a regular file with the expected original V1 naming pattern. These are metadata checks, not dataset authentication or permission checks.
- The count-tool directory must match the plan's unchanged `count_tool_root`; the three public entry/manifest files must exist. No tool file contents are loaded here. Full fingerprint verification remains the original registrar's responsibility.
- The helper accepts the exact existing `elsa-source-registration-plan-v1`, independent-local mode, one-archive first-registration recipe. It refuses changed verification mode, non-null archive pin, claimed edition, measurement setting, review value or review scope. It does not normalize or approve them.
- Only `input_archives[0].archive_path` changes at the JSON data-value level. All other scientific/configuration fields, including extra bindings, remain equal. JSON indentation may change. The backup preserves the original file bytes exactly.
- The fixed exclusive backup is `registration.reviewed.json.before_archive_path.backup` beside the plan, mode `0600`. A newly updated plan is `0600`; the private parent remains unchanged. An existing backup blocks another placeholder update. It is not silently replaced.
- A helper-only exclusive `.prepare_plan.lock` prevents concurrent helper edits. Only the helper's own newly created lock/temp file is removed on normal completion/failure. A crashed helper's stale lock or backup blocks an uncertain update; neither is silently overwritten. These are configuration-edit artifacts, not source-registration attempt markers.
- The backup and candidate are flushed before an atomic same-directory replacement. The original is checked for concurrent changes and operation evidence is rechecked before replacement. Failed pre-commit writes leave the original intact and retain any created backup. A post-replacement durability error reports `UPDATE_COMPLETION_UNCERTAIN_INSPECT_LOCALLY`; it does not claim that no change occurred.

### Operation evidence checked without reading receipts

Default destinations are the documented `registration.authorization.json` and `registration_output` beside the plan. Known `operation_started.private.json` and `completion.private.json` markers are checked directly in the run directory and inside the documented output directory. Metadata-only inspection of run-directory entries detects other authorization-named files and conservatively blocks every unexpected sibling, including differently named output directories. No receipt or participant result is opened.

If the independently planned authorization/output destinations differ or are outside that run directory, explicitly supply `--authorization "/ABSOLUTE/LOCAL/AUTHORIZATION_DESTINATION" --output "/ABSOLUTE/LOCAL/OUTPUT_DESTINATION"` to **both** commands. The helper does not search other private storage or discover unrelated operation destinations. Unknown sibling artifacts make the readiness result undetermined and stop rather than falsely claiming no consumed attempt.

Run this only while the existing workflow is idle. The helper lock does not lock the unchanged registrar; another process can race with metadata checks. Do not concurrently authorize or execute registration while editing the plan. Existing authorization, output or markers always block modification, including an otherwise idempotent edit.

## What still prevents legitimate registration

The path update intentionally preserves:

```json
{
  "verification_mode": "first_local_registration",
  "expected_archive_sha256": null,
  "archive_edition": "UNRESOLVED",
  "register_measurements": false,
  "source_use_review": "UNRESOLVED_NOT_AUTHORIZED",
  "reviewed_scope": []
}
```

The unresolved review must be independently established for archive hashing, selected-member decompression and private materialization before registration. A fresh original operator authorization is separately required. Neither is supplied by this helper. Original historical source authentication remains unestablished; archive existence and a V1 filename cannot repair it. No registration, count or training command is invoked or prepared for automatic execution here.

Do not upload the updated plan, backup, archive path, private markers, receipts or other protected content to Codex, ChatGPT or GitHub. Environment/TTY checks reject agent and CI operation; they cannot independently prove isolation from indexers or establish data-use rights.

## Synthetic tests

From repository root:

```sh
.venv/bin/python -B -m pytest -q -p no:cacheprovider results/hrs_elsa_source_registration_plan_helper_20261105/tests
```

The CLI guard is mocked only in invented unit fixtures. It remains active in the released helpers. No private configuration or real archive was used during development.
