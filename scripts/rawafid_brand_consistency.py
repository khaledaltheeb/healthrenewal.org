#!/usr/bin/env python3
"""Normalize and audit Rawafid identity across source or production HTML.

The command is intentionally idempotent and fail-closed. It updates public text,
metadata, favicons, manifest links, and social previews while preserving page
content, canonical URLs, local navigation, and the shared platform shell.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

BRAND_AR = "منصة روافد"
BRAND_EN = "Rawafid Platform"
BRAND_LONG_AR = "منصة روافد للعافية النفسية والدمج والتمكين"
DESCRIPTION_AR = (
    "منصة روافد منصة عربية للعافية النفسية والدمج والتمكين، تقدم موسوعة موثقة، "
    "وأدلة عملية، وأدوات تفاعلية، ومسارات معرفية داعمة للأفراد والأسر والمختصين والمجتمع."
)
PRIMARY = "#0b8f92"
SOCIAL_IMAGE = "https://healthrenewal.org/assets/brand/rawafid-social-card.jpg"

TEXT_EXTENSIONS = {
    ".html", ".htm", ".xml", ".json", ".webmanifest", ".md", ".txt", ".csv",
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".yml", ".yaml", ".svg", ".css",
}
SKIP_DIRS = {
    ".git", ".github", "node_modules", ".venv", "venv", "vendor", "dist", "build",
    "__pycache__", ".mypy_cache", ".pytest_cache", "_site",
}
SKIP_TOP_SOURCE = {"scripts", "tests", "reports"}
VERIFICATION_FILE_RE = re.compile(r"(?:google|bing|yandex|baidu)[A-Za-z0-9._-]*\.html$", re.I)

LEGACY_LITERALS = (
    "بوابة الصحة النفسية وذوي الاحتياجات الخاصة",
    "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
    "شعار منصة الصحة النفسية وذوي الاحتياجات الخاصة",
    "البحث في منصة الصحة النفسية",
    "منصة تجدد الصحة",
    "مصطلحات علم النفس",
    "Psychology Terminology",
)
LEGACY_HEALTH_RENEWAL_RE = re.compile(r"(?<![\w.-])health\s+renewal(?![\w.-])", re.I)

META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.I | re.S)
LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.I | re.S)
SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.I | re.S)
HTML_LANG_RE = re.compile(r"<html\b[^>]*\blang\s*=\s*([\"'])(.*?)\1", re.I | re.S)
TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title\s*>", re.I | re.S)
HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.I)

FAVICON_BLOCK = """<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/assets/brand/logo-mark.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
<link rel="stylesheet" href="/assets/brand/rawafid-brand.css">
<script defer src="/assets/brand/rawafid-brand.js"></script>"""

DEDUPE_META_KEYS = {
    "description", "author", "application-name", "theme-color",
    "og:type", "og:locale", "og:site_name", "og:url", "og:title", "og:description",
    "og:image", "og:image:alt", "twitter:card", "twitter:title", "twitter:description",
    "twitter:image", "twitter:image:alt",
}
OG_KEYS = {key for key in DEDUPE_META_KEYS if key.startswith("og:")}


@dataclass
class Report:
    schema_version: int = 3
    status: str = "failed"
    root: str = ""
    production_mode: bool = False
    text_files_scanned: int = 0
    html_files: int = 0
    files_changed: int = 0
    text_replacements: int = 0
    duplicate_meta_tags_removed: int = 0
    invalid_hreflang_links_removed: int = 0
    legacy_occurrences: int = 0
    legacy_files: int = 0
    html_missing_head: int = 0
    html_missing_brand_style: int = 0
    html_missing_brand_script: int = 0
    html_missing_application_name: int = 0
    html_missing_og_site_name: int = 0
    html_missing_theme_color: int = 0
    html_missing_manifest_link: int = 0
    html_duplicate_meta_tags: int = 0
    files_needing_changes: int = 0
    manifest_valid: bool = False
    manifest_errors: list[str] = field(default_factory=list)
    missing_assets: list[str] = field(default_factory=list)
    legacy_examples: list[str] = field(default_factory=list)
    changed_examples: list[str] = field(default_factory=list)


def attrs(tag: str) -> dict[str, str]:
    return {match.group(1).lower(): match.group(3) for match in ATTR_RE.finditer(tag)}


def html_language(text: str, path: Path) -> str:
    match = HTML_LANG_RE.search(text)
    if match:
        return match.group(2).strip().lower()
    parts = {part.lower() for part in path.parts}
    if "en" in parts:
        return "en"
    if "es" in parts:
        return "es"
    return "ar"


def page_brand(lang: str) -> str:
    return BRAND_AR if lang.startswith("ar") else BRAND_EN


def replace_legacy_text(text: str, path: Path) -> tuple[str, int]:
    lang = html_language(text, path) if path.suffix.lower() in {".html", ".htm"} else ""
    target = page_brand(lang) if lang else BRAND_EN
    count = 0
    replacements = (
        ("شعار منصة الصحة النفسية وذوي الاحتياجات الخاصة", f"شعار {BRAND_AR}"),
        ("بوابة الصحة النفسية وذوي الاحتياجات الخاصة", "بوابة منصة روافد"),
        ("منصة الصحة النفسية وذوي الاحتياجات الخاصة", BRAND_AR),
        ("البحث في منصة الصحة النفسية", f"البحث في {BRAND_AR}"),
        ("منصة تجدد الصحة", BRAND_AR),
        ("مصطلحات علم النفس", BRAND_AR),
        ("Psychology Terminology", target),
        ("https://healthrenewal.org/assets/brand/social-card.svg", SOCIAL_IMAGE),
        ("/assets/brand/social-card.svg", "/assets/brand/rawafid-social-card.jpg"),
    )
    for old, new in replacements:
        occurrences = text.count(old)
        if occurrences:
            text = text.replace(old, new)
            count += occurrences

    def replace_health_renewal(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return target

    text = LEGACY_HEALTH_RENEWAL_RE.sub(replace_health_renewal, text)
    text = re.sub(
        rf'("alternateName"\s*:\s*)\[\s*"{re.escape(BRAND_AR)}"\s*,\s*"{re.escape(BRAND_EN)}"\s*\]',
        rf'\1["{BRAND_EN}"]', text,
    )
    text = re.sub(
        rf'("alternateName"\s*:\s*)\[\s*"{re.escape(BRAND_EN)}"\s*,\s*"{re.escape(BRAND_AR)}"\s*\]',
        rf'\1["{BRAND_EN}"]', text,
    )
    text = re.sub(
        rf'("alternateName"\s*:\s*)"{re.escape(BRAND_AR)}"',
        rf'\1"{BRAND_EN}"', text,
    )
    return text, count


def meta_key(tag: str) -> str | None:
    values = attrs(tag)
    return (values.get("name") or values.get("property") or "").strip().lower() or None


def first_meta_content(text: str, key: str) -> str | None:
    for match in META_TAG_RE.finditer(text):
        if meta_key(match.group(0)) == key:
            value = attrs(match.group(0)).get("content")
            if value is not None:
                return value.strip()
    return None


def build_meta(key: str, content: str) -> str:
    attribute = "property" if key in OG_KEYS else "name"
    return f'<meta {attribute}="{key}" content="{content.replace(chr(34), "&quot;")}">'


def page_title(text: str) -> str:
    match = TITLE_RE.search(text)
    if not match:
        return BRAND_AR
    return re.sub(r"\s+", " ", match.group(1)).strip()


def normalize_meta(text: str, path: Path) -> tuple[str, int]:
    lang = html_language(text, path)
    brand = page_brand(lang)
    title = page_title(text)
    description = first_meta_content(text, "description") or (
        DESCRIPTION_AR if lang.startswith("ar") else "Rawafid Platform for mental wellbeing, inclusion and empowerment."
    )
    fixed = {
        "author": brand,
        "application-name": brand,
        "theme-color": PRIMARY,
        "og:site_name": brand,
        "og:title": title,
        "og:description": description,
        "og:image": SOCIAL_IMAGE,
        "og:image:alt": f"شعار {BRAND_AR}" if lang.startswith("ar") else f"{BRAND_EN} logo",
        "twitter:card": "summary_large_image",
        "twitter:title": title,
        "twitter:description": description,
        "twitter:image": SOCIAL_IMAGE,
        "twitter:image:alt": f"شعار {BRAND_AR}" if lang.startswith("ar") else f"{BRAND_EN} logo",
    }
    seen: set[str] = set()
    removed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal removed
        tag = match.group(0)
        key = meta_key(tag)
        if key not in DEDUPE_META_KEYS:
            return tag
        if key in seen:
            removed += 1
            return ""
        seen.add(key)
        value = fixed.get(key)
        if value is None:
            value = attrs(tag).get("content", "").strip()
        return build_meta(key, value)

    text = META_TAG_RE.sub(replace, text)
    additions = [build_meta(key, value) for key, value in fixed.items() if key not in seen]
    if additions and HEAD_CLOSE_RE.search(text):
        text = HEAD_CLOSE_RE.sub("\n" + "\n".join(additions) + "\n</head>", text, count=1)
    return text, removed


def normalize_brand_assets(text: str) -> str:
    def drop_link(match: re.Match[str]) -> str:
        values = attrs(match.group(0))
        rel = values.get("rel", "").lower()
        href = values.get("href", "")
        if "icon" in rel or rel == "manifest" or "rawafid-brand.css" in href:
            return ""
        return match.group(0)

    text = LINK_TAG_RE.sub(drop_link, text)
    text = SCRIPT_TAG_RE.sub(
        lambda match: "" if "rawafid-brand.js" in attrs(match.group(0)).get("src", "") else match.group(0),
        text,
    )
    text = re.sub(r"\s*</head\s*>", "\n</head>", text, count=1, flags=re.I)
    text = re.sub(r"\s*</head\s*>", "\n</head>", text, count=1, flags=re.I)
    if HEAD_CLOSE_RE.search(text):
        text = HEAD_CLOSE_RE.sub(FAVICON_BLOCK + "\n</head>", text, count=1)
    return text


def local_target(root: Path, href: str) -> Path | None:
    parsed = urlparse(href)
    if parsed.netloc and parsed.netloc.lower() not in {"healthrenewal.org", "www.healthrenewal.org"}:
        return None
    route = parsed.path or "/"
    candidate = root / (route.lstrip("/") or "index.html")
    return candidate / "index.html" if route.endswith("/") and route != "/" else candidate


def normalize_hreflang(text: str, root: Path, production: bool) -> tuple[str, int]:
    if not production:
        return text, 0
    removed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal removed
        values = attrs(match.group(0))
        if "alternate" not in values.get("rel", "").lower().split() or "hreflang" not in values:
            return match.group(0)
        target = local_target(root, values.get("href", ""))
        if target is not None and not target.is_file():
            removed += 1
            return ""
        return match.group(0)

    return LINK_TAG_RE.sub(replace, text), removed


def normalize_html(text: str, path: Path, root: Path, production: bool) -> tuple[str, dict[str, int]]:
    stats = {"replacements": 0, "duplicates": 0, "hreflang_removed": 0}
    text, stats["replacements"] = replace_legacy_text(text, path)
    if not HEAD_CLOSE_RE.search(text):
        return text, stats
    text, stats["duplicates"] = normalize_meta(text, path)
    text = normalize_brand_assets(text)
    text, stats["hreflang_removed"] = normalize_hreflang(text, root, production)
    return text, stats


def eligible(path: Path, root: Path, production: bool) -> bool:
    if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
        return False
    relative = path.relative_to(root)
    if any(part in SKIP_DIRS for part in relative.parts):
        return False
    if not production and relative.parts and relative.parts[0] in SKIP_TOP_SOURCE:
        return False
    if path.suffix.lower() in {".html", ".htm"} and VERIFICATION_FILE_RE.fullmatch(path.name):
        return False
    return True


def iter_text_files(root: Path, production: bool) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if eligible(path, root, production):
            yield path


def normalize_manifest(root: Path, fix: bool) -> tuple[bool, list[str], bool]:
    path = root / "manifest.webmanifest"
    if not path.is_file():
        return False, ["manifest.webmanifest is missing"], False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return False, [f"invalid JSON: {exc}"], False
    desired = {
        "id": "/",
        "name": BRAND_LONG_AR,
        "short_name": "روافد",
        "description": DESCRIPTION_AR,
        "lang": "ar",
        "dir": "rtl",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f7fffe",
        "theme_color": PRIMARY,
    }
    updated = dict(data)
    updated.update(desired)
    updated["categories"] = ["education", "health", "medical"]
    updated["icons"] = [
        {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
    ]
    changed = updated != data
    if changed and fix:
        path.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        data = updated
    errors = [f"{key} mismatch" for key, value in desired.items() if data.get(key) != value]
    if data.get("icons") != updated["icons"]:
        errors.append("icons mismatch")
    return not errors, errors, changed


def legacy_count(text: str) -> int:
    return sum(text.count(value) for value in LEGACY_LITERALS) + len(LEGACY_HEALTH_RENEWAL_RE.findall(text))


def duplicate_meta_count(text: str) -> int:
    counts: dict[str, int] = {}
    for match in META_TAG_RE.finditer(text):
        key = meta_key(match.group(0))
        if key in DEDUPE_META_KEYS:
            counts[key] = counts.get(key, 0) + 1
    return sum(value - 1 for value in counts.values() if value > 1)


def audit(root: Path, production: bool, report: Report) -> Report:
    assets = (
        "assets/brand/logo-mark.svg", "assets/brand/logo-lockup.svg", "assets/brand/rawafid-brand.css",
        "assets/brand/rawafid-brand.js", "assets/brand/rawafid-social-card.jpg", "favicon.ico",
        "favicon-16x16.png", "favicon-32x32.png", "apple-touch-icon.png",
        "android-chrome-192x192.png", "android-chrome-512x512.png",
    )
    report.missing_assets = [name for name in assets if not (root / name).is_file() or (root / name).stat().st_size == 0]
    for path in iter_text_files(root, production):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        report.text_files_scanned += 1
        count = legacy_count(text)
        if count:
            report.legacy_occurrences += count
            report.legacy_files += 1
            if len(report.legacy_examples) < 12:
                report.legacy_examples.append(str(path.relative_to(root)))
        if path.suffix.lower() not in {".html", ".htm"}:
            continue
        report.html_files += 1
        if not HEAD_CLOSE_RE.search(text):
            report.html_missing_head += 1
            continue
        report.html_missing_brand_style += int("/assets/brand/rawafid-brand.css" not in text)
        report.html_missing_brand_script += int("/assets/brand/rawafid-brand.js" not in text)
        report.html_missing_application_name += int(first_meta_content(text, "application-name") is None)
        report.html_missing_og_site_name += int(first_meta_content(text, "og:site_name") is None)
        report.html_missing_theme_color += int(first_meta_content(text, "theme-color") is None)
        report.html_missing_manifest_link += int("/manifest.webmanifest" not in text)
        report.html_duplicate_meta_tags += duplicate_meta_count(text)
        normalized, _ = normalize_html(text, path, root, production)
        report.files_needing_changes += int(normalized != text)
    report.manifest_valid, report.manifest_errors, manifest_changes = normalize_manifest(root, fix=False)
    report.files_needing_changes += int(manifest_changes)
    blocking = (
        report.legacy_occurrences + report.html_missing_head + report.html_missing_brand_style
        + report.html_missing_brand_script + report.html_missing_application_name + report.html_missing_og_site_name
        + report.html_missing_theme_color + report.html_missing_manifest_link + report.html_duplicate_meta_tags
        + report.files_needing_changes + len(report.missing_assets) + len(report.manifest_errors)
    )
    report.status = "passed" if report.html_files > 0 and blocking == 0 else "failed"
    return report


def normalize_root(root: Path, *, fix: bool, production: bool, report_path: Path | None = None) -> Report:
    root = root.resolve()
    report = Report(root=str(root), production_mode=production)
    for path in iter_text_files(root, production):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if path.suffix.lower() in {".html", ".htm"}:
            updated, stats = normalize_html(text, path, root, production)
        else:
            updated, replacements = replace_legacy_text(text, path)
            stats = {"replacements": replacements, "duplicates": 0, "hreflang_removed": 0}
        if updated != text:
            report.files_changed += 1
            if len(report.changed_examples) < 20:
                report.changed_examples.append(str(path.relative_to(root)))
            if fix:
                path.write_text(updated, encoding="utf-8")
        report.text_replacements += stats["replacements"]
        report.duplicate_meta_tags_removed += stats["duplicates"]
        report.invalid_hreflang_links_removed += stats["hreflang_removed"]
    _, _, manifest_changed = normalize_manifest(root, fix=fix)
    if manifest_changed:
        report.files_changed += 1
    final = Report(
        root=str(root), production_mode=production, files_changed=report.files_changed,
        text_replacements=report.text_replacements, duplicate_meta_tags_removed=report.duplicate_meta_tags_removed,
        invalid_hreflang_links_removed=report.invalid_hreflang_links_removed,
        changed_examples=report.changed_examples,
    )
    final = audit(root, production, final)
    if report_path is None:
        report_path = root / ("api/rawafid-brand-consistency-v3.json" if production else "reports/rawafid-brand-consistency-v3.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(asdict(final), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return final


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and audit Rawafid public identity.")
    parser.add_argument("--root", default=".")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fix", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--report")
    args = parser.parse_args()
    result = normalize_root(
        Path(args.root), fix=bool(args.fix), production=bool(args.production),
        report_path=Path(args.report) if args.report else None,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
