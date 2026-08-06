# Full content recovery — batch 004

## Scope

This batch restored the next missing production index after the communication guides recovery on `agent/full-content-recovery-v2`.

## Restored path

- Path: `learning-paths/all-pages/index.html`
- Current recovery branch before restoration: missing.
- Current `main` lineage used by PR #1080: missing at the PR base.
- Historical full source: `agent/full-content-recovery-v1`.
- Historical origin: restored previously from `agent/content-expansion-100-v2` in the closed, unmerged PR #1064.

## Versions compared

1. `agent/full-content-recovery-v2` before this batch: no file at the path.
2. `main` at the base of PR #1080: no file at the path.
3. `agent/full-content-recovery-v1`: complete static collection page.

The historical page declares 43 learning-path cards and includes Arabic RTL markup, canonical URL, responsive card layout, internal section search, platform shell assets, and `CollectionPage` schema with `numberOfItems: 43`.

## Decision and merge result

The historical version was adopted because it is the only complete version identified for this path. No shorter current page exists that requires semantic merging, so no current content was displaced.

The complete source was transferred without deletion, abbreviation, or regeneration. Source and restored file both resolve to Git blob SHA:

`5cfec531abd97555c89ecb60cde56b2f68e82a3f`

This SHA equality is the lossless-transfer verification for the page.

## Reserved-file check

Issue #158 was checked immediately before the write. No reservation for `learning-paths/all-pages/index.html` was found, and no other production path was modified in this batch.

## Validation status

Static structural verification completed:

- `lang="ar"` and `dir="rtl"` are present.
- canonical URL points to `/learning-paths/all-pages/`.
- `CollectionPage` schema declares 43 items.
- 43 static discovery cards are retained.
- responsive grid CSS and internal search are retained.
- source and target blob SHAs match exactly.

Repository-wide HTML, internal-link, mobile, print, Schema, accessibility, and workflow checks remain gating conditions on the final PR head.

## Merge gate

PR #1080 remains Draft. No merge is permitted until the final head passes HTML, internal links, RTL, mobile, print, Schema, accessibility, and all required repository checks.
