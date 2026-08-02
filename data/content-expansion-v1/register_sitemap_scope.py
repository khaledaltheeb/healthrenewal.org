#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "tests/test_content_expansion_v1.py"
LINE = '    "sitemap-family-sectors.xml",\n'
ANCHOR = '    "sitemap-family-main.xml",\n'

source = PATH.read_text(encoding="utf-8")
if LINE not in source:
    if ANCHOR not in source:
        raise SystemExit("sitemap scope anchor not found")
    source = source.replace(ANCHOR, ANCHOR + LINE, 1)
    PATH.write_text(source, encoding="utf-8")
print("sitemap-family-sectors.xml registered in scoped publication gate")
