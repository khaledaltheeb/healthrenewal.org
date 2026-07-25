#!/usr/bin/env python3
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_BUNDLE = Path(__file__).resolve().parents[1] / ".home-v234bundle"
_encoded = "".join(path.read_text(encoding="ascii").strip() for path in sorted(_BUNDLE.glob("part*")))
if not _encoded:
    raise RuntimeError(f"Missing home-sector v234 source bundle in {_BUNDLE}")
_source = gzip.decompress(base64.b64decode(_encoded, validate=True)).decode("utf-8")

# v10 generates a breadcrumb main, a hero main and a content main on sector hubs.
# Replace the full generated content range rather than retaining the old hero H1.
_legacy_multi_main_pattern = 'updated, count = re.subn(r"<main\\b[^>]*>.*?</main\\s*>", main, text, count=1, flags=re.I | re.S)'
_generated_v10_pattern = 'updated, count = re.subn(r"<main\\b[^>]*>.*</main\\s*>", main, text, count=1, flags=re.I | re.S)'
if _source.count(_legacy_multi_main_pattern) != 1:
    raise RuntimeError("Unexpected home-sector v234 replace_main contract")
_source = _source.replace(_legacy_multi_main_pattern, _generated_v10_pattern, 1)

exec(compile(_source, str(_BUNDLE / "upgrade_home_sector_v234.py"), "exec"), globals(), globals())
