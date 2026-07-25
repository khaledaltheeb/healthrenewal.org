#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import publish_special_needs_guides_v209 as publisher

ORIGINAL_UPSERT = publisher.upsert_urlset
MAIN_SITEMAP_MODE = "urlset"
LIBRARY_START = "<!-- special-needs-guide-library-v221:start -->"
LIBRARY_END = "<!-- special-needs-guide-library-v221:end -->"
INSERT_MARKER = "<!-- special-needs-guide-library-v221:insert -->"
RESOURCE_MARKER = '<div class="resources">'
STYLE_MARKER = 'id="special-needs-guide-library-style-v221"'
LIBRARY_STYLE = """
<style id="special-needs-guide-library-style-v221">
#special-needs-guide-library-v221 .resources{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
#special-needs-guide-library-v221 .resource{display:flex;flex-direction:column;background:linear-gradient(145deg,#fff,#f4fffc);border:1px solid #c7e8e3;border-radius:18px;padding:18px;box-shadow:0 12px 30px rgba(42,119,118,.08)}
#special-needs-guide-library-v221 .resource:nth-child(4n+1){background:linear-gradient(145deg,#fff,#fff0f6)}
#special-needs-guide-library-v221 .resource:nth-child(4n+2){background:linear-gradient(145deg,#fff,#eafff5)}
#special-needs-guide-library-v221 .resource:nth-child(4n+3){background:linear-gradient(145deg,#fff,#f0edff)}
#special-needs-guide-library-v221 .resource:nth-child(4n){background:linear-gradient(145deg,#fff,#fff6e8)}
#special-needs-guide-library-v221 .resource p{flex:1;color:#4b6e71}
#special-needs-guide-library-v221 .resource .button{align-self:flex-start}
@media(max-width:760px){#special-needs-guide-library-v221 .resources{grid-template-columns:1fr}}
@media print{#special-needs-guide-library-v221 .resource{box-shadow:none;break-inside:avoid}}
</style>
""".strip()
LIBRARY_SECTION = f"""{LIBRARY_START}
<section id="special-needs-guide-library-v221" aria-labelledby="special-needs-guide-library-title-v221">
<h2 id="special-needs-guide-library-title-v221">الأدلة العملية المتخصصة</h2>
<p>أدلة عربية موسعة للأسر والمعلمين ومقدمي الخدمات، مع حدود مهنية ومصادر ظاهرة وحالة مراجعة صريحة. لا تتحول هذه الأدلة إلى تشخيص أو قرار أهلية أو بديل عن التقييم الفردي.</p>
{RESOURCE_MARKER}{INSERT_MARKER}</div>
</section>
{LIBRARY_END}"""


def compatible_upsert(path: Path, urls: list[str], modified: str) -> None:
    global MAIN_SITEMAP_MODE
    if path.name != "sitemap.xml" or not path.is_file():
        ORIGINAL_UPSERT(path, urls, modified)
        return

    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    tree = ET.parse(path)
    root = tree.getroot()
    mode = root.tag.rsplit("}", 1)[-1]
    MAIN_SITEMAP_MODE = mode

    if mode == "urlset":
        ORIGINAL_UPSERT(path, urls, modified)
        return
    if mode != "sitemapindex":
        raise SystemExit(f"Unsupported main sitemap root: {mode}")

    child_url = f"{publisher.BASE}/sitemap-special-needs.xml"
    existing = {
        node.text
        for node in root.findall(f"{{{ns}}}sitemap/{{{ns}}}loc")
        if node.text
    }
    if child_url not in existing:
        node = ET.SubElement(root, f"{{{ns}}}sitemap")
        ET.SubElement(node, f"{{{ns}}}loc").text = child_url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = modified
        tree.write(path, encoding="utf-8", xml_declaration=True)


def inject_style(text: str) -> str:
    if STYLE_MARKER in text:
        return text
    if "</head>" in text:
        return text.replace("</head>", LIBRARY_STYLE + "</head>", 1)
    body = re.search(r"<body\b[^>]*>", text, flags=re.I)
    if body:
        return text[: body.end()] + LIBRARY_STYLE + text[body.end() :]
    return LIBRARY_STYLE + text


def ensure_hub_library(site: Path) -> None:
    hub_path = site / "special-needs" / "index.html"
    if not hub_path.is_file():
        raise SystemExit("Special-needs hub must exist before guide-library integration")

    text = inject_style(hub_path.read_text(encoding="utf-8"))

    if RESOURCE_MARKER not in text:
        anchor = '<section class="review">' if '<section class="review">' in text else "</main>"
        if anchor not in text:
            raise SystemExit("Special-needs hub has no safe insertion anchor")
        text = text.replace(anchor, LIBRARY_SECTION + anchor, 1)
    elif INSERT_MARKER not in text:
        text = text.replace(RESOURCE_MARKER, RESOURCE_MARKER + INSERT_MARKER, 1)

    if text.count(INSERT_MARKER) != 1:
        raise SystemExit("Special-needs hub guide insertion marker must be unique")
    if STYLE_MARKER not in text:
        raise SystemExit("Special-needs guide-library responsive style is missing")
    if LIBRARY_START in text:
        if LIBRARY_END not in text:
            raise SystemExit("Special-needs guide-library closing marker is missing")
        library = text.split(LIBRARY_START, 1)[1].split(LIBRARY_END, 1)[0]
        if library.count(RESOURCE_MARKER) != 1:
            raise SystemExit("Contracted special-needs guide library must contain one resources container")

    hub_path.write_text(text, encoding="utf-8")


def compatible_link_hub(site: Path, guides: list[dict[str, Any]]) -> None:
    ensure_hub_library(site)
    hub_path = site / "special-needs" / "index.html"
    text = hub_path.read_text(encoding="utf-8")
    payload = publisher.hub_cards(guides)

    if publisher.START in text and publisher.END in text:
        text, count = re.subn(
            re.escape(publisher.START) + r".*?" + re.escape(publisher.END),
            payload,
            text,
            count=1,
            flags=re.S,
        )
        if count != 1:
            raise SystemExit(f"Could not refresh guide block {publisher.START}")
    else:
        if INSERT_MARKER not in text:
            raise SystemExit("Special-needs guide insertion marker is missing")
        text = text.replace(INSERT_MARKER, payload + INSERT_MARKER, 1)

    if text.count(publisher.START) != 1 or text.count(publisher.END) != 1:
        raise SystemExit(f"Guide block markers are not unique: {publisher.START}")
    hub_path.write_text(text, encoding="utf-8")


def publish(site: Path) -> dict[str, Any]:
    global MAIN_SITEMAP_MODE
    MAIN_SITEMAP_MODE = "urlset"
    ensure_hub_library(site)
    publisher.upsert_urlset = compatible_upsert
    publisher.link_hub = compatible_link_hub
    try:
        report = publisher.publish(site)
    finally:
        publisher.upsert_urlset = ORIGINAL_UPSERT
        # Keep the compatible hub linker installed: v210-v212 execute in the
        # same v217 process and reuse it with their own block markers.

    hub_text = (site / "special-needs" / "index.html").read_text(encoding="utf-8")
    for marker in (INSERT_MARKER, publisher.START, publisher.END):
        if marker not in hub_text:
            raise SystemExit(f"Special-needs hub compatibility marker is missing: {marker}")

    report["main_sitemap_mode"] = MAIN_SITEMAP_MODE
    report_path = site / "api" / "special-needs-guides-v209.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
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
