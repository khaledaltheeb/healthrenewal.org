from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_HOST = "khaledaltheeb.github.io"
BASE_PATH = "/"
VERIFY_RE = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.I,
)
REVIEW_RE = re.compile(
    r"(?:آخر\s+(?:تحديث|مراجعة)|تاريخ\s+المراجعة|مراجعة\s+المحتوى|reviewed\s*(?:at|on)|dateModified)"
    r".{0,80}?(20\d{2}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2})",
    re.I | re.S,
)
SOURCE_HEADING_RE = re.compile(r"^(?:المصادر|المراجع|مصادر ومراجع|المراجع العلمية|sources|references)$", re.I)
SENSITIVE_PREFIXES = (
    "encyclopedia/",
    "terms/",
    "care-guides/",
    "assessment-lab/",
    "daily-tools/",
    "learning-paths/",
    "sectors/family/",
    "sectors/special-needs/",
)


@dataclass
class PageSignals:
    title: str = ""
    meta_description: str = ""
    h1_count: int = 0
    canonical_urls: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    visible_text_parts: list[str] = field(default_factory=list)
    json_ld_raw: list[str] = field(default_factory=list)
    external_https_links: list[str] = field(default_factory=list)
    time_datetimes: list[str] = field(default_factory=list)

    @property
    def visible_text(self) -> str:
        return " ".join(self.visible_text_parts)


class ProvenanceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.signals = PageSignals()
        self.stack: list[str] = []
        self.script_type_stack: list[str] = []
        self._json_ld_buffer: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        data = {key.lower(): (value or "") for key, value in attrs}
        self.stack.append(tag)

        if tag == "h1":
            self.signals.h1_count += 1
        if tag == "meta" and data.get("name", "").lower() == "description":
            self.signals.meta_description = data.get("content", "").strip()
        if tag == "link" and "canonical" in data.get("rel", "").lower().split():
            self.signals.canonical_urls.append(data.get("href", "").strip())
        if tag == "a":
            href = data.get("href", "").strip()
            parsed = urlparse(href)
            if parsed.scheme == "https" and parsed.netloc and parsed.netloc != BASE_HOST:
                self.signals.external_https_links.append(href)
        if tag == "time" and data.get("datetime", "").strip():
            self.signals.time_datetimes.append(data["datetime"].strip())
        if tag == "script":
            script_type = data.get("type", "").strip().lower()
            self.script_type_stack.append(script_type)
            if script_type == "application/ld+json":
                self._json_ld_buffer = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script":
            script_type = self.script_type_stack.pop() if self.script_type_stack else ""
            if script_type == "application/ld+json" and self._json_ld_buffer is not None:
                self.signals.json_ld_raw.append("".join(self._json_ld_buffer).strip())
                self._json_ld_buffer = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self._json_ld_buffer is not None:
            self._json_ld_buffer.append(data)
        text = " ".join(data.split())
        if not text:
            return
        if self.stack and self.stack[-1] == "title":
            self.signals.title = (self.signals.title + " " + text).strip()
        if any(tag in self.stack for tag in ("h1", "h2", "h3", "h4", "h5", "h6")):
            self.signals.headings.append(text)
        if not any(tag in self.stack for tag in ("script", "style", "noscript", "svg")):
            self.signals.visible_text_parts.append(text)


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def canonical_is_valid(url: str, rel: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != BASE_HOST:
        return False
    if parsed.query or parsed.fragment or not parsed.path.startswith(BASE_PATH):
        return False
    expected_suffix = rel
    if expected_suffix == "index.html":
        expected_suffix = ""
    elif expected_suffix.endswith("/index.html"):
        expected_suffix = expected_suffix[: -len("index.html")]
    expected_path = BASE_PATH + expected_suffix
    return parsed.path == expected_path


def analyze_page(path: Path, site: Path) -> dict[str, Any]:
    rel = path.relative_to(site).as_posix()
    raw = path.read_text(encoding="utf-8", errors="strict")
    parser = ProvenanceParser()
    parser.feed(raw)
    signals = parser.signals

    errors: list[str] = []
    warnings: list[str] = []
    if signals.h1_count != 1:
        errors.append(f"Expected exactly one H1, found {signals.h1_count}")
    if len(signals.canonical_urls) != 1:
        errors.append(f"Expected exactly one canonical, found {len(signals.canonical_urls)}")
        canonical_valid = False
    else:
        canonical_valid = canonical_is_valid(signals.canonical_urls[0], rel)
        if not canonical_valid:
            errors.append(f"Invalid canonical: {signals.canonical_urls[0]}")

    json_ld_valid = True
    review_evidence = bool(REVIEW_RE.search(signals.visible_text)) or any(
        re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value[:10]) for value in signals.time_datetimes
    )
    source_evidence = False
    source_heading = any(SOURCE_HEADING_RE.fullmatch(heading.strip()) for heading in signals.headings)

    for raw_json in signals.json_ld_raw:
        if not raw_json:
            json_ld_valid = False
            errors.append("Empty JSON-LD block")
            continue
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            json_ld_valid = False
            errors.append(f"Invalid JSON-LD: {exc.msg}")
            continue
        for node in _walk_json(payload):
            if node.get("dateModified") or node.get("datePublished"):
                review_evidence = True
            if node.get("citation") or node.get("isBasedOn"):
                source_evidence = True

    if source_heading and signals.external_https_links:
        source_evidence = True
    sensitive = rel.startswith(SENSITIVE_PREFIXES)
    if sensitive and not review_evidence:
        warnings.append("Sensitive page has no detectable review date")
    if sensitive and not source_evidence:
        warnings.append("Sensitive page has no detectable source evidence")

    return {
        "path": rel,
        "sensitive": sensitive,
        "h1_count": signals.h1_count,
        "canonical_count": len(signals.canonical_urls),
        "canonical_valid": canonical_valid,
        "json_ld_blocks": len(signals.json_ld_raw),
        "json_ld_valid": json_ld_valid,
        "review_evidence": review_evidence,
        "source_evidence": source_evidence,
        "external_https_links": len(signals.external_https_links),
        "errors": errors,
        "warnings": warnings,
    }


