#!/usr/bin/env python3
from pathlib import Path

root=Path(__file__).resolve().parents[1]
worker=root/'ai-search/assets/search-worker.js'
text=worker.read_text(encoding='utf-8')
old="""  return pipeline('feature-extraction', MODEL_ID, {\n    dtype: DTYPE,\n    device: 'wasm',\n    revision: MODEL_REVISION,\n    progress_callback: progressCallback,\n  });\n"""
new="""  return pipeline('feature-extraction', MODEL_ID, {\n    dtype: DTYPE,\n    revision: MODEL_REVISION,\n    progress_callback: progressCallback,\n  });\n"""
if text.count(old) != 1:
    raise SystemExit(f'Expected one portable WASM fallback, found {text.count(old)}')
worker.write_text(text.replace(old,new,1),encoding='utf-8')

publisher=root/'.github/workflows/publish-semantic-search-live.yml'
text=publisher.read_text(encoding='utf-8')
old='for attempt in $(seq 1 120); do'
new='for attempt in $(seq 1 240); do'
if text.count(old) != 1:
    raise SystemExit(f'Expected one deployment wait loop, found {text.count(old)}')
publisher.write_text(text.replace(old,new,1),encoding='utf-8')
print('Applied E5 runtime cleanup.')
