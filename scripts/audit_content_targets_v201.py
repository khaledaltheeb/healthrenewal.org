#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "content" / "content-growth-roadmap-v201.json"
VERIFY_FILE = "google644f1f7a8b7aaa2b.html"

SOURCE_REGISTRIES = {
    "practical_tips": [("content/sectors-v10/tips.json", "guides")],
    "family": [("content/sectors-v10/family.json", "articles")],
    "child": [("content/sectors-v10/child.json", "articles")],
    "home_family": [("content/sectors-v10/home.json", "articles")],
    "youth": [("content/v353/youth-sector-ar.json", "guides")],
    "care_guides": [
        ("content/v18/care-guides-ar.json", "guides"),
        ("content/v18/care-guides-adhd-ar.json", "guides"),
        ("content/v18/care-guides-autism-ar.json", "guides"),
    ],
}


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "svg", "noscript", "template"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "svg", "noscript", "template"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)

    def text(self) -> str:
        return " ".join(self.parts)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def source_count(target_key: str) -> tuple[int | None, list[dict[str, Any]]]:
    registries = SOURCE_REGISTRIES.get(target_key)
    if not registries:
        return None, []
    total = 0
    details: list[dict[str, Any]] = []
    for relative, field in registries:
        path = ROOT / relative
        if not path.is_file():
            details.append({"path": relative, "field": field, "exists": False, "count": 0})
            continue
        payload = load_json(path)
        values = payload.get(field, []) if isinstance(payload, dict) else []
        count = len(values) if isinstance(values, list) else 0
        details.append({"path": relative, "field": field, "exists": True, "count": count})
        total += count
    return total, details


def extract(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, re.I | re.S)
    return html.unescape(re.sub(r"\s+", " ", match.group(1)).strip()) if match else None


