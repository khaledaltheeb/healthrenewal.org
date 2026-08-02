#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from pathlib import Path

BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
FOUNDER = "مصطلحات علم النفس"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
BASE_PATH = "/"
VERIFY_FILE = "google644f1f7a8b7aaa2b.html"
TOOLS_ROUTE = "tools/index.html"
TOOLS_DESIGN = "marshmallow-v245"
TOOLS_STYLE_ID = "tools-marshmallow-v245-style"

# Unicode-aware \w matches Arabic letters and digits but excludes punctuation
# such as the Arabic comma, so replacements also work after normal punctuation.
REPLACEMENTS = (
    (re.compile(r"(?<!\w)المعاقين(?!\w)"), "ذوي الاحتياجات الخاصة"),
    (re.compile(r"(?<!\w)معاقين(?!\w)"), "ذوي الاحتياجات الخاصة"),
    (re.compile(r"(?<!\w)المعاقون(?!\w)"), "ذوو الاحتياجات الخاصة"),
    (re.compile(r"(?<!\w)معاقون(?!\w)"), "ذوو الاحتياجات الخاصة"),
    (re.compile(r"(?<!\w)المعاقة(?!\w)"), "شخص من ذوي الاحتياجات الخاصة"),
    (re.compile(r"(?<!\w)معاقة(?!\w)"), "شخص من ذوي الاحتياجات الخاصة"),
    (re.compile(r"(?<!\w)المعاق(?!\w)"), "الشخص ذو الاحتياجات الخاصة"),
    (re.compile(r"(?<!\w)معاق(?!\w)"), "شخص ذو احتياجات خاصة"),
)
BANNED_RE = re.compile(
    r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)"
)

SHELL_STYLE = f"""
<style id="platform-shell-v201-style">
.platform-shell-v201{{font-family:Tahoma,Arial,sans-serif;box-sizing:border-box}}
.platform-shell-v201 *{{box-sizing:border-box}}
.platform-shell-v201-header{{background:#fff;border-bottom:1px solid #c9e9e5;padding:12px max(4vw,18px);display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;color:#173f45}}
.platform-shell-v201-brand{{display:flex;align-items:center;gap:10px;text-decoration:none;color:#173f45;font-weight:900}}
.platform-shell-v201-mark{{display:grid;place-items:center;width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#dffaf7,#eee9ff);border:1px solid #a9dcd6;font-size:1.25rem}}
.platform-shell-v201-name{{display:grid;line-height:1.35}}.platform-shell-v201-name small{{font-weight:700;color:#567477}}
.platform-shell-v201-nav{{display:flex;gap:8px;flex-wrap:wrap}}.platform-shell-v201-nav a{{color:#086e69;text-decoration:none;font-weight:800;padding:6px 8px;border-radius:9px}}.platform-shell-v201-nav a:focus-visible{{outline:3px solid #168f88;outline-offset:2px}}
.platform-shell-v201-footer{{margin-top:34px;border-top:1px solid #c9e9e5;background:#f7fcfb;padding:24px max(4vw,18px);color:#496d70}}
.platform-shell-v201-footer p{{margin:.35rem 0}}
@media(max-width:760px){{.platform-shell-v201-header{{align-items:flex-start;flex-direction:column}}}}
@media print{{.platform-shell-v201-header,.platform-shell-v201-footer{{box-shadow:none;background:#fff}}}}
</style>
""".strip()

