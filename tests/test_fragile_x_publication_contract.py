from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "special-needs/conditions/fragile-x-syndrome"
URL = "https://healthrenewal.org/special-needs/conditions/fragile-x-syndrome/"
PAGES = {
    "index.html": URL,
    "genetics-diagnosis/index.html": URL + "genetics-diagnosis/",
    "health-lifespan/index.html": URL + "health-lifespan/",
    "communication-education/index.html": URL + "communication-education/",
    "behavior-intervention/index.html": URL + "behavior-intervention/",
    "family-safety-transition/index.html": URL + "family-safety-transition/",
}


class ContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1 = 0
        self.lang = None
        self.direction = None
        self.canonicals: list[str] = []
        self.ids: set[str] = set()
        self.hrefs: list[str] = []
        self.jsonld: list[str] = []
        self._in_jsonld = False
        self._json_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
            self.direction = values.get("dir")
        if tag == "h1":
            self.h1 += 1
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href"):
            self.hrefs.append(values["href"])
        if tag == "link" and "canonical" in values.get("rel", "").split():
            self.canonicals.append(values.get("href", ""))
        if tag == "script" and values.get("type") == "application/ld+json":
            self._in_jsonld = True
            self._json_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_jsonld:
            self.jsonld.append("".join(self._json_parts))
            self._in_jsonld = False

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._json_parts.append(data)


def schema_types(value) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        current = value.get("@type")
        if isinstance(current, str):
            found.add(current)
        elif isinstance(current, list):
            found.update(item for item in current if isinstance(item, str))
        for child in value.values():
            found.update(schema_types(child))
    elif isinstance(value, list):
        for child in value:
            found.update(schema_types(child))
    return found


def test_fragile_x_publication_contract() -> None:
    failures: list[str] = []
    combined = ""
    total_size = 0

    for relative, canonical in PAGES.items():
        path = BASE / relative
        if not path.is_file():
            failures.append(f"missing page: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        combined += "\n" + text
        total_size += len(text)
        minimum = 11500 if relative == "index.html" else 8500
        if len(text) < minimum:
            failures.append(f"page too short: {relative} ({len(text)} < {minimum})")
        if "khaledaltheeb.github.io" in text or "pterminology-site" in text:
            failures.append(f"legacy domain in {relative}")
        if re.search(r'<meta\s+[^>]*name=["\']keywords["\']', text, re.I):
            failures.append(f"meta keywords in {relative}")
        parser = ContractParser()
        parser.feed(text)
        if (parser.lang, parser.direction) != ("ar", "rtl"):
            failures.append(f"language/direction failure: {relative}")
        if parser.h1 != 1:
            failures.append(f"expected one H1 in {relative}; found {parser.h1}")
        if parser.canonicals != [canonical]:
            failures.append(f"canonical failure in {relative}: {parser.canonicals}")
        if "main" not in parser.ids:
            failures.append(f"missing main target in {relative}")
        schemas = []
        for raw in parser.jsonld:
            try:
                schemas.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                failures.append(f"invalid JSON-LD in {relative}: {exc}")
        types = schema_types(schemas)
        if not {"MedicalWebPage", "BreadcrumbList"}.issubset(types):
            failures.append(f"schema types missing in {relative}: {sorted(types)}")
        for href in parser.hrefs:
            if href.startswith("#") and href[1:] and href[1:] not in parser.ids:
                failures.append(f"broken anchor {href} in {relative}")

    if total_size < 72000:
        failures.append(f"combined guide is not sufficiently expanded: {total_size}")

    required_terms = [
        "FMR1", "FMRP", "CGG", "الطفرة الكاملة", "الطفرة السابقة",
        "المثيلة", "الفسيفسائية", "AGG", "الإكسوم", "FXTAS", "FXPOI",
        "الاستشارة الجينية", "التشخيص التفريقي", "التواصل المعزز",
        "القرار المدعوم", "لا يوجد", "علاج شاف", "23765048",
        "10.1542/peds.2010-3500", "10.1038/gim.2013.61",
        "الخصوصية", "الاستغلال", "التنمر", "خطة الطوارئ",
    ]
    for term in required_terms:
        if term not in combined:
            failures.append(f"missing required concept/source: {term}")

    hub = (BASE / "index.html").read_text(encoding="utf-8")
    for relative in list(PAGES)[1:]:
        link = relative.removesuffix("index.html")
        if f'href="{link}"' not in hub:
            failures.append(f"hub does not link page: {relative}")

    evidence_path = BASE / "evidence.json"
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        failures.append(f"invalid evidence registry: {exc}")
        evidence = {}
    if len(evidence.get("sources", [])) < 10:
        failures.append("evidence registry requires at least 10 sources")
    if len(evidence.get("claim_matrix", [])) < 6:
        failures.append("evidence registry requires at least 6 mapped claims")

    sitemap_path = ROOT / "sitemap-fragile-x-syndrome.xml"
    try:
        sitemap_root = ET.parse(sitemap_path).getroot()
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = {node.text for node in sitemap_root.findall("sm:url/sm:loc", namespace)}
    except (FileNotFoundError, ET.ParseError) as exc:
        failures.append(f"invalid fragile X sitemap: {exc}")
        locations = set()
    expected_urls = set(PAGES.values())
    if locations != expected_urls:
        failures.append(f"sitemap URLs mismatch: {locations ^ expected_urls}")

    sitemap_index = (ROOT / "sitemap-index.xml").read_text(encoding="utf-8")
    if "https://healthrenewal.org/sitemap-fragile-x-syndrome.xml" not in sitemap_index:
        failures.append("fragile X sitemap not registered in sitemap-index.xml")
    conditions_hub = (ROOT / "special-needs/conditions/index.html").read_text(encoding="utf-8")
    if URL not in conditions_hub:
        failures.append("conditions hub does not link fragile X guide")

    assert not failures, "\n".join(failures)
