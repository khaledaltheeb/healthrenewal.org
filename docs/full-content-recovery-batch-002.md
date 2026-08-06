# Full content recovery — batch 002

## Restored path

`learning-paths/all-pages/index.html`

## Compared versions

| Location | Result |
|---|---|
| `agent/full-content-recovery-v1` | Path absent (GitHub Contents API returned 404 before restoration). |
| `agent/content-expansion-100-v2` | Complete HTML page; source blob `4c7eab3b18f615856e09c871ef0d9adf56cee8d5`. |

## Selection decision

The historical branch version is the only complete discovered version for this path and is therefore the non-destructive recovery base. It declares 43 items and includes Arabic RTL markup, a canonical URL, responsive viewport metadata, `CollectionPage` JSON-LD with `numberOfItems: 43`, search/filter UI, and static cards linking to the published learning paths.

## Merge record

No shorter current version existed, so there was no current content to overwrite or discard. The exact historical Git blob was attached to the recovery branch without regenerating, trimming, or rewriting its HTML.

## Required validation before merge

- HTML parsing and document structure
- all internal links and the declared 43-card count
- RTL behavior
- mobile viewport and responsive card grid
- print rendering
- JSON-LD syntax and `CollectionPage` semantics

PR #1064 must remain draft and unmerged until repository gates pass on the final branch head. Coordination and reservation are recorded in Issue #158.
