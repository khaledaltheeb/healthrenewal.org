#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://khaledaltheeb.github.io/pterminology-site"
DEFAULT_REGISTRY = ROOT / "content" / "course-import" / "registry.json"
DEFAULT_FEEDS = ROOT / "content" / "course-import" / "feeds"
REGISTRY_SCHEMA = ROOT / "api" / "v1" / "course-provider-registry.schema.json"
COURSE_SCHEMA = ROOT / "api" / "v1" / "courses.schema.json"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,120}$")
PROVIDER_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,79}$")
HOST_RE = re.compile(r"^[A-Za-z0-9.-]+$")
LANG_RE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
HTML_RE = re.compile(r"<[^>]+>")
DELIVERY = {"online", "in_person", "hybrid", "self_paced"}
STATUS = {"scheduled", "open", "closed", "archived"}


def fail(message: str) -> None:
    raise SystemExit(message)


def clean(value: Any, field: str, *, minimum: int = 0, maximum: int = 10000) -> str:
    if not isinstance(value, str):
        fail(f"{field} must be a string")
    text = " ".join(value.split()).strip()
    if not minimum <= len(text) <= maximum:
        fail(f"{field} length is outside {minimum}..{maximum}")
    if HTML_RE.search(text):
        fail(f"{field} must not contain HTML")
    return text


def https_url(value: Any, field: str, allowed_hosts: set[str] | None = None) -> str:
    url = clean(value, field, minimum=8, maximum=2048)
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        fail(f"{field} must be a credential-free HTTPS URL")
    if allowed_hosts is not None and host not in allowed_hosts:
        fail(f"{field} host is not authorized: {host}")
    return url


def iso_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(clean(value, field, minimum=10, maximum=10))
    except ValueError as exc:
        fail(f"{field} must be an ISO date: {exc}")


def iso_datetime(value: Any, field: str) -> str:
    raw = clean(value, field, minimum=16, maximum=40)
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        fail(f"{field} must be an ISO date-time: {exc}")
    return raw


def load_json(path: Path, field: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"Cannot read {field} from {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{field} must be a JSON object")
    return value


def validate_registry(path: Path) -> dict[str, Any]:
    data = load_json(path, "provider registry")
    if data.get("registryVersion") != "1.0" or data.get("policy") != "permission_required":
        fail("Provider registry contract is invalid")
    iso_date(data.get("updatedAt"), "registry.updatedAt")
    providers = data.get("providers")
    if not isinstance(providers, list) or len(providers) > 500:
        fail("registry.providers must be an array with at most 500 entries")
    seen: set[str] = set()
    today = date.today()
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(providers):
        if not isinstance(item, dict):
            fail(f"registry.providers[{index}] must be an object")
        provider_id = clean(item.get("id"), f"provider[{index}].id", minimum=2, maximum=80)
        if not PROVIDER_ID_RE.fullmatch(provider_id) or provider_id in seen:
            fail(f"Invalid or duplicate provider id: {provider_id}")
        seen.add(provider_id)
        status = item.get("status")
        if status not in {"authorized", "suspended", "revoked", "expired"}:
            fail(f"Invalid provider status for {provider_id}")
        authorization = item.get("authorization")
        feed = item.get("feed")
        rights = item.get("rights")
        if not all(isinstance(value, dict) for value in (authorization, feed, rights)):
            fail(f"Provider {provider_id} is missing authorization, feed or rights")
        verified = iso_date(authorization.get("verifiedAt"), f"{provider_id}.authorization.verifiedAt")
        expires_raw = authorization.get("expiresAt")
        expires = iso_date(expires_raw, f"{provider_id}.authorization.expiresAt") if expires_raw else None
        if verified > today:
            fail(f"Provider {provider_id} authorization verification date is in the future")
        if status == "authorized" and expires is not None and expires < today:
            fail(f"Provider {provider_id} authorization has expired")
        allowed_hosts_raw = feed.get("allowedHosts")
        if not isinstance(allowed_hosts_raw, list) or not allowed_hosts_raw:
            fail(f"Provider {provider_id} requires allowedHosts")
        allowed_hosts = {clean(host, f"{provider_id}.allowedHost", minimum=3, maximum=253).lower() for host in allowed_hosts_raw}
        if any(not HOST_RE.fullmatch(host) for host in allowed_hosts):
            fail(f"Provider {provider_id} contains an invalid allowed host")
        max_bytes = feed.get("maxBytes")
        if not isinstance(max_bytes, int) or not 1024 <= max_bytes <= 10 * 1024 * 1024:
            fail(f"Provider {provider_id} maxBytes is invalid")
        checksum = feed.get("sha256")
        if checksum is not None and (not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum)):
            fail(f"Provider {provider_id} sha256 is invalid")
        if feed.get("format") != "authorized-course-feed-v1":
            fail(f"Provider {provider_id} feed format is unsupported")
        if rights.get("metadataReuse") is not True or rights.get("contentReuse") is not False:
            fail(f"Provider {provider_id} rights must allow metadata and forbid course-content copying")
        normalized.append({
            "id": provider_id,
            "name": clean(item.get("name"), f"{provider_id}.name", minimum=2, maximum=160),
            "website": https_url(item.get("website"), f"{provider_id}.website"),
            "status": status,
            "authorization": {
                "evidenceUrl": https_url(authorization.get("evidenceUrl"), f"{provider_id}.authorization.evidenceUrl"),
                "license": clean(authorization.get("license"), f"{provider_id}.authorization.license", minimum=2, maximum=200),
                "verifiedAt": verified.isoformat(),
                "expiresAt": expires.isoformat() if expires else None,
            },
            "feed": {
                "url": https_url(feed.get("url"), f"{provider_id}.feed.url", allowed_hosts),
                "allowedHosts": sorted(allowed_hosts),
                "maxBytes": max_bytes,
                "sha256": checksum,
            },
            "rights": {
                "metadataReuse": True,
                "contentReuse": False,
                "attributionRequired": bool(rights.get("attributionRequired")),
                "attributionText": clean(rights.get("attributionText", ""), f"{provider_id}.rights.attributionText", maximum=500),
            },
        })
    return {**data, "providers": normalized}


