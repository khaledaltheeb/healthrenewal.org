#!/usr/bin/env python3
"""Deterministically complete Open Graph and Twitter metadata for HTML pages."""
from __future__ import annotations

import html
import re
from html.parser import HTMLParser

SOCIAL_IMAGE = "https://healthrenewal.org/assets/brand/social-card.svg"
SITE_NAME = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"


class HeadMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.canonical = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {str(key).lower(): "" if value is None else str(value) for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = (data.get("property") or data.get("name") or "").lower().strip()
            if key and key not in self.meta:
                self.meta[key] = data.get("content", "").strip()
        elif tag == "link" and data.get("rel", "").lower() == "canonical":
            self.canonical = data.get("href", "").strip()

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()


def inspect_head(source: str) -> HeadMetadataParser:
    parser = HeadMetadataParser()
    parser.feed(source)
    parser.close()
    return parser


def meta_tag(attribute: str, key: str, value: str) -> str:
    return f'<meta {attribute}="{key}" content="{html.escape(value, quote=True)}">'


def ensure_social_metadata(source: str) -> str:
    """Add only missing social tags and remain byte-stable after the first pass."""
    parsed = inspect_head(source)
    title = parsed.meta.get("og:title") or parsed.title
    description = parsed.meta.get("description") or parsed.meta.get("og:description")
    canonical = parsed.meta.get("og:url") or parsed.canonical
    if not title or not description:
        return source

    required: list[tuple[str, str, str]] = [
        ("property", "og:type", parsed.meta.get("og:type") or "article"),
        ("property", "og:locale", "ar_AR"),
        ("property", "og:site_name", SITE_NAME),
        ("property", "og:title", title),
        ("property", "og:description", description),
    ]
    if canonical:
        required.append(("property", "og:url", canonical))
    required.extend([
        ("property", "og:image", SOCIAL_IMAGE),
        ("property", "og:image:alt", title),
        ("name", "twitter:card", "summary_large_image"),
        ("name", "twitter:title", title),
        ("name", "twitter:description", description),
        ("name", "twitter:image", SOCIAL_IMAGE),
        ("name", "twitter:image:alt", title),
    ])

    missing = [meta_tag(attribute, key, value) for attribute, key, value in required if key not in parsed.meta]
    if not missing:
        return source
    matches = list(re.finditer(r"</head\s*>", source, flags=re.I))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one </head>; found {len(matches)}")
    match = matches[0]
    prefix = source[:match.start()]
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    return prefix + "\n".join(missing) + "\n" + source[match.start():]
