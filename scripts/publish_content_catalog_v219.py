from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import enhance_sitewide_seo_v216 as seo
from content_discovery_v219 import publish as publish_catalog
from publish_section_directory_v221 import publish as publish_sections
from sync_public_api_discovery_v219 import sync

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()


def run_required_publisher(script_name: str) -> None:
    script = ROOT / "scripts" / script_name
    if not script.is_file():
        raise SystemExit(f"Missing required publisher: {script}")
    subprocess.run([sys.executable, str(script), str(SITE)], check=True)


def publish_tips_v234_when_production_ready() -> bool:
    """Replace v15 tips only inside the complete homepage production build.

    The real pipeline writes both the v15 core report and homepage-v20 report
    before calling this catalog publisher. Focused fixtures do not carry both
    markers and remain isolated from the 49-page institutional tips build.
    """
    ready = (
        (SITE / "robots.txt").is_file()
        and (SITE / "assets").is_dir()
        and (SITE / "api/core-sections-v15.json").is_file()
        and (SITE / "api/homepage-v20.json").is_file()
        and (SITE / "tips").is_dir()
    )
    if not ready:
        return False
    run_required_publisher("publish_tips_hub_v234.py")
    run_required_publisher("verify_tips_v234.py")
    return True


def main() -> int:
    tips_v234_published = publish_tips_v234_when_production_ready()

    section_report = publish_sections(SITE, ROOT)
    seo.SITE = SITE
    seo_results = {}
    for relative in ("index.html", "sections/index.html"):
        path = SITE / relative
        changed, result = seo.enrich_page(path)
        if result.get("status") in {"missing_head", "missing_title_and_h1"}:
            raise SystemExit(f"SEO enrichment failed for {relative}: {result}")
        seo_results[relative] = {"changed": changed, "status": result.get("status")}

    result = publish_catalog(SITE, ROOT)
    result["section_directory"] = section_report
    result["section_directory_seo"] = seo_results
    result["public_api_report"] = sync(ROOT, SITE, "published")
    result["tips_v234_published"] = tips_v234_published
    result["tips_v234_report"] = "api/tips-audit-v234.json" if tips_v234_published else None
    result["tips_v234_verification"] = (
        "api/tips-verification-v234.json" if tips_v234_published else None
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
