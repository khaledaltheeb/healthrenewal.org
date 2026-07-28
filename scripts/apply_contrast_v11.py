from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

MARKER_CSS = "v11 — global readable contrast layer"
MARKER_JS = "v11 — runtime contrast guard"
MARKER_HERO_HEADER_CSS = "v283 — adaptive hero/header contrast contract"
MARKER_HERO_HEADER_JS = "v283 — computed-style hero/header contrast guard"
VERIFY_NAME = "google644f1f7a8b7aaa2b.html"
HERO_HEADER_CSS_ASSET = "hero-header-contrast-v283.css"
HERO_HEADER_JS_ASSET = "hero-header-contrast-v283.js"
LEGACY_HERO_HEADER_ASSET = "hero-header-black-v282.css"


def inject_before(text: str, closing: str, addition: str) -> str:
    if closing in text:
        return text.replace(closing, f"{addition}\n{closing}", 1)
    return text + "\n" + addition + "\n"


def remove_asset_tags(text: str) -> str:
    patterns = (
        rf"\s*<link\b[^>]*href=[\"'][^\"']*(?:{re.escape(LEGACY_HERO_HEADER_ASSET)}|{re.escape(HERO_HEADER_CSS_ASSET)})(?:\?[^\"']*)?[\"'][^>]*>\s*",
        rf"\s*<script\b[^>]*src=[\"'][^\"']*{re.escape(HERO_HEADER_JS_ASSET)}(?:\?[^\"']*)?[\"'][^>]*>\s*</script>\s*",
    )
    for pattern in patterns:
        text = re.sub(pattern, "\n", text, flags=re.IGNORECASE)
    return text


