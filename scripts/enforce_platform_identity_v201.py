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
BASE_PATH = "/pterminology-site/"
VERIFY_FILE = "google644f1f7a8b7aaa2b.html"

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
.platform-shell-v201-name{{display:grid;line-height:1.35}}
.platform-shell-v201-name small{{font-weight:700;color:#567477}}
.platform-shell-v201-nav{{display:flex;gap:8px;flex-wrap:wrap}}
.platform-shell-v201-nav a{{color:#086e69;text-decoration:none;font-weight:800;padding:6px 8px;border-radius:9px}}
.platform-shell-v201-nav a:focus-visible{{outline:3px solid #168f88;outline-offset:2px}}
.platform-shell-v201-footer{{margin-top:34px;border-top:1px solid #c9e9e5;background:#f7fcfb;padding:24px max(4vw,18px);color:#496d70}}
.platform-shell-v201-footer p{{margin:.35rem 0}}
@media(max-width:760px){{.platform-shell-v201-header{{align-items:flex-start;flex-direction:column}}}}
@media print{{.platform-shell-v201-header,.platform-shell-v201-footer{{box-shadow:none;background:#fff}}}}
</style>
""".strip()

HEADER = f"""<header class="platform-shell-v201 platform-shell-v201-header" data-platform-shell="header">
<a class="platform-shell-v201-brand" href="{BASE_PATH}"><span class="platform-shell-v201-mark" aria-hidden="true">ن</span><span class="platform-shell-v201-name">{BRAND}<small>{SLOGAN}</small></span></a>
<nav class="platform-shell-v201-nav" aria-label="التنقل المؤسسي"><a href="{BASE_PATH}start-here/">ابدأ من هنا</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}tips/">النصائح</a><a href="{BASE_PATH}care-guides/">أدلة التعامل</a><a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a></nav>
</header>"""

FOOTER = f"""<footer class="platform-shell-v201 platform-shell-v201-footer" data-platform-shell="footer"><p><strong>{BRAND}</strong> — {SLOGAN}</p><p>الاسم المؤسس: {FOUNDER}. المحتوى للتثقيف والدعم العام ولا يستبدل التقييم أو الرعاية المهنية الفردية.</p><p><a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}partners/">الشركاء والشفافية</a> · <a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة والتربية الدامجة</a></p></footer>"""


def run_script(name: str, site: Path) -> None:
    script = Path(__file__).with_name(name)
    if not script.is_file():
        raise SystemExit(f"Missing required publisher: {script}")
    subprocess.run([sys.executable, str(script), str(site)], check=True)


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
    return re.sub(r"</head>", SHELL_STYLE + "</head>", text, count=1, flags=re.I), True


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
            lambda match: match.group(1) + html.escape(value, quote=True) + match.group(3),
            text,
        )
        replacements += count
    return text, replacements


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")

    run_script("publish_tips_hub_v234.py", site)
    run_script("verify_tips_v234.py", site)
    run_script("publish_trust_guides_v201.py", site)
    run_script("finalize_trust_guides_links_v201.py", site)

    special_needs_published = False
    special_needs_accessibility_finalized = False
    if (site / "special-needs").is_dir():
        run_script("publish_special_needs_hub_v201.py", site)
        run_script("finalize_special_needs_hub_accessibility_v201.py", site)
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
        "tips_v234_published": True,
        "tips_v234_report": "api/tips-audit-v234.json",
        "tips_v234_verification": "api/tips-verification-v234.json",
        "trust_guides_published": True,
        "trust_guides_links_finalized": True,
        "trust_guides_report": "api/trust-guides-v201.json",
        "special_needs_hub_published": special_needs_published,
        "special_needs_hub_accessibility_finalized": special_needs_accessibility_finalized,
        "special_needs_hub_report": "api/special-needs-hub-v201.json" if special_needs_published else None,
        "remaining_banned_pages": [],
        "missing_header_pages": [],
        "missing_footer_pages": [],
        "content_targets_report": "api/content-targets-v201.json",
    }

    for page in sorted(site.rglob("*.html")):
        if page.name == VERIFY_FILE:
            continue
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
        text, count = update_brand_metadata(text)
        stats["brand_metadata_updates"] += count
        page.write_text(text, encoding="utf-8")

        relative = page.relative_to(site).as_posix()
        if BANNED_RE.search(text):
            stats["remaining_banned_pages"].append(relative)
        if not re.search(r"<header\b", text, re.I):
            stats["missing_header_pages"].append(relative)
        if not re.search(r"<footer\b", text, re.I):
            stats["missing_footer_pages"].append(relative)

    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    report = api / "platform-identity-v201.json"
    report.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    if stats["remaining_banned_pages"]:
        raise SystemExit(f"Banned person-label language remains in: {stats['remaining_banned_pages'][:20]}")
    if stats["missing_header_pages"] or stats["missing_footer_pages"]:
        raise SystemExit(
            f"Site shell incomplete: headers={stats['missing_header_pages'][:20]}, "
            f"footers={stats['missing_footer_pages'][:20]}"
        )

    run_script("audit_content_targets_v201.py", site)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