def audit_site(site: Path) -> dict[str, Any]:
    pages: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []
    for path in sorted(site.rglob("*.html")):
        raw = path.read_text(encoding="utf-8", errors="strict")
        if path.parent == site and VERIFY_RE.match(raw.strip()):
            continue
        page = analyze_page(path, site)
        pages.append(page)
        errors.extend(f"{page['path']}: {message}" for message in page["errors"])
        warnings.extend(f"{page['path']}: {message}" for message in page["warnings"])

    sensitive_pages = [page for page in pages if page["sensitive"]]
    report = {
        "version": "70-content-provenance",
        "pages_scanned": len(pages),
        "sensitive_pages": len(sensitive_pages),
        "critical_error_count": len(errors),
        "warning_count": len(warnings),
        "pages_with_exactly_one_h1": sum(page["h1_count"] == 1 for page in pages),
        "pages_with_valid_canonical": sum(page["canonical_valid"] for page in pages),
        "pages_with_valid_json_ld": sum(page["json_ld_valid"] for page in pages),
        "sensitive_pages_with_review_evidence": sum(page["review_evidence"] for page in sensitive_pages),
        "sensitive_pages_with_source_evidence": sum(page["source_evidence"] for page in sensitive_pages),
        "critical_errors": errors[:500],
        "warnings": warnings[:1000],
        "weak_provenance_pages": [
            {key: page[key] for key in ("path", "review_evidence", "source_evidence", "warnings")}
            for page in sensitive_pages
            if not page["review_evidence"] or not page["source_evidence"]
        ][:500],
    }
    return report


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not site.is_dir():
        raise SystemExit(f"Site directory does not exist: {site}")
    report = audit_site(site)
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "content-provenance-v70.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["critical_error_count"]:
        raise SystemExit("\n".join(report["critical_errors"][:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
