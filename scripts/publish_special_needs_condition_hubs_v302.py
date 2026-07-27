#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://khaledaltheeb.github.io/pterminology-site"
BP = "/pterminology-site/"
MANIFEST = ROOT / "content/v302/special-needs-condition-hubs-ar.json"
PROVIDERS = ROOT / "content/v302/special-needs-providers-ar.json"
SOURCE_OVERRIDE_FILE = ROOT / "content/v312/special-needs-condition-source-url-overrides.json"
VERSION = 302
BRIDGE_VERSION = 322
UPDATED = "2026-07-27"
MARK = "data-condition-hubs-v302"
HUB_MARKER = MARK
ENCYCLOPEDIA_BRIDGE_MARKER = "data-specialized-condition-portals-v322"
AUTISM_TOPIC_BRIDGE_MARKER = "data-autism-scientific-portal-v322"
PROVIDERS_FILE = PROVIDERS
INSERT = '<section class="section" id="method">'
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object required: {path}")
    return data


def https(url: str) -> bool:
    parsed = urlparse(str(url))
    return parsed.scheme == "https" and bool(parsed.netloc)


def normalized_host(url: str) -> str:
    return urlparse(str(url)).netloc.lower().removeprefix("www.")


def official_domain_family(organization: str, old: str, new: str) -> bool:
    old_host = normalized_host(old)
    new_host = normalized_host(new)
    if not old_host or not new_host:
        return False
    if old_host == new_host:
        return True
    if organization == "ASHA":
        return (old_host == "asha.org" or old_host.endswith(".asha.org")) and (
            new_host == "asha.org" or new_host.endswith(".asha.org")
        )
    return False


def validate_provider_data(data: dict) -> None:
    if data.get("version") != VERSION or not isinstance(data.get("providers"), list):
        raise SystemExit("Provider contract failed")
    ids: set[str] = set()
    allowed_types = set(data.get("allowed_types", []))
    allowed_specialties = set(data.get("allowed_specialties", []))
    for provider in data["providers"]:
        provider_id = str(provider.get("id", "")).strip()
        if not provider_id or provider_id in ids:
            raise SystemExit(f"Invalid provider id: {provider_id}")
        ids.add(provider_id)
        if provider.get("type") not in allowed_types:
            raise SystemExit(f"Invalid provider type: {provider_id}")
        specialties = provider.get("specialties", [])
        if not specialties or any(value not in allowed_specialties for value in specialties):
            raise SystemExit(f"Invalid specialties: {provider_id}")
        if any(provider.get(key) and not https(provider[key]) for key in ("website", "maps_url", "whatsapp_uri")):
            raise SystemExit(f"Invalid provider URL: {provider_id}")
        if provider.get("published") is True:
            missing = [
                key
                for key in data.get("required_fields_for_publication", [])
                if provider.get(key) in ("", None, [])
            ]
            if missing or provider.get("verification_status") != "verified":
                raise SystemExit(f"Unverified provider cannot publish: {provider_id}; {missing}")


validate_providers = validate_provider_data


def apply_source_url_overrides(conditions: list[dict]) -> int:
    data = read(SOURCE_OVERRIDE_FILE)
    overrides = data.get("overrides")
    if data.get("version") != 312 or data.get("language") != "ar" or not isinstance(overrides, dict):
        raise SystemExit("Source URL override contract failed")
    indexed: dict[str, dict] = {}
    for condition in conditions:
        for source in condition.get("sources", []):
            source_id = str(source.get("id", "")).strip()
            if not source_id or source_id in indexed:
                raise SystemExit(f"Duplicate source id while applying URL overrides: {source_id}")
            indexed[source_id] = source
    for source_id, item in overrides.items():
        if source_id not in indexed or not isinstance(item, dict):
            raise SystemExit(f"Unknown source URL override: {source_id}")
        source = indexed[source_id]
        old = str(item.get("from", ""))
        new = str(item.get("to", ""))
        title = str(item.get("title", "")).strip()
        organization = str(item.get("organization", "")).strip()
        if source.get("url") != old:
            raise SystemExit(f"Source URL override no longer matches its declared original: {source_id}")
        if not title:
            raise SystemExit(f"Source URL override title is required: {source_id}")
        if not https(new) or not official_domain_family(organization, old, new):
            raise SystemExit(f"Source URL override must remain on the same verified HTTPS official domain family: {source_id}")
        if organization != source.get("organization"):
            raise SystemExit(f"Source URL override organization mismatch: {source_id}")
        if not str(item.get("reason", "")).strip() or not str(item.get("verification_method", "")).strip():
            raise SystemExit(f"Source URL override requires reason and verification method: {source_id}")
        source["url"] = new
        source["title"] = title
    return len(overrides)


