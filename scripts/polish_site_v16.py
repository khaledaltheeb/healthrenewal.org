from __future__ import annotations

import html
import json
import re
import struct
import subprocess
import sys
import zlib
from collections import defaultdict
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
VERIFY = "google644f1f7a8b7aaa2b.html"
BASE_PATH = "/pterminology-site/"
LAB_SLASH_SENTINEL = "__PTERMINOLOGY_LITERAL_SLASH_V198__"
LAB_DEFINITION_PATTERN = re.compile(
    r'(<script\b[^>]*type=["\']application/json["\'][^>]*id=["\']lab-definition["\'][^>]*>)(.*?)(</script>)',
    re.I | re.S,
)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def make_icon(size: int, target: Path) -> None:
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            t = (x + y) / max(1, 2 * size - 2)
            r = int(255 * (1 - t) + 103 * t)
            g = int(226 * (1 - t) + 213 * t)
            b = int(239 * (1 - t) + 205 * t)
            cx, cy = size * 0.5, size * 0.5
            radius = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if radius < size * 0.30:
                r, g, b = 255, 255, 255
            if size * 0.08 < abs(x - cx) < size * 0.12 and y > size * 0.30:
                r, g, b = 32, 123, 122
            if y > size * 0.62 and abs(x - cx) < size * 0.26:
                curve = abs((x - cx) / (size * 0.26))
                if abs(y - (size * (0.67 + 0.10 * curve))) < size * 0.025:
                    r, g, b = 32, 123, 122
            row.extend((r, g, b, 255))
        rows.append(bytes(row))
    raw = b"".join(rows)
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(raw, 9))
    payload += png_chunk(b"IEND", b"")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


def title_from_html(text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(match.group(1))).strip() if match else "هذه الصفحة"


def expand_description(text: str, page_title: str) -> tuple[str, bool]:
    match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']\s*/?>', text, re.I | re.S)
    if not match:
        description = f"{page_title} — محتوى عربي منظم يشرح المفهوم والخطوات العملية والفروق المهمة ومتى تحتاج إلى مساعدة مهنية."
        return text.replace("</head>", f'<meta name="description" content="{html.escape(description, quote=True)}"></head>', 1), True
    old = html.unescape(match.group(1)).strip()
    if len(old) >= 50:
        return text, False
    suffix = " دليل عربي منظم يوضح المفهوم والفروق والخطوات العملية ومتى تحتاج إلى مساعدة مهنية."
    new = (old.rstrip(" .،؛:") + " —" + suffix).strip()
    escaped = html.escape(new, quote=True)
    text = text[:match.start(1)] + escaped + text[match.end(1):]
    for key in ("og:description", "twitter:description"):
        pattern = re.compile(rf'(<meta\s+(?:property|name)=["\']{re.escape(key)}["\']\s+content=["\'])(.*?)(["\']\s*/?>)', re.I | re.S)
        text = pattern.sub(lambda m: m.group(1) + escaped + m.group(3), text, count=1)
    return text, True


def has_meta_key(text: str, key: str, *, attribute: str) -> bool:
    return bool(
        re.search(
            rf'<meta\b[^>]*\b{attribute}\s*=\s*["\']{re.escape(key)}["\'][^>]*>',
            text,
            re.I | re.S,
        )
    )


def inject_social_metadata(text: str, page_title: str) -> tuple[str, int]:
    description_match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']\s*/?>',
        text,
        re.I | re.S,
    )
    description = (
        html.unescape(description_match.group(1)).strip()
        if description_match
        else f"{page_title} — محتوى عربي منظم وموثوق."
    )
    additions: list[str] = []
    fields = (
        ("property", "og:title", page_title),
        ("property", "og:description", description),
        ("property", "og:type", "website"),
        ("name", "twitter:card", "summary"),
        ("name", "twitter:title", page_title),
        ("name", "twitter:description", description),
    )
    for attribute, key, value in fields:
        if has_meta_key(text, key, attribute=attribute):
            continue
        additions.append(
            f'<meta {attribute}="{key}" content="{html.escape(value, quote=True)}">'
        )
    if not additions:
        return text, 0
    if "</head>" not in text:
        raise SystemExit(f"HTML head is not closed while adding social metadata: {page_title}")
    return text.replace("</head>", "".join(additions) + "</head>", 1), len(additions)


