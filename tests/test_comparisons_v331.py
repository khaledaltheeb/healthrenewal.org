from __future__ import annotations

import base64
import gzip
import hashlib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ENCODED = (_ROOT / ".comparisons-v331/test-source").read_text(encoding="ascii").strip().encode("ascii")
_SOURCE = gzip.decompress(base64.b85decode(_ENCODED))
_EXPECTED = "99d86da03e95ad82e19c4ef9311d2a0bf6be725f26bf51a3d8f928f55b2c2d84"
if hashlib.sha256(_SOURCE).hexdigest() != _EXPECTED:
    raise RuntimeError("comparison test source integrity check failed")
exec(compile(_SOURCE.decode("utf-8"), __file__, "exec"), globals(), globals())