def load() -> tuple[dict, dict, list[dict]]:
    manifest = read(MANIFEST)
    providers = read(PROVIDERS)
    validate_provider_data(providers)
    if manifest.get("version") != VERSION or len(manifest.get("condition_files", [])) != 2:
        raise SystemExit("Condition manifest failed")
    conditions = [read(ROOT / path) for path in manifest["condition_files"]]
    if {item.get("slug") for item in conditions} != {"autism", "down-syndrome"}:
        raise SystemExit("Required condition slugs missing")
    manifest["_source_url_override_count"] = apply_source_url_overrides(conditions)
    for condition in conditions:
        if BANNED.search(json.dumps(condition, ensure_ascii=False)):
            raise SystemExit(f"Banned language: {condition.get('slug')}")
        sources = condition.get("sources", [])
        indexed = {source.get("id"): source for source in sources}
        if len(sources) < 5 or len(indexed) != len(sources):
            raise SystemExit(f"Source contract failed: {condition.get('slug')}")
        for source in sources:
            if not https(source.get("url")) or source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
                raise SystemExit(f"Invalid source: {source}")
        if len(condition.get("sections", [])) < 12:
            raise SystemExit(f"Section depth failed: {condition.get('slug')}")
        seen: set[str] = set()
        for section in condition["sections"]:
            section_id = section.get("id")
            refs = section.get("source_ids", [])
            if (
                not section_id
                or section_id in seen
                or len(section.get("points", [])) < 3
                or not refs
                or any(ref not in indexed for ref in refs)
            ):
                raise SystemExit(f"Section contract failed: {condition.get('slug')}/{section_id}")
            seen.add(section_id)
    return manifest, providers, conditions


def provider_cards(data: dict, slug: str) -> tuple[str, int]:
    rows = [
        provider
        for provider in data["providers"]
        if provider.get("published") is True
        and provider.get("verification_status") == "verified"
        and slug in provider.get("specialties", [])
    ]
    if not rows:
        return (
            '<div class="empty"><h3>الدليل المحلي قيد الإعداد والتحقق</h3>'
            '<p>لم تُنشر أسماء أو أرقام بعد. تظهر السجلات تلقائيًا بعد التحقق المهني.</p>'
            '<p><code>content/v302/special-needs-providers-ar.json</code></p></div>',
            0,
        )
    cards: list[str] = []
    for provider in sorted(rows, key=lambda item: (str(item.get("country", "")), str(item.get("city", "")), str(item.get("name_ar", "")))):
        links: list[str] = []
        if provider.get("phone_uri") and provider.get("phone_display"):
            links.append(f'<a href="tel:{e(provider["phone_uri"])}">{e(provider["phone_display"])}</a>')
        for key, label in (("whatsapp_uri", "واتساب"), ("website", "الموقع"), ("maps_url", "الخريطة")):
            if provider.get(key):
                links.append(f'<a href="{e(provider[key])}" rel="noopener noreferrer">{label}</a>')
        location = "، ".join(e(value) for value in (provider.get("city"), provider.get("governorate"), provider.get("country")) if value)
        services = "، ".join(e(value) for value in provider.get("services", [])) or "الخدمات غير مفصلة"
        cards.append(
            f'<article class="provider"><small>{e(provider.get("professional_title") or provider["type"])}</small>'
            f'<h3>{e(provider["name_ar"])}</h3><p>{services}</p><p><b>الموقع:</b> {location}</p>'
            f'<p>{" · ".join(links) or "لا توجد وسائل اتصال منشورة"}</p>'
            f'<small>تم التحقق: {e(provider.get("verified_at"))}</small></article>'
        )
    return "".join(cards), len(cards)