def replace_marked_iife(text: str, marker: str, payload: str) -> tuple[str, bool]:
    """Replace one previously appended marker IIFE without deleting later bundle code."""
    marker_at = text.find(marker)
    if marker_at < 0:
        return text.rstrip() + "\n\n" + payload.rstrip() + "\n", False

    comment_at = text.rfind("/*", 0, marker_at + 1)
    if comment_at < 0:
        raise SystemExit(f"Unable to locate opening comment for runtime marker: {marker}")

    closing = re.search(r"\n\}\)\(\);(?:\r?\n)?", text[marker_at:])
    if not closing:
        raise SystemExit(f"Unable to locate IIFE terminator for runtime marker: {marker}")

    block_end = marker_at + closing.end()
    refreshed = text[:comment_at].rstrip() + "\n\n" + payload.rstrip() + "\n" + text[block_end:].lstrip("\r\n")
    return refreshed, True


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    repo = Path(__file__).resolve().parents[1]
    css_source = repo / "content" / "accessibility" / "contrast-v11.css"
    hero_header_css_source = repo / "content" / "accessibility" / HERO_HEADER_CSS_ASSET
    hero_header_js_source = repo / "content" / "accessibility" / HERO_HEADER_JS_ASSET
    js_source = repo / "content" / "accessibility" / "contrast-guard-v11.js"
    css_target = site / "assets" / "css" / "theme-v10.css"
    hero_header_css_target = site / "assets" / "css" / HERO_HEADER_CSS_ASSET
    hero_header_js_target = site / "assets" / "js" / HERO_HEADER_JS_ASSET
    legacy_target = site / "assets" / "css" / LEGACY_HERO_HEADER_ASSET
    js_target = site / "assets" / "js" / "app-v10.js"

    required = (
        site,
        css_source,
        hero_header_css_source,
        hero_header_js_source,
        js_source,
        css_target,
        js_target,
    )
    for path in required:
        if not path.exists():
            raise SystemExit(f"Missing required path: {path}")

    css_payload = css_source.read_text(encoding="utf-8")
    hero_header_css_payload = hero_header_css_source.read_text(encoding="utf-8")
    hero_header_js_payload = hero_header_js_source.read_text(encoding="utf-8")
    js_payload = js_source.read_text(encoding="utf-8")
    current_css = css_target.read_text(encoding="utf-8")
    current_js = js_target.read_text(encoding="utf-8")

    if MARKER_CSS not in current_css:
        current_css = current_css.rstrip() + "\n\n" + css_payload.rstrip() + "\n"
    css_target.write_text(current_css, encoding="utf-8")

    current_js, refreshed_base_guard = replace_marked_iife(current_js, MARKER_JS, js_payload)
    js_target.write_text(current_js, encoding="utf-8")

    hero_header_css_target.parent.mkdir(parents=True, exist_ok=True)
    hero_header_js_target.parent.mkdir(parents=True, exist_ok=True)
    hero_header_css_target.write_text(hero_header_css_payload.rstrip() + "\n", encoding="utf-8")
    hero_header_js_target.write_text(hero_header_js_payload.rstrip() + "\n", encoding="utf-8")
    if legacy_target.exists():
        legacy_target.unlink()

    site_base = os.environ.get("SITE_BASE", "https://khaledaltheeb.github.io/pterminology-site/")
    base_path = urlparse(site_base).path.rstrip("/") + "/"
    css_url = f"{base_path}assets/css/theme-v10.css"
    hero_header_css_url = f"{base_path}assets/css/{HERO_HEADER_CSS_ASSET}"
    js_url = f"{base_path}assets/js/app-v10.js"
    hero_header_js_url = f"{base_path}assets/js/{HERO_HEADER_JS_ASSET}"

    html_files = sorted(site.rglob("*.html"))
    content_files = [page for page in html_files if page.name != VERIFY_NAME]
    injected_css = 0
    injected_hero_header_css = 0
    injected_js = 0
    injected_hero_header_js = 0
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

        cleaned = remove_asset_tags(text)
        if cleaned != text:
            text = cleaned
            changed = True

        text = inject_before(
            text,
            "</head>",
            f'<link rel="stylesheet" href="{hero_header_css_url}" data-hero-header-contrast="v283">',
        )
        injected_hero_header_css += 1
        changed = True

        text = inject_before(
            text,
            "</body>",
            f'<script src="{hero_header_js_url}" data-hero-header-contrast="v283" defer></script>',
        )
        injected_hero_header_js += 1
        changed = True

        if changed:
            page.write_text(text, encoding="utf-8")

    target = site / "terms" / "psychological-well-being" / "index.html"
    target_text = target.read_text(encoding="utf-8") if target.exists() else ""
    target_sentence = "خبرة واسعة تشمل الرضا والمعنى والقدرة على إدارة الانفعالات وبناء علاقات داعمة."

    failures: list[str] = []
    rendered_css = css_target.read_text(encoding="utf-8")
    rendered_hero_header_css = hero_header_css_target.read_text(encoding="utf-8")
    rendered_hero_header_js = hero_header_js_target.read_text(encoding="utf-8")
    rendered_base_js = js_target.read_text(encoding="utf-8")

    if MARKER_CSS not in rendered_css:
        failures.append("contrast CSS marker missing")
    if MARKER_HERO_HEADER_CSS not in rendered_hero_header_css:
        failures.append("adaptive hero/header CSS marker missing")
    if MARKER_HERO_HEADER_JS not in rendered_hero_header_js:
        failures.append("adaptive hero/header JS marker missing")
    if "--hh-on-light" not in rendered_hero_header_css or "--hh-on-dark" not in rendered_hero_header_css:
        failures.append("adaptive hero/header surface tokens missing")
    if "currentRatio" not in rendered_hero_header_js:
        failures.append("computed contrast logic missing")
    if LEGACY_HERO_HEADER_ASSET in rendered_hero_header_css:
        failures.append("legacy black contract leaked into adaptive CSS")
    if rendered_base_js.count(MARKER_JS) != 1:
        failures.append(f"expected exactly one refreshed base contrast guard, found {rendered_base_js.count(MARKER_JS)}")
    if "v291 clears legacy classes and defers adaptive shell surfaces" not in rendered_base_js:
        failures.append("refreshed adaptive-aware base guard missing from generated app bundle")
    if not target.exists():
        failures.append("psychological well-being page missing")
    elif target_sentence not in target_text:
        failures.append("target sentence missing from psychological well-being page")

    unstyled: list[str] = []
    unguarded: list[str] = []
    invalid_contract: list[str] = []
    legacy_contract: list[str] = []

    css_pattern = re.compile(r"<link\b[^>]*hero-header-contrast-v283\.css[^>]*>", re.IGNORECASE)
    js_pattern = re.compile(r"<script\b[^>]*hero-header-contrast-v283\.js[^>]*>\s*</script>", re.IGNORECASE)

    for page in content_files:
        text = page.read_text(encoding="utf-8", errors="strict")
        if "theme-v10.css" not in text:
            unstyled.append(str(page.relative_to(site)))
        if "app-v10.js" not in text:
            unguarded.append(str(page.relative_to(site)))
        if LEGACY_HERO_HEADER_ASSET in text:
            legacy_contract.append(str(page.relative_to(site)))

        css_matches = list(css_pattern.finditer(text))
        js_matches = list(js_pattern.finditer(text))
        valid_css = len(css_matches) == 1 and ("</head>" not in text or css_matches[0].end() <= text.index("</head>"))
        valid_js = len(js_matches) == 1 and ("</body>" not in text or js_matches[0].end() <= text.index("</body>"))
        if not valid_css or not valid_js:
            invalid_contract.append(str(page.relative_to(site)))

    if unstyled:
        failures.append(f"pages without theme CSS: {len(unstyled)}")
    if unguarded:
        failures.append(f"pages without base contrast guard JS: {len(unguarded)}")
    if invalid_contract:
        failures.append(f"pages without exactly one adaptive hero/header CSS+JS contract: {len(invalid_contract)}")
    if legacy_contract:
        failures.append(f"pages still referencing legacy black contract: {len(legacy_contract)}")

    report = {
        "version": "v292-runtime-refresh",
        "html_pages": len(html_files),
        "content_pages": len(content_files),
        "pages_with_theme": len(content_files) - len(unstyled),
        "pages_with_base_guard": len(content_files) - len(unguarded),
        "pages_with_adaptive_hero_header_contract": len(content_files) - len(invalid_contract),
        "pages_with_legacy_black_contract": len(legacy_contract),
        "base_guard_refreshed": refreshed_base_guard,
        "base_guard_occurrences": rendered_base_js.count(MARKER_JS),
        "injected_css_links": injected_css,
        "injected_hero_header_css_links": injected_hero_header_css,
        "injected_js_links": injected_js,
        "injected_hero_header_js_links": injected_hero_header_js,
        "injected_theme_meta": theme_meta,
        "hero_header_contract": "adaptive WCAG AA: dark text on light surfaces; light text on dark surfaces",
        "hero_header_css_asset": f"assets/css/{HERO_HEADER_CSS_ASSET}",
        "hero_header_js_asset": f"assets/js/{HERO_HEADER_JS_ASSET}",
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