class RestrictedRedirect(HTTPRedirectHandler):
    def __init__(self, allowed_hosts: set[str]) -> None:
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Request | None:
        https_url(newurl, "redirect URL", self.allowed_hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def remote_feed(provider: dict[str, Any]) -> bytes:
    approved = {item.strip() for item in os.environ.get("COURSE_IMPORT_APPROVED_PROVIDERS", "").split(",") if item.strip()}
    if os.environ.get("COURSE_IMPORT_NETWORK_ENABLED") != "1" or provider["id"] not in approved:
        fail(f"Remote import for {provider['id']} requires explicit environment approval")
    allowed = set(provider["feed"]["allowedHosts"])
    opener = build_opener(RestrictedRedirect(allowed))
    request = Request(provider["feed"]["url"], headers={"Accept": "application/json", "User-Agent": "pterminology-authorized-course-import/1.0"})
    try:
        with opener.open(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"application/json", "application/problem+json", "text/json"}:
                fail(f"Provider {provider['id']} returned unsupported content type: {content_type}")
            payload = response.read(provider["feed"]["maxBytes"] + 1)
    except (HTTPError, URLError, TimeoutError) as exc:
        fail(f"Remote feed request failed for {provider['id']}: {exc}")
    if len(payload) > provider["feed"]["maxBytes"]:
        fail(f"Remote feed exceeds maxBytes for {provider['id']}")
    return payload


def feed_bytes(provider: dict[str, Any], feeds_dir: Path, fetch_remote: bool) -> tuple[bytes, str]:
    local = feeds_dir / f"{provider['id']}.json"
    if local.is_file():
        payload = local.read_bytes()
        if len(payload) > provider["feed"]["maxBytes"]:
            fail(f"Local feed exceeds maxBytes for {provider['id']}")
        source = local.relative_to(ROOT).as_posix() if local.is_relative_to(ROOT) else str(local)
    elif fetch_remote:
        payload = remote_feed(provider)
        source = provider["feed"]["url"]
    else:
        fail(f"Authorized provider {provider['id']} has no local feed and remote fetching is disabled")
    digest = hashlib.sha256(payload).hexdigest()
    expected = provider["feed"].get("sha256")
    if expected and digest != expected:
        fail(f"Feed checksum mismatch for {provider['id']}")
    return payload, source


def string_list(value: Any, field: str, limit: int, item_limit: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > limit:
        fail(f"{field} must be an array with at most {limit} items")
    return [clean(item, f"{field}[]", maximum=item_limit) for item in value]


def validate_feed(payload: bytes, provider: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail(f"Invalid JSON feed for {provider['id']}: {exc}")
    if not isinstance(data, dict) or data.get("feedVersion") != "1.0":
        fail(f"Feed version is invalid for {provider['id']}")
    feed_provider = data.get("provider")
    authorization = data.get("authorization")
    courses = data.get("courses")
    if not isinstance(feed_provider, dict) or feed_provider.get("id") != provider["id"]:
        fail(f"Feed provider identity mismatch for {provider['id']}")
    if not isinstance(authorization, dict) or authorization.get("status") != "authorized":
        fail(f"Feed authorization status is invalid for {provider['id']}")
    for field in ("evidenceUrl", "license", "verifiedAt"):
        if authorization.get(field) != provider["authorization"].get(field):
            fail(f"Feed authorization {field} does not match registry for {provider['id']}")
    if not isinstance(courses, list) or not 1 <= len(courses) <= 5000:
        fail(f"Feed for {provider['id']} must contain 1..5000 courses")
    allowed_hosts = set(provider["feed"]["allowedHosts"])
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, course in enumerate(courses):
        if not isinstance(course, dict):
            fail(f"Course {index} for {provider['id']} must be an object")
        course_id = clean(course.get("id"), f"course[{index}].id", minimum=1, maximum=120)
        if not ID_RE.fullmatch(course_id) or course_id in seen:
            fail(f"Invalid or duplicate course id for {provider['id']}: {course_id}")
        seen.add(course_id)
        language = clean(course.get("language"), f"{course_id}.language", minimum=2, maximum=5)
        if not LANG_RE.fullmatch(language):
            fail(f"Invalid language for {provider['id']}/{course_id}")
        delivery = course.get("deliveryMode")
        status = course.get("status")
        if delivery not in DELIVERY or status not in STATUS:
            fail(f"Invalid delivery mode or status for {provider['id']}/{course_id}")
        rights = course.get("rights")
        if not isinstance(rights, dict) or rights.get("metadataReuse") is not True or rights.get("contentReuse", False) is not False:
            fail(f"Course rights are invalid for {provider['id']}/{course_id}")
        price = course.get("price")
        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0):
            fail(f"Invalid price for {provider['id']}/{course_id}")
        currency = course.get("currency")
        if currency is not None and (not isinstance(currency, str) or not CURRENCY_RE.fullmatch(currency)):
            fail(f"Invalid currency for {provider['id']}/{course_id}")
        if price is not None and currency is None:
            fail(f"Currency is required when price is present for {provider['id']}/{course_id}")
        item = {
            "id": course_id,
            "providerId": provider["id"],
            "providerName": clean(course.get("providerName", provider["name"]), f"{course_id}.providerName", minimum=2, maximum=160),
            "title": clean(course.get("title"), f"{course_id}.title", minimum=3, maximum=220),
            "summary": clean(course.get("summary", ""), f"{course_id}.summary", maximum=1500),
            "language": language,
            "canonicalUrl": https_url(course.get("canonicalUrl"), f"{course_id}.canonicalUrl", allowed_hosts),
            "enrollmentUrl": https_url(course.get("enrollmentUrl"), f"{course_id}.enrollmentUrl", allowed_hosts),
            "imageUrl": https_url(course.get("imageUrl"), f"{course_id}.imageUrl", allowed_hosts) if course.get("imageUrl") else None,
            "instructors": string_list(course.get("instructors"), f"{course_id}.instructors", 50, 160),
            "categories": string_list(course.get("categories"), f"{course_id}.categories", 30, 100),
            "audience": string_list(course.get("audience"), f"{course_id}.audience", 20, 120),
            "deliveryMode": delivery,
            "price": price,
            "currency": currency,
            "startsAt": iso_datetime(course.get("startsAt"), f"{course_id}.startsAt") if course.get("startsAt") else None,
            "endsAt": iso_datetime(course.get("endsAt"), f"{course_id}.endsAt") if course.get("endsAt") else None,
            "duration": clean(course.get("duration", ""), f"{course_id}.duration", maximum=120) or None,
            "status": status,
            "updatedAt": iso_datetime(course.get("updatedAt"), f"{course_id}.updatedAt"),
            "attributionText": clean(rights.get("attributionText", provider["rights"].get("attributionText", "")), f"{course_id}.attributionText", maximum=500),
        }
        output.append(item)
    return output


def upsert_sitemap(site: Path, course_count: int) -> str:
    child = site / "sitemap-courses.xml"
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}urlset")
    node = ET.SubElement(root, f"{{{ns}}}url")
    ET.SubElement(node, f"{{{ns}}}loc").text = f"{BASE}/courses/"
    ET.SubElement(node, f"{{{ns}}}lastmod").text = date.today().isoformat()
    ET.SubElement(node, f"{{{ns}}}changefreq").text = "daily" if course_count else "monthly"
    ET.SubElement(node, f"{{{ns}}}priority").text = "0.75"
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)

    main = site / "sitemap.xml"
    if not main.is_file():
        fail("Main sitemap is missing")
    tree = ET.parse(main)
    main_root = tree.getroot()
    mode = main_root.tag.rsplit("}", 1)[-1]
    child_url = f"{BASE}/sitemap-courses.xml"
    if mode == "sitemapindex":
        values = [(n.text or "").strip() for n in main_root.findall("{*}sitemap/{*}loc")]
        if child_url not in values:
            item = ET.SubElement(main_root, f"{{{ns}}}sitemap")
            ET.SubElement(item, f"{{{ns}}}loc").text = child_url
            ET.SubElement(item, f"{{{ns}}}lastmod").text = date.today().isoformat()
    elif mode == "urlset":
        values = [(n.text or "").strip() for n in main_root.findall("{*}url/{*}loc")]
        page_url = f"{BASE}/courses/"
        if page_url not in values:
            item = ET.SubElement(main_root, f"{{{ns}}}url")
            ET.SubElement(item, f"{{{ns}}}loc").text = page_url
            ET.SubElement(item, f"{{{ns}}}lastmod").text = date.today().isoformat()
    else:
        fail(f"Unsupported main sitemap mode: {mode}")
    tree.write(main, encoding="utf-8", xml_declaration=True)
    return mode


