#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONTACT = ROOT / "contact" / "index.html"
SHELL = ROOT / "assets" / "platform" / "platform-core.js"
SITEMAP = ROOT / "sitemap.xml"
REPORT = ROOT / "api" / "contact-publication-v1.json"
CONTACT_URL = "https://healthrenewal.org/contact/"
EMAIL = "contact@healthrenewal.org"


class ContactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.metas: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.forms: list[dict[str, str]] = []
        self.ids: set[str] = set()
        self.mailtos: list[str] = []
        self.scripts: list[tuple[str, str]] = []
        self._script_type = ""
        self._script_data: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {str(k).lower(): str(v or "") for k, v in attrs}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.metas.append(values)
        elif tag == "link":
            self.links.append(values)
        elif tag == "form":
            self.forms.append(values)
        elif tag == "a" and values.get("href", "").startswith("mailto:"):
            self.mailtos.append(values["href"])
        elif tag == "script":
            self._script_type = values.get("type", "")
            self._script_data = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script":
            self.scripts.append((self._script_type, "".join(self._script_data)))
            self._script_type = ""
            self._script_data = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._script_type:
            self._script_data.append(data)


def meta_content(parser: ContactParser, *, name: str | None = None, prop: str | None = None) -> str:
    for item in parser.metas:
        if name is not None and item.get("name", "").lower() == name.lower():
            return item.get("content", "")
        if prop is not None and item.get("property", "").lower() == prop.lower():
            return item.get("content", "")
    return ""


def patch_footer() -> bool:
    text = SHELL.read_text(encoding="utf-8")
    contact_line = "        element('a', { href: url('contact/'), text: 'تواصل معنا' }),"
    if contact_line in text:
        if text.count(contact_line) != 1:
            raise AssertionError("contact footer link must occur exactly once")
        return False

    anchor = "        element('a', { href: url('accessibility/'), text: 'الإتاحة' }),"
    if text.count(anchor) != 1:
        raise AssertionError("stable accessibility footer anchor not found exactly once")
    text = text.replace(anchor, anchor + "\n" + contact_line, 1)
    SHELL.write_text(text, encoding="utf-8")
    return True


def validate_contact() -> dict[str, object]:
    if not CONTACT.is_file():
        raise AssertionError("contact/index.html is missing")
    raw = CONTACT.read_text(encoding="utf-8")
    parser = ContactParser()
    parser.feed(raw)

    canonical = [x.get("href", "") for x in parser.links if "canonical" in x.get("rel", "").lower().split()]
    robots = meta_content(parser, name="robots").lower()
    description = meta_content(parser, name="description")
    og_url = meta_content(parser, prop="og:url")

    assert parser.title.strip() and "تواصل" in parser.title, parser.title
    assert 90 <= len(description) <= 190, len(description)
    assert canonical == [CONTACT_URL], canonical
    assert "index" in robots and "follow" in robots and "noindex" not in robots, robots
    assert og_url == CONTACT_URL, og_url
    assert "contact-form" in parser.ids
    assert "form-status" in parser.ids
    assert any(EMAIL in value for value in parser.mailtos), parser.mailtos
    assert EMAIL in raw
    assert "mailto:" + EMAIL in raw
    assert "navigator.clipboard" in raw
    assert "form.checkValidity()" in raw
    assert "ContactPage" in raw and "ContactPoint" in raw and "BreadcrumbList" in raw
    assert "application/ld+json" in [kind for kind, _ in parser.scripts]
    assert not re.search(r"<form[^>]+action=['\"]https?://", raw, re.I), "external form processor detected"
    assert "meta name=\"keywords\"" not in raw.lower(), "obsolete meta keywords must not be added"

    json_ld_documents = []
    for kind, payload in parser.scripts:
        if kind == "application/ld+json":
            json_ld_documents.append(json.loads(payload))
    assert json_ld_documents, "JSON-LD is missing"

    return {
        "title": parser.title.strip(),
        "description_length": len(description),
        "canonical": canonical[0],
        "robots": robots,
        "mailtos": len(parser.mailtos),
        "json_ld_documents": len(json_ld_documents),
        "external_form_processor": False,
    }


def validate_footer() -> None:
    text = SHELL.read_text(encoding="utf-8")
    line = "element('a', { href: url('contact/'), text: 'تواصل معنا' })"
    assert text.count(line) == 1, text.count(line)


def validate_sitemap() -> dict[str, object]:
    if not SITEMAP.is_file():
        raise AssertionError("sitemap.xml is missing")
    root = ET.parse(SITEMAP).getroot()
    urls = [
        (node.text or "").strip()
        for node in root.iter()
        if node.tag.split("}", 1)[-1] == "loc" and node.text
    ]
    assert CONTACT_URL in urls, "contact URL is missing from sitemap.xml"
    assert len(urls) == len(set(urls)), "duplicate sitemap URLs"
    assert all(url.startswith("https://healthrenewal.org/") for url in urls), "non-canonical host in sitemap"
    return {"urls": len(urls), "contact_present": True, "duplicates": 0}


def main() -> int:
    footer_changed = patch_footer()
    contact = validate_contact()
    validate_footer()

    report = {
        "version": 1,
        "status": "source-validated",
        "contact_url": CONTACT_URL,
        "email": EMAIL,
        "footer_changed": footer_changed,
        "contact": contact,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
