#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from html import escape
from pathlib import Path

START = "<!-- special-needs-protocol-links-v326:start -->"
END = "<!-- special-needs-protocol-links-v326:end -->"
HREF_RE = re.compile(r"href=['\"]([^'\"]+)['\"]", re.I)


def insert_before(html: str, marker: str, block: str) -> str:
    if START in html and END in html:
        html = re.sub(re.escape(START) + r".*?" + re.escape(END), "", html, flags=re.S)
    pos = html.lower().rfind(marker.lower())
    if pos < 0:
        return html + block
    return html[:pos] + block + html[pos:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site")
    args = parser.parse_args()
    site = Path(args.site).resolve()
    report_path = site / "api" / "special-needs-protocols-v326.json"
    if not report_path.is_file():
        raise SystemExit(f"Missing v326 report: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    slugs = list(report.get("protocol_slugs") or [])
    if len(slugs) != 50:
        raise SystemExit(f"Expected 50 protocol slugs, found {len(slugs)}")

    index_path = site / "special-needs" / "protocols" / "index.html"
    hub_path = site / "special-needs" / "index.html"
    if not index_path.is_file() or not hub_path.is_file():
        raise SystemExit("Missing protocol index or special-needs hub")

    index_html = index_path.read_text(encoding="utf-8")
    existing = set(HREF_RE.findall(index_html))
    missing = []
    for slug in slugs:
        absolute = f"/special-needs/protocols/{slug}/"
        full = f"https://healthrenewal.org{absolute}"
        if absolute not in existing and full not in existing:
            missing.append(slug)

    if missing:
        items = "".join(
            f'<li><a href="/special-needs/protocols/{escape(slug)}/">{escape(slug.replace("-", " "))}</a></li>'
            for slug in missing
        )
        block = (
            f"\n{START}\n"
            '<nav class="protocol-discovery-v326" aria-label="روابط البروتوكولات المنشورة">'
            '<h2>التصفح المباشر للبروتوكولات</h2><ul>' + items + '</ul></nav>\n'
            f"{END}\n"
        )
        index_html = insert_before(index_html, "</main>", block)
        index_path.write_text(index_html, encoding="utf-8")

    hub_html = hub_path.read_text(encoding="utf-8")
    hub_links = set(HREF_RE.findall(hub_html))
    if "/special-needs/protocols/" not in hub_links and "https://healthrenewal.org/special-needs/protocols/" not in hub_links:
        block = (
            f"\n{START}\n"
            '<nav class="protocol-hub-link-v326" aria-label="بروتوكولات التقييم والعلاج والتأهيل">'
            '<a href="/special-needs/protocols/">بروتوكولات التقييم والعلاج والتأهيل: 50 مسارًا موثقًا</a>'
            '</nav>\n'
            f"{END}\n"
        )
        hub_html = insert_before(hub_html, "</main>", block)
        hub_path.write_text(hub_html, encoding="utf-8")

    for slug in slugs:
        page = site / "special-needs" / "protocols" / slug / "index.html"
        if not page.is_file():
            raise SystemExit(f"Missing generated protocol page: {slug}")
        text = page.read_text(encoding="utf-8")
        links = set(HREF_RE.findall(text))
        if "/special-needs/protocols/" not in links and "https://healthrenewal.org/special-needs/protocols/" not in links:
            block = (
                f"\n{START}\n"
                '<nav class="protocol-backlink-v326" aria-label="دليل البروتوكولات">'
                '<a href="/special-needs/protocols/">العودة إلى دليل البروتوكولات</a>'
                '</nav>\n'
                f"{END}\n"
            )
            text = insert_before(text, "</main>", block)
            page.write_text(text, encoding="utf-8")

    print(json.dumps({"status": "passed", "protocols": len(slugs), "index_missing_links_repaired": len(missing)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
