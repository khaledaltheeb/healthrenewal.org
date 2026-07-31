# Arabic semantic search

This directory provides a zero-API-cost semantic search interface for the static website.

## Runtime architecture

1. The browser first checks for a precomputed Float16 E5 index in `ai-search/data/`.
2. When that index is not ready, the worker reads `sitemap-index.xml` and discovers the published page corpus.
3. `Xenova/multilingual-e5-small` embeds page-path seed text locally in the browser.
4. The resulting Float32 vectors are cached in IndexedDB on the visitor's device.
5. The worker fetches only the strongest candidate pages, extracts their visible text, and performs a second semantic reranking pass.
6. Arabic lexical and title matching remain available as a fallback.

This means semantic search still works without OpenAI, Claude, a private API key, a vector database, or a server-side inference bill. A precomputed index remains an optional performance acceleration.

## Offline/precomputed build

```bash
python -m pip install -r scripts/semantic-search-requirements.txt
python scripts/build_semantic_search_index.py --root . --output ai-search/data
```

The remote builder can also crawl the deployed sitemap corpus and write normalized Float16 shards. The browser automatically prefers those shards when they are available.

## Privacy and safety

- Queries and locally generated embeddings remain on the visitor's device.
- IndexedDB stores vectors derived from public page paths, not personal answers.
- The feature retrieves passages and original links; it does not diagnose, prescribe, or generate unsupported medical answers.
- Relevance percentages are ranking scores, not medical certainty.
