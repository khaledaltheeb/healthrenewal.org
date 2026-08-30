#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip
from pathlib import Path
_PARTS=Path(__file__).with_name("special-needs-protocols-v326-source.parts")
_encoded="".join(path.read_text(encoding="ascii").strip() for path in sorted(_PARTS.glob("part-*.txt")))
_source=gzip.decompress(base64.b64decode(_encoded,validate=True)).decode("utf-8")
# The v326 source bundle was authored against the retired GitHub Pages origin.
# Normalize every generated canonical/discovery URL to the production domain
# before compiling the embedded publisher so sitemaps, canonicals and reports
# cannot leak the legacy host.
_source=_source.replace(
    "https://khaledaltheeb.github.io/pterminology-site",
    "https://healthrenewal.org",
)
exec(compile(_source,__file__,"exec"),globals(),globals())
