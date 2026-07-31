from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_PATH = "/"
CRITICAL_PREFIXES = (
    "sections/",
    "encyclopedia/",
    "hubs/",
    "assessments/",
    "cognitive-tests/",
    "comparisons/",
    "guided-assessment/",
    "library/",
    "tips/",
    "care-guides/",
    "special-needs/",
    "sectors/",
    "assessment-lab/",
    "cognitive-lab/",
    "daily-tools/",
    "learning-paths/",
    "magazine/",
    "trust/",
    "partners/",
    "developers/",
    "start-here/",
    "provider-assessment-demo/",
    "api/",
    "en/",
    "es/",
    "guides/",
    "blog/",
)
REQUIRED_GATEWAYS = (
    "sections/",
    "encyclopedia/",
    "comparisons/",
    "library/",
    "guided-assessment/",
    "hubs/",
    "assessments/",
    "cognitive-tests/",
    "care-guides/",
    "special-needs/",
    "assessment-lab/",
    "cognitive-lab/",
    "daily-tools/",
    "learning-paths/",
    "magazine/",
    "trust/",
    "partners/",
    "developers/",
    "start-here/",
    "provider-assessment-demo/",
    "api/",
)


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(str(href))


def route_for(path: Path, site: Path) -> str:
    rel = path.relative_to(site).as_posix()
    return "" if rel == "index.html" else rel.removesuffix("index.html")


def resolve_route(source: Path, href: str, site: Path) -> str | None:
    parsed = urlparse(href)
    if parsed.scheme in {"http", "https"}:
        if not parsed.path.startswith(BASE_PATH):
            return None
        raw = parsed.path[len(BASE_PATH):]
    elif parsed.scheme or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    elif parsed.path.startswith(BASE_PATH):
        raw = parsed.path[len(BASE_PATH):]
    elif parsed.path.startswith("/"):
        return None
    else:
        raw = (source.parent.relative_to(site) / unquote(parsed.path)).as_posix()
    raw = unquote(raw).lstrip("/")
    target = (site / raw).resolve()
    try:
        target.relative_to(site)
    except ValueError:
        return None
    if href.endswith("/") or not target.suffix:
        target /= "index.html"
    if target.name != "index.html":
        return None
    return route_for(target, site)


def sitemap_routes(site: Path) -> set[str]:
    routes: set[str] = set()
    for path in site.glob("sitemap*.xml"):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        for node in root.findall("{*}url/{*}loc"):
            if not node.text:
                continue
            parsed = urlparse(node.text.strip())
            if parsed.path.startswith(BASE_PATH):
                routes.add(unquote(parsed.path[len(BASE_PATH):]).lstrip("/"))
    return routes


def is_indexable(source: str) -> bool:
    for tag in re.findall(r"<meta\b[^>]*>", source, flags=re.I | re.S):
        if not re.search(r"\bname\s*=\s*([\"'])robots\1", tag, flags=re.I):
            continue
        content = re.search(r"\bcontent\s*=\s*([\"'])(.*?)\1", tag, flags=re.I | re.S)
        if content and "noindex" in content.group(2).lower():
            return False
    return True


def audit(site: Path, require_gateways: bool = False) -> dict[str, object]:
    all_pages = sorted(site.rglob("index.html"))
    pages = [
        page
        for page in all_pages
        if is_indexable(page.read_text(encoding="utf-8"))
    ]
    routes = {route_for(page, site): page for page in pages}
    inbound: Counter[str] = Counter()
    for page in pages:
        parser = LinkParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for href in parser.links:
            target = resolve_route(page, href, site)
            if target in routes and target != route_for(page, site):
                inbound[target] += 1
    mapped = sitemap_routes(site)
    orphan = sorted(route for route in routes if route and inbound[route] == 0)
    missing_sitemap = sorted(route for route in routes if route not in mapped)
    critical = sorted(route for route in orphan if route.startswith(CRITICAL_PREFIXES))
    critical_unmapped = sorted(route for route in missing_sitemap if route.startswith(CRITICAL_PREFIXES))
    required_gateways = list(REQUIRED_GATEWAYS) if require_gateways else []
    missing_gateways = sorted(route for route in required_gateways if route not in routes)
    gateway_orphans = sorted(route for route in required_gateways if route in routes and inbound[route] == 0)
    gateway_unmapped = sorted(route for route in required_gateways if route in routes and route not in mapped)
    failed = bool(critical or critical_unmapped or missing_gateways or gateway_orphans or gateway_unmapped)
    return {
        "version": 220,
        "status": "failed" if failed else "passed",
        "pages": len(pages),
        "html_pages": len(all_pages),
        "excluded_noindex_pages": len(all_pages) - len(pages),
        "sitemap_routes": len(mapped),
        "orphan_pages": orphan,
        "missing_from_sitemaps": missing_sitemap,
        "critical_prefixes": list(CRITICAL_PREFIXES),
        "critical_orphans": critical,
        "critical_unmapped": critical_unmapped,
        "required_gateways": required_gateways,
        "missing_gateways": missing_gateways,
        "gateway_orphans": gateway_orphans,
        "gateway_unmapped": gateway_unmapped,
        "inbound_distribution": dict(sorted(Counter(inbound.values()).items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site")
    parser.add_argument("--fail-on-critical", action="store_true")
    parser.add_argument("--require-gateways", action="store_true")
    args = parser.parse_args()
    site = Path(args.site).resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    report = audit(site, require_gateways=args.require_gateways)
    output = site / "api" / "orphan-page-audit-v197.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.fail_on_critical and report["status"] != "passed":
        raise SystemExit("Critical orphan, sitemap, or gateway discovery defects detected")


if __name__ == "__main__":
    main()