def schema(condition: dict, provider_count: int) -> str:
    url = f'{BASE}/special-needs/{condition["slug"]}/'
    graph: list[dict] = [
        {
            "@type": "MedicalWebPage",
            "@id": url + "#page",
            "url": url,
            "name": condition["page_title"],
            "description": condition["meta_description"],
            "inLanguage": "ar",
            "dateModified": UPDATED,
            "about": {"@id": url + "#condition"},
        },
        {
            "@type": "MedicalCondition",
            "@id": url + "#condition",
            "name": condition["short_title"],
            "alternateName": condition["english_title"],
            "description": condition["definition"],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": BASE + "/special-needs/"},
                {"@type": "ListItem", "position": 3, "name": condition["short_title"], "item": url},
            ],
        },
    ]
    if provider_count:
        graph.append({"@type": "ItemList", "@id": url + "#providers", "name": "مقدمو الخدمات", "numberOfItems": provider_count})
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


CSS = '''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:#123f43;line-height:1.9;background:linear-gradient(145deg,#fff,#effaf7)}a{color:#056a64}.wrap{width:min(1180px,92%);margin:auto}.skip{position:absolute;right:-9999px}.skip:focus{right:8px;top:8px;background:#fff;padding:8px;z-index:50}header{position:sticky;top:0;z-index:20;background:#fffffff5;border-bottom:1px solid #c6e2df}.head{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:10px 0}.brand{display:flex;align-items:center;gap:9px;text-decoration:none;font-weight:900;color:#123f43}.brand img{width:46px}nav{display:flex;gap:9px;flex-wrap:wrap}nav a{text-decoration:none;font-weight:800}.hero{padding:48px 0 24px}.hero-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:20px}.kicker{font-weight:900;color:#7d3153;margin:0}h1{font-size:clamp(2.2rem,5vw,4.4rem);line-height:1.18;margin:.15em 0}h2{font-size:clamp(1.45rem,3vw,2.2rem);line-height:1.35}.lead,.summary{color:#506d70}.panel,.section,.evidence-section,.empty,.provider,.sources{background:#fff;border:1px solid #c6e2df;border-radius:19px;padding:19px;box-shadow:0 14px 36px #104c4c18}.notice{border-right:6px solid #7d3153;background:#fff2f6;padding:13px;border-radius:13px}.actions{display:flex;gap:8px;flex-wrap:wrap}.btn{padding:9px 13px;border-radius:11px;background:#a9ebdf;color:#103f42;text-decoration:none;font-weight:900}.grid{display:grid;grid-template-columns:270px 1fr;gap:18px;align-items:start;padding:26px 0}.toc{position:sticky;top:78px;max-height:calc(100vh - 95px);overflow:auto}.toc a{display:block;padding:5px;border-bottom:1px solid #e4f0ee;text-decoration:none}.stack{display:grid;gap:15px}.title-row{display:flex;justify-content:space-between;gap:12px}.ref{font-weight:900;text-decoration:none;background:#effaf7;padding:2px 5px;border-radius:7px}.directory,.source-area{padding:34px 0}.provider-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}.provider{display:flex;flex-direction:column}.sources li{margin:1rem 0;border-bottom:1px solid #e1eeec;padding-bottom:.8rem}.sources small{display:block;color:#506d70}.level{background:#e9f8f5;border:1px solid #b8deda;border-radius:7px;padding:1px 5px;font-weight:900}code{direction:ltr;unicode-bidi:embed;background:#eef5f4;padding:2px 4px}footer{border-top:1px solid #c6e2df;padding:26px 0;color:#506d70}@media(max-width:880px){.hero-grid,.grid{grid-template-columns:1fr}.toc{position:static;max-height:none}.provider-grid{grid-template-columns:1fr 1fr}}@media(max-width:620px){.head{align-items:flex-start;flex-direction:column}.provider-grid{grid-template-columns:1fr}.title-row{display:block}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{header,.skip,.actions,.toc{display:none}.grid{display:block}.panel,.section,.provider,.sources{box-shadow:none}}'''


