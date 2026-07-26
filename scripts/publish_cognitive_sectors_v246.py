from __future__ import annotations

# Verified compressed source bundle for the institutional cognitive sectors publisher.
import base64
import gzip
from pathlib import Path

_PARTS = tuple(Path(__file__).with_name("v246_cognitive_parts").glob("part*.b85"))
if not _PARTS:
    raise SystemExit("Missing cognitive publisher bundle parts")
payload = "".join(path.read_text(encoding="ascii") for path in sorted(_PARTS))
source = gzip.decompress(base64.b85decode(payload.encode("ascii"))).decode("utf-8")
exec(compile(source, __file__, "exec"), {"__name__": __name__, "__file__": __file__})
