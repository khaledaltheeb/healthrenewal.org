from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

VERSION = 237
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_URL = "https://healthrenewal.org/"
VERIFY = "google644f1f7a8b7aaa2b.html"
ERROR_MARKER = "data-error-page-jsonld-v237"
HEADING_RE = re.compile(r"<h([1-6])(\b[^>]*)>(.*?)</h\1\s*>", re.IGNORECASE | re.DOTALL)
PROTECTED_RE = re.compile(
    r"<!--.*?-->|<(script|style|textarea|template)\b[^>]*>.*?</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)


class SemanticParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heading_levels: list[int] = []
        self.jsonld_blocks: list[str] = []
        self.title_parts: list[str] = []
        self._in_title = False
        self._in_jsonld = False
        self._jsonld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        lower = tag.lower()
        if re.fullmatch(r"h[1-6]", lower):
            self.heading_levels.append(int(lower[1]))
        if lower == "title":
            self._in_title = True
        if lower == "script" and str(data.get("type", "")).lower() == "application/ld+json":
            self._in_jsonld = True
            self._jsonld_parts = []

    def handle_endtag(self, tag: str) -> None:
        lower = tag.lower()
        if lower == "title":
            self._in_title = False
        if lower == "script" and self._in_jsonld:
            self.jsonld_blocks.append("".join(self._jsonld_parts).strip())
            self._in_jsonld = False
            self._jsonld_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._jsonld_parts.append(data)
            return
        if self._in_title:
            clean = re.sub(r"\s+", " ", data).strip()
            if clean:
                self.title_parts.append(clean)


def parse(text: str) -> SemanticParser:
    parser = SemanticParser()
    parser.feed(text)
    return parser


def heading_jumps(levels: list[int]) -> list[tuple[int, int]]:
    return [(previous, current) for previous, current in zip(levels, levels[1:]) if current > previous + 1]


def normalize_heading_hierarchy(text: str) -> tuple[str, int]:
    """Close missing heading levels while preserving the relative subtree structure."""

    previous_level: int | None = None
    active_shifts: list[tuple[int, int]] = []
    updates = 0

    def normalize_segment(segment: str) -> str:
        def replace(match: re.Match[str]) -> str:
            nonlocal previous_level, updates
            original_level = int(match.group(1))

            while active_shifts and original_level <= active_shifts[-1][0]:
                active_shifts.pop()

            adjusted_level = original_level - sum(delta for _, delta in active_shifts)
            if previous_level is not None and adjusted_level > previous_level + 1:
                missing = adjusted_level - (previous_level + 1)
                active_shifts.append((original_level - 1, missing))
                adjusted_level -= missing

            adjusted_level = max(1, min(6, adjusted_level))
            previous_level = adjusted_level
            if adjusted_level == original_level:
                return match.group(0)

            updates += 1
            return f"<h{adjusted_level}{match.group(2)}>{match.group(3)}</h{adjusted_level}>"

        return HEADING_RE.sub(replace, segment)

    parts: list[str] = []
    cursor = 0
    for protected in PROTECTED_RE.finditer(text):
        parts.append(normalize_segment(text[cursor:protected.start()]))
        parts.append(protected.group(0))
        cursor = protected.end()
    parts.append(normalize_segment(text[cursor:]))
    return "".join(parts), updates


def error_page_schema(title: str) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title or "الصفحة غير موجودة",
        "url": BASE_URL + "404.html",
        "inLanguage": "ar",
        "isPartOf": {
            "@type": "WebSite",
            "name": "مصطلحات علم النفس",
            "url": BASE_URL,
        },
    }
    return (
        f'<script type="application/ld+json" {ERROR_MARKER}>\n'
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + "\n</script>"
    )


def ensure_error_page_jsonld(text: str) -> tuple[str, bool]:
    parser = parse(text)
    if parser.jsonld_blocks:
        return text, False
    if "</head>" not in text.lower():
        raise SystemExit("404.html is missing a closing head tag")
    title = " ".join(parser.title_parts).strip()
    script = error_page_schema(title)
    updated, count = re.subn(r"</head\s*>", script + "\n</head>", text, count=1, flags=re.IGNORECASE)
    if count != 1:
        raise SystemExit("Unable to insert 404 WebPage JSON-LD")
    return updated, True


def finalize(site: Path = SITE) -> dict[str, object]:
    site = Path(site).resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")

    pages_scanned = 0
    heading_pages_updated = 0
    heading_tags_updated = 0
    changed_pages: list[str] = []
    error_jsonld_added = False

    html_pages = [page for page in sorted(site.rglob("*.html")) if page.name != VERIFY]
    for page in html_pages:
        pages_scanned += 1
        original = page.read_text(encoding="utf-8")
        updated, page_updates = normalize_heading_hierarchy(original)
        if page.name == "404.html" and page.parent == site:
            updated, added = ensure_error_page_jsonld(updated)
            error_jsonld_added = error_jsonld_added or added

        if updated != original:
            page.write_text(updated, encoding="utf-8")
            changed_pages.append(page.relative_to(site).as_posix())
        if page_updates:
            heading_pages_updated += 1
            heading_tags_updated += page_updates

    remaining_jumps: list[dict[str, object]] = []
    invalid_jsonld: list[str] = []
    for page in html_pages:
        rel = page.relative_to(site).as_posix()
        text = page.read_text(encoding="utf-8")
        parser = parse(text)
        jumps = heading_jumps(parser.heading_levels)
        if jumps:
            remaining_jumps.append({"page": rel, "jumps": [f"h{a}->h{b}" for a, b in jumps]})
        for block in parser.jsonld_blocks:
            try:
                json.loads(block)
            except json.JSONDecodeError:
                invalid_jsonld.append(rel)

    error_page = site / "404.html"
    error_page_jsonld_present = False
    error_marker_count = 0
    if error_page.is_file():
        error_text = error_page.read_text(encoding="utf-8")
        error_parser = parse(error_text)
        error_page_jsonld_present = bool(error_parser.jsonld_blocks)
        error_marker_count = error_text.count(ERROR_MARKER)

    unresolved = bool(remaining_jumps or invalid_jsonld)
    if error_page.is_file() and (not error_page_jsonld_present or error_marker_count > 1):
        unresolved = True

    report: dict[str, object] = {
        "version": VERSION,
        "status": "passed" if not unresolved else "failed",
        "scope": "global-heading-hierarchy-and-404-jsonld",
        "pages_scanned": pages_scanned,
        "heading_pages_updated": heading_pages_updated,
        "heading_tags_updated": heading_tags_updated,
        "changed_pages": changed_pages,
        "remaining_heading_jumps": len(remaining_jumps),
        "heading_jump_details": remaining_jumps,
        "error_page_jsonld_added": error_jsonld_added,
        "error_page_jsonld_present": error_page_jsonld_present,
        "error_page_marker_count": error_marker_count,
        "invalid_jsonld_pages": sorted(set(invalid_jsonld)),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "semantic-structure-v237.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if unresolved:
        raise SystemExit(f"Semantic structure v237 remains unresolved: {report}")
    return report


def main() -> None:
    print(json.dumps(finalize(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