def render_catalog(courses: list[dict[str, Any]], providers: list[dict[str, Any]]) -> str:
    cards = []
    for course in courses:
        details = " · ".join(filter(None, [course["providerName"], course["language"], course["deliveryMode"], course.get("duration")]))
        price = "مجاني أو غير محدد" if course["price"] is None else f"{course['price']:g} {course['currency']}"
        cards.append(f'''<article class="card"><p class="eyebrow">{html.escape(details)}</p><h2>{html.escape(course["title"])}</h2><p>{html.escape(course["summary"] or "راجع صفحة المزود للتفاصيل الكاملة.")}</p><p><strong>السعر المعلن:</strong> {html.escape(price)} · <strong>الحالة:</strong> {html.escape(course["status"])}</p><p><a href="{html.escape(course["canonicalUrl"], quote=True)}" rel="noopener noreferrer">صفحة الدورة الأصلية</a> · <a href="{html.escape(course["enrollmentUrl"], quote=True)}" rel="noopener noreferrer">التسجيل لدى المزود</a></p>{f'<p class="attribution">{html.escape(course["attributionText"])}</p>' if course["attributionText"] else ''}</article>''')
    body = "".join(cards) if cards else '<section class="empty"><h2>لا توجد حاليًا تغذية دورات مخولة منشورة</h2><p>لا تعرض المنصة أي دورة خارجية قبل توثيق هوية المزود والإذن والترخيص وحقوق إعادة استخدام البيانات الوصفية.</p></section>'
    item_list = [{"@type": "Course", "name": item["title"], "url": item["canonicalUrl"], "provider": {"@type": "Organization", "name": item["providerName"]}} for item in courses]
    schema = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": "دليل الدورات المخولة", "url": f"{BASE}/courses/", "mainEntity": {"@type": "ItemList", "numberOfItems": len(item_list), "itemListElement": item_list}}, ensure_ascii=False).replace("</", "<\\/")
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>دليل الدورات المخولة | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title><meta name="description" content="دليل دورات عربي يعرض البيانات الوصفية للدورات من مزودين ذوي إذن موثق فقط، مع الروابط الأصلية والترخيص والحدود المهنية."><meta name="keywords" content="دورات علم النفس,دورات الصحة النفسية,دورات التربية الخاصة,دورات ذوي الاحتياجات الخاصة,دورات معتمدة,تدريب نفسي"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}/courses/"><meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="دليل الدورات المخولة"><meta property="og:description" content="بيانات دورات من مصادر يوجد إذن موثق لاستيراد بياناتها الوصفية فقط."><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema}</script><style>:root{{--ink:#153f45;--muted:#526f73;--brand:#08766e;--line:#c5e5e1;--soft:#effaf8;--pink:#fff1f6}}*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.85;color:var(--ink);background:linear-gradient(145deg,#fff,var(--soft))}}.wrap{{width:min(1120px,92%);margin:auto}}header,footer{{padding:24px 0}}nav{{display:flex;gap:10px;flex-wrap:wrap}}a{{color:#066b65;font-weight:800}}main{{padding:20px 0 60px}}h1{{font-size:clamp(2rem,5vw,4rem)}}.notice,.card,.empty{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:22px;margin:16px 0}}.notice{{border-right:6px solid #93466b;background:var(--pink)}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:15px}}.eyebrow,.attribution{{color:var(--muted)}}@media(max-width:760px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><div class="wrap"><header><nav><a href="/pterminology-site/">الرئيسية</a><a href="/pterminology-site/api/">واجهة API</a><a href="/pterminology-site/trust/">الثقة والمنهجية</a></nav></header><main><p>تكامل دورات بإذن موثق</p><h1>دليل الدورات المخولة</h1><section class="notice"><h2>ما الذي تعرضه المنصة؟</h2><p>نعرض بيانات وصفية وروابط أصلية فقط. لا ننسخ محتوى الدورة أو الفيديو أو الملفات أو الاختبارات. التسجيل والدفع — إن وجدا — يتمان لدى المزود الأصلي، ولا يعني الإدراج اعتماد المنصة لجودة الدورة.</p><p><strong>المزودون المخولون المنشورون:</strong> {len(providers)} · <strong>الدورات:</strong> {len(courses)}</p></section><div class="grid">{body}</div></main><footer><p>منصة الصحة النفسية وذوي الاحتياجات الخاصة — معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</p></footer></div></body></html>'''


