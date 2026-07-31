# Arabic semantic search

This directory provides a zero-API-cost semantic search interface for the static website.

## Runtime architecture

1. The browser first checks for a precomputed Float16 E5 index in `ai-search/data/`.
2. When that index is not ready, the worker reads `sitemap-index.xml` and discovers up to 6,000 published page URLs.
3. Arabic lexical matching, page paths, section labels, and a bounded Arabic-to-English topic alias map select at most 96 candidates.
4. The worker fetches the visible text of at most 36 leading pages.
5. `Xenova/multilingual-e5-small` embeds only that bounded candidate set and performs a two-stage semantic reranking pass.
6. Plain Arabic lexical search remains available when the model cannot run.

The fallback does **not** embed the complete site on the visitor's device. It avoids an unbounded first-use wait while retaining semantic understanding over the strongest candidates. Search still works without OpenAI, Claude, a private API key, a vector database, or a server-side inference bill.

## Offline/precomputed build

```bash
python -m pip install -r scripts/semantic-search-requirements.txt
python scripts/build_semantic_search_index.py --root . --output ai-search/data
```

The remote builder can crawl the deployed sitemap corpus and write normalized Float16 shards. The browser automatically prefers those shards when available; bounded local reranking is the resilient fallback.

## Privacy and safety

- Queries and locally generated candidate embeddings remain on the visitor's device.
- Only public pages from the platform origin are fetched.
- Candidate vectors are held in a bounded in-memory cache and are not sent to a private API.
- The feature retrieves passages and original links; it does not diagnose, prescribe, or generate unsupported medical answers.
- Relevance percentages are ranking scores, not medical certainty.
