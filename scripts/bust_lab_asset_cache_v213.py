from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
VERSION = "213"
RUNTIME_SUFFIX = "assets/js/lab-v12.js"
SCRIPT_RE = re.compile(
    r'(<script\b[^>]*\bsrc=["\'])([^"\']*assets/js/lab-v12\.js)(?:\?[^"\']*)?(["\'][^>]*>\s*</script>)',
    re.IGNORECASE,
)


def lab_pages() -> list[Path]:
    pages: list[Path] = []
    for root_name in ("assessment-lab", "cognitive-lab"):
        root = SITE / root_name
        if not root.is_dir():
            raise SystemExit(f"Missing generated lab root: {root}")
        pages.extend(sorted(root.rglob("*.html")))
    return sorted(set(pages))


def version_page(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    matches = list(SCRIPT_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one lab runtime in {path}, found {len(matches)}")

    def replace(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}?v={VERSION}{match.group(3)}"

    updated = SCRIPT_RE.sub(replace, text, count=1)
    if updated.count(f"{RUNTIME_SUFFIX}?v={VERSION}") != 1:
        raise SystemExit(f"Versioned runtime marker missing or duplicated in {path}")
    if re.search(r'assets/js/lab-v12\.js(?:["\'])', updated):
        raise SystemExit(f"Unversioned lab runtime remains in {path}")
    changed = updated != text
    if changed:
        path.write_text(updated, encoding="utf-8")
    return changed, updated


def publish_cognitive_sectors() -> dict:
    publisher = Path(__file__).with_name("publish_cognitive_sectors_v246.py")
    if not publisher.is_file():
        raise SystemExit(f"Missing cognitive sectors publisher: {publisher}")
    subprocess.run([sys.executable, str(publisher), "--self-test"], check=True)
    subprocess.run([sys.executable, str(publisher), str(SITE)], check=True)
    report_path = SITE / "api/cognitive-sectors-v246.json"
    if not report_path.is_file():
        raise SystemExit(f"Missing cognitive sectors publication report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.get("status") == "published", report
    assert report["legacy_sector"]["pages"] >= 8, report
    assert report["modern_sector"]["pages"] >= 53, report
    assert report["total_detail_pages"] >= 61, report
    assert report["sitemap_required_urls"] >= 63, report
    assert report["sitemap_mapped_required_urls"] >= 63, report
    assert report["sitemap_unmapped_urls"] == [], report
    assert report.get("open_text_controls") == [], report
    contracts = report.get("contracts", {})
    assert contracts.get("all_detail_pages_published") is True, report
    assert contracts.get("all_answers_are_selection_based") is True, report
    assert contracts.get("complete_inventory") is True, report
    assert contracts.get("sitemap_registered") is True, report
    return report


def apply_tools_descendant_marshmallow() -> dict:
    tools_root = SITE / "tools"
    if not tools_root.is_dir():
        return {
            "version": 250,
            "status": "not-applicable",
            "pages": 0,
            "child_pages": 0,
            "quiz_fixed": False,
            "unstyled_pages": [],
        }

    publisher = Path(__file__).with_name("apply_tools_descendant_marshmallow_v250.py")
    if not publisher.is_file():
        raise SystemExit(f"Missing tools descendant Marshmallow publisher: {publisher}")
    subprocess.run([sys.executable, str(publisher), str(SITE)], check=True)
    report_path = SITE / "api/tools-descendant-marshmallow-v250.json"
    if not report_path.is_file():
        raise SystemExit(f"Missing tools descendant Marshmallow report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report.get("status") == "published", report
    assert report.get("pages", 0) >= 2, report
    assert report.get("child_pages", 0) >= 1, report
    assert report.get("quiz_route") == "tools/quiz/index.html", report
    assert report.get("quiz_fixed") is True, report
    assert report.get("unstyled_pages") == [], report
    assert report.get("dark_mode_blackening_blocked") is True, report
    return report


def main() -> None:
    pages = lab_pages()
    if len(pages) != 95:
        raise SystemExit(f"Expected 95 lab HTML pages (40 assessments + 53 cognitive + 2 indexes), found {len(pages)}")

    changed = 0
    cognitive = 0
    assessments = 0
    for page in pages:
        was_changed, _ = version_page(page)
        changed += int(was_changed)
        relative = page.relative_to(SITE).as_posix()
        cognitive += int(relative.startswith("cognitive-lab/"))
        assessments += int(relative.startswith("assessment-lab/"))

    runtime = SITE / RUNTIME_SUFFIX
    if not runtime.is_file():
        raise SystemExit(f"Missing generated runtime: {runtime}")
    runtime_text = runtime.read_text(encoding="utf-8")
    required_stroop_markers = [
        "mode==='stroop_basic'||mode==='stroop_advanced'",
        "stimulusInk",
        "stimulusWord",
        "#b42318",
        "#175cd3",
        "#067647",
        "#b54708",
        "#6941c6",
        "#087e8b",
    ]
    missing = [marker for marker in required_stroop_markers if marker not in runtime_text]
    if missing:
        raise SystemExit(f"Generated Stroop runtime is incomplete: {missing}")

    cognitive_sectors = publish_cognitive_sectors()
    tools_descendants = apply_tools_descendant_marshmallow()

    report = {
        "version": 213,
        "status": "production-ready",
        "pages_scanned": len(pages),
        "assessment_pages": assessments,
        "cognitive_pages": cognitive,
        "pages_changed": changed,
        "versioned_runtime_url": f"/{RUNTIME_SUFFIX}?v={VERSION}",
        "unversioned_runtime_pages": 0,
        "duplicate_runtime_pages": 0,
        "stroop_palette_colors": 6,
        "stroop_inline_ink": True,
        "cache_busting_required": True,
        "cognitive_sectors_v246": {
            "status": cognitive_sectors["status"],
            "legacy_pages": cognitive_sectors["legacy_sector"]["pages"],
            "modern_pages": cognitive_sectors["modern_sector"]["pages"],
            "total_detail_pages": cognitive_sectors["total_detail_pages"],
            "sitemap_target_urls": cognitive_sectors["sitemap_urls"],
            "sitemap_required_urls": cognitive_sectors["sitemap_required_urls"],
            "sitemap_mapped_required_urls": cognitive_sectors["sitemap_mapped_required_urls"],
            "sitemap_duplicates_avoided": cognitive_sectors["sitemap_duplicates_avoided"],
            "sitemap_unmapped_urls": cognitive_sectors["sitemap_unmapped_urls"],
            "contracts": cognitive_sectors["contracts"],
        },
        "tools_descendant_marshmallow_v250": {
            "status": tools_descendants["status"],
            "pages": tools_descendants["pages"],
            "child_pages": tools_descendants.get("child_pages", 0),
            "quiz_fixed": tools_descendants["quiz_fixed"],
            "unstyled_pages": tools_descendants["unstyled_pages"],
        },
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-asset-cache-v213.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