TOOLS_MARSHMALLOW_STYLE = f"""
<style id="{TOOLS_STYLE_ID}">
html[data-tools-design="{TOOLS_DESIGN}"]{{color-scheme:light!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245{{
  --tm-ink:#173f45;--tm-muted:#4d686b;--tm-brand:#075f5b;--tm-berry:#5b2946;
  --tm-mint:#e5faf5;--tm-mint-line:#b8e4db;--tm-rose:#fff0f5;--tm-rose-line:#f1bfd2;
  --tm-lilac:#f2edff;--tm-lilac-line:#d7caf4;--tm-peach:#fff0e8;--tm-peach-line:#f2cbbb;
  --tm-butter:#fff8d8;--tm-line:#c7e3de;--tm-white:#fff;
  color:var(--tm-ink)!important;
  background:linear-gradient(140deg,#fffafd 0%,var(--tm-mint) 48%,var(--tm-lilac) 100%)!important;
}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(*){{text-shadow:none!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(h1,h2,h3,h4,h5,h6){{color:var(--tm-berry)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(p,li,dd,small,.muted,[class$="-description"],[class$="-summary"]){{color:var(--tm-muted)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(label,legend,dt,strong){{color:var(--tm-ink)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 main :where(
  section,article,aside,form,fieldset,details,dialog,
  .card,.panel,.box,.tile,.tool-card,.resource-card,.feature-card,.result-card,
  [class$="-card"],[class$="-panel"],[class$="-box"],[class$="-tile"]
){{
  background:linear-gradient(145deg,var(--tm-white),var(--tm-mint))!important;
  color:var(--tm-ink)!important;
  border-color:var(--tm-line)!important;
  box-shadow:0 15px 34px rgba(80,151,139,.14)!important;
}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(.grid,.cards,.tools-grid,[class$="-grid"]) > :nth-child(4n+1){{background:linear-gradient(145deg,#fff,var(--tm-rose))!important;border-color:var(--tm-rose-line)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(.grid,.cards,.tools-grid,[class$="-grid"]) > :nth-child(4n+2){{background:linear-gradient(145deg,#fff,var(--tm-mint))!important;border-color:var(--tm-mint-line)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(.grid,.cards,.tools-grid,[class$="-grid"]) > :nth-child(4n+3){{background:linear-gradient(145deg,#fff,var(--tm-lilac))!important;border-color:var(--tm-lilac-line)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(.grid,.cards,.tools-grid,[class$="-grid"]) > :nth-child(4n){{background:linear-gradient(145deg,#fff,var(--tm-peach))!important;border-color:var(--tm-peach-line)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(pre,code,kbd,samp,mark,.tag,.badge,.chip,.pill,[class$="-tag"],[class$="-badge"],[class$="-chip"],[class$="-pill"]){{
  background:var(--tm-lilac)!important;color:#4a315f!important;border-color:var(--tm-lilac-line)!important;
  box-shadow:none!important;text-shadow:none!important;
}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(input,select,textarea){{background:#fff!important;color:var(--tm-ink)!important;border-color:#91c7be!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(button,.button,[role="button"]){{
  background:linear-gradient(145deg,#fff,var(--tm-mint))!important;color:#103f42!important;
  border:2px solid #76cbbf!important;box-shadow:0 5px 0 #d3ece7,0 10px 20px rgba(80,151,139,.12)!important;
}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(a){{color:var(--tm-brand)!important;text-underline-offset:.22em}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(table){{background:#fff!important;color:var(--tm-ink)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(th){{background:var(--tm-lilac)!important;color:#4a315f!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(td){{background:#fff!important;color:var(--tm-ink)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 :where(svg text){{fill:var(--tm-ink)!important}}
body.tools-marshmallow-v245.tools-marshmallow-v245 ::selection{{background:var(--tm-butter);color:#493700}}
@media(prefers-color-scheme:dark){{
  body.tools-marshmallow-v245.tools-marshmallow-v245{{color-scheme:light!important;color:var(--tm-ink)!important;background:linear-gradient(140deg,#fffafd 0%,var(--tm-mint) 48%,var(--tm-lilac) 100%)!important}}
}}
@media(prefers-contrast:more){{
  body.tools-marshmallow-v245.tools-marshmallow-v245 main :where(section,article,aside,form,fieldset,details,dialog,.card,.panel,.box,.tile,[class$="-card"],[class$="-panel"],[class$="-box"],[class$="-tile"]){{background:#fff!important;border-color:currentColor!important;box-shadow:none!important}}
}}
@media print{{body.tools-marshmallow-v245.tools-marshmallow-v245,body.tools-marshmallow-v245.tools-marshmallow-v245 main :where(section,article,aside,form,fieldset,details){{background:#fff!important;color:#000!important;box-shadow:none!important}}}}
</style>
""".strip()

