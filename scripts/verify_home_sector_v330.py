#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "index": ROOT / "sectors" / "home" / "index.html",
    "library": ROOT / "sectors" / "home" / "library" / "index.html",
    "assessment": ROOT / "sectors" / "home" / "assessment" / "index.html",
    "interventions": ROOT / "sectors" / "home" / "interventions" / "index.html",
}
CANONICALS = {
    "index": "https://healthrenewal.org/sectors/home/",
    "library": "https://healthrenewal.org/sectors/home/library/",
    "assessment": "https://healthrenewal.org/sectors/home/assessment/",
    "interventions": "https://healthrenewal.org/sectors/home/interventions/",
}
MIN_WORDS = {"index": 850, "library": 600, "assessment": 600, "interventions": 800}
REQUIRED_MARKERS = {
    "index": ["الأخطار المنزلية والطبية تسبق تحسين الروتين", "المنزل للروتين والوقت والمكان والأدوات والحواس والسلامة", "مبادئ تصميم المنزل الداعم", "لا تعني اعتمادًا سريريًا خارجيًا"],
    "library": ["لا تقدم تشخيصًا من شكل الغرفة أو الروتين", "البيئة الحسية ومساحات الهدوء", "خطة الأزمات المنزلية"],
    "assessment": ["لا تفسر الخطر أو المرض بوصفه سلوكًا", "حلل البيئة والحواس", "حدود قوائم فحص المنزل", "صياغة مفيدة"],
    "interventions": ["لا تستخدم الروتين أو العزل لإدارة خطر طبي أو عنف", "قاعدة منع الضرر", "لا تستخدم الجداول والأقفال والكاميرات والعزل", "قياس الأثر وقواعد التوقف"],
}
REQUIRED_LINKS = {
    "index": ["library/", "assessment/", "interventions/"],
    "library": ["../", "../assessment/", "../interventions/"],
    "assessment": ["../", "../library/", "../interventions/"],
    "interventions": ["../", "../library/", "../assessment/"],
}
BANNED_PATTERNS = [r"\bمعاقين\b", r"(?<!لا )علاج مضمون", r"(?<!لا تعد ب)نتيجة مضمونة"]
ALLOWED_HOSTS = {"www.who.int", "www.unicef.org"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.text: list[str] = []
        self.ids: list[str] = []
        self.hrefs: list[str] = []
        self.tags: Counter[str] = Counter()
        self.headings: list[int] = []
        self.canonical: list[str] = []
        self.meta: dict[str, str] = {}
        self.html_attrs: dict[str, str] = {}
        self.json_ld: list[str] = []
        self._json: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = {key.lower(): value or "" for key, value in attrs}
        self.stack.append(tag)
        self.tags[tag] += 1
        if tag == "html":
            self.html_attrs = data
        if "id" in data:
            self.ids.append(data["id"])
        if tag == "a":
            self.hrefs.append(data.get("href", ""))
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag == "link" and data.get("rel", "").lower() == "canonical":
            self.canonical.append(data.get("href", ""))
        if tag == "meta":
            key = data.get("name") or data.get("property")
            if key:
                self.meta[key.lower()] = data.get("content", "")
        if tag == "script" and data.get("type", "").lower() == "application/ld+json":
            self._json = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self._json is not None:
            self.json_ld.append("".join(self._json))
            self._json = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self._json is not None:
            self._json.append(data)
            return
        if any(tag in self.stack for tag in ("style", "script", "svg", "template", "noscript")):
            return
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.text.append(value)


def schema_types(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        item = value.get("@type")
        if isinstance(item, str):
            found.add(item)
        elif isinstance(item, list):
            found.update(entry for entry in item if isinstance(entry, str))
        for child in value.values():
            found.update(schema_types(child))
    elif isinstance(value, list):
        for child in value:
            found.update(schema_types(child))
    return found


def validate_page(name: str, path: Path) -> dict[str, object]:
    errors: list[str] = []
    if not path.exists():
        return {"name": name, "status": "failed", "errors": ["missing page"]}
    source = path.read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(source)
    visible = " ".join(parser.text)
    words = len(re.findall(r"[\w\u0600-\u06ff]+", visible, re.UNICODE))

    if not re.match(r"\s*<!doctype html>", source, re.I):
        errors.append("missing doctype")
    if parser.html_attrs.get("lang") != "ar" or parser.html_attrs.get("dir") != "rtl":
        errors.append("invalid language or direction")
    if parser.tags["h1"] != 1:
        errors.append(f"expected one h1, found {parser.tags['h1']}")
    if parser.tags["main"] != 1 or parser.tags["header"] != 1 or parser.tags["footer"] != 1:
        errors.append("missing semantic shell")
    if words < MIN_WORDS[name]:
        errors.append(f"visible words {words} below {MIN_WORDS[name]}")
    if parser.canonical != [CANONICALS[name]]:
        errors.append(f"canonical mismatch: {parser.canonical}")
    if "noindex" in source.lower():
        errors.append("page must remain indexable")
    if not parser.meta.get("description") or not parser.meta.get("robots"):
        errors.append("missing metadata")
    duplicate_ids = [key for key, count in Counter(parser.ids).items() if count > 1]
    if duplicate_ids:
        errors.append(f"duplicate ids: {duplicate_ids}")
    for previous, current in zip(parser.headings, parser.headings[1:]):
        if current > previous + 1:
            errors.append(f"heading jump h{previous} to h{current}")
            break
    for marker in REQUIRED_MARKERS[name]:
        if marker not in visible:
            errors.append(f"missing marker: {marker}")
    for href in REQUIRED_LINKS[name]:
        if href not in parser.hrefs:
            errors.append(f"missing link: {href}")
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, source):
            errors.append(f"banned pattern: {pattern}")
    if any(not href or href == "#" for href in parser.hrefs):
        errors.append("placeholder link")

    types: set[str] = set()
    for raw in parser.json_ld:
        try:
            types.update(schema_types(json.loads(raw)))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON-LD: {exc}")
    required_type = "CollectionPage" if name == "library" else "MedicalWebPage"
    if required_type not in types or "BreadcrumbList" not in types:
        errors.append("missing schema types")
    if name == "index" and not {"ItemList", "FAQPage"}.issubset(types):
        errors.append("missing main schemas")

    external = [href for href in parser.hrefs if href.startswith("http://") or href.startswith("https://")]
    for href in external:
        parsed = urlparse(href)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            errors.append(f"invalid external source: {href}")
    if name == "index" and len(external) < 4:
        errors.append("main page needs four institutional sources")

    return {
        "name": name,
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "status": "passed" if not errors else "failed",
        "visible_words": words,
        "schema_types": sorted(types),
        "external_sources": len(external),
        "errors": errors,
    }


def validate() -> dict[str, object]:
    pages = [validate_page(name, path) for name, path in PAGES.items()]
    errors: list[str] = []
    css = ROOT / "sectors" / "home" / "assets" / "home-sector.css"
    if not css.exists() or "home-sector-a11y-scroll-v330" not in css.read_text(encoding="utf-8"):
        errors.append("missing responsive stylesheet marker")
    portal = (ROOT / "sectors" / "index.html").read_text(encoding="utf-8")
    if 'href="home/"' not in portal:
        errors.append("parent portal missing home link")
    for page in pages:
        if page["status"] != "passed":
            errors.extend(f"{page['name']}: {item}" for item in page["errors"])
    return {"status": "passed" if not errors else "failed", "version": 330, "pages": pages, "errors": errors}


def main() -> int:
    cli = argparse.ArgumentParser(description="Verify home and daily-environment sector v330.")
    cli.add_argument("--json", action="store_true")
    args = cli.parse_args()
    report = validate()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) if args.json else report)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
