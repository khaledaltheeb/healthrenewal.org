from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

MARKER_CSS = "v11 — global readable contrast layer"
MARKER_JS = "v11 — runtime contrast guard"
MARKER_HERO_HEADER = "v282 — deterministic black hero/header text contract"
VERIFY_NAME = "google644f1f7a8b7aaa2b.html"
HERO_HEADER_ASSET = "hero-header-black-v282.css"


def inject_before(text: str, closing: str, addition: str) -> str:
    if closing in text:
        return text.replace(closing, f"{addition}\n{closing}", 1)
    return text + "\n" + addition + "\n"


def remove_existing_hero_header_links(text: str) -> str:
    pattern = re.compile(
        r"\s*<link\b[^>]*href=[\"'][^\"']*hero-header-black-v282\.css(?:\?[^\"']*)?[\"'][^>]*>\s*",
        flags=re.IGNORECASE,
    )
    return pattern.sub("\n", text)


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    repo = Path(__file__).resolve().parents[1]
    css_source = repo / "content" / "accessibility" / "contrast-v11.css"
    hero_header_source = repo / "content" / "accessibility" / HERO_HEADER_ASSET
    js_source = repo / "content" / "accessibility" / "contrast-guard-v11.js"
    css_target = site / "assets" / "css" / "theme-v10.css"
    hero_header_target = site / "assets" / "css" / HERO_HEADER_ASSET
    js_target = site / "assets" / "js" / "app-v10.js"

    for required in (site, css_source, hero_header_source, js_source, css_target, js_target):
        if not required.exists():
            raise SystemExit(f"Missing required path: {required}")

    css_payload = css_source.read_text(encoding="utf-8")
    hero_header_payload = hero_header_source.read_text(encoding="utf-8")
    js_payload = js_source.read_text(encoding="utf-8")
    current_css = css_target.read_text(encoding="utf-8")
    current_js = js_target.read_text(encoding="utf-8")

    if MARKER_CSS not in current_css:
        current_css = current_css.rstrip() + "\n\n" + css_payload.rstrip() + "\n"
    css_target.write_text(current_css, encoding="utf-8")

    # Publish the hero/header contract as a dedicated final-cascade asset. Appending
    # it to theme-v10.css is insufficient on legacy pages that load another
    # stylesheet after theme-v10.css.
    hero_header_target.parent.mkdir(parents=True, exist_ok=True)
    hero_header_target.write_text(hero_header_payload.rstrip() + "\n", encoding="utf-8")

    if MARKER_JS not in current_js:
        js_target.write_text(current_js.rstrip() + "\n\n" + js_payload.rstrip() + "\n", encoding="utf-8")

    site_base = os.environ.get("SITE_BASE", "https://khaledaltheeb.github.io/pterminology-site/")
    base_path = urlparse(site_base).path.rstrip("/") + "/"
    css_url = f"{base_path}assets/css/theme-v10.css"
    hero_header_url = f"{base_path}assets/css/{HERO_HEADER_ASSET}"
    js_url = f"{base_path}assets/js/app-v10.js"

    html_files = sorted(site.rglob("*.html"))
    content_files = [p for p in html_files if p.name != VERIFY_NAME]
    injected_css = 0
    injected_hero_header_css = 0
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

        # Remove stale/duplicate copies, then inject immediately before </head> so
        # this stylesheet is the final author stylesheet in every generated page.
        without_contract = remove_existing_hero_header_links(text)
        if without_contract != text:
            text = without_contract
            changed = True
        text = inject_before(
            text,
            "</head>",
            f'<link rel="stylesheet" href="{hero_header_url}" data-hero-header-black-contract="v282">',
        )
        injected_hero_header_css += 1
        changed = True

        if changed:
            page.write_text(text, encoding="utf-8")

    target = site / "terms" / "psychological-well-being" / "index.html"
    target_text = target.read_text(encoding="utf-8") if target.exists() else ""
    target_sentence = "خبرة واسعة تشمل الرضا والمعنى والقدرة على إدارة الانفعالات وبناء علاقات داعمة."

    failures: list[str] = []
    rendered_css = css_target.read_text(encoding="utf-8")
    rendered_hero_header_css = hero_header_target.read_text(encoding="utf-8")
    if MARKER_CSS not in rendered_css:
        failures.append("contrast CSS marker missing")
    if MARKER_HERO_HEADER not in rendered_hero_header_css:
        failures.append("hero/header black CSS marker missing")
    if "--hero-header-text-v282: #000000" not in rendered_hero_header_css:
        failures.append("hero/header pure-black token missing")

    descendant_contract = ") * {\n  color: var(--hero-header-text-v282) !important;"
    if descendant_contract not in hero_header_payload:
        failures.append("hero/header descendant coverage missing")
    if "-webkit-text-fill-color: var(--hero-header-text-v282) !important;" not in hero_header_payload:
        failures.append("hero/header text-fill coverage missing")

    if MARKER_JS not in js_target.read_text(encoding="utf-8"):
        failures.append("contrast JS marker missing")
    if not target.exists():
        failures.append("psychological well-being page missing")
    elif target_sentence not in target_text:
        failures.append("target sentence missing from psychological well-being page")

    unstyled = []
    unguarded = []
    missing_final_contract = []
    duplicate_contract = []
    for page in content_files:
        text = page.read_text(encoding="utf-8", errors="strict")
        if "theme-v10.css" not in text:
            unstyled.append(str(page.relative_to(site)))
        if "app-v10.js" not in text:
            unguarded.append(str(page.relative_to(site)))
        matches = list(re.finditer(r"<link\b[^>]*hero-header-black-v282\.css[^>]*>", text, re.IGNORECASE))
        if len(matches) != 1:
            duplicate_contract.append(str(page.relative_to(site)))
        elif "</head>" in text and matches[0].end() > text.index("</head>"):
            missing_final_contract.append(str(page.relative_to(site)))
        elif re.search(r"<link\b[^>]*rel=[\"']stylesheet[\"'][^>]*>", text[matches[0].end(): text.index("</head>")], re.IGNORECASE):
            missing_final_contract.append(str(page.relative_to(site)))
    if unstyled:
        failures.append(f"pages without theme CSS: {len(unstyled)}")
    if unguarded:
        failures.append(f"pages without contrast guard JS: {len(unguarded)}")
    if duplicate_contract:
        failures.append(f"pages without exactly one hero/header contract link: {len(duplicate_contract)}")
    if missing_final_contract:
        failures.append(f"pages where hero/header contract is not final stylesheet: {len(missing_final_contract)}")

    report = {
        "version": "v282-hero-header-black",
        "html_pages": len(html_files),
        "content_pages": len(content_files),
        "pages_with_theme": len(content_files) - len(unstyled),
        "pages_with_guard": len(content_files) - len(unguarded),
        "pages_with_final_hero_header_contract": len(content_files) - len(set(duplicate_contract + missing_final_contract)),
        "injected_css_links": injected_css,
        "injected_hero_header_css_links": injected_hero_header_css,
        "injected_js_links": injected_js,
        "injected_theme_meta": theme_meta,
        "hero_header_contract": "rgb(0, 0, 0)",
        "hero_header_layer_present": MARKER_HERO_HEADER in rendered_hero_header_css,
        "hero_header_asset": f"assets/css/{HERO_HEADER_ASSET}",
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
