from __future__ import annotations

"""واجهة نشر مؤسسية للأدوات اليومية ومسارات التعلم.

تُبقي البيانات محلية على الجهاز، وتزامن مسار الإخراج صراحةً مع نواة
الناشر عند الاستدعاء من الاختبارات أو من سطر الأوامر.
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

SEO_CONTRACT = 223
SITE_NAME = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
FOUNDING_NAME = "مصطلحات علم النفس"
SOCIAL_IMAGE = _core.BASE + "assets/brand/social-card.svg"
LOGO = _core.PATH + "assets/brand/logo-mark.svg"
MANIFEST = _core.PATH + "manifest.webmanifest"
SEARCH = _core.PATH + "opensearch.xml"


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
        result.setdefault(
            "alternateName",
            current_name if current_name and current_name != SITE_NAME else FOUNDING_NAME,
        )
        result.setdefault("url", _core.BASE)
        result.setdefault("logo", SOCIAL_IMAGE)
    return result


def shell(
    title: str,
    description: str,
    canonical: str,
    schema: dict[str, Any],
    body: str,
) -> str:
    structured = json.dumps(
        institutionalize_schema(schema),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    keywords = ",".join(topic_keywords(title, description, canonical))
    page_type = (
        "website"
        if canonical in {_core.BASE + "daily-tools/", _core.BASE + "learning-paths/"}
        else "article"
    )
    title_text = f"{title} | {SITE_NAME}"
    image_alt = f"هوية {SITE_NAME}"
    esc = _core.e
    return f'''<!doctype html><html lang="ar" dir="rtl" data-design="marshmallow-v{_core.DESIGN_CONTRACT}" data-seo="institutional-v{SEO_CONTRACT}"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title_text)}</title><meta name="description" content="{esc(description)}"><meta name="keywords" content="{esc(keywords)}">
<meta name="author" content="{esc(SITE_NAME)}"><meta name="application-name" content="{esc(SITE_NAME)}"><meta name="subject" content="الصحة النفسية والأدوات النفسية التفاعلية"><meta name="audience" content="الأفراد والأسر ومقدمو الرعاية">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><meta name="theme-color" content="#e5faf5"><meta name="color-scheme" content="light">
<link rel="canonical" href="{esc(canonical)}"><link rel="manifest" href="{MANIFEST}"><link rel="icon" href="{LOGO}" type="image/svg+xml"><link rel="apple-touch-icon" href="{LOGO}"><link rel="search" type="application/opensearchdescription+xml" title="البحث في المنصة" href="{SEARCH}"><link rel="sitemap" type="application/xml" href="{_core.BASE}sitemap.xml">
<meta property="og:type" content="{page_type}"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="{esc(SITE_NAME)}"><meta property="og:title" content="{esc(title_text)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:image" content="{SOCIAL_IMAGE}"><meta property="og:image:alt" content="{esc(image_alt)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title_text)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="{SOCIAL_IMAGE}"><meta name="twitter:image:alt" content="{esc(image_alt)}">
<script type="application/ld+json">{structured}</script><style>{_core.STYLE}</style></head><body>{body}</body></html>'''


def _expected_pages(data: dict[str, Any], site: Path) -> list[Path]:
    return (
        [site / "daily-tools" / "index.html", site / "learning-paths" / "index.html"]
        + [site / "daily-tools" / tool["slug"] / "index.html" for tool in data["tools"]]
        + [site / "learning-paths" / path["slug"] / "index.html" for path in data["paths"]]
    )


def validate_metadata(data: dict[str, Any], site: Path | None = None) -> None:
    target = Path(site or _core.SITE).resolve()
    required = (
        f'data-seo="institutional-v{SEO_CONTRACT}"',
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
    for page in _expected_pages(data, target):
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


def publish(data: dict[str, Any], site: Path | str | None = None) -> None:
    target = Path(site or _core.SITE).resolve()
    if not target.is_dir():
        raise SystemExit(f"Missing site output: {target}")
    globals()["SITE"] = target
    _core.SITE = target
    _core.shell = shell
    _core.publish(data)
    validate_metadata(data, target)


_core.shell = shell


if __name__ == "__main__":
    requested_site = Path(sys.argv[1] if len(sys.argv) > 1 else _core.SITE).resolve()
    publish(json.loads(_core.DATA.read_text(encoding="utf-8")), requested_site)
