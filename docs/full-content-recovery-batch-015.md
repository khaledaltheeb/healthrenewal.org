# Full content recovery — batch 015

## Scope
This batch fixes the exhaustive-history audit without changing or shortening editorial content.

## Evidence from the previous audit artifact
Run `31204124012` successfully fetched branch and pull-request history, compiled the recovery engine, and passed `tests/test_recovery_no_shortening_guard_v1.py`. The generated artifact reported:

- 935 pull-request heads discovered.
- 1,101 HTML paths with history.
- 8,547 distinct historical Git blob versions.
- 56 versions for the most-versioned path.
- Five paths beyond the former 24-version cap:
  - `index.html`: 56
  - `api/index.html`: 29
  - `family-guide/index.html`: 29
  - `provider-assessment-demo/index.html`: 26
  - `404.html`: 25

The report failed for one reason only: PR #1094's own head SHA (`e80afa1eaf15217619db9c4fbd1eaf8b08aff105`) was listed as unavailable.

## Root cause
On `pull_request` events, `actions/checkout` defaults to the synthetic pull-request merge ref unless a ref is specified. The workflow step was named `Checkout exact pull request head with full history`, but it did not explicitly select the PR head SHA. Therefore the audit could have the merge commit locally while the PR head object itself was absent when the REST inventory later attempted to materialize every PR head.

## Fix
The checkout now explicitly uses:

```yaml
ref: ${{ github.event.pull_request.head.sha || github.sha }}
fetch-depth: 0
```

This makes the current PR head a guaranteed local commit object on pull-request runs, while preserving `workflow_dispatch` support through `github.sha`.

## Content safety
- No editorial page was deleted, replaced, or shortened in this batch.
- The Main-first additive recovery strategy remains unchanged.
- Missing routes still use the longest candidate first (`words -> score -> sections -> bytes`).
- The no-shortening regression suite remains mandatory.
- The exhaustive audit still fails if any advertised historical PR head is genuinely unavailable; the current PR is not exempted or silently ignored.

## Merge gate
PR #1094 remains Draft. Do not merge until the new head passes exhaustive-history/no-shortening plus the required HTML, internal-link, RTL, responsive/mobile, print, Schema/WCAG and production gates.
