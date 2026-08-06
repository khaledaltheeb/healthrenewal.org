# Full content recovery — batch 005

## Restored path

`special-needs/all-pages/index.html`

## Versions compared

1. `main`: path absent.
2. `agent/full-content-recovery-v2` before this batch: path absent.
3. Historical generated version: Git blob `7a44a61f494f66c20e03df4b48050f102d7b4878` — 111,505 bytes, 2,288 lines, approximately 12,064 words.
4. Normalized complete version from `agent/full-content-recovery-v1`: Git blob `03c7b30dc5dfab884ca552e2a4f9b94aabae3b49` — 84,091 bytes, preserving 149 cards with the current platform shell.

## Decision

The normalized complete version was selected as the restoration base. Raw byte or word count was not treated as sufficient evidence of scientific richness: the larger historical file contains generated structural inflation, while the selected version preserves the full 149-item catalogue and adds the platform header/footer, legal and licensing links, responsive navigation, canonical metadata, RTL support, search, and `CollectionPage` structured data.

No unique scientific claim from the older version was asserted as merged without page-level evidence. The selected Git blob was transferred directly to avoid truncation, regeneration, or accidental omission.

## Integrity

- Source blob: `03c7b30dc5dfab884ca552e2a4f9b94aabae3b49`
- Restored target blob: `03c7b30dc5dfab884ca552e2a4f9b94aabae3b49`
- Restoration commit: `ad716c39842edcdf2cff889ea6e5a42a088aadce`
- Files changed by the restoration commit: one added production page; no deletions.

## Coordination and exclusions

The path was reserved and the comparison decision recorded in Issue #158. Reserved areas including `outside-the-box/**`, `provider-assessment-demo/**`, and magazine files were not modified.

PR #1080 remains a draft and must not be merged until HTML, internal-link, RTL, mobile, print, Schema, accessibility, and repository-required checks complete successfully.