def inject_json_ld(text: str, page_title: str) -> tuple[str, bool]:
    if re.search(
        r'<script\b[^>]*type=["\']application/ld\+json["\']',
        text,
        re.I,
    ):
        return text, False
    description_match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']\s*/?>',
        text,
        re.I | re.S,
    )
    description = (
        html.unescape(description_match.group(1)).strip()
        if description_match
        else f"{page_title} — محتوى عربي منظم وموثوق."
    )
    payload = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": page_title,
            "description": description,
            "inLanguage": "ar",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    script = f'<script type="application/ld+json">{payload}</script>'
    if "</head>" not in text:
        raise SystemExit(f"HTML head is not closed while adding JSON-LD: {page_title}")
    return text.replace("</head>", script + "</head>", 1), True


def inject_robots(text: str, *, noindex: bool = False) -> tuple[str, bool]:
    desired = (
        "noindex,follow"
        if noindex
        else "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"
    )
    pattern = re.compile(
        r'(<meta\s+name=["\']robots["\']\s+content=["\'])(.*?)(["\']\s*/?>)',
        re.I | re.S,
    )
    match = pattern.search(text)
    if match:
        current = html.unescape(match.group(2)).strip()
        if current.casefold() == desired.casefold() or (
            noindex and "noindex" in current.casefold()
        ):
            return text, False
        if not noindex:
            return text, False
        escaped = html.escape(desired, quote=True)
        return pattern.sub(
            lambda item: item.group(1) + escaped + item.group(3),
            text,
            count=1,
        ), True
    tag = f'<meta name="robots" content="{desired}">'
    return text.replace("</head>", tag + "</head>", 1), True


def label_inputs(text: str, page_title: str) -> tuple[str, int]:
    count = 0
    pattern = re.compile(r"<input\b([^>]*)>", re.I)

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        attrs = match.group(1)
        if re.search(r"\baria-(?:label|labelledby)\s*=", attrs, re.I):
            return match.group(0)
        kind_match = re.search(r"\btype\s*=\s*['\"]?([^'\"\s>]+)", attrs, re.I)
        kind = kind_match.group(1).lower() if kind_match else "text"
        if kind in {"hidden", "submit", "button", "reset", "radio", "checkbox"}:
            return match.group(0)
        placeholder = re.search(r"\bplaceholder\s*=\s*([" + "'\"" + r"])(.*?)\1", attrs, re.I | re.S)
        name = re.search(r"\bname\s*=\s*([" + "'\"" + r"])(.*?)\1", attrs, re.I | re.S)
        label = (placeholder.group(2) if placeholder else name.group(2) if name else f"حقل إدخال في {page_title}").strip()
        count += 1
        return f'<input aria-label="{html.escape(label, quote=True)}"{attrs}>'

    return pattern.sub(repl, text), count


def label_image_links(text: str) -> tuple[str, int]:
    count = 0
    pattern = re.compile(r"<a\b([^>]*)>(\s*<img\b[^>]*\balt=([\"'])(.*?)\3[^>]*>\s*)</a>", re.I | re.S)

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        attrs, body, _, alt = match.groups()
        if re.search(r"\baria-label\s*=", attrs, re.I):
            return match.group(0)
        count += 1
        return f'<a aria-label="{html.escape(html.unescape(alt), quote=True)}"{attrs}>{body}</a>'

    return pattern.sub(repl, text), count


def defer_scripts(text: str) -> tuple[str, int]:
    count = 0
    pattern = re.compile(r"<script\b([^>]*\bsrc\s*=\s*[^>]+)>", re.I)

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        attrs = match.group(1)
        if re.search(r"\b(?:defer|async)\b", attrs, re.I) or re.search(r"\btype\s*=\s*['\"]module['\"]", attrs, re.I):
            return match.group(0)
        count += 1
        return f"<script defer{attrs}>"

    return pattern.sub(repl, text), count


def add_app_links(text: str) -> tuple[str, bool]:
    if "icon-192.png" in text:
        return text, False
    payload = f'<link rel="icon" type="image/png" sizes="192x192" href="{BASE_PATH}assets/icons/icon-192.png"><link rel="apple-touch-icon" sizes="192x192" href="{BASE_PATH}assets/icons/icon-192.png">'
    return text.replace("</head>", payload + "</head>", 1), True


