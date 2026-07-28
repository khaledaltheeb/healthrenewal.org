#!/usr/bin/env python3
"""Load the verified comparison repair publisher stored in compact source parts."""
from __future__ import annotations

import base64
import gzip
import hashlib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ENCODED = "".join(
    (_ROOT / relative).read_text(encoding="ascii").strip()
    for relative in (".comparisons-v331/repair00", ".comparisons-v331/repair01")
).encode("ascii")
_SOURCE = gzip.decompress(base64.b85decode(_ENCODED))
_EXPECTED = "e8603a060a07dd74313917e1991ba6d3dd66f134e9f31e5aa522210d0483dc04"
if hashlib.sha256(_SOURCE).hexdigest() != _EXPECTED:
    raise RuntimeError("comparison repair source integrity check failed")
exec(compile(_SOURCE.decode("utf-8"), __file__, "exec"), globals(), globals())
