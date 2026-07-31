#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
BASE_URL = "https://healthrenewal.org/"
SOCIAL_IMAGE = f"{BASE_URL}assets/brand/social-card.svg"
SITE_NAME = {
    "ar": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
    "en": "Mental Health and Special Needs Platform",
}
DEFAULT_ROBOTS = "index,follow,max-snippet:-1,max-image-preview:large"
DEFAULT_THEME = "#075f5b"
EXCLUDED_DIRS = {".git", ".github", "node_modules", "__pycache__", ".venv"}

TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
HEAD_RE = re.compile(r"</head\s*>", re.I)
LANG_RE = re.compile(r"<html\b[^>]*\blang=[\"']([^\"']+)", re.I)
DESC_RE = re.compile(r"<meta\b[^>]*\bname=[\"']description[\"'][^>]*content=[\"']([^\"']*)[\"']", re.I)
CANONICAL_RE = re.compile(r"<link\b[^>]*\brel=[\"']canonical[\"'][^>]*href=[\"']([^\"']*)[\"']", re.I)
ROBOTS_RE = re.compile(r"<meta\b[^>]*\bname=[\"']robots[\"'][^>]*content=[\"']([^\"']*)[\"']", re.I)
JSONLD_RE = re.compile(r"<script\b[^>]*type=[\"']application/ld\+json[\"']", re.I)
OG_TITLE_RE = re.compile(r"<meta\b[^>]*property=[\"']og:title[\"']", re.I)
OG_DESC_RE = re.compile(r"<meta\b[^>]*property=[\"']og:description[\"']", re.I)
TW_CARD_RE = re.compile(r"<meta\b[^>]*name=[\"']twitter:card[\"']", re.I)


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def escape_attr(value: str) -> str:
    return html.escape(value, quote=True)


def infer_locale(lang: str) -> str:
    lang = lang.lower()
    if lang.startswith("ar"):
        return "ar_AR"
    if lang.startswith("en"):
        return "en_US"
    if lang.startswith("es"):
        return "es_ES"
    return "ar_AR"


def infer_site_name(lang: str) -> str:
    return SITE_NAME.get(lang.split("-", 1)[0].lower(), SITE_NAME["ar"])


def infer_title(text: str, path: Path) -> str:
    m = TITLE_RE.search(text)
    if m:
        title = compact(re.sub(r"<[^>]+>", "", m.group(1)))
        if title:
            return title
    name = path.stem if path.stem != "index" else path.parent.name or "صفحة"
    return f"{name} | {SITE_NAME['ar']}"


def infer_description(text: str, title: str, path: Path) -> str:
    m = DESC_RE.search(text)
    if m and compact(m.group(1)):
        return compact(m.group(1))
    if title:
        return f"{title} — محتوى من {SITE_NAME['ar']} مع توضيح واضح ومراجع موثوقة."
    return f"محتوى من {SITE_NAME['ar']} مع توضيح واضح ومراجع موثوقة."


def infer_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return BASE_URL
    if rel.endswith("/index.html"):
        route = rel[:-10]
        return BASE_URL.rstrip("/") + "/" + route + "/"
    if rel.endswith(".html"):
        route = rel[:-5]
        return BASE_URL.rstrip("/") + "/" + route
    return BASE_URL.rstrip("/") + "/" + rel + "/"


def infer_robots(text: str) -> str | None:
    m = ROBOTS_RE.search(text)
    if m and compact(m.group(1)):
        return compact(m.group(1))
    return None


def build_jsonld(title: str, description: str, url: str, lang: str) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": description,
        "url": url,
        "inLanguage": lang.replace("_", "-"),
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME["ar"], "url": BASE_URL},
        "publisher": {"@type": "Organization", "name": SITE_NAME["ar"], "url": BASE_URL},
        "dateModified": datetime.utcnow().date().isoformat(),
    }
    return "<script type=\"application/ld+json\">" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "</script>"


def build_meta_block(text: str, path: Path) -> str:
    lang = LANG_RE.search(text)
    language = lang.group(1) if lang else "ar"
    locale = infer_locale(language)
    title = infer_title(text, path)
    description = infer_description(text, title, path)
    url = infer_url(path)
    site_name = infer_site_name(language)
    robots = infer_robots(text) or DEFAULT_ROBOTS
    block = []
    block.append(f'<meta name="description" content="{escape_attr(description)}">')
    block.append(f'<meta name="robots" content="{escape_attr(robots)}">')
    block.append(f'<meta name="theme-color" content="{DEFAULT_THEME}">')
    block.append(f'<link rel="canonical" href="{escape_attr(url)}">')
    block.append('<meta property="og:type" content="website">')
    block.append(f'<meta property="og:locale" content="{escape_attr(locale)}">')
    block.append(f'<meta property="og:site_name" content="{escape_attr(site_name)}">')
    block.append(f'<meta property="og:title" content="{escape_attr(title)}">')
    block.append(f'<meta property="og:description" content="{escape_attr(description)}">')
    block.append(f'<meta property="og:url" content="{escape_attr(url)}">')
    block.append(f'<meta property="og:image" content="{escape_attr(SOCIAL_IMAGE)}">')
    block.append(f'<meta property="og:image:alt" content="{escape_attr(title)}">')
    block.append('<meta name="twitter:card" content="summary_large_image">')
    block.append(f'<meta name="twitter:title" content="{escape_attr(title)}">')
    block.append(f'<meta name="twitter:description" content="{escape_attr(description)}">')
    block.append(f'<meta name="twitter:image" content="{escape_attr(SOCIAL_IMAGE)}">')
    block.append(f'<meta name="twitter:image:alt" content="{escape_attr(title)}">')
    block.append(build_jsonld(title, description, url, locale))
    return "\n".join(block)


