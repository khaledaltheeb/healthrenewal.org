from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "404.html"
FORBIDDEN_DESTINATIONS = {
    "/encyclopedia/",
    "/care-guides/",
    "/sitemap.xml",
    "/sitemap-index.xml",
}


class RecoveryPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.html_attrs: dict[str, str] = {}
        self.h1_count = 0
        self.links: list[str] = []
        self.robots: list[str] = []
        self.in_recovery_nav = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag == "html":
            self.html_attrs = values
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta" and values.get("name") in {"robots", "googlebot"}:
            self.robots.append(values.get("content", ""))
        elif tag == "nav" and values.get("aria-label") == "مسارات بديلة":
            self.in_recovery_nav = True
        elif tag == "a" and self.in_recovery_nav:
            self.links.append(values.get("href", ""))

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav" and self.in_recovery_nav:
            self.in_recovery_nav = False


def parse_page() -> RecoveryPageParser:
    parser = RecoveryPageParser()
    parser.feed(PAGE.read_text(encoding="utf-8"))
    return parser


def test_404_has_arabic_rtl_semantics_and_noindex() -> None:
    parser = parse_page()
    assert parser.html_attrs.get("lang") == "ar"
    assert parser.html_attrs.get("dir") == "rtl"
    assert parser.h1_count == 1
    assert parser.robots == ["noindex,follow", "noindex,follow"]


def test_recovery_links_are_safe_published_html_routes() -> None:
    parser = parse_page()
    assert parser.links, "404 recovery navigation must expose usable destinations"
    assert not (set(parser.links) & FORBIDDEN_DESTINATIONS)

    for href in parser.links:
        parsed = urlparse(href)
        assert not parsed.scheme and not parsed.netloc, f"external recovery link: {href}"
        assert href.startswith("/"), f"recovery link must be root-absolute: {href}"
        assert not href.lower().endswith((".xml", ".json")), f"machine endpoint exposed: {href}"

        if href == "/":
            target = ROOT / "index.html"
        else:
            target = ROOT / href.strip("/") / "index.html"
        assert target.is_file(), f"recovery destination is not published in source: {href}"


def test_recovery_controls_keep_mobile_touch_target_contract() -> None:
    source = PAGE.read_text(encoding="utf-8")
    assert ".links a{display:inline-flex" in source
    assert "min-height:46px" in source
    assert "@media(max-width:560px)" in source
    assert ".links a{justify-content:center;width:100%}" in source
    assert "@media(prefers-reduced-motion:reduce)" in source
