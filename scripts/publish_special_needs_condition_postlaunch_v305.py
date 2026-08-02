#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "content" / "v305" / "special-needs-condition-postlaunch-ar.json"
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
VERSION = 305
SLUGS = ("autism", "down-syndrome")
WORD_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
ID_RE = re.compile(r'\bid="([^"]+)"')
HREF_RE = re.compile(r'\bhref="([^"]+)"')
META_MARKER = "condition-postlaunch-v305-meta"
BREADCRUMB_MARKER = "condition-postlaunch-v305-breadcrumbs"
CONTENT_MARKER = "condition-postlaunch-v305-content"
STYLE_MARKER = "condition-postlaunch-v305-style"
INTENTIONAL_SHARED_ROUTE = BASE_PATH + "special-needs/early-intervention-family-action-plan/"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON object required: {path}")
    return payload


def load_config() -> dict[str, Any]:
    data = read_json(CONFIG)
    if data.get("version") != VERSION or data.get("language") != "ar":
        raise SystemExit("Post-launch configuration contract failed")
    conditions = data.get("conditions")
    if not isinstance(conditions, dict) or set(conditions) != set(SLUGS):
        raise SystemExit("Post-launch condition routes are incomplete")
    common = data.get("common_guides")
    policy = data.get("provider_policy")
    if not isinstance(common, list) or len(common) < 3:
        raise SystemExit("At least three common guides are required")
    if not isinstance(policy, dict) or len(policy.get("points", [])) < 4:
        raise SystemExit("Provider transparency policy is incomplete")

    condition_hrefs: dict[str, list[str]] = {}
    for slug in SLUGS:
        item = conditions[slug]
        if not isinstance(item, dict):
            raise SystemExit(f"Invalid condition configuration: {slug}")
        if len(item.get("how_to_use", [])) < 4 or len(item.get("related_guides", [])) < 4:
            raise SystemExit(f"Post-launch depth contract failed: {slug}")
        hrefs = [str(link.get("href", "")) for link in item["related_guides"]]
        if len(hrefs) != len(set(hrefs)):
            raise SystemExit(f"Duplicate condition-specific guide route: {slug}")
        condition_hrefs[slug] = hrefs

    common_hrefs = [str(link.get("href", "")) for link in common]
    if len(common_hrefs) != len(set(common_hrefs)):
        raise SystemExit("Duplicate common guide route")
    all_hrefs = [*condition_hrefs["autism"], *condition_hrefs["down-syndrome"], *common_hrefs]
    if any(not href.startswith(BASE_PATH) or not href.endswith("/") for href in all_hrefs):
        raise SystemExit("All internal guide links must be site-relative directory routes")
    counts = Counter(all_hrefs)
    duplicates = {href: count for href, count in counts.items() if count > 1}
    if duplicates != {INTENTIONAL_SHARED_ROUTE: 2}:
        raise SystemExit(f"Unexpected cross-condition guide duplication: {duplicates}")
    if any(href in common_hrefs for href in condition_hrefs["autism"] + condition_hrefs["down-syndrome"]):
        raise SystemExit("Common guides must not be repeated inside condition-specific lists")
    return data


def marked(kind: str, body: str) -> str:
    return f"<!-- {kind}:start -->{body}<!-- {kind}:end -->"


