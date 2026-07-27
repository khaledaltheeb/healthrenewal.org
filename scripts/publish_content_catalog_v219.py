from __future__ import annotations

import json
import sys
from pathlib import Path

import enhance_sitewide_seo_v216 as seo
from audit_publication_surface_v322 import audit as audit_publication_surface
from content_discovery_v219 import publish as publish_catalog
from publish_section_directory_v322 import publish as publish_sections
from sync_public_api_discovery_v219 import sync

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()


def main() -> int:
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
    result["publication_surface"] = audit_publication_surface(SITE)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
