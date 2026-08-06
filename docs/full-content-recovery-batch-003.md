# Full content recovery — batch 003

## Restored path

`sectors/all-pages/index.html`

## Recovery decision

- Recovery branch: `agent/full-content-recovery-v1`
- Pull request: #1064
- Coordination issue: #158
- Current recovery head before this batch: `c4ee0412f63baa97cbb23dc148edf85db7f29896`
- Historical/source branch: `agent/content-expansion-100-v2`
- Source branch head inspected: `58467478feb7d0c5dd75b14da438933f7bcf5fcc`
- Selected source blob: `3583d0cc221dac8669af86db29ae8aa1879f256c`

## Versions compared

1. Current recovery branch: path absent (`404` through the repository contents API).
2. Default-branch path history: no commits returned for this path.
3. `agent/content-expansion-100-v2`: one complete Git blob containing the full static index.
4. Repository-wide comparison: the path is classified as added in the source branch relative to the recovery head; no competing version for this exact path was identified during this batch.

## Why this version was selected

This is the only identified complete version for the exact path and is not a placeholder or baseline shell. It contains 69 fixed HTML cards linking the sector hub, assessment, intervention, library, and applied guide pages. It also contains Arabic metadata, canonical URL, RTL markup, responsive grid CSS, keyboard-visible focus styling, client-side filtering, and `CollectionPage` Schema with `numberOfItems: 69`.

Because there was no second content-bearing version for the exact path, there was nothing safe to merge from a shorter copy. The source blob is restored byte-for-byte; no page content was deleted, shortened, regenerated, or manually reconstructed.

## Content and structural checks performed before commit

- HTML document shell and UTF-8 metadata present.
- `lang="ar"` and `dir="rtl"` present.
- Responsive viewport metadata present.
- Canonical URL points to `https://healthrenewal.org/sectors/all-pages/`.
- Meta description and index/follow robots directives present.
- Schema type: `CollectionPage`; declared item count: 69.
- Responsive CSS grid uses `auto-fit` and `minmax`.
- Search control has an explicit label; focus-visible styles are present.
- All restored links are site-root-relative, so they remain independent of the page nesting depth.
- Source blob contains no placeholder markers or empty content regions.

## Pending repository gates

The PR remains draft and must not be merged until the final PR head passes the repository's HTML, internal-link, RTL, mobile/responsive, print, Schema, accessibility, and other required checks. This batch does not claim deployment or live-SHA parity.
