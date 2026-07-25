#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKED_SCRIPT = ROOT / "scripts/publish_practical_tips_v237.py.gz.b64"
PACKED_REGISTRY = ROOT / "content/v237/practical-tips-v237.json.gz.b64"
REGISTRY = ROOT / "content/v237/practical-tips-v237.json"


def _decode(path: Path) -> bytes:
    return gzip.decompress(base64.b64decode(path.read_bytes()))


if not REGISTRY.exists():
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_bytes(_decode(PACKED_REGISTRY))

_SOURCE = _decode(PACKED_SCRIPT).decode("utf-8")
exec(compile(_SOURCE, str(PACKED_SCRIPT), "exec"), globals(), globals())
