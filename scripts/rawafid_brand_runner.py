#!/usr/bin/env python3
"""Run the Rawafid normalizer while preserving search-engine verification files."""
from __future__ import annotations

import re
from pathlib import Path

import rawafid_brand_consistency as consistency

_VERIFICATION_FILE_RE = re.compile(
    r"(?:google|bing|yandex|baidu)[A-Za-z0-9._-]*\.html$",
    re.IGNORECASE,
)
_ORIGINAL_ELIGIBLE = consistency.eligible


def _eligible(path: Path, root: Path, production: bool) -> bool:
    if path.suffix.lower() in {".html", ".htm"} and _VERIFICATION_FILE_RE.fullmatch(path.name):
        return False
    return _ORIGINAL_ELIGIBLE(path, root, production)


def normalize_root(*args, **kwargs):
    consistency.eligible = _eligible
    try:
        return consistency.normalize_root(*args, **kwargs)
    finally:
        consistency.eligible = _ORIGINAL_ELIGIBLE