def add_seo(text: str, path: Path) -> str:
    if "</head>" not in text.lower():
        return text
    lower = text.lower()
    if not OG_TITLE_RE.search(text):
        block = build_meta_block(text, path)
        return text.replace("</head>", block + "\n</head>", 1)
    # If some core tags already exist, fill only the missing ones.
    block = []
    title = infer_title(text, path)
    description = infer_description(text, title, path)
    url = infer_url(path)
    lang = LANG_RE.search(text)
    language = lang.group(1) if lang else "ar"
    locale = infer_locale(language)
    site_name = infer_site_name(language)
    robots = infer_robots(text) or DEFAULT_ROBOTS
    if not DESC_RE.search(text):
        block.append(f'<meta name="description" content="{escape_attr(description)}">')
    if not ROBOTS_RE.search(text):
        block.append(f'<meta name="robots" content="{escape_attr(robots)}">')
    if not re.search(r'<meta\b[^>]*name=[\"\']theme-color[\"']', text, re.I):
        block.append(f'<meta name="theme-color" content="{DEFAULT_THEME}">')
    if not CANONICAL_RE.search(text):
        block.append(f'<link rel="canonical" href="{escape_attr(url)}">')
    if not re.search(r'<meta\b[^>]*property=[\"\']og:type[\"']', text, re.I):
        block.append('<meta property="og:type" content="website">')
    if not re.search(r'<meta\b[^>]*property=[\"\']og:locale[\"']', text, re.I):
        block.append(f'<meta property="og:locale" content="{escape_attr(locale)}">')
    if not re.search(r'<meta\b[^>]*property=[\"\']og:site_name[\"']', text, re.I):
        block.append(f'<meta property="og:site_name" content="{escape_attr(site_name)}">')
    if not OG_TITLE_RE.search(text):
        block.append(f'<meta property="og:title" content="{escape_attr(title)}">')
    if not OG_DESC_RE.search(text):
        block.append(f'<meta property="og:description" content="{escape_attr(description)}">')
    if not re.search(r'<meta\b[^>]*property=[\"\']og:url[\"']', text, re.I):
        block.append(f'<meta property="og:url" content="{escape_attr(url)}">')
    if not re.search(r'<meta\b[^>]*property=[\"\']og:image[\"']', text, re.I):
        block.append(f'<meta property="og:image" content="{escape_attr(SOCIAL_IMAGE)}">')
    if not re.search(r'<meta\b[^>]*property=[\"\']og:image:alt[\"']', text, re.I):
        block.append(f'<meta property="og:image:alt" content="{escape_attr(title)}">')
    if not TW_CARD_RE.search(text):
        block.append('<meta name="twitter:card" content="summary_large_image">')
    if not re.search(r'<meta\b[^>]*name=[\"\']twitter:title[\"']', text, re.I):
        block.append(f'<meta name="twitter:title" content="{escape_attr(title)}">')
    if not re.search(r'<meta\b[^>]*name=[\"\']twitter:description[\"']', text, re.I):
        block.append(f'<meta name="twitter:description" content="{escape_attr(description)}">')
    if not re.search(r'<meta\b[^>]*name=[\"\']twitter:image[\"']', text, re.I):
        block.append(f'<meta name="twitter:image" content="{escape_attr(SOCIAL_IMAGE)}">')
    if not re.search(r'<meta\b[^>]*name=[\"\']twitter:image:alt[\"']', text, re.I):
        block.append(f'<meta name="twitter:image:alt" content="{escape_attr(title)}">')
    if not JSONLD_RE.search(text):
        block.append(build_jsonld(title, description, url, locale))
    if block:
        return text.replace("</head>", "\n".join(block) + "\n</head>", 1)
    return text


def should_process(path: Path) -> bool:
    if path.suffix.lower() != ".html":
        return False
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    return True


def main() -> int:
    changed = 0
    for path in sorted(ROOT.rglob("*.html")):
        if not should_process(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        updated = add_seo(text, path)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    print(f"updated_files={changed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