HEADER = f"""<header class="platform-shell-v201 platform-shell-v201-header" data-platform-shell="header">
<a class="platform-shell-v201-brand" href="{BASE_PATH}"><span class="platform-shell-v201-mark" aria-hidden="true">ن</span><span class="platform-shell-v201-name">{BRAND}<small>{SLOGAN}</small></span></a>
<nav class="platform-shell-v201-nav" aria-label="التنقل المؤسسي"><a href="{BASE_PATH}start-here/">ابدأ من هنا</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}tips/">النصائح</a><a href="{BASE_PATH}care-guides/">أدلة التعامل</a><a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a></nav>
</header>"""

FOOTER = f"""<footer class="platform-shell-v201 platform-shell-v201-footer" data-platform-shell="footer"><p><strong>{BRAND}</strong> — {SLOGAN}</p><p>الاسم المؤسس: {FOUNDER}. المحتوى للتثقيف والدعم العام ولا يستبدل التقييم أو الرعاية المهنية الفردية.</p><p><a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}partners/">الشركاء والشفافية</a> · <a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة والتربية الدامجة</a></p></footer>"""


def replace_language(text: str) -> tuple[str, int]:
    changed = 0
    for pattern, replacement in REPLACEMENTS:
        text, count = pattern.subn(replacement, text)
        changed += count
    return text, changed


def insert_after_body(text: str, payload: str) -> str:
    match = re.search(r"<body\b[^>]*>", text, re.I)
    if not match:
        return text
    return text[: match.end()] + payload + text[match.end() :]


def ensure_style(text: str) -> tuple[str, bool]:
    if "platform-shell-v201-style" in text:
        return text, False
    if "</head>" not in text.lower():
        return text, False
    text = re.sub(r"</head>", SHELL_STYLE + "</head>", text, count=1, flags=re.I)
    return text, True


def _add_class_to_body(text: str, class_name: str) -> tuple[str, bool]:
    match = re.search(r"<body\b[^>]*>", text, re.I)
    if not match:
        return text, False
    tag = match.group(0)
    class_match = re.search(r'\bclass\s*=\s*(["\'])(.*?)\1', tag, re.I | re.S)
    if class_match:
        classes = class_match.group(2).split()
        if class_name in classes:
            return text, False
        classes.append(class_name)
        replacement = f'class={class_match.group(1)}{" ".join(classes)}{class_match.group(1)}'
        updated_tag = tag[: class_match.start()] + replacement + tag[class_match.end() :]
    else:
        updated_tag = tag[:-1] + f' class="{class_name}">'
    return text[: match.start()] + updated_tag + text[match.end() :], True


def _element_has_class(text: str, tag_name: str, class_name: str) -> bool:
    match = re.search(fr"<{re.escape(tag_name)}\b[^>]*>", text, re.I | re.S)
    if not match:
        return False
    class_match = re.search(r'\bclass\s*=\s*(["\'])(.*?)\1', match.group(0), re.I | re.S)
    return bool(class_match and class_name in class_match.group(2).split())


def _add_tools_html_marker(text: str) -> tuple[str, bool]:
    match = re.search(r"<html\b[^>]*>", text, re.I)
    if not match:
        return text, False
    tag = match.group(0)
    if re.search(
        rf'\bdata-tools-design\s*=\s*(["\']){re.escape(TOOLS_DESIGN)}\1',
        tag,
        re.I,
    ):
        return text, False
    updated_tag = tag[:-1] + f' data-tools-design="{TOOLS_DESIGN}">'
    return text[: match.start()] + updated_tag + text[match.end() :], True


def ensure_tools_marshmallow(text: str) -> tuple[str, bool]:
    changed = False
    text, updated = _add_tools_html_marker(text)
    changed = changed or updated
    text, updated = _add_class_to_body(text, "tools-marshmallow-v245")
    changed = changed or updated
    if TOOLS_STYLE_ID not in text:
        if "</head>" not in text.lower():
            raise SystemExit("Tools page head is missing; Marshmallow contrast cannot be installed")
        text = re.sub(r"</head>", TOOLS_MARSHMALLOW_STYLE + "</head>", text, count=1, flags=re.I)
        changed = True
    return text, changed