def fix_duplicate_comparison_titles() -> int:
    pages = sorted((SITE / "comparisons").glob("comparison-*/index.html"))
    groups: dict[str, list[Path]] = defaultdict(list)
    for page in pages:
        text = page.read_text(encoding="utf-8")
        match = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
        if match:
            groups[html.unescape(match.group(1)).strip()].append(page)
    changed = 0
    for full_title, duplicates in groups.items():
        if len(duplicates) < 2:
            continue
        core = full_title.split(" | ", 1)[0]
        for index, page in enumerate(duplicates[1:], start=2):
            text = page.read_text(encoding="utf-8")
            new_core = f"{core} — دليل التمييز العملي {index - 1}"
            new_full = new_core + (" | " + full_title.split(" | ", 1)[1] if " | " in full_title else "")
            text = text.replace(full_title, new_full)
            text = re.sub(r"<h1([^>]*)>.*?</h1>", lambda m: f"<h1{m.group(1)}>{html.escape(new_core)}</h1>", text, count=1, flags=re.I | re.S)
            text = text.replace(core, new_core)
            page.write_text(text, encoding="utf-8")
            changed += 1
    return changed


def transform_literal_lab_slashes(*, protect: bool) -> int:
    source = '"/"' if protect else f'"{LAB_SLASH_SENTINEL}"'
    target = f'"{LAB_SLASH_SENTINEL}"' if protect else '"/"'
    changed = 0
    for folder in ("cognitive-lab", "assessment-lab"):
        root = SITE / folder
        if not root.is_dir():
            continue
        for page in root.rglob("index.html"):
            text = page.read_text(encoding="utf-8")

            def replace_definition(match: re.Match[str]) -> str:
                nonlocal changed
                payload = match.group(2)
                count = payload.count(source)
                if count:
                    changed += count
                    payload = payload.replace(source, target)
                return match.group(1) + payload + match.group(3)

            updated = LAB_DEFINITION_PATTERN.sub(replace_definition, text)
            if updated != text:
                page.write_text(updated, encoding="utf-8")
    return changed


def main() -> None:
    if not SITE.exists():
        raise SystemExit(f"Missing site directory: {SITE}")
    icons = SITE / "assets" / "icons"
    make_icon(192, icons / "icon-192.png")
    make_icon(512, icons / "icon-512.png")

    comparison_titles = fix_duplicate_comparison_titles()
    stats = {"descriptions": 0, "social_metadata": 0, "json_ld": 0, "robots": 0, "inputs": 0, "image_links": 0, "deferred_scripts": 0, "app_links": 0, "comparison_titles": comparison_titles}
    for page in SITE.rglob("*.html"):
        if page.name == VERIFY:
            continue
        text = page.read_text(encoding="utf-8")
        page_title = title_from_html(text)
        relative_path = page.relative_to(SITE).as_posix()
        indexable = relative_path != "404.html"
        text, changed = expand_description(text, page_title); stats["descriptions"] += int(changed)
        text, count = inject_social_metadata(text, page_title); stats["social_metadata"] += count
        text, changed = inject_json_ld(text, page_title); stats["json_ld"] += int(changed)
        text, changed = inject_robots(text, noindex=not indexable); stats["robots"] += int(changed)
        text, count = label_inputs(text, page_title); stats["inputs"] += count
        text, count = label_image_links(text); stats["image_links"] += count
        text, count = defer_scripts(text); stats["deferred_scripts"] += count
        text, changed = add_app_links(text); stats["app_links"] += int(changed)
        page.write_text(text, encoding="utf-8")

    manifest_path = SITE / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["icons"] = [
        {"src": BASE_PATH + "assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
        {"src": BASE_PATH + "assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    protected_slashes = transform_literal_lab_slashes(protect=True)
    normalizer = Path(__file__).with_name("normalize_internal_base_paths_v198.py")
    try:
        subprocess.run([sys.executable, str(normalizer), str(SITE)], check=True)
    finally:
        restored_slashes = transform_literal_lab_slashes(protect=False)
    if restored_slashes != protected_slashes:
        raise SystemExit(
            f"Literal lab slash restoration mismatch: protected={protected_slashes}, restored={restored_slashes}"
        )

    base_report_path = SITE / "api" / "internal-base-paths-v198.json"
    base_report = json.loads(base_report_path.read_text(encoding="utf-8"))
    if base_report.get("status") != "passed":
        raise SystemExit(f"Internal base-path normalization failed: {base_report}")
    stats["internal_base_path_version"] = int(base_report["version"])
    stats["internal_base_path_replacements"] = int(base_report["replacements"])
    stats["internal_base_path_files_changed"] = int(base_report["files_changed"])
    stats["internal_base_path_remaining_errors"] = int(base_report["remaining_error_files"])
    stats["literal_lab_slashes_protected"] = protected_slashes
    stats["literal_lab_slashes_restored"] = restored_slashes

    api = SITE / "api"; api.mkdir(exist_ok=True)
    (api / "polish-v16.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
