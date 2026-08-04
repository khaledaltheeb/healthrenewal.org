# Verified conservative publication — 2026-08-04

This release consolidates verified discovery, metadata, structured-data, RSS, sitemap and crawl-surface repairs on top of the current `main` branch.

## Preservation guarantees

- No force push.
- No deletion of editorial, medical, educational or interactive content.
- Historical pull-request branches remain preserved.
- Pre-release and generated release heads are retained under `archive/` branches.
- The previous `main` state is retained under a dedicated archive branch.

## Validation rule

Merge only at the recorded head SHA after repository quality gates execute successfully. Post-deployment checks must verify the custom domain and public machine-readable surfaces.
