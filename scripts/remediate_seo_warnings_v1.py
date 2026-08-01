#!/usr/bin/env python3
"""Resolve reviewable SEO warnings deterministically across sitemap HTML pages.

The processor preserves existing editorial metadata and only completes or
normalizes fields that are absent or explicitly mapped for correction:
- decorative image semantics for intentionally empty alt text;
- concise intent-preserving titles for known overlong titles;
- synchronized descriptions for known undersized descriptions;
- complete Open Graph and Twitter cards using the platform social image.
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, urlparse

from social_metadata_v2 import ensure_social_metadata

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://healthrenewal.org"

TITLE_MAP = {
    "family-guide/conditions/neurofibromatosis-type-1/index.html":
        "الورام الليفي العصبي النوع الأول NF1 | دليل الأسرة",
    "magazine/adhd-personalized-neurofeedback-sham-rct-2026.html":
        "التغذية الراجعة العصبية وADHD | تجربة عشوائية 2026",
    "magazine/adhd-rhythmic-music-game-rct-2026.html":
        "لعبة موسيقية إيقاعية لأعراض ADHD | تجربة عشوائية 2026",
    "magazine/autism-behavioral-domains-network-meta-analysis-2026.html":
        "تدخلات التوحد حسب المجالات السلوكية | تحليل شبكي 2026",
    "magazine/autism-mentorship-program-pilot-rct-2026.html":
        "برنامج إرشاد للأشخاص ذوي التوحد | دراسة تجريبية 2026",
    "magazine/aya-cancer-digital-mental-health-meta-analysis-2026.html":
        "الصحة النفسية الرقمية لليافعين المصابين بالسرطان | تحليل 2026",
    "magazine/intellectual-disability-healthcare-transition-review-2026.html":
        "الانتقال للرعاية الصحية لدى ذوي الإعاقة الذهنية | مراجعة 2026",
    "magazine/neurodevelopmental-disabilities-navigator-act-parent-stress-rct-2026.html":
        "Navigator ACT لضغط والدي ذوي الإعاقات النمائية | تجربة 2026",
    "trust/index.html":
        "منهجية الثقة والمصادر والمراجعة | منصة الصحة النفسية",
}

DESCRIPTION_MAP = {
    "family-guide/tools/appointment-prep/index.html": (
        "قائمة عربية قابلة للطباعة لتحضير موعد الطبيب أو المختص: الأعراض والأدوية "
        "والتغيرات والأسئلة والأهداف، مع تنظيم المعلومات دون استبدال التقييم المهني."
    ),
}


def sitemap_urls(path: Path, seen: set[Path] | None = None) -> list[str]:
    seen = seen or set()
    path = path.resolve()
    if path in seen or not path.is_file():
        return []
    seen.add(path)
    root = ET.parse(path).getroot()
    urls: list[str] = []
    for node in root.iter():
        if not node.tag.endswith("loc") or not node.text:
            continue
        value = node.text.strip()
        parsed = urlparse(value)
        if parsed.path.endswith(".xml"):
            urls.extend(sitemap_urls(ROOT / unquote(parsed.path.lstrip("/")), seen))
        elif value.startswith(ORIGIN):
            urls.append(value)
    return urls


def url_to_html(url: str) -> Path | None:
    parsed = urlparse(url)
    relative = unquote(parsed.path.lstrip("/"))
    if not relative:
        return ROOT / "index.html"
    if relative.endswith("/"):
        return ROOT / relative / "index.html"
    if relative.endswith(".html"):
        return ROOT / relative
    return None


def mark_empty_alt_decorative(source: str) -> str:
    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        if not re.search(r"\balt\s*=\s*([\"'])\s*\1", tag, flags=re.I):
            return tag
        if re.search(r"\baria-hidden\s*=\s*([\"'])true\1", tag, flags=re.I) or re.search(
            r"\brole\s*=\s*([\"'])(?:presentation|none)\1", tag, flags=re.I
        ):
            return tag
        ending = "/>" if tag.endswith("/>") else ">"
        body = tag[: -len(ending)].rstrip()
        return f'{body} aria-hidden="true" role="presentation"{ending}'

    return re.sub(r"<img\b[^>]*>", replace, source, flags=re.I)


def replace_title(source: str, value: str) -> str:
    source, count = re.subn(
        r"<title>.*?</title>",
        f"<title>{value}</title>",
        source,
        count=1,
        flags=re.I | re.S,
    )
    if count != 1:
        raise RuntimeError("Expected exactly one title element")
    for property_name in ("og:title", "twitter:title", "og:image:alt", "twitter:image:alt"):
        pattern = re.compile(
            rf"(<meta\b(?=[^>]*(?:property|name)=[\"']{re.escape(property_name)}[\"'])[^>]*\bcontent=[\"'])[^\"']*([\"'][^>]*>)",
            flags=re.I,
        )
        source = pattern.sub(lambda match: match.group(1) + value + match.group(2), source, count=1)
    return source


def replace_description(source: str, value: str) -> str:
    for name in ("description", "og:description", "twitter:description"):
        pattern = re.compile(
            rf"(<meta\b(?=[^>]*(?:property|name)=[\"']{re.escape(name)}[\"'])[^>]*\bcontent=[\"'])[^\"']*([\"'][^>]*>)",
            flags=re.I,
        )
        source, count = pattern.subn(lambda match: match.group(1) + value + match.group(2), source, count=1)
        if name == "description" and count != 1:
            raise RuntimeError("Primary meta description was not found")
    return source


def collect_paths() -> set[Path]:
    index = ROOT / "sitemap-index.xml"
    if not index.is_file():
        index = ROOT / "sitemap.xml"
    paths = {path for url in sitemap_urls(index) if (path := url_to_html(url)) and path.is_file()}
    paths.update(ROOT / relative for relative in TITLE_MAP)
    paths.update(ROOT / relative for relative in DESCRIPTION_MAP)
    return {path for path in paths if path.is_file()}


def collect_changes() -> list[tuple[Path, str]]:
    changes: list[tuple[Path, str]] = []
    for path in sorted(collect_paths()):
        current = path.read_text(encoding="utf-8")
        updated = mark_empty_alt_decorative(current)
        relative = path.relative_to(ROOT).as_posix()
        if relative in TITLE_MAP:
            updated = replace_title(updated, TITLE_MAP[relative])
        if relative in DESCRIPTION_MAP:
            updated = replace_description(updated, DESCRIPTION_MAP[relative])
        updated = ensure_social_metadata(updated)
        if updated != current:
            changes.append((path, updated))
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    changes = collect_changes()
    if args.check:
        for path, _ in changes:
            print(path.relative_to(ROOT))
        return 1 if changes else 0

    for path, content in changes:
        path.write_text(content, encoding="utf-8")
    print(f"Resolved warning patterns in {len(changes)} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
