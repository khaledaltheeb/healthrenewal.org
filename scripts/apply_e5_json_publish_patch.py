#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Required contract not found in {path}: {old[:120]!r}")
    if text.count(old) != 1:
        raise SystemExit(f"Contract is not unique in {path}: {text.count(old)} matches")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


builder = ROOT / "scripts/build_semantic_search_index.py"
replace_once(builder, "import argparse\nimport hashlib", "import argparse\nimport base64\nimport hashlib")
replace_once(
    builder,
    '    for pattern in ("shard-*.meta.json", "shard-*.f16.bin"):\n',
    '    for pattern in ("shard-*.meta.json", "shard-*.f16.bin", "shard-*.f16.json"):\n',
)
replace_once(
    builder,
    '''        metadata_name = f"shard-{shard_number:03d}.meta.json"\n        embeddings_name = f"shard-{shard_number:03d}.f16.bin"\n        metadata_path = output / metadata_name\n        embeddings_path = output / embeddings_name\n\n        metadata_payload = [asdict(chunk) for chunk in chunks[start:end]]\n        metadata_bytes = write_json(metadata_path, metadata_payload)\n        shard_vectors = embeddings[start:end]\n        shard_vectors.tofile(embeddings_path)\n        vector_bytes = embeddings_path.read_bytes()\n\n        shards.append(\n            {\n                "metadata": metadata_name,\n                "embeddings": embeddings_name,\n                "count": end - start,\n                "metadataBytes": len(metadata_bytes),\n                "embeddingBytes": len(vector_bytes),\n                "metadataSha256": sha256_bytes(metadata_bytes),\n                "embeddingSha256": sha256_bytes(vector_bytes),\n            }\n        )\n''',
    '''        metadata_name = f"shard-{shard_number:03d}.meta.json"\n        embeddings_name = f"shard-{shard_number:03d}.f16.bin"\n        embeddings_json_name = f"shard-{shard_number:03d}.f16.json"\n        metadata_path = output / metadata_name\n        embeddings_path = output / embeddings_name\n        embeddings_json_path = output / embeddings_json_name\n\n        metadata_payload = [asdict(chunk) for chunk in chunks[start:end]]\n        metadata_bytes = write_json(metadata_path, metadata_payload)\n        shard_vectors = embeddings[start:end]\n        shard_vectors.tofile(embeddings_path)\n        vector_bytes = embeddings_path.read_bytes()\n        vector_sha256 = sha256_bytes(vector_bytes)\n        embeddings_json_bytes = write_json(\n            embeddings_json_path,\n            {\n                "version": 1,\n                "encoding": "base64",\n                "dtype": "float16",\n                "endianness": "little",\n                "dimensions": DIMENSIONS,\n                "count": end - start,\n                "byteLength": len(vector_bytes),\n                "sha256": vector_sha256,\n                "data": base64.b64encode(vector_bytes).decode("ascii"),\n            },\n        )\n\n        shards.append(\n            {\n                "metadata": metadata_name,\n                "embeddings": embeddings_name,\n                "embeddingsJson": embeddings_json_name,\n                "encoding": "base64",\n                "count": end - start,\n                "metadataBytes": len(metadata_bytes),\n                "embeddingBytes": len(vector_bytes),\n                "embeddingsJsonBytes": len(embeddings_json_bytes),\n                "metadataSha256": sha256_bytes(metadata_bytes),\n                "embeddingSha256": vector_sha256,\n                "embeddingsJsonSha256": sha256_bytes(embeddings_json_bytes),\n            }\n        )\n''',
)

worker = ROOT / "ai-search/assets/search-worker.js"
replace_once(
    worker,
    '''async function fetchBinary(url) {\n  const response = await fetch(url, { cache: 'force-cache' });\n  if (!response.ok) throw new Error(`HTTP ${response.status}`);\n  return response.arrayBuffer();\n}\n''',
    '''async function fetchBinary(url) {\n  const response = await fetch(url, { cache: 'force-cache' });\n  if (!response.ok) throw new Error(`HTTP ${response.status}`);\n  return response.arrayBuffer();\n}\n\nfunction decodeBase64ToArrayBuffer(value) {\n  const binary = atob(String(value || ''));\n  const bytes = new Uint8Array(binary.length);\n  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);\n  return bytes.buffer;\n}\n\nasync function fetchShardVectorBuffer(shard, manifestUrl) {\n  if (shard.embeddingsJson) {\n    const payload = await fetchJson(new URL(shard.embeddingsJson, manifestUrl));\n    if (payload?.version !== 1 || payload?.encoding !== 'base64') {\n      throw new Error('ترميز متجهات الفهرس غير مدعوم.');\n    }\n    if (payload.dtype !== 'float16' || payload.endianness !== 'little') {\n      throw new Error('نوع متجهات الفهرس غير متوافق.');\n    }\n    if (payload.dimensions !== DIMENSIONS || payload.count !== shard.count) {\n      throw new Error('أبعاد حزمة المتجهات غير متطابقة.');\n    }\n    const buffer = decodeBase64ToArrayBuffer(payload.data);\n    if (buffer.byteLength !== payload.byteLength || buffer.byteLength !== shard.embeddingBytes) {\n      throw new Error('حجم حزمة المتجهات غير صحيح.');\n    }\n    return buffer;\n  }\n  return fetchBinary(new URL(shard.embeddings, manifestUrl));\n}\n''',
)
replace_once(
    worker,
    '''    const [metadata, buffer] = await Promise.all([\n      fetchJson(new URL(shard.metadata, manifestUrl)),\n      fetchBinary(new URL(shard.embeddings, manifestUrl)),\n    ]);\n''',
    '''    const [metadata, buffer] = await Promise.all([\n      fetchJson(new URL(shard.metadata, manifestUrl)),\n      fetchShardVectorBuffer(shard, manifestUrl),\n    ]);\n''',
)

browser_test = ROOT / "tests/test_ai_search_browser_index_v2.py"
replace_once(
    browser_test,
    '''        self.assertIn("loadGeneratedIndex", worker)\n        self.assertIn("local-rerank", worker)\n''',
    '''        self.assertIn("loadGeneratedIndex", worker)\n        self.assertIn("fetchShardVectorBuffer", worker)\n        self.assertIn("decodeBase64ToArrayBuffer", worker)\n        self.assertIn("embeddingsJson", worker)\n        self.assertIn("local-rerank", worker)\n''',
)

production_test = ROOT / "tests/test_multilingual_e5_production_v3.py"
replace_once(
    production_test,
    '''    def test_generated_results_are_unique_per_page(self) -> None:\n''',
    '''    def test_pages_compatible_base64_vector_artifact_is_generated(self) -> None:\n        builder = (ROOT / "scripts/build_semantic_search_index.py").read_text(encoding="utf-8")\n        worker = (ROOT / "ai-search/assets/search-worker.js").read_text(encoding="utf-8")\n        self.assertIn("shard-{shard_number:03d}.f16.json", builder)\n        self.assertIn("base64.b64encode", builder)\n        self.assertIn('"embeddingsJson"', builder)\n        self.assertIn('"encoding": "base64"', builder)\n        self.assertIn("fetchShardVectorBuffer", worker)\n        self.assertIn("decodeBase64ToArrayBuffer", worker)\n\n    def test_generated_results_are_unique_per_page(self) -> None:\n''',
)

print("Applied E5 Pages-compatible JSON vector patch.")
