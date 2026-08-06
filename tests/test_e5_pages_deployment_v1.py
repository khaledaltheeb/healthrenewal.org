#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / '.github/workflows/deploy-semantic-search-live.yml').read_text(encoding='utf-8')
robots = (ROOT / 'robots.txt').read_text(encoding='utf-8')

required = (
    'name: Validate multilingual E5 package',
    'workflows: ["Semantic search index"]',
    "github.event.workflow_run.conclusion == 'success'",
    "github.event.workflow_run.head_branch == 'main'",
    "github.event.workflow_run.head_sha",
    "github.sha",
    "persist-credentials: false",
    "permissions:\n  contents: read",
    "group: e5-source-validation-",
    "cancel-in-progress: true",
    "ai-search/data",
    "manifest.json",
    "embeddingsJsonSha256",
    "embeddingSha256",
    "base64.b64decode",
    "documentCount'] > 0",
    "chunkCount'] > 0",
)
for fragment in required:
    assert fragment in workflow, fragment

for forbidden in (
    'actions/download-artifact@',
    'actions/upload-pages-artifact@',
    'actions/deploy-pages@',
    'git push',
    '[skip ci]',
    'ref: main',
):
    assert forbidden not in workflow, forbidden

assert robots.count('Sitemap: https://healthrenewal.org/sitemap-index.xml') == 1
assert 'Sitemap: https://healthrenewal.org/sitemap.xml' not in robots
print({
    'passed': True,
    'contract': 'e5-source-validator-v2',
    'required_contracts': len(required),
    'sitemap_policy': 'index-only',
    'source_mutation': False,
})
