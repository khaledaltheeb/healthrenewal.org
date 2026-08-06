# Full content recovery — batch 004

## Scope

This batch audited the next missing production index after the communication guides recovery on `agent/full-content-recovery-v2`.

## Candidate

- Path: `learning-paths/all-pages/index.html`
- Current recovery branch: missing.
- Current `main` lineage used by PR #1080: missing at the PR base.
- Historical full source: `agent/full-content-recovery-v1`.
- Historical origin: restored previously from `agent/content-expansion-100-v2` in the closed, unmerged PR #1064.

## Versions compared

1. `agent/full-content-recovery-v2`: no file at the path.
2. `main` at the base of PR #1080: no file at the path.
3. `agent/full-content-recovery-v1`: complete static collection page.

The historical page declares 43 learning-path cards and includes Arabic RTL markup, canonical URL, responsive card layout, internal section search, platform shell assets, and `CollectionPage` schema with `numberOfItems: 43`.

## Decision

The historical version remains the approved recovery source because it is the only complete version identified for this path. No shorter current page exists that requires semantic merging.

The file was not recreated from a truncated API response. The connector display clipped the long source, and reconstructing from the visible excerpt would risk silently dropping cards or markup. That would violate the no-deletion/no-abbreviation recovery rule. The next write must use a byte-complete Git blob transfer or another lossless source operation, followed by blob-SHA equality verification.

## Reserved-file check

No reserved production paths were modified. This batch only adds this audit record. The recovery candidate remains limited to `learning-paths/all-pages/index.html` and must be rechecked against Issue #158 immediately before transfer.

## Merge gate

PR #1080 remains Draft. No merge is permitted until the final head passes HTML, internal links, RTL, mobile, print, Schema, accessibility, and repository-wide required checks.
