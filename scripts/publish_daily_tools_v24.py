from __future__ import annotations

"""واجهة نشر SEO للأدوات اليومية.

يحافظ الناشر الأساسي على الخصوصية المحلية: لا تُرسل البيانات إلى خادم.
المحتوى تنظيمي غير تشخيصي، ويعرض بوضوح متى تطلب المساعدة من مختص.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import publish_daily_tools_v24_core as _core
from scripts.publish_daily_tools_v24_core import *  # noqa: F401,F403

SEO_CONTRACT = 219
SITE_NAME = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
FOUNDING_NAME = "مصطلحات علم النفس"
SOCIAL_IMAGE = BASE + "assets/brand/social-card.svg"
LOGO = PATH + "assets/brand/logo-mark.svg"
MANIFEST = PATH + "manifest.webmanifest"
SEARCH = PATH + "opensearch.xml"


def _unique(values: Iterable[str], limit: int = 8) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = re.sub(r"\s+", " ", str(raw or "")).strip(" ،,.-")
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value[:90])
        if len(result) >= limit:
            break
    return result


def topic_keywords(title: str, description: str, canonical: str) -> list[str]:
    if "/learning-paths/" in canonical:
        route_terms = (
            "مسارات تعلم الصحة النفسية",
            "تعليم نفسي عربي",
            "مهارات نفسية عملية",
            "خطة تعلم قصيرة",
            "أدوات دعم نفسي",
        )
    else:
        route_terms = (
            "أدوات نفسية تفاعلية",
            "تمارين الصحة النفسية",
            "تنظيم التوتر",
            "متابعة نفسية محلية",
            "أدوات دعم الأسرة",
        )
    description_term = description if len(description) <= 90 else ""
    return _unique((title, description_term, *route_terms, FOUNDING_NAME))


def institutionalize_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [institutionalize_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: institutionalize_schema(item) for key, item in value.items()}
    item_type = result.get("@type")
    types = set(item_type) if isinstance(item_type, list) else {item_type}
    if "Organization" in types:
        current_name = str(result.get("name") or "").strip()
        result["name"] = SITE_NAME
        if current_name and current_name != SITE_NAME:
            result.setdefault("alternateName", current_name)
        else:
            result.setdefault("alternateName", FOUNDING_NAME)
        result.setdefault("url", BASE)
        result.setdefault("logo", SOCIAL_IMAGE)
    return result


def shell(title: str, description: str, canonical: str, schema: dict[str, Any], body: str) -> str:
    normalized_schema = institutionalize_schema(schema)
    structured = json.dumps(normalized_schema, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    keywords = ",".join(topic_keywords(title, description, canonical))
    page_type = "website" if canonical in {BASE + "daily-tools/", BASE + "learning-paths/"} else "article"
    title_text = f"{title} | {SITE_NAME}"
    image_alt = f"هوية {SITE_NAME}"
    return f'''<!doctype html><html lang="ar" dir="rtl" data-design="marshmallow-v{DESIGN_CONTRACT}" data-seo="institutional-v{SEO_CONTRACT}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title_text)}</title><meta name="description" content="{e(description)}"><meta name="keywords" content="{e(keywords)}"><meta name="author" content="{e(SITE_NAME)}"><meta name="application-name" content="{e(SITE_NAME)}"><meta name="subject" content="الصحة النفسية والأدوات النفسية التفاعلية"><meta name="audience" content="الأفراد والأسر ومقدمو الرعاية"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><meta name="theme-color" content="#e5faf5"><meta name="color-scheme" content="light"><link rel="canonical" href="{e(canonical)}"><link rel="manifest" href="{MANIFEST}"><link rel="icon" href="{LOGO}" type="image/svg+xml"><link rel="apple-touch-icon" href="{LOGO}"><link rel="search" type="application/opensearchdescription+xml" title="البحث في المنصة" href="{SEARCH}"><link rel="sitemap" type="application/xml" href="{BASE}sitemap.xml"><meta property="og:type" content="{page_type}"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="{e(SITE_NAME)}"><meta property="og:title" content="{e(title_text)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(canonical)}"><meta property="og:image" content="{SOCIAL_IMAGE}"><meta property="og:image:alt" content="{e(image_alt)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title_text)}"><meta name="twitter:description" content="{e(description)}"><meta name="twitter:image" content="{SOCIAL_IMAGE}"><meta name="twitter:image:alt" content="{e(image_alt)}"><script type="application/ld+json">{structured}</script><style>{STYLE}</style></head><body>{body}</body></html>'''


def _expected_pages(data: dict[str, Any]) -> list[Path]:
    return (
        [SITE / "daily-tools" / "index.html", SITE / "learning-paths" / "index.html"]
        + [SITE / "daily-tools" / tool["slug"] / "index.html" for tool in data["tools"]]
        + [SITE / "learning-paths" / path["slug"] / "index.html" for path in data["paths"]]
    )


def validate_metadata(data: dict[str, Any]) -> None:
    required = (
        'data-seo="institutional-v219"',
        '<meta name="keywords"',
        '<link rel="canonical"',
        '<link rel="manifest"',
        '<link rel="icon"',
        '<link rel="search"',
        'property="og:image"',
        'name="twitter:card"',
        'name="twitter:image"',
        'application/ld+json',
    )
    errors: list[str] = []
    for page in _expected_pages(data):
        if not page.is_file():
            errors.append(f"missing page: {page}")
            continue
        text = page.read_text(encoding="utf-8")
        missing = [marker for marker in required if marker not in text]
        match = re.search(r'<meta name="keywords" content="([^"]+)">', text)
        keywords = [item.strip() for item in match.group(1).split(",")] if match else []
        if missing:
            errors.append(f"{page}: missing {missing}")
        if not 4 <= len(keywords) <= 8 or len(keywords) != len(set(keywords)):
            errors.append(f"{page}: invalid topic keyword set {keywords}")
        if text.count('<meta name="description"') != 1 or text.count('<link rel="canonical"') != 1:
            errors.append(f"{page}: duplicate or missing primary metadata")
        schema_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
        if not schema_match:
            errors.append(f"{page}: JSON-LD is missing")
        else:
            schema_text = schema_match.group(1)
            if '"@type":"Organization","name":"مصطلحات علم النفس"' in schema_text:
                errors.append(f"{page}: founding name remains the primary Organization identity")
            if '"@type":"Organization"' in schema_text and SITE_NAME not in schema_text:
                errors.append(f"{page}: institutional Organization identity is missing")
    if errors:
        raise SystemExit("Daily tools metadata contract failed:\n" + "\n".join(errors))


def publish(data: dict[str, Any]) -> None:
    _core.shell = shell
    _core.publish(data)
    validate_metadata(data)


_core.shell = shell


if __name__ == "__main__":
    if not SITE.exists():
        raise SystemExit("Missing site output")
    publish(json.loads(DATA.read_text(encoding="utf-8")))
