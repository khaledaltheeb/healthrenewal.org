#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import publish_special_needs_guides_v209 as shared
import publish_special_needs_guides_v209_compat as compat

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content" / "v214" / "special-needs-guides-manifest-ar.json"
GUIDE_DIR = ROOT / "content" / "v214" / "special-needs-guides"
START = "<!-- special-needs-guides-v214:start -->"
END = "<!-- special-needs-guides-v214:end -->"
ALLOWED_HOSTS = {"www.who.int", "www.unicef.org", "www.un.org", "social.desa.un.org", "www.undrr.org"}
BANNED = shared.BANNED


def load_data() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    guides = []
    for slug in manifest.get("guide_slugs", []):
        path = GUIDE_DIR / f"{slug}.json"
        if not path.is_file():
            raise SystemExit(f"Missing v214 guide file: {path}")
        guide = json.loads(path.read_text(encoding="utf-8"))
        if guide.get("slug") != slug:
            raise SystemExit(f"Guide slug mismatch in {path}: {guide.get('slug')} != {slug}")
        guide["reviewed_at"] = manifest["reviewed_at"]
        guides.append(guide)
    return {**manifest, "guides": guides}


def validate(data: dict[str, Any]) -> None:
    required = {"version", "batch", "status", "reviewed_at", "title", "description", "guides", "sources"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing v214 batch fields: {sorted(missing)}")
    if data["version"] != 214 or len(data["guides"]) != 5:
        raise SystemExit("v214 must contain exactly five guides")
    if data["status"] != "internally-reviewed":
        raise SystemExit("v214 must retain an honest internally-reviewed status")
    if data.get("external_review") != "recommended-not-completed":
        raise SystemExit("v214 must retain an honest external-review state")
    slugs = [guide["slug"] for guide in data["guides"]]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("v214 guide slugs must be unique")
    for guide in data["guides"]:
        for key in ("slug", "title", "description", "category", "audiences", "review_status", "external_review", "professional_limits", "when_to_seek_help", "intro", "sections", "checklist", "common_mistakes", "template", "source_ids", "reviewed_at"):
            if key not in guide:
                raise SystemExit(f"Missing {key} in {guide.get('slug')}")
        if guide["review_status"] != "internally-reviewed":
            raise SystemExit(f"Dishonest review state in {guide['slug']}")
        if guide["external_review"] != "recommended-not-completed":
            raise SystemExit(f"Dishonest external-review state in {guide['slug']}")
        if guide["reviewed_at"] != data["reviewed_at"]:
            raise SystemExit(f"Review date mismatch in {guide['slug']}")
        if not 90 <= len(guide["description"]) <= 180:
            raise SystemExit(f"Meta description length invalid in {guide['slug']}")
        if shared.words(guide) < 900:
            raise SystemExit(f"Guide is too thin: {guide['slug']} ({shared.words(guide)} words)")
        if len(guide["intro"]) < 3:
            raise SystemExit(f"Guide introduction is incomplete: {guide['slug']}")
        if len(guide["sections"]) < 5 or any(len(section.get("paragraphs", [])) < 3 for section in guide["sections"]):
            raise SystemExit(f"Guide sections are incomplete: {guide['slug']}")
        if len(guide["checklist"]) < 7 or len(guide["common_mistakes"]) < 5 or len(guide["template"]) < 8:
            raise SystemExit(f"Guide tools are incomplete: {guide['slug']}")
        if len(guide["source_ids"]) < 2:
            raise SystemExit(f"Guide requires at least two sources: {guide['slug']}")
        for source_id in guide["source_ids"]:
            if source_id not in data["sources"]:
                raise SystemExit(f"Unknown source {source_id} in {guide['slug']}")
    serialized = json.dumps(data, ensure_ascii=False)
    if BANNED.search(serialized):
        raise SystemExit("Prohibited person-label language remains in v214 content")
    for source_id, source in data["sources"].items():
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or parsed.netloc not in ALLOWED_HOSTS:
            raise SystemExit(f"Unapproved source host for {source_id}: {source['url']}")


def link_hub(site: Path, guides: list[dict[str, Any]]) -> None:
    old_start, old_end = shared.START, shared.END
    shared.START, shared.END = START, END
    try:
        shared.link_hub(site, guides)
    finally:
        shared.START, shared.END = old_start, old_end


def publish(site: Path) -> dict[str, Any]:
    data = load_data()
    validate(data)
    generated: list[str] = []
    urls: list[str] = []
    for guide in data["guides"]:
        citations = [data["sources"][source_id] for source_id in guide["source_ids"]]
        target = site / "special-needs" / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(shared.render_guide(guide, citations), encoding="utf-8")
        generated.append(target.relative_to(site).as_posix())
        urls.append(f"{shared.BASE}/special-needs/{guide['slug']}/")

    compat.MAIN_SITEMAP_MODE = "urlset"
    compat.compatible_upsert(site / "sitemap-special-needs.xml", urls, data["reviewed_at"])
    compat.compatible_upsert(site / "sitemap.xml", urls, data["reviewed_at"])
    link_hub(site, data["guides"])

    report = {"version": 214, "status": "built-not-published", "batch": data["batch"], "guide_count": len(data["guides"]), "generated_page_count": len(generated), "generated_pages": generated, "guide_files": [f"content/v214/special-needs-guides/{guide['slug']}.json" for guide in data["guides"]], "source_count": len(data["sources"]), "review_status": data["status"], "external_review": data["external_review"], "sitemap_urls": len(urls), "hub_linked": True, "minimum_source_words": min(shared.words(guide) for guide in data["guides"]), "main_sitemap_mode": compat.MAIN_SITEMAP_MODE}
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-guides-v214.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
