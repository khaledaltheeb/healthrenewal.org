# Arabic semantic search

This directory provides a zero-API-cost semantic search interface for the static website.

## Architecture

- Browser query embeddings: `Xenova/multilingual-e5-small` through Transformers.js.
- Offline document embeddings: `intfloat/multilingual-e5-small` through Sentence Transformers.
- Retrieval: normalized cosine similarity blended with Arabic lexical and title matching.
- Storage: sharded metadata JSON and normalized float16 embedding binaries.
- Privacy: user queries remain in the browser; no OpenAI, Claude, or private API key is used.

## Build locally

```bash
python -m pip install -r scripts/semantic-search-requirements.txt
python scripts/build_semantic_search_index.py --root . --output ai-search/data
```

The first build downloads the model. GitHub Actions caches it and regenerates the index after HTML changes on `main`.

## Safety boundary

The feature retrieves passages and links. It does not diagnose, prescribe, or generate unsupported medical answers. A later RAG answer layer should cite retrieved passages and refuse when evidence is insufficient.