def knowledge_route(condition: dict) -> tuple[str, str]:
    if condition["slug"] == "autism":
        return BP + "hubs/topic-058/", "المسار الموسوعي للتوحد"
    return BP + "encyclopedia/", "الموسوعة النفسية العربية"


def render(condition: dict, provider_data: dict, status: str) -> tuple[str, int]:
    cards, provider_count = provider_cards(provider_data, condition["slug"])
    url = f'{BASE}/special-needs/{condition["slug"]}/'
    knowledge_href, knowledge_label = knowledge_route(condition)
    toc = "".join(f'<a href="#{e(section["id"])}">{e(section["title"])}</a>' for section in condition["sections"])
    sections: list[str] = []
    for section in condition["sections"]:
        refs = " ".join(f'<a class="ref" href="#{e(ref)}">[{e(ref)}]</a>' for ref in section["source_ids"])
        points = "".join(f"<li>{e(point)}</li>" for point in section["points"])
        sections.append(
            f'<section class="evidence-section" id="{e(section["id"])}"><div class="title-row"><div>'
            f'<p class="kicker">محور علمي</p><h2>{e(section["title"])}</h2></div><div>{refs}</div></div>'
            f'<p class="summary">{e(section["summary"])}</p><ul>{points}</ul></section>'
        )
    sources = "".join(
        f'<li id="{e(source["id"])}"><span class="level">{e(source["level"])}</span> '
        f'<b>{e(source["id"])} — {e(source["organization"])}</b>: '
        f'<a href="{e(source["url"])}" rel="noopener noreferrer">{e(source["title"])}</a>'
        f'<small>تاريخ المراجعة المسجل: {e(source["reviewed"])}</small></li>'
        for source in condition["sources"]
    )
    audiences = "".join(f"<li>{e(value)}</li>" for value in condition["audiences"])
    page = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(condition['page_title'])}</title><meta name="description" content="{e(condition['meta_description'])}"><meta name="keywords" content="{e(','.join(condition['keywords']))}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{url}"><link rel="alternate" hreflang="ar" href="{url}"><link rel="alternate" hreflang="x-default" href="{url}"><link rel="icon" href="{BP}assets/brand/logo-mark.svg"><meta property="og:type" content="article"><meta property="og:url" content="{url}"><meta property="og:title" content="{e(condition['page_title'])}"><meta property="og:description" content="{e(condition['meta_description'])}"><meta property="og:image" content="{BASE}/assets/brand/social-card.svg"><script type="application/ld+json">{schema(condition,provider_count)}</script><style>{CSS}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى</a><header><div class="wrap head"><a class="brand" href="{BP}"><img src="{BP}assets/brand/logo-mark.svg" alt=""><span>منصة الصحة النفسية وذوي الاحتياجات الخاصة</span></a><nav><a href="{BP}">الرئيسية</a><a href="{BP}special-needs/">ذوو الاحتياجات الخاصة</a><a href="{BP}encyclopedia/">الموسوعة</a><a href="{BP}assessment-lab/">منصة التقييم</a><a href="{BP}trust/">المنهجية</a></nav></div></header><main id="main"><section class="hero"><div class="wrap hero-grid"><div><p class="kicker">مرجع علمي عبر مراحل الحياة</p><h1>{e(condition['short_title'])}</h1><p class="lead">{e(condition['lead'])}</p><div class="actions"><a class="btn" href="#definition">التعريف</a><a class="btn" href="{knowledge_href}">{e(knowledge_label)}</a><a class="btn" href="#directory">الأطباء والمراكز</a><a class="btn" href="#sources">المراجع</a></div><p class="notice"><b>حالة المراجعة:</b> {e(status)}. آخر تحديث {UPDATED}. يلزم تحقق سريري خارجي قبل وصف الصفحة بأنها معتمدة سريريًا.</p></div><aside class="panel"><h2 id="definition">التعريف المرجعي</h2><p>{e(condition['definition'])}</p><h3>الفئات المستفيدة</h3><ul>{audiences}</ul><p><b>تنبيه:</b> الصفحة لا تشخص الحالة ولا تستبدل التقييم الفردي.</p></aside></div></section><div class="wrap grid"><aside class="panel toc"><h2>محاور الدليل</h2>{toc}</aside><article class="stack">{''.join(sections)}</article></div><section class="directory" id="directory"><div class="wrap"><p class="kicker">دليل خدمات قابل للتحديث</p><h2>أطباء ومراكز وخدمات مرتبطة بـ{e(condition['short_title'])}</h2><p>لا تمثل القائمة تزكية. تحقق من الترخيص والمؤهلات ونطاق الخدمة والتكلفة وسياسة الحماية قبل الحجز.</p><div class="provider-grid">{cards}</div></div></section><section class="source-area" id="sources"><div class="wrap sources"><p class="kicker">قابلية التتبع العلمي</p><h2>المراجع الأصلية</h2><p>S1 جهة أو إرشاد رسمي، وS4 بوابة ممارسة مهنية.</p><ol>{sources}</ol></div></section></main><footer><div class="wrap"><p>محتوى تثقيفي لا يقدم تشخيصًا أو وصفة فردية. استخدم خدمات الطوارئ المحلية عند الخطر.</p><a href="{BP}special-needs/">العودة إلى المركز</a></div></footer></body></html>'''
    return page, provider_count


def hub_section(conditions: list[dict]) -> str:
    cards = "".join(
        f'<article class="path-card"><p class="eyebrow">بوابة حالة متخصصة</p><h3>{e(condition["short_title"])}</h3>'
        f'<p>{e(condition["meta_description"])}</p><a href="{BP}special-needs/{e(condition["slug"])}/">فتح الدليل العلمي الشامل</a></article>'
        for condition in conditions
    )
    return (
        f'<section class="section" {MARK} aria-labelledby="condition-hubs-title"><div class="wrap">'
        '<p class="eyebrow">بوابات علمية متخصصة</p><h2 id="condition-hubs-title">التوحد ومتلازمة داون: أدلة مستقلة عبر مراحل الحياة</h2>'
        '<p class="section-intro">صفحتان موسعتان تربطان التعريف والتشخيص والرعاية والتدخل والتعليم والرشد بالمراجع الأصلية، مع قسم جاهز لإضافة الأطباء والمراكز بعد التحقق.</p>'
        f'<div class="path-grid">{cards}</div></div></section>'
    )


def patch_hub(site: Path, conditions: list[dict]) -> None:
    path = site / "special-needs/index.html"
    source = path.read_text(encoding="utf-8")
    section = hub_section(conditions)
    if MARK in source:
        source, count = re.subn(rf'<section class="section" {MARK}.*?</section>', section, source, count=1, flags=re.S)
    else:
        if source.count(INSERT) != 1:
            raise SystemExit("Hub insertion point failed")
        source = source.replace(INSERT, section + INSERT, 1)
        count = 1
    if count != 1 or source.count(MARK) != 1:
        raise SystemExit("Hub idempotence failed")
    path.write_text(source, encoding="utf-8")


def encyclopedia_bridge_section(conditions: list[dict]) -> str:
    cards: list[str] = []
    for condition in conditions:
        note = (
            "مرتبط أيضًا بمسار الموضوع 58 داخل الموسوعة."
            if condition["slug"] == "autism"
            else "بوابة متخصصة خارج قائمة الموضوعات المئة، مع بقاء الوصول إليها من الموسوعة."
        )
        cards.append(
            '<article class="ency-topic-v2__card">'
            '<span class="ency-topic-v2__badge">بوابة علمية متخصصة</span>'
            f'<h2><a href="{BP}special-needs/{e(condition["slug"])}/">{e(condition["short_title"])}</a></h2>'
            f'<p>{e(condition["meta_description"])}</p><small>{e(note)}</small></article>'
        )
    return (
        f'<section class="ency-topic-v2__section" {ENCYCLOPEDIA_BRIDGE_MARKER} aria-labelledby="specialized-condition-portals-title">'
        '<h2 id="specialized-condition-portals-title">بوابات علمية متخصصة للتوحد ومتلازمة داون</h2>'
        '<p>هذه البوابات أعمق من المدخل الموسوعي العام، وتجمع الإرشادات الصحية والتقييم والدعم والحالات المصاحبة والأدلة العمرية في مسارات مستقلة.</p>'
        f'<div class="ency-topic-v2__grid">{"".join(cards)}</div></section>'
    )


def patch_encyclopedia(site: Path, conditions: list[dict]) -> dict[str, object]:
    path = site / "encyclopedia/index.html"
    if not path.is_file():
        return {"available": False, "added": False, "path": None}
    source = path.read_text(encoding="utf-8")
    block = encyclopedia_bridge_section(conditions)
    if ENCYCLOPEDIA_BRIDGE_MARKER in source:
        source, count = re.subn(
            rf'<section class="ency-topic-v2__section" {ENCYCLOPEDIA_BRIDGE_MARKER}.*?</section>',
            block,
            source,
            count=1,
            flags=re.S,
        )
    else:
        anchor = '<section class="ency-topic-v2__grid" aria-label="الموضوعات المرجعية">'
        if source.count(anchor) != 1:
            raise SystemExit("Topic-first encyclopedia insertion point is missing or ambiguous")
        source = source.replace(anchor, block + anchor, 1)
        count = 1
    if count != 1 or source.count(ENCYCLOPEDIA_BRIDGE_MARKER) != 1:
        raise SystemExit("Encyclopedia condition bridge idempotence failed")
    for slug in ("autism", "down-syndrome"):
        if source.count(f'{BP}special-needs/{slug}/') != 1:
            raise SystemExit(f"Specialized condition route missing or duplicated in encyclopedia: {slug}")
    path.write_text(source, encoding="utf-8")
    return {"available": True, "added": True, "path": "encyclopedia/index.html"}


def autism_topic_bridge() -> str:
    return (
        f'<section class="ency-topic-v2__section ency-topic-v2__notice" {AUTISM_TOPIC_BRIDGE_MARKER} '
        'aria-labelledby="autism-scientific-portal-title"><h2 id="autism-scientific-portal-title">الدليل العلمي المتخصص للتوحد</h2>'
        '<p>يتناول هذا المركز الزوايا الموسوعية العشرين. وللتقييم والدعم والحالات المصاحبة والتغير المفاجئ والمتابعة عبر العمر، انتقل إلى البوابة العلمية المتخصصة.</p>'
        f'<p><a class="ency-topic-v2__button" href="{BP}special-needs/autism/">فتح بوابة التوحد العلمية</a></p></section>'
    )


def patch_autism_topic(site: Path) -> dict[str, object]:
    path = site / "hubs/topic-058/index.html"
    if not path.is_file():
        return {"available": False, "added": False, "path": None}
    source = path.read_text(encoding="utf-8")
    if 'data-topic-hub-v2="true"' not in source:
        raise SystemExit("Autism topic 58 is not using the topic-first encyclopedia contract")
    block = autism_topic_bridge()
    if AUTISM_TOPIC_BRIDGE_MARKER in source:
        source, count = re.subn(
            rf'<section class="ency-topic-v2__section ency-topic-v2__notice" {AUTISM_TOPIC_BRIDGE_MARKER}.*?</section>',
            block,
            source,
            count=1,
            flags=re.S,
        )
    else:
        anchor = '<section class="ency-topic-v2__section">'
        if source.count(anchor) < 1:
            raise SystemExit("Autism topic bridge insertion point is missing")
        source = source.replace(anchor, block + anchor, 1)
        count = 1
    if count != 1 or source.count(AUTISM_TOPIC_BRIDGE_MARKER) != 1:
        raise SystemExit("Autism topic bridge idempotence failed")
    if source.count(f'{BP}special-needs/autism/') != 1:
        raise SystemExit("Autism scientific portal link is missing or duplicated")
    path.write_text(source, encoding="utf-8")
    return {"available": True, "added": True, "path": "hubs/topic-058/index.html"}


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def sitemap(site: Path, conditions: list[dict]) -> None:
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    path = site / "sitemap-special-needs.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag.rsplit("}", 1)[-1] != "urlset":
        raise SystemExit("Sitemap must be urlset")
    for condition in conditions:
        url = f'{BASE}/special-needs/{condition["slug"]}/'
        rows = [row for row in root.findall("{*}url") if (row.findtext("{*}loc") or "").strip() == url]
        if len(rows) > 1:
            raise SystemExit(f"Duplicate sitemap URL: {url}")
        row = rows[0] if rows else ET.SubElement(root, qualify(root, "url"))
        for key, value in {"loc": url, "lastmod": UPDATED, "changefreq": "monthly", "priority": "0.92"}.items():
            node = row.find(f"{{*}}{key}")
            if node is None:
                node = ET.SubElement(row, qualify(root, key))
            node.text = value
    tree.write(path, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> dict:
    manifest, providers, conditions = load()
    pages: list[str] = []
    provider_counts: dict[str, int] = {}
    for condition in conditions:
        page, count = render(condition, providers, manifest["review_status"])
        target = site / f'special-needs/{condition["slug"]}/index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        if BANNED.search(page) or page.count("<h1") != 1 or page.count("application/ld+json") != 1 or page.count("evidence-section") < 12:
            raise SystemExit(f"Render contract failed: {target}")
        pages.append(target.relative_to(site).as_posix())
        provider_counts[condition["slug"]] = count

    patch_hub(site, conditions)
    encyclopedia_bridge = patch_encyclopedia(site, conditions)
    autism_topic_bridge_report = patch_autism_topic(site)
    sitemap(site, conditions)

    report = {
        "version": VERSION,
        "status": "passed",
        "review_status": manifest["review_status"],
        "condition_count": 2,
        "condition_slugs": [condition["slug"] for condition in conditions],
        "generated_page_count": 2,
        "generated_pages": pages,
        "provider_source": PROVIDERS.relative_to(ROOT).as_posix(),
        "published_provider_count": sum(provider_counts.values()),
        "provider_counts": provider_counts,
        "hub_section_added": True,
        "sitemap_registered": True,
        "source_count": sum(len(condition["sources"]) for condition in conditions),
        "source_url_override_count": manifest.get("_source_url_override_count", 0),
        "source_url_override_source": SOURCE_OVERRIDE_FILE.relative_to(ROOT).as_posix(),
        "encyclopedia_bridge_version": BRIDGE_VERSION,
        "encyclopedia_bridge": encyclopedia_bridge,
        "autism_topic_bridge": autism_topic_bridge_report,
        "down_syndrome_specialized_route_visible": bool(encyclopedia_bridge.get("added")),
        "updated": UPDATED,
    }
    (site / "api").mkdir(parents=True, exist_ok=True)
    (site / "api/special-needs-condition-hubs-v302.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    site = parser.parse_args().site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
