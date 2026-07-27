#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import publish_autism_clinical_pathways_v324_core as core
from publish_autism_clinical_pathways_v324_core import *  # noqa: F401,F403

SHELL_MARKER = "<!-- pt-platform-shell:v1 -->"
SHELL_HEAD = """<!-- pt-platform-shell:v1 -->
<meta name="copyright" content="© 2026 Khaled Altheeb — منصة الصحة النفسية وذوي الاحتياجات الخاصة">
<meta name="rights" content="All rights reserved">
<link rel="license" href="/pterminology-site/copyright/">
<link rel="stylesheet" href="/pterminology-site/assets/platform/platform-core.css?v=1.1.0">
<script defer src="/pterminology-site/assets/platform/platform-core.js?v=1.1.0"></script>
"""


def normalize_page(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    if SHELL_MARKER not in source:
        if "</head>" not in source:
            raise SystemExit(f"Missing head in generated v324 page: {path}")
        source = source.replace("</head>", SHELL_HEAD + "</head>", 1)
    source, count = re.subn(
        r"<body(?:\s[^>]*)?>",
        '<body class="pt-platform" data-pt-normalized="1.1.0" data-pt-enhancer="true">',
        source,
        count=1,
        flags=re.I,
    )
    if count != 1 or source.count(SHELL_MARKER) != 1:
        raise SystemExit(f"Platform shell normalization failed: {path}")
    path.write_text(source, encoding="utf-8")


def publish(site: Path) -> dict:
    report = core.publish(site)
    for relative in report["generated_pages"]:
        normalize_page(site / relative)
    for item in report["pages"]:
        path = site / item["path"]
        source = path.read_text(encoding="utf-8")
        if SHELL_MARKER not in source or 'data-pt-normalized="1.1.0"' not in source:
            raise SystemExit(f"Missing institutional shell after normalization: {item['slug']}")
        item["words"] = core.words(source)
    report["minimum_guide_words"] = min(item["words"] for item in report["pages"])
    report["total_guide_words"] = sum(item["words"] for item in report["pages"])
    report["platform_shell_normalized"] = True
    api = site / "api" / "autism-clinical-pathways-v324.json"
    api.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Missing site directory: {args.site}")
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
