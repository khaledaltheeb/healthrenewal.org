#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip
from pathlib import Path
_PARTS=Path(__file__).with_name("special-needs-protocols-v326-source.parts")
_encoded="".join(path.read_text(encoding="ascii").strip() for path in sorted(_PARTS.glob("part-*.txt")))
_source=gzip.decompress(base64.b64decode(_encoded,validate=True)).decode("utf-8")
exec(compile(_source,__file__,"exec"),globals(),globals())
