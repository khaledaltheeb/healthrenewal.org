#!/usr/bin/env python3
"""Production-safe SEO metadata generator for pterminology-site.

The generator deliberately avoids obsolete or misleading SEO practices:
- it does not emit ``meta keywords``;
- it does not fabricate hreflang URLs;
- it does not hard-truncate titles or descriptions to invented character limits;
- it keeps raw text for JSON-LD and escapes only at the HTML boundary;
- it emits medical schema only when the caller explicitly selects a medical page type.

Only Python's standard library is required.
"""
from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping, Sequence
from urllib.parse import urljoin, urlparse, urlunparse


WHITESPACE_RE = re.compile(r"\s+")
LANGUAGE_TAG_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

SCHEMA_TYPE_MAP = {
    "webpage": "WebPage",
    "medical_webpage": "MedicalWebPage",
    "article": "Article",
    "medical_article": "MedicalScholarlyArticle",
    "web_application": "WebApplication",
}
MEDICAL_SCHEMA_TYPES = {"MedicalWebPage", "MedicalScholarlyArticle"}


def compact_text(value: str) -> str:
    """Collapse whitespace without changing the underlying Unicode text."""
    return WHITESPACE_RE.sub(" ", str(value or "")).strip()


def escape_attr(value: str) -> str:
    return html.escape(value, quote=True)


def normalize_base_url(value: str) -> str:
    parsed = urlparse(compact_text(value))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid public base URL: {value!r}")
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if not path.endswith("/"):
        path += "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def normalize_public_url(base_url: str, value: str, *, directory_hint: bool = False) -> str:
    """Resolve a public URL and reject host changes or traversal outside the project base."""
    raw = compact_text(value)
    if not raw:
        raise ValueError("A public URL or path is required")
    resolved = urljoin(base_url, raw.lstrip("/") if not urlparse(raw).scheme else raw)
    parsed = urlparse(resolved)
    base = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != base.netloc.lower():
        raise ValueError(f"URL must remain on the canonical host: {value!r}")
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if not path.startswith(base.path):
        raise ValueError(f"URL escapes the canonical project path: {value!r}")
    final_segment = path.rsplit("/", 1)[-1]
    if directory_hint and final_segment and "." not in final_segment and not path.endswith("/"):
        path += "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", "", ""))


def validate_language_tag(value: str) -> str:
    tag = compact_text(value).replace("_", "-")
    if not LANGUAGE_TAG_RE.fullmatch(tag):
        raise ValueError(f"Invalid BCP-47 language tag: {value!r}")
    parts = tag.split("-")
    normalized = [parts[0].lower()]
    for part in parts[1:]:
        normalized.append(part.upper() if len(part) == 2 and part.isalpha() else part)
    return "-".join(normalized)


def open_graph_locale(language_tag: str) -> str:
    parts = validate_language_tag(language_tag).split("-")
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]}_{parts[1].upper()}"


