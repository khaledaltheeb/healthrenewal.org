# Full content recovery — batch 014

## Purpose
Synchronize the single recovery branch with the latest `main` without allowing stale branch state to override newer repository work, while preserving every recovery-specific artifact and the no-shortening policy.

## Baseline and branch state
- Latest verified `main`: `7f6ba0ca03ae2454cf66daa461b3bdb9f4ec3255`.
- Previous recovery head: `d8eb36e5675c5c62a938d4ae892ccac1ffaffe67`.
- Before synchronization: recovery was ahead 25 / behind 23.
- Synchronization merge commit: `5956fcaba7d0736931c4b1089fb4106ab6eb5689`.
- After synchronization: recovery is ahead 26 / behind 0, and the merge base is the latest verified `main`.

## Non-destructive synchronization method
The resulting tree was built from the latest `main` tree, then only recovery-owned files were overlaid. This prevents unrelated stale branch files from replacing newer `main` files. No production page was deleted or shortened as part of the synchronization.

Recovery-owned files retained:
- `.github/workflows/audit-exhaustive-content-recovery-history-v1.yml`
- `docs/full-content-recovery-batch-008.md` through `docs/full-content-recovery-batch-013.md`
- `family-guide/conditions/global-developmental-delay/data.js`
- `scripts/recover_content_full_history_v3.py`
- `tests/test_recovery_no_shortening_guard_v1.py`

## Recovery engine decision
The current `main` engine already uses **Main-first additive recovery**: an existing current page is authoritative and history can only contribute unique editorial fragments; missing public paths may be restored from baseline/history.

The only intentional semantic difference retained by this branch is the ranking of candidates when a public path is completely missing:

- `main`: `score -> words -> sections -> bytes`
- recovery branch: `words -> score -> sections -> bytes`

The recovery ordering is retained because the recovery contract requires the longest/largest version to be the base for a missing page, while structural score remains the next tie-breaker. Existing `main` pages are still protected from historical replacement.

## GDD preservation
The enriched `family-guide/conditions/global-developmental-delay/data.js` remains preserved. Its historical additions include play/relationship guidance, following the child's interest, bodily boundaries/privacy/refusal/requesting help, caregiver wellbeing, preventive and dental care, practical safety planning, and additional WHO/UNICEF/Canadian Paediatric Society references. This material must not be lost during branch synchronization.

## Historical inventory gate
The recovery workflow retains exhaustive branch fetching plus every pull-request head advertised by the Git remote, unique-blob inventory, and explicit fetch-count checks. It does not silently treat unavailable history as successful evidence.

## Merge gate
PR #1094 remains Draft. Do not merge until the final head passes the exhaustive history inventory, no-shortening regression, HTML/internal links, RTL, mobile/responsive, print, Schema, WCAG/accessibility, production-artifact no-loss checks, and all required production workflows.

Coordination remains through Issue #158. Files reserved to other agents are outside this recovery branch scope.
