#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
worker=root/'ai-search/assets/search-worker.js'
text=worker.read_text(encoding='utf-8')
old="""async function fetchBinary(url) {\n  const response = await fetch(url, { cache: 'force-cache' });\n  if (!response.ok) throw new Error(`HTTP ${response.status}`);\n  return response.arrayBuffer();\n}\n\nfunction decodeBase64ToArrayBuffer(value) {\n"""
new="""async function fetchBinary(url) {\n  const response = await fetch(url, { cache: 'force-cache' });\n  if (!response.ok) throw new Error(`HTTP ${response.status}`);\n  return response.arrayBuffer();\n}\n\nfunction shardArtifactUrl(name, sha256, manifestUrl) {\n  const url = new URL(name, manifestUrl);\n  if (sha256) url.searchParams.set('v', String(sha256).slice(0, 20));\n  return url;\n}\n\nfunction decodeBase64ToArrayBuffer(value) {\n"""
if text.count(old) != 1:
    raise SystemExit(f'fetchBinary contract count={text.count(old)}')
text=text.replace(old,new,1)
old="const payload = await fetchJson(new URL(shard.embeddingsJson, manifestUrl));"
new="const payload = await fetchJson(shardArtifactUrl(shard.embeddingsJson, shard.embeddingsJsonSha256, manifestUrl));"
if text.count(old) != 1:
    raise SystemExit(f'JSON vector URL contract count={text.count(old)}')
text=text.replace(old,new,1)
old="return fetchBinary(new URL(shard.embeddings, manifestUrl));"
new="return fetchBinary(shardArtifactUrl(shard.embeddings, shard.embeddingSha256, manifestUrl));"
if text.count(old) != 1:
    raise SystemExit(f'binary vector URL contract count={text.count(old)}')
text=text.replace(old,new,1)
old="fetchJson(new URL(shard.metadata, manifestUrl)),"
new="fetchJson(shardArtifactUrl(shard.metadata, shard.metadataSha256, manifestUrl)),"
if text.count(old) != 1:
    raise SystemExit(f'metadata URL contract count={text.count(old)}')
text=text.replace(old,new,1)
worker.write_text(text,encoding='utf-8')

test=root/'tests/test_ai_search_browser_index_v2.py'
text=test.read_text(encoding='utf-8')
old='''        self.assertIn("embeddingsJson", worker)\n        self.assertIn("local-rerank", worker)\n'''
new='''        self.assertIn("embeddingsJson", worker)\n        self.assertIn("shardArtifactUrl", worker)\n        self.assertIn("embeddingsJsonSha256", worker)\n        self.assertIn("metadataSha256", worker)\n        self.assertIn("local-rerank", worker)\n'''
if text.count(old) != 1:
    raise SystemExit(f'test contract count={text.count(old)}')
test.write_text(text.replace(old,new,1),encoding='utf-8')
print('Applied E5 shard cache busting.')
