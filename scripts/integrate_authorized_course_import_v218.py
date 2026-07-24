#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts" / "apply_homepage_v20.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    anchor = '    publish_api_sitemap()\n    run_publisher("enforce_health_publication_gate_v192.py")\n'
    replacement = (
        '    publish_api_sitemap()\n'
        '    run_publisher("import_authorized_courses_v218.py")\n'
        '    run_publisher("verify_authorized_course_import_v218.py")\n'
        '    run_publisher("enhance_sitewide_seo_v216.py")\n'
        '    run_publisher("verify_sitewide_seo_v216.py")\n'
        '    run_publisher("enforce_health_publication_gate_v192.py")\n'
    )

    # Current production already runs sitewide SEO immediately before the health gate.
    current = (
        '    publish_api_sitemap()\n'
        '    run_publisher("enhance_sitewide_seo_v216.py")\n'
        '    run_publisher("verify_sitewide_seo_v216.py")\n'
        '    run_publisher("enforce_health_publication_gate_v192.py")\n'
    )
    if replacement not in text:
        if current in text:
            text = text.replace(current, replacement, 1)
        else:
            text = replace_once(text, anchor, replacement, "course importer integration")

    required = (
        'run_publisher("import_authorized_courses_v218.py")',
        'run_publisher("verify_authorized_course_import_v218.py")',
        'run_publisher("enhance_sitewide_seo_v216.py")',
        'run_publisher("verify_sitewide_seo_v216.py")',
        'run_publisher("enforce_health_publication_gate_v192.py")',
    )
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise SystemExit(f"Missing production integration markers: {missing}")
    if text.count('run_publisher("import_authorized_courses_v218.py")') != 1:
        raise SystemExit("Authorized course importer must run exactly once")
    if text.index('run_publisher("import_authorized_courses_v218.py")') > text.index('run_publisher("enhance_sitewide_seo_v216.py")'):
        raise SystemExit("Course catalog must be created before sitewide SEO enrichment")
    if text.index('run_publisher("verify_authorized_course_import_v218.py")') > text.index('run_publisher("enforce_health_publication_gate_v192.py")'):
        raise SystemExit("Course catalog verification must precede the health publication gate")

    TARGET.write_text(text, encoding="utf-8")
    print({"target": str(TARGET.relative_to(ROOT)), "importer": 218, "network_default": "disabled", "status": "integrated"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
