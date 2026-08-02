from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import enhance_sitewide_seo_v216 as seo
from audit_publication_surface_v322 import audit as audit_publication_surface
from content_discovery_v219 import publish as publish_catalog
from publish_section_directory_v322 import publish as publish_sections
from sync_public_api_discovery_v219 import sync

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
STATIC_PUBLIC_ROUTES = (
    "specialists-partners",
    "platform",
    "copyright",
    "sectors",
)


def preserve_generated_sector_pages(directory: str, names: list[str]) -> set[str]:
    """Keep the v353 youth hub while importing the additional static youth guides."""
    if Path(directory).resolve() == (ROOT / "sectors" / "youth").resolve():
        return {"index.html"} & set(names)
    return set()


def restore_static_public_routes() -> dict[str, int]:
    restored: dict[str, int] = {}
    for route in STATIC_PUBLIC_ROUTES:
        source = ROOT / route
        target = SITE / route
        if not source.is_dir():
            raise SystemExit(f"Missing repository public route: {route}/")
        ignore = preserve_generated_sector_pages if route == "sectors" else None
        shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore)
        pages = list(target.rglob("*.html"))
        if not pages:
            raise SystemExit(f"Restored public route has no HTML pages: {route}/")
        restored[route + "/"] = len(pages)
    return restored


def seo_targets() -> list[Path]:
    targets = [SITE / "index.html", SITE / "sections/index.html"]
    for route in STATIC_PUBLIC_ROUTES:
        targets.extend(sorted((SITE / route).rglob("*.html")))
    output: list[Path] = []
    seen: set[Path] = set()
    for path in targets:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        output.append(path)
    return output


def main() -> int:
    restored_routes = restore_static_public_routes()
    section_report = publish_sections(SITE, ROOT)

    seo.SITE = SITE
    seo_results: dict[str, dict[str, object]] = {}
    for path in seo_targets():
        if not path.is_file():
            raise SystemExit(f"SEO target is missing: {path.relative_to(SITE).as_posix()}")
        changed, result = seo.enrich_page(path)
        relative = path.relative_to(SITE).as_posix()
        if result.get("status") in {"missing_head", "missing_title_and_h1"}:
            raise SystemExit(f"SEO enrichment failed for {relative}: {result}")
        seo_results[relative] = {
            "changed": changed,
            "status": result.get("status"),
        }

    result = publish_catalog(SITE, ROOT)
    result["restored_static_public_routes"] = restored_routes
    result["section_directory"] = section_report
    result["section_directory_seo"] = seo_results
    result["public_api_report"] = sync(ROOT, SITE, "published")
    result["publication_surface"] = audit_publication_surface(SITE, fail=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
