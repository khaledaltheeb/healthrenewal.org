# AI search route deployment guard

`/ai-search/` is a mandatory public route. Every Pages artifact must include the complete `ai-search` directory, including its browser runtime, manifest, coverage report, metadata shards, and vector packages.

The canonical deployment workflow is `.github/workflows/deploy-complete-pages-with-ai-search.yml`. It assembles the public site from the latest `main`, validates the E5 package before upload, verifies the live route after deployment, and periodically repairs a missing or stale route.

Partial Pages publishers must not deploy an artifact that overlays only one section. They must either call the complete publisher or copy the complete current public surface and assert `/ai-search/` before upload.