def ensure_header(text: str) -> tuple[str, bool]:
    if re.search(r"<header\b", text, re.I):
        return text, False
    updated = insert_after_body(text, HEADER)
    return updated, updated != text


def ensure_footer(text: str) -> tuple[str, bool]:
    if re.search(r"<footer\b", text, re.I):
        return text, False
    if re.search(r"</body>", text, re.I):
        return re.sub(r"</body>", FOOTER + "</body>", text, count=1, flags=re.I), True
    return text + FOOTER, True


def update_brand_metadata(text: str) -> tuple[str, int]:
    replacements = 0
    patterns = (
        (r'(<meta\s+property=["\']og:site_name["\']\s+content=["\'])(.*?)(["\'])', BRAND),
        (r'("@type"\s*:\s*"Organization"\s*,\s*"name"\s*:\s*")(.*?)(")', BRAND),
        (r'("@type"\s*:\s*"WebSite"\s*,\s*"name"\s*:\s*")(.*?)(")', BRAND),
    )
    for raw, value in patterns:
        pattern = re.compile(raw, re.I | re.S)
        text, count = pattern.subn(
            lambda match: match.group(1) + html.escape(value, quote=True) + match.group(3), text
        )
        replacements += count
    return text, replacements


def publish_magazine(site: Path) -> dict[str, object]:
    publisher = Path(__file__).with_name("publish_magazine_v201.py")
    subprocess.run([sys.executable, str(publisher), str(site)], check=True)
    report_path = site / "api" / "magazine-v201.json"
    if not report_path.is_file():
        raise SystemExit("Magazine production report was not created")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    published = report.get("research_summaries_published")
    if not isinstance(published, int) or published < 1:
        raise SystemExit(f"Magazine production reported an invalid page count: {report}")
    if report.get("unwired_research_pages") != 0:
        raise SystemExit(f"Magazine has unwired pages: {report}")
    index = site / "magazine" / "index.html"
    marker = f'"numberOfItems":{published}'
    if not index.is_file() or marker not in index.read_text(encoding="utf-8"):
        raise SystemExit(f"Magazine production index contract failed for {published} pages")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")

    trust_guides_publisher = Path(__file__).with_name("publish_trust_guides_v201.py")
    subprocess.run([sys.executable, str(trust_guides_publisher), str(site)], check=True)
    trust_guides_link_finalizer = Path(__file__).with_name("finalize_trust_guides_links_v201.py")
    subprocess.run([sys.executable, str(trust_guides_link_finalizer), str(site)], check=True)
    trust_guides_published = True
    trust_guides_links_finalized = True
    section_directory_refreshed = False
    publication_surface_refreshed = False
    if (
        (site / "sections" / "index.html").is_file()
        and (site / "api" / "v1" / "section-directory.json").is_file()
    ):
        section_directory_publisher = Path(__file__).with_name(
            "publish_section_directory_v322.py"
        )
        subprocess.run(
            [sys.executable, str(section_directory_publisher), str(site)],
            check=True,
        )
        section_directory_refreshed = True
        publication_surface_auditor = Path(__file__).with_name(
            "audit_publication_surface_v322.py"
        )
        subprocess.run(
            [sys.executable, str(publication_surface_auditor), str(site)],
            check=True,
        )
        publication_surface_refreshed = True

    magazine_report = publish_magazine(site)

    special_needs_published = False
    special_needs_accessibility_finalized = False
    if (site / "special-needs").is_dir():
        hub_publisher = Path(__file__).with_name("publish_special_needs_hub_v201.py")
        subprocess.run([sys.executable, str(hub_publisher), str(site)], check=True)
        accessibility_finalizer = Path(__file__).with_name(
            "finalize_special_needs_hub_accessibility_v201.py"
        )
        subprocess.run([sys.executable, str(accessibility_finalizer), str(site)], check=True)
        special_needs_published = True
        special_needs_accessibility_finalized = True

    stats = {
        "version": 201,
        "brand": BRAND,
        "slogan": SLOGAN,
        "pages": 0,
        "language_replacements": 0,
        "headers_added": 0,
        "footers_added": 0,
        "styles_added": 0,
        "brand_metadata_updates": 0,
        "tools_marshmallow_route": TOOLS_ROUTE,
        "tools_marshmallow_design": TOOLS_DESIGN,
        "tools_marshmallow_pages": 0,
        "tools_marshmallow_updates": 0,
        "trust_guides_published": trust_guides_published,
        "trust_guides_links_finalized": trust_guides_links_finalized,
        "section_directory_refreshed_after_trust_guides": section_directory_refreshed,
        "publication_surface_refreshed_after_trust_guides": (
            publication_surface_refreshed
        ),
        "trust_guides_report": "api/trust-guides-v201.json",
        "magazine_published": True,
        "magazine_pages": magazine_report["research_summaries_published"],
        "magazine_unwired_pages": magazine_report["unwired_research_pages"],
        "magazine_report": "api/magazine-v201.json",
        "special_needs_hub_published": special_needs_published,
        "special_needs_hub_accessibility_finalized": special_needs_accessibility_finalized,
        "special_needs_hub_report": (
            "api/special-needs-hub-v201.json" if special_needs_published else None
        ),
        "remaining_banned_pages": [],
        "missing_header_pages": [],
        "missing_footer_pages": [],
        "content_targets_report": "api/content-targets-v201.json",
    }
    for page in sorted(site.rglob("*.html")):
        if page.name == VERIFY_FILE:
            continue
        relative = page.relative_to(site).as_posix()
        text = page.read_text(encoding="utf-8")
        stats["pages"] += 1
        text, count = replace_language(text)
        stats["language_replacements"] += count
        text, changed = ensure_header(text)
        stats["headers_added"] += int(changed)
        text, changed = ensure_footer(text)
        stats["footers_added"] += int(changed)
        if 'data-platform-shell="header"' in text or 'data-platform-shell="footer"' in text:
            text, changed = ensure_style(text)
            stats["styles_added"] += int(changed)
        if relative == TOOLS_ROUTE:
            stats["tools_marshmallow_pages"] += 1
            text, changed = ensure_tools_marshmallow(text)
            stats["tools_marshmallow_updates"] += int(changed)
        text, count = update_brand_metadata(text)
        stats["brand_metadata_updates"] += count
        page.write_text(text, encoding="utf-8")
        if BANNED_RE.search(text):
            stats["remaining_banned_pages"].append(relative)
        if not re.search(r"<header\b", text, re.I):
            stats["missing_header_pages"].append(relative)
        if not re.search(r"<footer\b", text, re.I):
            stats["missing_footer_pages"].append(relative)

    tools_page = site / TOOLS_ROUTE
    if tools_page.is_file():
        tools_text = tools_page.read_text(encoding="utf-8")
        required_tools_markers = (
            f'data-tools-design="{TOOLS_DESIGN}"',
            TOOLS_STYLE_ID,
            "--tm-mint:#e5faf5",
            "--tm-rose:#fff0f5",
            "--tm-lilac:#f2edff",
            "color:var(--tm-ink)!important",
        )
        missing = [marker for marker in required_tools_markers if marker not in tools_text]
        if not _element_has_class(tools_text, "body", "tools-marshmallow-v245"):
            missing.append("body class tools-marshmallow-v245")
        if missing:
            raise SystemExit(f"Tools Marshmallow contrast contract is incomplete: {missing}")

    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    report = api / "platform-identity-v201.json"
    report.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    if stats["remaining_banned_pages"]:
        raise SystemExit(
            f"Banned person-label language remains in: {stats['remaining_banned_pages'][:20]}"
        )
    if stats["missing_header_pages"] or stats["missing_footer_pages"]:
        raise SystemExit(
            f"Site shell incomplete: headers={stats['missing_header_pages'][:20]}, "
            f"footers={stats['missing_footer_pages'][:20]}"
        )
    target_audit = Path(__file__).with_name("audit_content_targets_v201.py")
    subprocess.run([sys.executable, str(target_audit), str(site)], check=True)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
