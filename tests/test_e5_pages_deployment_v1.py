#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = (ROOT / '.github/workflows/deploy-semantic-search-live.yml').read_text(encoding='utf-8')

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
    'manifest["documentCount"] > 0',
    'manifest["chunkCount"] > 0',
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

print({
    'passed': True,
    'contract': 'e5-source-validator-v2',
    'required_contracts': len(required),
    'source_mutation': False,
    'sitemap_contract': 'out-of-scope; validated by dedicated discovery gates',
})
