# Full content recovery audit — batch 012

## Scope

This batch continues the single-branch recovery effort on `agent/full-content-recovery-v4` / PR #1094. It does not delete or shorten editorial content and does not touch files reserved by PRs #1092, #1095, #1107, #1108, #1111, or #1112.

At the start of this batch, `main` had advanced to `0bffb77c383b570a9ead5cf83aaccbd1b8055a66` through the automated SEO sitemap / IndexNow refresh. PR #1094 remained Draft and unmerged.

## Defect discovered: the “full-history” scan was still sampled

`scripts/recover_content_full_history_v3.py` previously delegated to `recover_content_v1.history()` with a widened `limit=24`. The underlying implementation intentionally selects one early candidate plus high-change candidates until the limit is reached. That is useful for a representative scan, but it does **not** satisfy a strict recovery requirement to identify every available version of every page.

A path with 25+ distinct historical versions could therefore have its richest or scientifically strongest version omitted from comparison solely because it fell outside the representative 24-commit set.

## Correction implemented

The recovery entrypoint now reads `git log --all --raw` and keeps every distinct post-change HTML/HTM Git blob for every safe public path within the configured history horizon.

Important properties:

- no 24-version ceiling;
- every distinct reachable page blob is retained as a comparison candidate;
- identical content repeated across commits/branches is deduplicated by Git blob id rather than rescored repeatedly;
- the existing private/prototype surface guard remains in force;
- the existing no-shortening guard remains in force;
- missing routes and equal/longer restorations remain eligible;
- shorter historical candidates remain review sources, not destructive replacements.

The production workflow already invokes recovery with `--days 3650`; therefore the configured horizon covers the repository's full project lifetime rather than only the default recent window.

## Regression coverage

`tests/test_recovery_no_shortening_guard_v1.py` now additionally verifies that:

1. at least 30 distinct versions for one route are all retained, proving that the former 24-version ceiling is gone;
2. repeated identical blob content is deduplicated;
3. blocked historical implementation surfaces are excluded;
4. `full_history_candidates(..., limit=24)` still returns 31 distinct versions when 31 exist, proving that the compatibility argument no longer truncates recovery.

The prior no-shortening cases remain intact.

## PR-only history gap discovered

The production recovery workflow currently fetches every branch head, but not GitHub pull-request refs. A closed/unmerged PR whose source branch was deleted can therefore retain useful historical content at `refs/pull/<number>/head` while being absent from the fetched branch namespace.

To audit this gap without modifying files reserved by another agent, this batch adds a dedicated workflow:

`.github/workflows/audit-exhaustive-content-recovery-history-v1.yml`

It:

- fetches all branch refs;
- discovers and fetches all GitHub-advertised PR head refs;
- compiles the recovery engine;
- runs the no-shortening/exhaustive-history regression suite;
- inventories all distinct historical HTML versions across the fetched refs;
- emits an auditable JSON artifact with total paths, total distinct versions, maximum versions for one path, and paths that exceed the former 24-version ceiling.

### PR-ref fetch hardening

The first workflow attempt, Run `31159072693`, failed at the pull-ref fetch step because a direct wildcard fetch of `refs/pull/*/head` was not accepted reliably in this runtime.

A second attempt used the GitHub API to enumerate PR numbers and constructed explicit pull-ref refspecs, but Run `31159185704` still failed in the same fetch stage before any recovery tests ran. That proved that assuming every historical PR number maps to an independently fetchable head ref is also unsafe.

The workflow now uses Git itself as the source of truth:

1. `git ls-remote --refs origin 'refs/pull/*/head'` enumerates only PR head refs the remote actually advertises;
2. those exact refs are mapped to `refs/remotes/pull/<number>`;
3. they are fetched in bounded batches of 100;
4. the job asserts that the number fetched locally exactly equals the number advertised remotely and is non-zero.

This final fetch strategy is committed at `c9706057b38dddc0d329e36a6f88b156694c9e9a` and must pass before the recovery audit is accepted.

## CI state carried forward

The previous exact-head PR #1094 run had one known blocker: `Validate every assessment and cognitive tool v31` failed at `Finish exact production output` after the earlier build/cognitive stages succeeded.

PR #1112 owns that CI contract and remains separate. Its current head also reaches `Finish exact production output` before failing, so this batch does not claim that v31 is fixed and does not modify #1112-owned files.

## Merge policy

PR #1094 remains Draft and must not be merged until all of the following are true on the final exact head:

- exhaustive branch + PR-ref history audit passes;
- no-shortening regression passes;
- HTML and internal-link validation pass;
- RTL, responsive/mobile, print, Schema, WCAG/accessibility gates pass;
- the production recovery artifact is inspected and shows no content-bearing route regression;
- all remaining required production gates, including v31, pass;
- after merge only, GitHub Pages deployment and live `deployment.json` SHA must match the merged commit.
