#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / '.github/workflows/deploy-semantic-search-live.yml').read_text(encoding='utf-8')
robots = (ROOT / 'robots.txt').read_text(encoding='utf-8')

required = (
    "workflows: ['Semantic search index']",
    "github.event.workflow_run.conclusion == 'success'",
    "actions/download-artifact@v4",
    "actions/upload-pages-artifact@v4",
    "actions/deploy-pages@v4",
    "ai-search/data/manifest.json",
    "embeddingsJsonSha256",
    "embeddingSha256",
    "base64.b64decode",
    "reports/e5-live-production.json",
    "generatedAt",
    "healthrenewal.org/ai-search/data/manifest.json",
    "robotsSitemapIndexOnly",
)
for fragment in required:
    assert fragment in workflow, fragment

assert "github.event_name != 'pull_request'" in workflow
assert "group: semantic-search-pages-live" in workflow
assert "documentCount'] > 0" in workflow
assert "chunkCount'] > 0" in workflow
assert "[skip ci]" in workflow
assert "robots.count('Sitemap: https://healthrenewal.org/sitemap-index.xml') == 1" in workflow
assert "'Sitemap: https://healthrenewal.org/sitemap.xml' not in robots" in workflow
assert robots.count('Sitemap: https://healthrenewal.org/sitemap-index.xml') == 1
assert 'Sitemap: https://healthrenewal.org/sitemap.xml' not in robots
print({'passed': True, 'required_contracts': len(required), 'sitemap_policy': 'index-only'})