def publish(site: Path, registry_path: Path, feeds_dir: Path, fetch_remote: bool) -> dict[str, Any]:
    if not site.is_dir():
        fail(f"Site directory does not exist: {site}")
    registry = validate_registry(registry_path)
    active = [item for item in registry["providers"] if item["status"] == "authorized"]
    courses: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    global_ids: set[str] = set()
    for provider in active:
        payload, source = feed_bytes(provider, feeds_dir, fetch_remote)
        items = validate_feed(payload, provider)
        for course in items:
            global_id = f"{provider['id']}:{course['id']}"
            if global_id in global_ids:
                fail(f"Duplicate global course id: {global_id}")
            global_ids.add(global_id)
            course["globalId"] = global_id
            courses.append(course)
        sources.append({"providerId": provider["id"], "source": source, "sha256": hashlib.sha256(payload).hexdigest(), "courses": len(items)})
    courses.sort(key=lambda item: (item["status"] != "open", item["providerName"].casefold(), item["title"].casefold()))
    api_v1 = site / "api" / "v1"
    api_v1.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REGISTRY_SCHEMA, api_v1 / REGISTRY_SCHEMA.name)
    shutil.copy2(COURSE_SCHEMA, api_v1 / COURSE_SCHEMA.name)
    catalog = {
        "apiVersion": "1.0.0",
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "published" if courses else "no-authorized-feeds",
        "providerCount": len(active),
        "courseCount": len(courses),
        "policy": "permission_required",
        "contentReuse": False,
        "courses": courses,
    }
    (api_v1 / "courses.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    page = site / "courses" / "index.html"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(render_catalog(courses, active), encoding="utf-8")
    sitemap_mode = upsert_sitemap(site, len(courses))
    report = {
        "version": 218,
        "status": "passed",
        "registry": registry_path.relative_to(ROOT).as_posix() if registry_path.is_relative_to(ROOT) else str(registry_path),
        "registeredProviders": len(registry["providers"]),
        "authorizedProviders": len(active),
        "courseCount": len(courses),
        "remoteFetchEnabled": fetch_remote,
        "networkApprovalRequired": True,
        "metadataOnly": True,
        "contentReuse": False,
        "sitemapMode": sitemap_mode,
        "sources": sources,
        "outputs": ["api/v1/courses.json", "courses/index.html", "sitemap-courses.xml"],
    }
    api = site / "api"
    (api / "course-import-v218.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Import authorized course metadata only")
    parser.add_argument("site", type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--feeds-dir", type=Path, default=DEFAULT_FEEDS)
    parser.add_argument("--fetch-remote", action="store_true")
    args = parser.parse_args()
    publish(args.site.resolve(), args.registry.resolve(), args.feeds_dir.resolve(), args.fetch_remote)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
