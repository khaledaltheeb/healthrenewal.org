from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

MARKER_CSS = "v11 — global readable contrast layer"
MARKER_JS = "v11 — runtime contrast guard"
VERIFY_NAME = "google644f1f7a8b7aaa2b.html"


def inject_before(text: str, closing: str, addition: str) -> str:
    if closing in text:
        return text.replace(closing, f"{addition}\n{closing}", 1)
    return text + "\n" + addition + "\n"


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    repo = Path(__file__).resolve().parents[1]
    css_source = repo / "content" / "accessibility" / "contrast-v11.css"
    js_source = repo / "content" / "accessibility" / "contrast-guard-v11.js"
    css_target = site / "assets" / "css" / "theme-v10.css"
    js_target = site / "assets" / "js" / "app-v10.js"

    for required in (site, css_source, js_source, css_target, js_target):
        if not required.exists():
            raise SystemExit(f"Missing required path: {required}")

    css_payload = css_source.read_text(encoding="utf-8")
    js_payload = js_source.read_text(encoding="utf-8")
    current_css = css_target.read_text(encoding="utf-8")
    current_js = js_target.read_text(encoding="utf-8")

    if MARKER_CSS not in current_css:
        css_target.write_text(current_css.rstrip() + "\n\n" + css_payload.rstrip() + "\n", encoding="utf-8")
    if MARKER_JS not in current_js:
        js_target.write_text(current_js.rstrip() + "\n\n" + js_payload.rstrip() + "\n", encoding="utf-8")

    site_base = os.environ.get("SITE_BASE", "https://healthrenewal.org/")
    base_path = urlparse(site_base).path.rstrip("/") + "/"
    css_url = f"{base_path}assets/css/theme-v10.css"
    js_url = f"{base_path}assets/js/app-v10.js"

    html_files = sorted(site.rglob("*.html"))
    content_files = [p for p in html_files if p.name != VERIFY_NAME]
    injected_css = 0
    injected_js = 0
    theme_meta = 0

    for page in content_files:
        text = page.read_text(encoding="utf-8", errors="strict")
        changed = False
        if "theme-v10.css" not in text:
            text = inject_before(text, "</head>", f'<link rel="stylesheet" href="{css_url}">')
            injected_css += 1
            changed = True
        if "app-v10.js" not in text:
            text = inject_before(text, "</body>", f'<script src="{js_url}" defer></script>')
            injected_js += 1
            changed = True
        if 'name="theme-color"' not in text:
            text = inject_before(text, "</head>", '<meta name="theme-color" content="#effaf7">')
            theme_meta += 1
            changed = True
        if changed:
            page.write_text(text, encoding="utf-8")

    target = site / "terms" / "psychological-well-being" / "index.html"
    target_text = target.read_text(encoding="utf-8") if target.exists() else ""
    target_sentence = "خبرة واسعة تشمل الرضا والمعنى والقدرة على إدارة الانفعالات وبناء علاقات داعمة."

    failures: list[str] = []
    if MARKER_CSS not in css_target.read_text(encoding="utf-8"):
        failures.append("contrast CSS marker missing")
    if MARKER_JS not in js_target.read_text(encoding="utf-8"):
        failures.append("contrast JS marker missing")
    if not target.exists():
        failures.append("psychological well-being page missing")
    elif target_sentence not in target_text:
        failures.append("target sentence missing from psychological well-being page")

    unstyled = []
    unguarded = []
    for page in content_files:
        text = page.read_text(encoding="utf-8", errors="strict")
        if "theme-v10.css" not in text:
            unstyled.append(str(page.relative_to(site)))
        if "app-v10.js" not in text:
            unguarded.append(str(page.relative_to(site)))
    if unstyled:
        failures.append(f"pages without theme CSS: {len(unstyled)}")
    if unguarded:
        failures.append(f"pages without contrast guard JS: {len(unguarded)}")

    report = {
        "version": "v11-contrast",
        "html_pages": len(html_files),
        "content_pages": len(content_files),
        "pages_with_theme": len(content_files) - len(unstyled),
        "pages_with_guard": len(content_files) - len(unguarded),
        "injected_css_links": injected_css,
        "injected_js_links": injected_js,
        "injected_theme_meta": theme_meta,
        "target_page_found": target.exists(),
        "target_sentence_found": target_sentence in target_text,
        "failures": failures,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "contrast-audit-v11.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if failures:
        raise SystemExit("\n".join(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