def page_metrics(path: Path, site: Path, placeholder_phrases: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    parser = VisibleTextParser()
    parser.feed(text)
    visible = parser.text()
    words = re.findall(r"[\w\u0600-\u06ff]+", visible, re.UNICODE)
    title = extract(r"<title[^>]*>(.*?)</title>", text)
    h1s = re.findall(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S)
    description = extract(r'<meta\s+name=["\']description["\'][^>]*content=["\'](.*?)["\']', text)
    if description is None:
        description = extract(r'<meta\s+content=["\'](.*?)["\'][^>]*name=["\']description["\']', text)
    canonical = extract(r'<link\s+[^>]*rel=["\'][^"\']*canonical[^"\']*["\'][^>]*href=["\'](.*?)["\']', text)
    if canonical is None:
        canonical = extract(r'<link\s+[^>]*href=["\'](.*?)["\'][^>]*rel=["\'][^"\']*canonical[^"\']*["\']', text)
    placeholders = [phrase for phrase in placeholder_phrases if phrase in visible]
    return {
        "path": path.relative_to(site).as_posix(),
        "visible_words": len(words),
        "title": title,
        "h1_count": len(h1s),
        "description": description,
        "description_chars": len(description or ""),
        "canonical": canonical,
        "has_schema": "application/ld+json" in text,
        "has_header": bool(re.search(r"<header\b", text, re.I)),
        "has_footer": bool(re.search(r"<footer\b", text, re.I)),
        "internal_link_count": len(re.findall(r'<a\b[^>]*href=["\'](?:/|\.\.?/|[^:/#][^"\']*)["\']', text, re.I)),
        "placeholder_phrases": placeholders,
    }


def content_pages(site: Path, route: str) -> list[Path]:
    root = site / route
    if not root.is_dir():
        return []
    pages = []
    for page in sorted(root.rglob("index.html")):
        if page.parent == root:
            continue
        if page.name == VERIFY_FILE:
            continue
        pages.append(page)
    return pages


def audit_target(site: Path, key: str, target: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    pages = content_pages(site, target["route"])
    metrics = [page_metrics(page, site, quality["forbid_placeholder_phrases"]) for page in pages]
    minimum_words = int(target["minimum_visible_words"])
    below_depth = [item for item in metrics if item["visible_words"] < minimum_words]
    missing_structure = [
        item for item in metrics
        if not item["title"]
        or item["h1_count"] != 1
        or not item["description"]
        or not item["canonical"]
        or not item["has_schema"]
        or not item["has_header"]
        or not item["has_footer"]
    ]
    placeholders = [item for item in metrics if item["placeholder_phrases"]]
    title_counts = Counter(item["title"] for item in metrics if item["title"])
    canonical_counts = Counter(item["canonical"] for item in metrics if item["canonical"])
    duplicate_titles = sorted(title for title, count in title_counts.items() if count > 1)
    duplicate_canonicals = sorted(value for value, count in canonical_counts.items() if count > 1)
    source_total, source_details = source_count(key)
    published = len(metrics)
    target_minimum = int(target["minimum_count"])
    confirmed = target.get("current_confirmed_count")
    return {
        "key": key,
        "label": target["label"],
        "route": target["route"],
        "target_minimum": target_minimum,
        "published_count": published,
        "target_gap": max(0, target_minimum - published),
        "source_registry_count": source_total,
        "source_registries": source_details,
        "confirmed_baseline": confirmed,
        "minimum_visible_words": minimum_words,
        "minimum_words_observed": min((item["visible_words"] for item in metrics), default=0),
        "median_visible_words": sorted(item["visible_words"] for item in metrics)[len(metrics) // 2] if metrics else 0,
        "below_depth_count": len(below_depth),
        "below_depth_pages": below_depth[:100],
        "missing_structure_count": len(missing_structure),
        "missing_structure_pages": missing_structure[:100],
        "placeholder_page_count": len(placeholders),
        "placeholder_pages": placeholders[:100],
        "duplicate_titles": duplicate_titles,
        "duplicate_canonicals": duplicate_canonicals,
        "pages": metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    parser.add_argument("--roadmap", type=Path, default=ROADMAP)
    parser.add_argument("--fail-on-regressions", action="store_true")
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    roadmap = load_json(args.roadmap.resolve())
    quality = roadmap["quality_contract"]
    targets = {
        key: audit_target(site, key, target, quality)
        for key, target in roadmap["targets"].items()
    }
    totals = {
        "published_pages_across_targets": sum(item["published_count"] for item in targets.values()),
        "target_pages": sum(item["target_minimum"] for item in targets.values()),
        "remaining_gap": sum(item["target_gap"] for item in targets.values()),
        "below_depth_pages": sum(item["below_depth_count"] for item in targets.values()),
        "missing_structure_pages": sum(item["missing_structure_count"] for item in targets.values()),
        "placeholder_pages": sum(item["placeholder_page_count"] for item in targets.values()),
    }
    regressions: list[str] = []
    for key, item in targets.items():
        baseline = item["confirmed_baseline"]
        if isinstance(baseline, int) and item["published_count"] < baseline:
            regressions.append(f"{key}: published_count={item['published_count']} below confirmed baseline={baseline}")
        if item["missing_structure_count"]:
            regressions.append(f"{key}: {item['missing_structure_count']} pages missing required structure")
        if item["placeholder_page_count"]:
            regressions.append(f"{key}: {item['placeholder_page_count']} pages contain placeholder phrases")
        if item["duplicate_titles"]:
            regressions.append(f"{key}: duplicate titles {item['duplicate_titles'][:5]}")
        if item["duplicate_canonicals"]:
            regressions.append(f"{key}: duplicate canonicals {item['duplicate_canonicals'][:5]}")
    report = {
        "version": 201,
        "status": "passed" if not regressions else "regressions-detected",
        "platform_name": roadmap["platform_name"],
        "roadmap_status": roadmap["status"],
        "totals": totals,
        "targets": targets,
        "regressions": regressions,
        "target_gaps_are_blocking": False,
        "note": "الهدف العددي لا يمنع البناء في مرحلة التوسع، لكن التراجع عن خط أساس مؤكد أو نشر صفحات ناقصة بنيويًا أو تحمل عبارات مؤقتة يمنع القبول عند تفعيل --fail-on-regressions."
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    path = api / "content-targets-v201.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "totals": totals,
        "counts": {key: value["published_count"] for key, value in targets.items()},
        "gaps": {key: value["target_gap"] for key, value in targets.items()},
        "regressions": regressions,
        "report": str(path),
    }, ensure_ascii=False, indent=2))
    if args.fail_on_regressions and regressions:
        raise SystemExit("\n".join(regressions[:50]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
