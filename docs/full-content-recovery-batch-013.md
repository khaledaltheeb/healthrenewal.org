# Full content recovery — batch 013

Date: 2026-08-07
Branch: `agent/full-content-recovery-v4`
PR: #1094
Coordination: #158

## Objective

Keep the recovery branch on the current main-first additive recovery model, preserve all existing editorial content, prefer the longest available source when a public route is completely missing, and audit every reachable branch/PR history version without the former 24-version ceiling.

## Findings

1. Current `main` had moved to `4c870016b9f6910bbc601767e207b0c32ae48d08` while PR #1094 still diverged from merge-base `11f7c86c57635892e77d53ed7e60146ab82711f2`.
2. `main` now contains a newer recovery engine that treats current main as authoritative for existing routes and only adds unique historical fragments. The PR still carried an older replacement-oriented engine.
3. The PR workflow/test suite still referenced removed legacy interfaces (`full_history_candidates`, `_parse_distinct_history`, `restore_without_shortening`), so the exhaustive audit could fail before validating the current engine.
4. The new main-first engine selected a missing route candidate by structural score before word count. For a route that no longer exists on main, this could still choose a shorter historical page over a longer one.

## Changes

- Replaced the stale PR recovery implementation with the current main-first additive engine.
- Changed missing-route candidate priority to: words, score, sections, bytes. Existing main routes remain protected and are never replaced by historical pages.
- Reworked `tests/test_recovery_no_shortening_guard_v1.py` for the current architecture. It now verifies:
  - more than 24 historical commits remain visible;
  - reserved private historical surfaces remain blocked;
  - a longer missing-route candidate wins even when a shorter candidate has a higher structural score;
  - historical insertion is additive and preserves the primary page;
  - duplicate fragments are recognized;
  - reserved prefixes remain excluded.
- Reworked `.github/workflows/audit-exhaustive-content-recovery-history-v1.yml` to use `all_history()` and `CatFile` from the current engine, count unique Git blobs per safe HTML path, fetch branch and recoverable PR heads, and report unavailable PR heads explicitly.

## Commits

- `35f9cedaa312a4b4cbf241001ccffd37c4fd256c` — align engine with current main-first additive policy.
- `2080a29604b110b9038d6aa58410525d6d54e1f2` — prefer longest source for completely missing routes.
- `e297cd9fd4f5e8c832ac914d79eda8038505c7cd` — align recovery regression tests with the current engine.
- `5c277bd059dbd2a62dc3cabf31b15fa41c29d204` — align exhaustive history audit workflow with v3.1.

## Current gate state

At the time of this batch, PR #1094 is still Draft and unmerged. It is `ahead 23 / behind 16` relative to current main and GitHub reports it as not mergeable. No pull-request workflow runs were yet visible for head `5c277bd059dbd2a62dc3cabf31b15fa41c29d204`.

No merge is permitted until the branch is synchronized safely with current main and the final head passes exhaustive history inventory, no-loss checks, HTML/link checks, RTL/responsive/mobile/print checks, Schema/WCAG, production artifact validation, and the remaining production gates.