def replace_marked(source: str, kind: str, block: str) -> tuple[str, bool]:
    start, end = f"<!-- {kind}:start -->", f"<!-- {kind}:end -->"
    if source.count(start) != source.count(end):
        raise SystemExit(f"Unbalanced marker: {kind}")
    if start not in source:
        return source, False
    source, count = re.subn(re.escape(start) + r".*?" + re.escape(end), block, source, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Could not replace marker: {kind}")
    return source, True


def insert_before(source: str, kind: str, block: str, anchor: str) -> str:
    source, replaced = replace_marked(source, kind, block)
    if replaced:
        return source
    if source.count(anchor) != 1:
        raise SystemExit(f"Insertion anchor must occur once for {kind}: {anchor}")
    return source.replace(anchor, block + anchor, 1)


def insert_before_regex(source: str, kind: str, block: str, pattern: str) -> str:
    source, replaced = replace_marked(source, kind, block)
    if replaced:
        return source
    match = re.search(pattern, source, re.I | re.S)
    if not match:
        raise SystemExit(f"Regex insertion anchor missing for {kind}: {pattern}")
    return source[: match.start()] + block + source[match.start() :]


def extract(source: str, pattern: str, label: str) -> str:
    match = re.search(pattern, source, re.I | re.S)
    if not match:
        raise SystemExit(f"Missing {label} in generated condition page")
    return html.unescape(match.group(1).strip())


def route_target(site: Path, href: str) -> Path:
    return site / href[len(BASE_PATH) :].strip("/") / "index.html"


def validate_routes(site: Path, links: list[dict[str, Any]], slug: str) -> None:
    hrefs = [str(item.get("href", "")) for item in links]
    if len(hrefs) != len(set(hrefs)):
        raise SystemExit(f"Duplicate related route in {slug}")
    missing = [href for href in hrefs if not route_target(site, href).is_file()]
    if missing:
        raise SystemExit(f"Related routes are not generated for {slug}: {missing}")
    for item in links:
        if not str(item.get("label", "")).strip() or not str(item.get("summary", "")).strip():
            raise SystemExit(f"Related guide labels and summaries are required: {slug}")


def render_meta(title: str, description: str, image: str, reviewed_at: str) -> str:
    body = (
        '<meta name="theme-color" content="#0d5f61"><meta name="color-scheme" content="light">'
        '<meta name="referrer" content="strict-origin-when-cross-origin"><meta property="og:locale" content="ar_AR">'
        f'<meta property="article:modified_time" content="{esc(reviewed_at)}">'
        '<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}">'
        f'<meta name="twitter:image" content="{esc(image)}">'
    )
    return marked(META_MARKER, body)


def render_style() -> str:
    css = """
:where(h1,h2,h3,[id]){scroll-margin-top:6.5rem}:focus-visible{outline:3px solid #8b2f5b;outline-offset:3px;border-radius:.25rem}
.breadcrumbs{padding:.75rem 0;border-bottom:1px solid #c6e2df;background:#f7fcfb}.breadcrumbs ol{display:flex;gap:.45rem;flex-wrap:wrap;list-style:none;padding:0;margin:0}
.breadcrumbs li:not(:last-child)::after{content:'←';margin-inline-start:.45rem;color:#607b7d}.breadcrumbs a{text-decoration:none;font-weight:800}
.postlaunch{padding:1rem 0 2.5rem}.postlaunch-grid{display:grid;grid-template-columns:1fr 1.25fr;gap:1rem;align-items:start}
.use-card,.policy-card,.related-card{background:#fff;border:1px solid #c6e2df;border-radius:18px;padding:1.1rem;box-shadow:0 12px 28px #104c4c14}
.use-card ol,.policy-card ul{margin-block-end:0}.related-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.8rem}
.related-card{display:flex;flex-direction:column;min-height:100%}.related-card h3{font-size:1.05rem;line-height:1.5;margin:.1rem 0 .45rem}
.related-card p{color:#506d70;margin:.1rem 0 .85rem}.related-card a{margin-top:auto;font-weight:900}
.audit-badge{display:inline-flex;gap:.35rem;align-items:center;border:1px solid #99cbc5;background:#eefaf7;border-radius:999px;padding:.2rem .65rem;font-size:.86rem;font-weight:900}
.policy-card{margin-top:1rem;border-inline-start:6px solid #8b2f5b}@media(max-width:820px){.postlaunch-grid,.related-grid{grid-template-columns:1fr}}
@media print{.breadcrumbs,.audit-badge{display:none}.postlaunch-grid,.related-grid{display:block}.use-card,.policy-card,.related-card{box-shadow:none;margin-bottom:.8rem}}
""".strip()
    return marked(STYLE_MARKER, f"<style>{css}</style>")


def render_breadcrumbs(slug: str, label: str) -> str:
    del slug
    body = (
        '<nav class="breadcrumbs" aria-label="مسار التنقل"><div class="wrap"><ol>'
        f'<li><a href="{BASE_PATH}">الرئيسية</a></li><li><a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a></li>'
        f'<li><span aria-current="page">{esc(label)}</span></li></ol></div></nav>'
    )
    return marked(BREADCRUMB_MARKER, body)


def guide_cards(links: list[dict[str, Any]]) -> str:
    return "".join(
        '<article class="related-card">'
        f'<h3>{esc(item["label"])}</h3><p>{esc(item["summary"])}</p>'
        f'<a href="{esc(item["href"])}">فتح الدليل العملي</a></article>'
        for item in links
    )


def render_content(config: dict[str, Any], slug: str) -> str:
    condition = config["conditions"][slug]
    steps = "".join(f"<li>{esc(item)}</li>" for item in condition["how_to_use"])
    links = [*condition["related_guides"], *config["common_guides"]]
    policy = config["provider_policy"]
    policy_points = "".join(f"<li>{esc(item)}</li>" for item in policy["points"])
    body = f'''
<section class="postlaunch" id="use-this-guide" aria-labelledby="use-this-guide-title"><div class="wrap">
<p class="audit-badge">تدقيق تقني وربط داخلي v{VERSION} · {esc(config["reviewed_at"])}</p><div class="postlaunch-grid">
<section class="use-card"><p class="kicker">طريقة استخدام عملية</p><h2 id="use-this-guide-title">كيف تستخدم هذا الدليل دون تشخيص ذاتي؟</h2><ol>{steps}</ol></section>
<section aria-labelledby="related-guides-title"><p class="kicker">مسارات مترابطة</p><h2 id="related-guides-title">أدلة عملية مرتبطة بالحاجة اليومية</h2><div class="related-grid">{guide_cards(links)}</div></section>
</div><aside class="policy-card" id="provider-listing-policy" aria-labelledby="provider-policy-title"><p class="kicker">شفافية الدليل المحلي</p>
<h2 id="provider-policy-title">{esc(policy["title"])}</h2><ul>{policy_points}</ul></aside></div></section>
'''.strip()
    return marked(CONTENT_MARKER, body)


def visible_word_count(source: str) -> int:
    return len(WORD_RE.findall(html.unescape(re.sub(r"<[^>]+>", " ", source))))


def validate_page(site: Path, slug: str, source: str, expected_links: list[dict[str, Any]]) -> dict[str, Any]:
    required = (
        f"<!-- {META_MARKER}:start -->", f"<!-- {BREADCRUMB_MARKER}:start -->",
        f"<!-- {CONTENT_MARKER}:start -->", f"<!-- {STYLE_MARKER}:start -->",
        'name="twitter:card"', 'property="og:locale"', 'name="referrer"',
        'aria-label="مسار التنقل"', 'aria-current="page"', 'id="provider-listing-policy"', ":focus-visible",
    )
    missing = [item for item in required if item not in source]
    if missing:
        raise SystemExit(f"Post-launch markers missing for {slug}: {missing}")
    if source.count("<h1") != 1:
        raise SystemExit(f"Exactly one H1 is required: {slug}")
    ids = ID_RE.findall(source)
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise SystemExit(f"Duplicate HTML ids in {slug}: {duplicates}")
    injected_hrefs = [item["href"] for item in expected_links]
    missing_links = [href for href in injected_hrefs if source.count(f'href="{href}"') != 1]
    if missing_links:
        raise SystemExit(f"Injected internal links missing or duplicated in {slug}: {missing_links}")
    unresolved = [href for href in injected_hrefs if not route_target(site, href).is_file()]
    if unresolved:
        raise SystemExit(f"Injected internal links are unresolved in {slug}: {unresolved}")
    if 'target="_blank"' in source:
        raise SystemExit(f"Unnecessary new-window behavior detected: {slug}")
    return {
        "slug": slug, "path": f"special-needs/{slug}/index.html", "words": visible_word_count(source),
        "h2": len(re.findall(r"<h2\b", source)), "html_ids": len(ids), "related_link_count": len(injected_hrefs),
        "meta_enhanced": True, "visible_breadcrumbs": True, "provider_policy_visible": True, "focus_visibility_guard": True,
    }


def enhance_page(site: Path, config: dict[str, Any], slug: str) -> dict[str, Any]:
    path = site / "special-needs" / slug / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing condition page for post-launch enhancement: {path}")
    source = path.read_text(encoding="utf-8")
    title = extract(source, r"<title>(.*?)</title>", "title")
    description = extract(source, r'<meta\s+name="description"\s+content="([^"]+)"', "meta description")
    image = extract(source, r'<meta\s+property="og:image"\s+content="([^"]+)"', "Open Graph image")
    condition = config["conditions"][slug]
    links = [*condition["related_guides"], *config["common_guides"]]
    validate_routes(site, links, slug)
    source = insert_before(source, META_MARKER, render_meta(title, description, image, config["reviewed_at"]), "</head>")
    source = insert_before(source, STYLE_MARKER, render_style(), "</head>")
    source = insert_before(source, BREADCRUMB_MARKER, render_breadcrumbs(slug, condition["label"]), '<section class="hero">')
    source = insert_before_regex(source, CONTENT_MARKER, render_content(config, slug), r'<section\b[^>]*\bid="directory"[^>]*>')
    report = validate_page(site, slug, source, links)
    path.write_text(source, encoding="utf-8")
    return report


def publish(site: Path) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    config = load_config()
    pages = [enhance_page(site, config, slug) for slug in SLUGS]
    report = {
        "version": VERSION, "status": "passed", "reviewed_at": config["reviewed_at"],
        "condition_count": len(pages), "condition_slugs": list(SLUGS),
        "generated_pages": [item["path"] for item in pages],
        "minimum_words": min(item["words"] for item in pages), "minimum_h2": min(item["h2"] for item in pages),
        "related_link_count": sum(item["related_link_count"] for item in pages),
        "visible_breadcrumbs": True, "meta_enhanced": True, "provider_policy_visible": True,
        "focus_visibility_guard": True, "config_source": CONFIG.relative_to(ROOT).as_posix(), "pages": pages,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-condition-postlaunch-v305.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
