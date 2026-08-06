# Full content recovery — batch 006

## Scope

Repository: `khaledaltheeb/healthrenewal.org`

Working branch: `agent/full-content-recovery-v2`

Coordination issue: #158

Pull request: #1080

## Branch and baseline state

- Current recovery head before this record: `c45d62b07a7046d37a4b74afd5f5c7c5e776cc49`.
- Current `main`: `ab295194f410a8e7bf798c4b13aedf6cf25d3fb1`.
- PR #1080 remains open, draft, unmerged, and reports zero deletions.
- The branch is therefore one `main` commit behind and must be refreshed before any merge decision.

## Completed comparison

Compared `agent/full-content-recovery-v2` against `agent/full-content-recovery-v1`.

Historical recovery-v1 production pages were:

1. `special-needs/guides/communication/index.html`
2. `learning-paths/all-pages/index.html`
3. `special-needs/all-pages/index.html`
4. `sectors/all-pages/index.html`

Result:

- The first three paths are already present in PR #1080.
- `sectors/all-pages/index.html` is already present on the current recovery branch with 69 cards, RTL, canonical metadata, responsive discovery grid, search control, and `CollectionPage` schema. It is therefore not missing and must not be re-added or replaced from the older branch.
- No additional missing production page remains in `agent/full-content-recovery-v1` after these comparisons.

## Wider historical branch review

Compared `agent/full-content-recovery-v2` against `agent/content-expansion-100-v2`.

That historical branch contains large generated families under:

- `care-guides/evidence-guided/**`
- `comparisons/disability-support/**`
- `daily-tools/disability-support/**`
- `learning-paths/evidence-guided/**`

These pages were generated in uniform 62-line templates and are coupled to historical data and generation scripts. They must not be copied into the recovery PR as isolated HTML files because:

1. raw line count is not evidence of scientific richness;
2. the templates may contain repeated implementation blocks;
3. isolated HTML restoration would not establish the current source-of-truth, publisher, sitemap, search, API, or deployment artifact contract;
4. several target areas are reserved or actively modified by other agents, especially `outside-the-box/**`, `provider-assessment-demo/**`, and magazine paths.

## Recovery decision

No production page was added in this batch.

This is intentional, not a stalled recovery:

- all uniquely identified recovery-v1 pages are now accounted for;
- the next candidate set requires content-by-content scientific comparison and source-of-truth integration, not direct blob copying;
- copying a generated historical page without that evidence would risk restoring template volume rather than unique useful content.

## Next admissible action

Before selecting another page:

1. update the recovery branch onto the current `main` without losing the three restored production pages;
2. verify their blob/content integrity after the update;
3. inspect each candidate family against current source data and generator ownership;
4. choose only a page with demonstrably unique, non-repeated scientific content;
5. integrate it through the current publisher, sitemap, search, API, and artifact pipeline;
6. keep PR #1080 draft and unmerged until HTML, links, RTL, mobile, print, Schema, SEO, and repository-wide gates succeed.

## Safety record

- No content deleted.
- No content shortened.
- No reserved production file modified.
- No merge performed.
