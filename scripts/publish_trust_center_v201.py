from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import publish_trust_center_v71 as legacy

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BRAND = "منصة روافد"
FOUNDER = "مصطلحات علم النفس"
SLOGAN = "للعافية النفسية والدمج والتمكين"
TRUST_LINK = '<a href="trust/">الثقة والمنهجية</a>'


def brand_page(page: str) -> str:
    page = page.replace("الثقة والمنهج التحريري | مصطلحات علم النفس", f"الثقة والمنهج التحريري | {BRAND}")
    page = page.replace("في منصة مصطلحات علم النفس", f"في {BRAND}")
    page = page.replace('"name": "مصطلحات علم النفس"', f'"name": "{BRAND}"')
    page = page.replace("<body>\n<main>", '<body>\n<a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a>\n<main id="main">', 1)
    if "الاسم المؤسس:" not in page:
        page = page.replace(
            "</footer>",
            f"<p><strong>{BRAND}</strong> — {SLOGAN}</p><p>الاسم المؤسس: {FOUNDER}.</p></footer>",
            1,
        )
    if ".skip{" not in page:
        page = page.replace(
            "<style>",
            "<style>.skip{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px 14px;border:2px solid #168f88;border-radius:12px;z-index:99}.skip:focus{right:8px}",
            1,
        )
    return page


def add_link_to_nav(text: str, nav_match: re.Match[str], link: str) -> tuple[str, bool]:
    nav_html = nav_match.group(0)
    if link in nav_html:
        return text, False
    updated_nav = re.sub(r"</nav>", link + "</nav>", nav_html, count=1, flags=re.I)
    return text[: nav_match.start()] + updated_nav + text[nav_match.end() :], True


def insert_into_first_nav(text: str, link: str) -> tuple[str, bool]:
    header = re.search(r"<header\b[^>]*>.*?</header>", text, re.I | re.S)
    if header:
        relative_nav = re.search(r"<nav\b[^>]*>.*?</nav>", header.group(0), re.I | re.S)
        if relative_nav:
            start = header.start() + relative_nav.start()
            end = header.start() + relative_nav.end()
            absolute_nav = re.match(r".*", text[start:end], re.S)
            if absolute_nav is None:
                raise SystemExit("Unable to resolve homepage navigation")
            nav_html = text[start:end]
            if link in nav_html:
                return text, False
            updated_nav = re.sub(r"</nav>", link + "</nav>", nav_html, count=1, flags=re.I)
            return text[:start] + updated_nav + text[end:], True
    nav = re.search(r"<nav\b[^>]*>.*?</nav>", text, re.I | re.S)
    if nav:
        return add_link_to_nav(text, nav, link)
    raise SystemExit("Homepage contains no navigation element for trust-center integration")


def insert_into_footer(text: str, link: str) -> tuple[str, bool]:
    footer = re.search(r"<footer\b[^>]*>.*?</footer>", text, re.I | re.S)
    if not footer:
        raise SystemExit("Homepage contains no footer for trust-center integration")
    if link in footer.group(0):
        return text, False
    footer_html = footer.group(0)
    footer_links = re.search(r'<div\b[^>]*class=["\'][^"\']*footer-links[^"\']*["\'][^>]*>.*?</div>', footer_html, re.I | re.S)
    if footer_links:
        updated_links = re.sub(r"</div>", link + "</div>", footer_links.group(0), count=1, flags=re.I)
        updated_footer = footer_html[: footer_links.start()] + updated_links + footer_html[footer_links.end() :]
    else:
        updated_footer = re.sub(r"</footer>", f"<p class=\"trust-center-link\">{link}</p></footer>", footer_html, count=1, flags=re.I)
    return text[: footer.start()] + updated_footer + text[footer.end() :], True


def patch_homepage(site: Path) -> dict[str, bool]:
    path = site / "index.html"
    if not path.is_file():
        raise SystemExit("Missing generated homepage before trust-center publication")
    text = path.read_text(encoding="utf-8")
    text, nav_added = insert_into_first_nav(text, TRUST_LINK)
    text, footer_added = insert_into_footer(text, TRUST_LINK)
    header = re.search(r"<header\b[^>]*>.*?</header>", text, re.I | re.S)
    footer = re.search(r"<footer\b[^>]*>.*?</footer>", text, re.I | re.S)
    if not header or TRUST_LINK not in header.group(0):
        raise SystemExit("Trust link is absent from homepage navigation")
    if not footer or TRUST_LINK not in footer.group(0):
        raise SystemExit("Trust link is absent from homepage footer")
    path.write_text(text, encoding="utf-8")
    return {"navigation_link_added": nav_added, "footer_link_added": footer_added}


def publish(site: Path = SITE) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")
    claims = legacy.load_json(legacy.CLAIMS_PATH)
    urgent = legacy.load_json(legacy.URGENT_PATH)
    disability = legacy.load_json(legacy.DISABILITY_PATH)
    legacy.validate_sources(claims, urgent, disability)
    page, report = legacy.make_page(claims, urgent, disability)
    page = brand_page(page)
    out = site / "trust"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    integration = patch_homepage(site)
    legacy.write_sitemap(site, report["updated_at"])
    report.update(
        {
            "version": 201,
            "brand": BRAND,
            "founding_name": FOUNDER,
            "slogan": SLOGAN,
            "semantic_homepage_integration": True,
            **integration,
        }
    )
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "trust-center-v71.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (api / "trust-center-v201.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    publish()