def validate_iso_date(value: str | date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    candidate = compact_text(value)
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid ISO-8601 date: {value!r}") from exc
    return candidate


def safe_json_for_html(value: Any) -> str:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


@dataclass(frozen=True, slots=True)
class EntityIdentity:
    name: str
    url: str | None = None
    entity_type: str = "Organization"

    def as_schema(self, base_url: str) -> dict[str, Any]:
        if self.entity_type not in {"Organization", "Person"}:
            raise ValueError("entity_type must be Organization or Person")
        output: dict[str, Any] = {"@type": self.entity_type, "name": compact_text(self.name)}
        if self.url:
            output["url"] = normalize_public_url(base_url, self.url, directory_hint=True)
        return output


@dataclass(frozen=True, slots=True)
class ImageMetadata:
    path: str
    alt: str
    width: int = 1200
    height: int = 630

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Image width and height must be positive")
        if not compact_text(self.alt):
            raise ValueError("A descriptive image alt value is required")


@dataclass(frozen=True, slots=True)
class PageSeoInput:
    page_path: str
    title: str
    description: str
    image: ImageMetadata
    language: str = "ar-JO"
    schema_kind: str = "webpage"
    social_type: str = "website"
    translations: Mapping[str, str] = field(default_factory=dict)
    x_default_url: str | None = None
    author: EntityIdentity | None = None
    reviewer: EntityIdentity | None = None
    date_published: str | date | datetime | None = None
    date_modified: str | date | datetime | None = None
    medical_specialty: str | None = None
    medical_condition: str | None = None
    breadcrumbs: Sequence[tuple[str, str]] = field(default_factory=tuple)
    robots_directives: Sequence[str] = (
        "index",
        "follow",
        "max-snippet:-1",
        "max-image-preview:large",
        "max-video-preview:-1",
    )


class SEOMetaGenerator:
    """Generate valid, evidence-aligned head metadata and JSON-LD."""

    def __init__(
        self,
        *,
        base_url: str,
        site_name: str,
        publisher: EntityIdentity,
        logo_path: str,
        twitter_handle: str = "",
        theme_color: str = "#ffffff",
        default_preconnects: Sequence[str] = (),
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.site_name = compact_text(site_name)
        self.publisher = publisher
        self.logo_url = normalize_public_url(self.base_url, logo_path)
        handle = compact_text(twitter_handle)
        self.twitter_handle = f"@{handle.lstrip('@')}" if handle else ""
        if not HEX_COLOR_RE.fullmatch(theme_color):
            raise ValueError("theme_color must be a six-digit hexadecimal color")
        self.theme_color = theme_color.lower()
        self.default_preconnects = tuple(self._validate_external_origin(item) for item in default_preconnects)

    @staticmethod
    def _validate_external_origin(value: str) -> str:
        parsed = urlparse(compact_text(value))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid preconnect origin: {value!r}")
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), "", "", "", ""))

    def _breadcrumbs_schema(self, breadcrumbs: Sequence[tuple[str, str]]) -> dict[str, Any] | None:
        if not breadcrumbs:
            return None
        items = []
        for position, (name, url) in enumerate(breadcrumbs, start=1):
            items.append(
                {
                    "@type": "ListItem",
                    "position": position,
                    "name": compact_text(name),
                    "item": normalize_public_url(self.base_url, url, directory_hint=True),
                }
            )
        return {"@type": "BreadcrumbList", "itemListElement": items}

    def _schema_graph(self, page: PageSeoInput, page_url: str, image_url: str) -> list[dict[str, Any]]:
        schema_type = SCHEMA_TYPE_MAP.get(page.schema_kind)
        if schema_type is None:
            raise ValueError(f"Unsupported schema_kind: {page.schema_kind!r}")

        publisher = self.publisher.as_schema(self.base_url)
        publisher["logo"] = {
            "@type": "ImageObject",
            "url": self.logo_url,
        }
        image_object = {
            "@type": "ImageObject",
            "url": image_url,
            "width": page.image.width,
            "height": page.image.height,
            "caption": compact_text(page.image.alt),
        }
        node: dict[str, Any] = {
            "@type": schema_type,
            "@id": f"{page_url}#primary",
            "url": page_url,
            "name": compact_text(page.title),
            "headline": compact_text(page.title),
            "description": compact_text(page.description),
            "inLanguage": validate_language_tag(page.language),
            "isAccessibleForFree": True,
            "image": image_object,
            "mainEntityOfPage": {"@type": "WebPage", "@id": page_url},
            "publisher": publisher,
        }
        if page.author:
            node["author"] = page.author.as_schema(self.base_url)
        if page.reviewer:
            node["reviewedBy"] = page.reviewer.as_schema(self.base_url)
        published = validate_iso_date(page.date_published)
        modified = validate_iso_date(page.date_modified)
        if published:
            node["datePublished"] = published
        if modified:
            node["dateModified"] = modified
        if schema_type in MEDICAL_SCHEMA_TYPES:
            if page.medical_specialty:
                node["specialty"] = compact_text(page.medical_specialty)
            if page.medical_condition:
                node["about"] = {
                    "@type": "MedicalCondition",
                    "name": compact_text(page.medical_condition),
                }

        graph = [node]
        breadcrumbs = self._breadcrumbs_schema(page.breadcrumbs)
        if breadcrumbs:
            graph.append(breadcrumbs)
        return graph

    def generate_head_tags(self, page: PageSeoInput) -> str:
        title = compact_text(page.title)
        description = compact_text(page.description)
        if not title:
            raise ValueError("title is required")
        if not description:
            raise ValueError("description is required")

        language = validate_language_tag(page.language)
        page_url = normalize_public_url(self.base_url, page.page_path, directory_hint=True)
        image_url = normalize_public_url(self.base_url, page.image.path)
        display_title = title if self.site_name.casefold() in title.casefold() else f"{title} | {self.site_name}"

        tags = [
            "<!-- SEO metadata generated by scripts/seo_meta_generator_v334.py -->",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
        ]
        for origin in dict.fromkeys(self.default_preconnects):
            tags.append(f'<link rel="preconnect" href="{escape_attr(origin)}">')
        tags.extend(
            [
                f"<title>{html.escape(display_title)}</title>",
                f'<meta name="description" content="{escape_attr(description)}">',
                f'<meta name="robots" content="{escape_attr(", ".join(page.robots_directives))}">',
                f'<link rel="canonical" href="{escape_attr(page_url)}">',
            ]
        )

        normalized_translations: dict[str, str] = {}
        for raw_language, raw_url in page.translations.items():
            lang = validate_language_tag(raw_language)
            normalized_translations[lang] = normalize_public_url(self.base_url, raw_url, directory_hint=True)
        if normalized_translations:
            normalized_translations.setdefault(language, page_url)
            for lang, url in sorted(normalized_translations.items()):
                tags.append(f'<link rel="alternate" hreflang="{escape_attr(lang)}" href="{escape_attr(url)}">')
            if page.x_default_url:
                x_default = normalize_public_url(self.base_url, page.x_default_url, directory_hint=True)
                tags.append(f'<link rel="alternate" hreflang="x-default" href="{escape_attr(x_default)}">')

        tags.extend(
            [
                f'<meta property="og:site_name" content="{escape_attr(self.site_name)}">',
                f'<meta property="og:type" content="{escape_attr(compact_text(page.social_type) or "website")}">',
                f'<meta property="og:title" content="{escape_attr(display_title)}">',
                f'<meta property="og:description" content="{escape_attr(description)}">',
                f'<meta property="og:url" content="{escape_attr(page_url)}">',
                f'<meta property="og:image" content="{escape_attr(image_url)}">',
                f'<meta property="og:image:secure_url" content="{escape_attr(image_url)}">',
                f'<meta property="og:image:width" content="{page.image.width}">',
                f'<meta property="og:image:height" content="{page.image.height}">',
                f'<meta property="og:image:alt" content="{escape_attr(compact_text(page.image.alt))}">',
                f'<meta property="og:locale" content="{escape_attr(open_graph_locale(language))}">',
                '<meta name="twitter:card" content="summary_large_image">',
                f'<meta name="twitter:title" content="{escape_attr(display_title)}">',
                f'<meta name="twitter:description" content="{escape_attr(description)}">',
                f'<meta name="twitter:image" content="{escape_attr(image_url)}">',
                f'<meta name="twitter:image:alt" content="{escape_attr(compact_text(page.image.alt))}">',
            ]
        )
        if self.twitter_handle:
            tags.extend(
                [
                    f'<meta name="twitter:site" content="{escape_attr(self.twitter_handle)}">',
                    f'<meta name="twitter:creator" content="{escape_attr(self.twitter_handle)}">',
                ]
            )
        tags.append(f'<meta name="theme-color" content="{self.theme_color}">')

        graph = self._schema_graph(page, page_url, image_url)
        tags.append(
            '<script type="application/ld+json">'
            + safe_json_for_html({"@context": "https://schema.org", "@graph": graph})
            + "</script>"
        )
        return "\n".join(tags)


__all__ = [
    "EntityIdentity",
    "ImageMetadata",
    "PageSeoInput",
    "SEOMetaGenerator",
    "compact_text",
    "normalize_base_url",
    "normalize_public_url",
    "safe_json_for_html",
]
