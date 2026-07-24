from __future__ import annotations

"""غلاف SEO مؤسسي لسجل النوم المحلي.

السجل غير تشخيصي، لا تُرسل البيانات إلى خادم، ويوفر حذف البيانات.
يوضح متى تطلب المساعدة من مختص دون أن يحل محل الرعاية المهنية.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import publish_sleep_log_v49_core as _core
from scripts.publish_sleep_log_v49_core import *  # noqa: F401,F403

BASE = "https://khaledaltheeb.github.io/pterminology-site/"
PATH = "/pterminology-site/"
SITE_NAME = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SEO_CONTRACT = 219
SOCIAL_IMAGE = BASE + "assets/brand/social-card.svg"
LOGO = PATH + "assets/brand/logo-mark.svg"
CANONICAL = BASE + "daily-tools/sleep-wind-down-plan/"
TITLE = "سجل النوم المحلي — متابعة تنظيمية غير تشخيصية"
DESCRIPTION = "سجل عربي محلي اختياري لمتابعة أوقات النوم وجودته والطاقة، مع تصدير وطباعة وحذف شامل دون إرسال البيانات إلى خادم."
KEYWORDS = (
    "سجل النوم المحلي",
    "متابعة النوم",
    "روتين ما قبل النوم",
    "جودة النوم",
    "الطاقة بعد الاستيقاظ",
    "أداة نوم تفاعلية",
    "الصحة النفسية",
    "مصطلحات علم النفس",
)


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _structured_data() -> str:
    payload = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebApplication",
                "name": "سجل النوم المحلي",
                "description": DESCRIPTION,
                "applicationCategory": "HealthApplication",
                "operatingSystem": "Any",
                "inLanguage": "ar",
                "url": CANONICAL,
                "isAccessibleForFree": True,
            },
            {
                "@type": "WebPage",
                "name": TITLE,
                "description": DESCRIPTION,
                "inLanguage": "ar",
                "url": CANONICAL,
                "isPartOf": {"@id": BASE + "#website"},
            },
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _institutional_head(style: str) -> str:
    title_text = f"{TITLE} | {SITE_NAME}"
    image_alt = f"هوية {SITE_NAME}"
    return f'''<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title_text)}</title><meta name="description" content="{e(DESCRIPTION)}"><meta name="keywords" content="{e(','.join(KEYWORDS))}"><meta name="author" content="{e(SITE_NAME)}"><meta name="application-name" content="{e(SITE_NAME)}"><meta name="subject" content="النوم والصحة النفسية والمتابعة التنظيمية"><meta name="audience" content="البالغون والأسر ومقدمو الرعاية"><meta name="seo-contract" content="institutional-v{SEO_CONTRACT}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><meta name="theme-color" content="#e5faf5"><meta name="color-scheme" content="light"><link rel="canonical" href="{CANONICAL}"><link rel="manifest" href="{PATH}manifest.webmanifest"><link rel="icon" href="{LOGO}" type="image/svg+xml"><link rel="apple-touch-icon" href="{LOGO}"><link rel="search" type="application/opensearchdescription+xml" title="البحث في المنصة" href="{PATH}opensearch.xml"><link rel="sitemap" type="application/xml" href="{BASE}sitemap.xml"><meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="{e(SITE_NAME)}"><meta property="og:title" content="{e(title_text)}"><meta property="og:description" content="{e(DESCRIPTION)}"><meta property="og:url" content="{CANONICAL}"><meta property="og:image" content="{SOCIAL_IMAGE}"><meta property="og:image:alt" content="{e(image_alt)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title_text)}"><meta name="twitter:description" content="{e(DESCRIPTION)}"><meta name="twitter:image" content="{SOCIAL_IMAGE}"><meta name="twitter:image:alt" content="{e(image_alt)}"><script type="application/ld+json">{_structured_data()}</script>{style}</head>'''


def enrich_metadata() -> None:
    if not TARGET.is_file():
        raise SystemExit(f"Missing generated sleep log: {TARGET}")
    text = TARGET.read_text(encoding="utf-8")
    head_match = re.search(r"<head>.*?</head>", text, re.S)
    if not head_match:
        raise SystemExit("Sleep log head is missing")
    style_match = re.search(r"<style>.*?</style>", head_match.group(0), re.S)
    if not style_match:
        raise SystemExit("Sleep log style block is missing")
    text = text[: head_match.start()] + _institutional_head(style_match.group(0)) + text[head_match.end() :]
    TARGET.write_text(text, encoding="utf-8")
    validate_metadata()


def validate_metadata() -> None:
    text = TARGET.read_text(encoding="utf-8")
    required = (
        'name="seo-contract" content="institutional-v219"',
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
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise SystemExit(f"Sleep log metadata contract missing: {missing}")
    match = re.search(r'<meta name="keywords" content="([^"]+)">', text)
    keywords = [item.strip() for item in match.group(1).split(",")] if match else []
    if len(keywords) != 8 or len(keywords) != len(set(keywords)):
        raise SystemExit(f"Sleep log keyword contract invalid: {keywords}")
    for marker in ('<meta name="description"', '<link rel="canonical"', '<meta property="og:url"'):
        if text.count(marker) != 1:
            raise SystemExit(f"Sleep log duplicate primary metadata: {marker}")


def publish() -> None:
    _core.publish()
    enrich_metadata()


if __name__ == "__main__":
    publish()
