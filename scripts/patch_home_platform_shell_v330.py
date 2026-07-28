#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    ROOT / "sectors" / "home" / "index.html": "../../copyright/",
    ROOT / "sectors" / "home" / "library" / "index.html": "../../../copyright/",
    ROOT / "sectors" / "home" / "assessment" / "index.html": "../../../copyright/",
    ROOT / "sectors" / "home" / "interventions" / "index.html": "../../../copyright/",
}
MARKER = "<!-- pt-platform-shell:v1 -->"

for path, license_href in PAGES.items():
    source = path.read_text(encoding="utf-8")
    if MARKER not in source:
        shell = (
            f'{MARKER}'
            '<meta name="copyright" content="© 2026 Khaled Altheeb — منصة الصحة النفسية وذوي الاحتياجات الخاصة">'
            '<meta name="rights" content="All rights reserved">'
            f'<link rel="license" href="{license_href}">'
        )
        platform_css = '<link rel="stylesheet" href="'
        position = source.find(platform_css)
        if position < 0:
            raise SystemExit(f"platform stylesheet not found in {path}")
        source = source[:position] + shell + source[position:]
    body_token = 'data-pt-normalized="1.1.0"'
    if 'data-pt-enhancer="true"' not in source:
        if body_token not in source:
            raise SystemExit(f"normalized body marker not found in {path}")
        source = source.replace(body_token, body_token + ' data-pt-enhancer="true"', 1)
    path.write_text(source, encoding="utf-8")
    print(path.relative_to(ROOT))
