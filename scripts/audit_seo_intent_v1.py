#!/usr/bin/env python3
"""Load the staged, checksum-stable sitewide SEO audit implementation."""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_BUNDLE = Path(__file__).resolve().parents[1] / ".seo-bundle" / "audit_seo_intent_v1.py.gz.b64"
_SOURCE = gzip.decompress(base64.b64decode(_BUNDLE.read_bytes()))
exec(compile(_SOURCE, str(Path(__file__).resolve()), "exec"), globals())
