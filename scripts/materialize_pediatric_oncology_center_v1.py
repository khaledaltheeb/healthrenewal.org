#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

BASE_URL = "https://healthrenewal.org"
EDGE_URL = "https://ghljwfwqsyfnthvlzxjy.supabase.co/functions/v1/pediatric-oncology-center-catalog"
OIDC_AUDIENCE = "rawafid-pediatric-oncology-center-v1"
MARKER = "<!-- rawafid:pediatric-oncology-center:v1 -->"
REPORT = Path("api/pediatric-oncology-center-audit-v1.json")

DOMAIN_GUIDANCE: dict[str, tuple[str, tuple[str, ...], str]] = {
    "pediatric-cancer-types-diagnosis": (
        "ابدأ من التشخيص الموثق لا من قائمة أعراض عامة. هذا المسار يفصل بين اسم الورم وموقعه ودرجته ومرحلته وخصائصه الجزيئية، ثم يربط الصفحات المتخصصة دون نقل استنتاج من مرض إلى آخر.",
        ("تمييز التشخيص النسيجي والجزيئي عن المرحلة أو مجموعة الخطورة.", "فهم وظيفة الفحص: تشخيص أو تصنيف أو متابعة.", "ربط النتيجة بنوع الورم والسياق السريري قبل تفسيرها."),
        "لا تستخدم المحتوى لاستنتاج تشخيص من الأعراض أو لتفسير تقرير مرضي خارج سياقه؛ دوره تنظيم الفهم والأسئلة قبل مناقشتها مع فريق أورام الأطفال.",
    ),
    "pediatric-cancer-treatment-care": (
        "ينظم هذا المسار وسائل العلاج والرعاية السريرية وسلامة المتابعة. الجراحة والأشعة والعلاج الكيميائي والموجه والمناعي والزراعة ليست بدائل متكافئة، ومكان كل منها يتغير حسب المرض والمرحلة والبروتوكول.",
        ("فهم هدف الوسيلة العلاجية ومكانها في الخطة.", "تمييز الرعاية القياسية عن الخيار البحثي أو المشروط.", "ربط السلامة والآثار الجانبية بتعليمات المركز المعالج."),
        "لا يحتوي المسار على وصفات أو جرعات فردية. خطة الفريق المعالج هي المرجع للحالة المحددة.",
    ),
    "pediatric-cancer-supportive-rehab": (
        "يجمع الرعاية الداعمة والتأهيل وجودة الحياة: الأعراض والنوم والتعب والتغذية والنشاط والوظيفة اليومية. الهدف هو تقليل العبء والمحافظة على المشاركة بالتوازي مع علاج السرطان.",
        ("تحديد العرض أو المشكلة الوظيفية وتوقيتها وأثرها.", "فصل الإجراءات المنزلية الآمنة عن القرارات الطبية.", "طلب تقييم عند ظهور عرض جديد أو شديد أو متفاقم."),
        "لا تؤخر النصائح العامة تقييم سبب طبي محتمل. المحتوى يساعد على الملاحظة والتواصل ولا يشخّص السبب في المنزل.",
    ),
    "pediatric-cancer-psychosocial-family": (
        "يضع هذا المسار الطفل والأسرة داخل الرعاية: التواصل والدعم الانفعالي والوالدان والإخوة والتكيف مع عدم اليقين، مع مراعاة العمر والنمو واللغة والخصوصية والاختلافات الفردية.",
        ("البدء بصوت الطفل أو المراهق وما يفهمه وما يقلقه.", "حماية الروتين والعلاقات والاختيارات الممكنة.", "معرفة متى يصبح الضيق معطلًا ويحتاج تقييمًا متخصصًا."),
        "الدعم النفسي لا يعني إلغاء المشاعر الصعبة أو تقديم طمأنة غير مضمونة؛ الهدف تنظيم المعلومات والمساندة والوظيفة وطلب المساعدة عند الحاجة.",
    ),
    "pediatric-cancer-daily-life-school": (
        "يربط هذا المسار العلاج بالحياة اليومية: المدرسة واللعب والعلاقات والتنقل والدعم الاجتماعي والمالي. العودة للحياة عملية تدريجية تتغير مع العلاج والطاقة والمناعة والقدرات الوظيفية.",
        ("تنسيق الحد الأدنى اللازم من المعلومات بين الأسرة والمدرسة والفريق.", "تحديد التسهيلات حسب الوظيفة الحالية لا التشخيص وحده.", "مراجعة الخطة مع تغير المرحلة والاحتياجات."),
        "الخدمات والحقوق تختلف بين الدول؛ التفاصيل المحلية تحتاج جهة رسمية أو اختصاصيًا اجتماعيًا.",
    ),
    "pediatric-cancer-palliative-bereavement": (
        "تغطي الرعاية التلطيفية جودة الحياة والأعراض والتواصل والدعم ويمكن أن تتزامن مع علاج موجه للمرض. ويشمل المسار أيضًا الحزن والفقد ودعم الأسرة بلغة حساسة وغير اختزالية.",
        ("تحديد أهداف الرعاية وما يهم الطفل والأسرة الآن.", "التواصل الصادق المتدرج حول التغير وعدم اليقين.", "الوصول إلى فرق التلطيف والدعم النفسي والاجتماعي عند الحاجة."),
        "المحتوى لا يتنبأ بالمدة ولا يحدد قرارات نهاية الحياة؛ هذه قرارات لفريق يعرف الحالة وقيم الأسرة والسياق المحلي.",
    ),
    "pediatric-cancer-survivorship-late-effects": (
        "النجاة ليست نهاية المتابعة. يجمع هذا المسار الآثار المتأخرة والمراقبة الموجهة للمخاطر والخصوبة والنمو والصحة النفسية والتعلم والانتقال إلى رعاية البالغين.",
        ("ربط المتابعة بالتشخيص والتعرضات العلاجية السابقة.", "الاحتفاظ بملخص علاج وخطة متابعة قابلة للنقل.", "معالجة الدراسة والعمل والصحة النفسية ونمط الحياة ضمن خطة النجاة."),
        "احتمال أثر متأخر لا يعني أنه سيحدث لكل ناجٍ، ولا توجد قائمة فحوص موحدة تصلح للجميع دون خطة موجهة للمخاطر.",
    ),
    "pediatric-cancer-research-evidence": (
        "هذه طبقة قراءة الدليل: الدراسات والتجارب والطب الدقيق والمراجعات والإرشادات. لا تساوي بين أنواع الأدلة؛ المرحلة الأولى أو سلسلة الحالات لا تحمل وزن تجربة مقارنة أو مراجعة منهجية مناسبة.",
        ("تحديد تصميم الدراسة والعينة والمقارنة والنتيجة الأساسية.", "الفصل بين الدلالة الإحصائية والحجم العملي للأثر.", "قراءة القيود وهوية المصدر وحالة السحب أو التصحيح."),
        "وجود مادة في المرصد لا يعني تبني نتيجتها أو صلاحيتها للعلاج؛ الملخص يشرح الدليل ويربطه بالمصدر الأصلي للتحقق.",
    ),
    "pediatric-cancer-theses-dissertations": (
        "يعامل هذا المسار الرسائل الجامعية كطبقة بحثية قابلة للاكتشاف والنقد، لا كبديل تلقائي للدراسات المحكمة. تبقى المؤسسة والدرجة والمستودع والمعرف الدائم وحدود التحكيم واضحة.",
        ("التحقق من السجل الجامعي والمعرف الدائم.", "فحص المنهج والعينة والقيود قبل الاستنتاج.", "البحث عن نشر محكم لاحق للمشروع عند توفره."),
        "الرسائل مفيدة لاكتشاف بيانات وفجوات بحثية، لكن الاستنتاج السريري يحتاج موازنتها مع الأدلة المحكمة والإرشادات الأحدث.",
    ),
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def request_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected non-object JSON response")
    return data


def github_oidc_token() -> str:
    raw = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
    bearer = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
    if not raw or not bearer:
        raise RuntimeError("GitHub Actions OIDC environment is unavailable")
    parsed = urllib.parse.urlsplit(raw)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True) if k != "audience"]
    query.append(("audience", OIDC_AUDIENCE))
    oidc = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment))
    data = request_json(oidc, {"authorization": f"Bearer {bearer}", "accept": "application/json"})
    token = str(data.get("value") or "")
    if not token:
        raise RuntimeError("OIDC token is missing")
    return token


def edge(token: str, query: str) -> dict[str, Any]:
    return request_json(f"{EDGE_URL}?{query}", {"authorization": f"Bearer {token}", "accept": "application/json", "user-agent": "rawafid-pediatric-oncology-center/1"})


def fetch_catalog(token: str) -> dict[str, Any]:
    data = edge(token, "mode=catalog")
    if data.get("schema_version") != 1:
        raise RuntimeError("Unexpected pediatric oncology catalog schema")
    return data


def fetch_page(token: str, page_id: str) -> dict[str, Any]:
    data = edge(token, "mode=page&id=" + urllib.parse.quote(page_id))
    if not isinstance(data.get("item"), dict):
        raise RuntimeError(f"Missing page payload for {page_id}")
    return data["item"]


def json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def arabic_words(text: str) -> int:
    return sum(1 for token in re.split(r"\s+", text.strip()) if re.search(r"[ء-ي]", token))


def visible_words(source: str) -> int:
    source = re.sub(r"<(script|style|template)\b[^>]*>.*?</\1>", " ", source, flags=re.I | re.S)
    source = re.sub(r"<!--.*?-->|<[^>]+>", " ", source, flags=re.S)
    return arabic_words(html.unescape(source))


def safe_route(route: str) -> None:
    if not route.startswith("/") or route.startswith("//") or ".." in route or "\\" in route:
        raise ValueError(f"Unsafe canonical route: {route!r}")


def route_paths(root: Path, route: str) -> list[Path]:
    safe_route(route)
    relative = route.lstrip("/")
    if route.endswith("/"):
        return [root / relative / "index.html"]
    if route.endswith(".html"):
        return [root / relative]
    return [root / relative, root / relative / "index.html", root / f"{relative}.html"]


def destination(root: Path, route: str) -> Path:
    for path in route_paths(root, route):
        if path.is_file():
            return path
    return route_paths(root, route)[0]


def indexable(source: str) -> bool:
    values = re.findall(r'<meta\b[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']+)["\']', source, flags=re.I | re.S)
    return bool(values) and any("index" in value.lower() for value in values) and all("noindex" not in value.lower() for value in values)


def has_canonical(source: str, route: str) -> bool:
    target = re.escape(BASE_URL + route)
    return bool(re.search(rf'<link\b[^>]*(?:href=["\']{target}["\'][^>]*rel=["\'][^"\']*canonical|rel=["\'][^"\']*canonical[^"\']*["\'][^>]*href=["\']{target}["\'])', source, flags=re.I | re.S))


def build_model(payload: dict[str, Any]) -> dict[str, Any]:
    categories = [dict(x) for x in payload.get("categories") or [] if isinstance(x, dict)]
    items = [dict(x) for x in payload.get("items") or [] if isinstance(x, dict)]
    relations = [dict(x) for x in payload.get("relations") or [] if isinstance(x, dict)]
    if not categories or not items:
        raise ValueError("Pediatric oncology catalog is empty")
    cats = {str(x["id"]): x for x in categories}
    pages = {str(x["id"]): x for x in items}
    children: dict[str, list[str]] = defaultdict(list)
    direct: dict[str, set[str]] = {cid: set() for cid in cats}
    for cat in categories:
        parent = str(cat.get("parent_id") or "")
        if parent in cats:
            children[parent].append(str(cat["id"]))
    for rel in relations:
        cid, iid = str(rel.get("category_id") or ""), str(rel.get("content_id") or "")
        if cid in direct and iid in pages:
            direct[cid].add(iid)
    aggregate: dict[str, set[str]] = {}
    def walk(cid: str, seen: tuple[str, ...] = ()) -> set[str]:
        if cid in aggregate:
            return aggregate[cid]
        if cid in seen:
            raise ValueError("Category cycle")
        result = set(direct[cid])
        for child in children.get(cid, []):
            result |= walk(child, seen + (cid,))
        aggregate[cid] = result
        return result
    for cid in cats:
        walk(cid)
    empty = [str(cats[cid].get("slug")) for cid in cats if not aggregate[cid]]
    if empty:
        raise ValueError(f"Empty active pediatric oncology sections are forbidden: {empty}")
    roots = [cid for cid, cat in cats.items() if str(cat.get("parent_id") or "") not in cats]
    key = lambda cid: (int(cats[cid].get("sort_order") or 0), str(cats[cid].get("name_ar") or ""))
    roots.sort(key=key)
    for value in children.values(): value.sort(key=key)
    return {"categories": categories, "items": items, "relations": relations, "cats": cats, "pages": pages, "children": children, "direct": direct, "aggregate": aggregate, "roots": roots}


def ancestors(model: dict[str, Any], cid: str) -> list[dict[str, Any]]:
    out, seen = [], set()
    while cid in model["cats"] and cid not in seen:
        seen.add(cid); cat = model["cats"][cid]; out.append(cat)
        parent = str(cat.get("parent_id") or "")
        if parent not in model["cats"]: break
        cid = parent
    return list(reversed(out))


def guidance(model: dict[str, Any], cid: str) -> tuple[str, tuple[str, ...], str]:
    chain = ancestors(model, cid)
    cat = model["cats"][cid]
    root_slug = str(chain[0].get("slug") or "") if chain else str(cat.get("slug") or "")
    base = DOMAIN_GUIDANCE.get(root_slug)
    description = str(cat.get("description") or "")
    if base:
        return ((description + " " + base[0]).strip(), base[1], base[2])
    return ((description + " هذا المسار يجمع الصفحات المرتبطة مباشرة والموضوعات الثانوية دون إنشاء نسخ محتوى مكررة.").strip(), ("ابدأ بالصفحة الأقرب لسؤالك.", "راجع المصدر ونوع الدليل وحدوده.", "استخدم المحتوى لتنظيم الأسئلة لا لاتخاذ قرار فردي."), "المحتوى تثقيفي ومصدري ولا يستبدل التقييم أو القرار السريري.")


def sorted_pages(values: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(values, key=lambda x: (str(x.get("published_at") or ""), str(x.get("title") or "")), reverse=True)


def card(item: dict[str, Any]) -> str:
    kind = "بحث" if item.get("content_type") == "research" else "دليل"
    return f'<article class="card"><p class="tag">{esc(kind)} · {int(item.get("reference_count") or 0)} مصادر</p><h3><a href="{esc(item.get("canonical_url"))}">{esc(item.get("title"))}</a></h3><p>{esc(item.get("excerpt") or item.get("seo_description") or "قراءة موثقة ضمن مركز سرطان الأطفال.")}</p></article>'


def shell(title: str, description: str, route: str, body: str, schema: Any, article: bool = False) -> str:
    og_type = "article" if article else "website"
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)}</title><meta name="description" content="{esc(description[:160])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{esc(BASE_URL + route)}"><meta property="og:type" content="{og_type}"><meta property="og:site_name" content="منصة روافد"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description[:160])}"><meta property="og:url" content="{esc(BASE_URL + route)}"><script type="application/ld+json">{json_script(schema)}</script><style>body{{font-family:Tahoma,Arial,sans-serif;background:#f6fbfa;color:#163f43;margin:0;line-height:1.9}}main{{width:min(1180px,92%);margin:auto;padding:30px 0 70px}}header,section,article.page,aside{{background:#fff;border:1px solid #d0e6e2;border-radius:20px;padding:clamp(18px,4vw,32px);margin:15px 0}}h1{{font-size:clamp(2rem,5vw,3.15rem);line-height:1.3}}h2{{color:#075f5b;margin-top:1.6rem}}h3{{color:#1c6664}}a{{color:#075f5b;text-underline-offset:3px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}.card{{border:1px solid #d7eae7;border-radius:16px;padding:17px;background:#fcfefe}}.card h3{{margin:.25rem 0}}.tag,.note{{font-weight:800;color:#743756}}.stats{{display:flex;flex-wrap:wrap;gap:9px}}.stat{{background:#eaf6f3;border-radius:999px;padding:7px 12px;font-weight:800}}.notice{{border-inline-start:4px solid #075f5b;padding-inline-start:14px}}.sources li{{margin:.55rem 0;overflow-wrap:anywhere}}@media(max-width:640px){{main{{width:94%}}header,section,article.page,aside{{padding:18px;border-radius:15px}}}}</style></head><body>{MARKER}<main>{body}</main></body></html>'''


def render_section(payload: dict[str, Any], model: dict[str, Any], cid: str) -> str:
    cat = model["cats"][cid]; name = str(cat.get("name_ar") or cat.get("slug")); route = f'/sections/{cat["slug"]}/'
    chain = ancestors(model, cid); intro, focus, boundary = guidance(model, cid)
    page_ids = model["aggregate"][cid]; direct = model["direct"][cid]; child_ids = model["children"].get(cid, [])
    pages = sorted_pages(model["pages"][iid] for iid in page_ids)
    crumbs = ['<a href="/">الرئيسية</a>', '<a href="/sectors/pediatric-oncology/">مركز سرطان الأطفال</a>'] + [f'<a href="/sections/{esc(x["slug"])}/">{esc(x.get("name_ar"))}</a>' for x in chain[:-1]]
    child_cards = "".join(f'<article class="card"><p class="tag">{len(model["aggregate"][child])} صفحة ضمن الفرع</p><h3><a href="/sections/{esc(model["cats"][child]["slug"])}/">{esc(model["cats"][child].get("name_ar"))}</a></h3><p>{esc(model["cats"][child].get("description") or "")}</p></article>' for child in child_ids)
    body = f'<nav>{" ← ".join(crumbs)}</nav><header><p class="tag">مسار معرفي داخل مركز سرطان الأطفال</p><h1>{esc(name)}</h1><p>{esc(cat.get("description") or "")}</p><div class="stats"><span class="stat">{len(pages)} صفحة ضمن المسار</span><span class="stat">{len(direct)} مرتبطة مباشرة</span><span class="stat">{len(child_ids)} فروع</span></div></header><section><h2>كيف تستخدم هذا المسار؟</h2><p>{esc(intro)}</p><ul>{"".join(f"<li>{esc(x)}</li>" for x in focus)}</ul><p class="notice">{esc(boundary)}</p></section>'
    if child_ids:
        body += f'<section><h2>الموضوعات الفرعية</h2><p>يحسب كل رقم المحتوى المنشور في الفرع نفسه وفروعه، لذلك لا تظهر قيمة صفر عندما تكون الصفحات موجودة داخل الشجرة.</p><div class="grid">{child_cards}</div></section>'
    body += f'<section><h2>الصفحات المنشورة في هذا المسار</h2><p>تضم القائمة الروابط الأساسية والموضوعية الثانوية مع إزالة التكرار؛ كل بطاقة تعرض وصفًا ومصادر بدل عنوان منفرد.</p><div class="grid">{"".join(card(x) for x in pages)}</div></section><aside><h2>حدود الاستخدام</h2><p>المحتوى للتثقيف وتنظيم المعرفة. لا يقدم تشخيصًا أو خطة علاج فردية، والمصدر الأصلي وفريق أورام الأطفال هما المرجع عند التحقق أو اتخاذ قرار لحالة محددة.</p><p><a href="/sectors/pediatric-oncology/all-pages/">الفهرس الكامل للمركز</a> · <a href="/disclaimer/">إخلاء المسؤولية والتنبيهات</a></p></aside>'
    schema = {"@context":"https://schema.org","@graph":[{"@type":"CollectionPage","name":name,"description":cat.get("description") or intro,"url":BASE_URL+route,"inLanguage":"ar","numberOfItems":len(pages)},{"@type":"ItemList","numberOfItems":len(pages),"itemListElement":[{"@type":"ListItem","position":i+1,"name":str(x.get("title") or ""),"url":BASE_URL+str(x.get("canonical_url") or "")} for i,x in enumerate(pages)]}]}
    return shell(f"{name} | مركز سرطان الأطفال | روافد", str(cat.get("seo_description") or cat.get("description") or intro), route, body, schema)


def render_sector(payload: dict[str, Any], model: dict[str, Any]) -> str:
    sector = payload["sector"]; pages = sorted_pages(model["items"]); roots = model["roots"]
    root_cards = "".join(f'<article class="card"><p class="tag">{len(model["aggregate"][cid])} صفحة · {len(model["children"].get(cid, []))} فروع</p><h3><a href="/sections/{esc(model["cats"][cid]["slug"])}/">{esc(model["cats"][cid].get("name_ar"))}</a></h3><p>{esc(model["cats"][cid].get("description") or "")}</p></article>' for cid in roots)
    recent = [x for x in pages if x.get("content_type") == "research"][:12]
    route = "/sectors/pediatric-oncology/"
    body = f'<nav><a href="/">الرئيسية</a> ← <a href="/sectors/">القطاعات</a></nav><header><p class="tag">مركز معرفي متخصص</p><h1>مركز سرطان الأطفال</h1><p>{esc(sector.get("description") or "")}</p><div class="stats"><span class="stat">{len(pages)} صفحة منشورة</span><span class="stat">{len(roots)} مسارات رئيسية</span><span class="stat">{len(model["categories"])} قسمًا وفرعًا</span><span class="stat">الحد الأدنى {min(int(x.get("reference_count") or 0) for x in pages)} مصادر للصفحة</span></div><p><a href="/sectors/pediatric-oncology/all-pages/">فتح الفهرس الكامل</a></p></header><section><h2>من التشخيص إلى الحياة بعد العلاج</h2><p>بُني المركز كخريطة مترابطة لا كمجموعة عناوين. ابدأ بنوع السرطان والتشخيص، أو انتقل إلى العلاج والرعاية الداعمة والدعم النفسي والأسري والمدرسة والنجاة. تبقى الدراسات والرسائل الجامعية في طبقة دليل منفصلة حتى لا تختلط النتيجة البحثية الحديثة بالمعلومة السريرية المستقرة.</p><p class="notice">كل صفحة منشورة قابلة للاكتشاف من الشجرة أو الفهرس الكامل. الصفحة التي تخدم أكثر من موضوع تظهر في المسارات ذات الصلة دون إنشاء نسخة محتوى مكررة.</p></section><section><h2>المسارات الرئيسية</h2><div class="grid">{root_cards}</div></section><section><h2>أحدث القراءات البحثية</h2><p>اقرأ تصميم الدراسة والعينة والقيود قبل الخلاصة؛ حداثة الدراسة لا تعني تلقائيًا قوة الدليل.</p><div class="grid">{"".join(card(x) for x in recent)}</div></section><section><h2>معيار النشر داخل المركز</h2><p>يفصل المركز بين المحتوى المنشور والسجلات التحريرية والنسخ المؤرشفة. لا تدخل النسخ المكررة أو المسودات المدمجة في العد المنشور، وتستخدم التصنيفات الثانوية للربط الموضوعي دون تكرار الصفحة.</p><p>المحتوى الطبي عالي الحساسية يشرح المعرفة والدليل وحدوده بلغة عربية دقيقة، بينما تبقى القرارات الفردية للفريق المعالج.</p></section>'
    schema = {"@context":"https://schema.org","@type":"CollectionPage","name":"مركز سرطان الأطفال","description":sector.get("description"),"url":BASE_URL+route,"inLanguage":"ar","numberOfItems":len(pages)}
    return shell(str(sector.get("seo_title") or "مركز سرطان الأطفال | روافد"), str(sector.get("seo_description") or sector.get("description") or ""), route, body, schema)


def render_all(model: dict[str, Any]) -> str:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for page in model["items"]:
        cid = str(page.get("category_id") or ""); chain = ancestors(model, cid)
        groups[str(chain[0].get("name_ar") or "مسارات أخرى") if chain else "مسارات أخرى"].append(page)
    sections = "".join(f'<section><h2>{esc(name)} ({len(values)})</h2><div class="grid">{"".join(card(x) for x in sorted_pages(values))}</div></section>' for name,values in sorted(groups.items()))
    route = "/sectors/pediatric-oncology/all-pages/"
    body = f'<nav><a href="/">الرئيسية</a> ← <a href="/sectors/pediatric-oncology/">مركز سرطان الأطفال</a></nav><header><p class="tag">فهرس تغطية كامل</p><h1>جميع صفحات مركز سرطان الأطفال</h1><p>فهرس واحد لجميع الصفحات المنشورة، يعرض كل صفحة مرة واحدة وفق تصنيفها الأساسي بينما تظهر العلاقات الثانوية داخل صفحات المسارات.</p><div class="stats"><span class="stat">{len(model["items"])} صفحة منشورة</span><span class="stat">لا صفحات يتيمة</span></div></header>{sections}'
    schema = {"@context":"https://schema.org","@type":"ItemList","name":"جميع صفحات مركز سرطان الأطفال","numberOfItems":len(model["items"]),"itemListElement":[{"@type":"ListItem","position":i+1,"name":str(x.get("title") or ""),"url":BASE_URL+str(x.get("canonical_url") or "")} for i,x in enumerate(sorted_pages(model["items"]))]}
    return shell("جميع صفحات مركز سرطان الأطفال | روافد", "الفهرس الكامل لجميع صفحات مركز سرطان الأطفال المنشورة في روافد، منظمة حسب المسارات مع وصف مختصر ومصادر لكل مادة.", route, body, schema)


def markdown_html(text: str) -> str:
    out, para, items, kind = [], [], [], "ul"
    def flush_para():
        if para:
            value = " ".join(x.strip() for x in para if x.strip()).strip(); para.clear()
            if value: out.append(f"<p>{esc(value)}</p>")
    def flush_list():
        if items:
            out.append(f'<{kind}>' + ''.join(f'<li>{esc(x)}</li>' for x in items) + f'</{kind}>'); items.clear()
    for raw in text.replace("\r\n","\n").replace("\r","\n").split("\n"):
        line = raw.strip()
        if not line: flush_para(); flush_list(); continue
        h = re.match(r"^(#{2,4})\s+(.+)$", line)
        if h: flush_para(); flush_list(); level=len(h.group(1)); out.append(f'<h{level}>{esc(h.group(2))}</h{level}>'); continue
        b = re.match(r"^[-*]\s+(.+)$", line); n = re.match(r"^\d+[.)]\s+(.+)$", line)
        if b or n:
            flush_para(); wanted="ol" if n else "ul"
            if items and wanted != kind: flush_list()
            kind=wanted; items.append((n or b).group(1)); continue
        flush_list(); para.append(line)
    flush_para(); flush_list(); return "\n".join(out)


def refs_html(item: dict[str, Any]) -> str:
    out=[]
    for ref in item.get("references_json") or []:
        if not isinstance(ref, dict): continue
        url=str(ref.get("url") or "")
        if not url.startswith(("https://","http://")): continue
        label=str(ref.get("title") or ref.get("publisher") or ref.get("doi") or ref.get("pmid") or url)
        out.append(f'<li><a href="{esc(url)}" rel="noopener noreferrer">{esc(label)}</a></li>')
    return "".join(out)


def render_page(item: dict[str, Any], model: dict[str, Any]) -> str:
    route=str(item["canonical_url"]); title=str(item.get("title") or ""); desc=str(item.get("seo_description") or item.get("excerpt") or "قراءة موثقة ضمن مركز سرطان الأطفال.")
    cid=str(item.get("category_id") or ""); cat=model["cats"].get(cid); cat_name=str(cat.get("name_ar") or "مركز سرطان الأطفال") if cat else "مركز سرطان الأطفال"; cat_slug=str(cat.get("slug") or "") if cat else ""
    refs=item.get("references_json") if isinstance(item.get("references_json"),list) else []
    citations=[str(r.get("url")) for r in refs if isinstance(r,dict) and str(r.get("url") or "").startswith(("http://","https://"))]
    kind="ScholarlyArticle" if item.get("content_type")=="research" else "Article"
    schema={"@context":"https://schema.org","@type":kind,"headline":title,"description":desc,"url":BASE_URL+route,"inLanguage":"ar","datePublished":str(item.get("published_at") or "")[:10],"dateModified":str(item.get("updated_at") or item.get("published_at") or "")[:10],"author":{"@type":"Organization","name":str(item.get("author_display_name") or "فريق تحرير منصة روافد")},"publisher":{"@type":"Organization","name":"منصة روافد","url":BASE_URL+"/"},"citation":citations}
    note="هذه قراءة بحثية؛ نتيجة دراسة منفردة لا تساوي توصية علاجية." if item.get("content_type")=="research" else "هذا دليل تثقيفي عام ولا يحدد تشخيصًا أو خطة علاج فردية."
    related=set(model["direct"].get(cid,set())); related.discard(str(item.get("id"))); related_cards="".join(card(model["pages"][x]) for x in list(related)[:6] if x in model["pages"])
    body=f'<nav><a href="/">الرئيسية</a> ← <a href="/sectors/pediatric-oncology/">مركز سرطان الأطفال</a>{(f" ← <a href=/sections/{esc(cat_slug)}/>{esc(cat_name)}</a>" if cat_slug else "")}</nav><header><p class="tag">{esc(cat_name)}</p><h1>{esc(title)}</h1><p>{esc(item.get("excerpt") or desc)}</p><p class="notice">{esc(note)}</p></header><article class="page">{markdown_html(str(item.get("body_text") or ""))}</article><section><h2>المصادر الأصلية والمراجع</h2><ol class="sources">{refs_html(item)}</ol></section>'
    if related_cards: body += f'<section><h2>قراءات مرتبطة</h2><div class="grid">{related_cards}</div></section>'
    body += '<aside><p><a href="/sectors/pediatric-oncology/">العودة إلى المركز</a> · <a href="/disclaimer/">إخلاء المسؤولية والتنبيهات</a></p></aside>'
    return shell(f"{title} | روافد", desc, route, body, schema, True)


def repair_reason(root: Path, item: dict[str, Any]) -> tuple[str | None, Path]:
    route=str(item.get("canonical_url") or ""); found=next((p for p in route_paths(root,route) if p.is_file()),None); target=found or destination(root,route)
    if found is None: return "missing", target
    try: source=found.read_text(encoding="utf-8")
    except UnicodeDecodeError: return "non-utf8", target
    floor=max(700,int(int(item.get("arabic_word_count") or 0)*0.60)); actual=visible_words(source)
    if actual < floor: return f"thin:{actual}<{floor}", target
    if not indexable(source): return "not-indexable", target
    if not has_canonical(source,route): return "canonical-mismatch", target
    if len(re.findall(r"<h1\b",source,re.I)) != 1: return "h1-contract", target
    return None,target


def write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(source,encoding="utf-8",newline="\n")


def materialize(root: Path, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    root=root.resolve(); model=build_model(payload); quality=payload.get("quality") or {}
    if quality.get("duplicate_canonicals") or quality.get("missing_titles") or quality.get("missing_canonicals") or quality.get("missing_seo"): raise ValueError(f"Catalog quality failure: {quality}")
    if int(quality.get("minimum_arabic_words") or 0)<1000 or int(quality.get("minimum_references") or 0)<3: raise ValueError(f"Published page quality floor failed: {quality}")
    repairs=[]
    for meta in model["items"]:
        reason,target=repair_reason(root,meta)
        if reason:
            page=fetch_page(token,str(meta["id"])); write(target,render_page(page,model)); repairs.append({"slug":meta["slug"],"canonical_url":meta["canonical_url"],"reason":reason,"destination":target.relative_to(root).as_posix()})
    for cat in model["categories"]: write(root/"sections"/str(cat["slug"])/"index.html",render_section(payload,model,str(cat["id"])))
    write(root/"sectors"/"pediatric-oncology"/"index.html",render_sector(payload,model)); write(root/"sectors"/"pediatric-oncology"/"all-pages"/"index.html",render_all(model))
    failures={"missing_pages":[],"thin_pages":[],"not_indexable_pages":[],"canonical_mismatches":[],"zero_sections":[],"thin_sections":[]}
    for meta in model["items"]:
        found=next((p for p in route_paths(root,str(meta["canonical_url"])) if p.is_file()),None)
        if not found: failures["missing_pages"].append(meta["canonical_url"]); continue
        source=found.read_text(encoding="utf-8"); floor=max(700,int(int(meta.get("arabic_word_count") or 0)*0.60)); words=visible_words(source)
        if words<floor: failures["thin_pages"].append({"route":meta["canonical_url"],"words":words,"floor":floor})
        if not indexable(source): failures["not_indexable_pages"].append(meta["canonical_url"])
        if not has_canonical(source,str(meta["canonical_url"])): failures["canonical_mismatches"].append(meta["canonical_url"])
    section_quality=[]
    for cat in model["categories"]:
        cid=str(cat["id"]); route=f'/sections/{cat["slug"]}/'; count=len(model["aggregate"][cid]); path=root/"sections"/str(cat["slug"])/"index.html"; words=visible_words(path.read_text(encoding="utf-8"))
        if count==0: failures["zero_sections"].append(route)
        if words<220: failures["thin_sections"].append({"route":route,"words":words})
        section_quality.append({"route":route,"aggregate_pages":count,"direct_pages":len(model["direct"][cid]),"child_sections":len(model["children"].get(cid,[])),"visible_arabic_words":words})
    status="passed" if all(not v for v in failures.values()) else "failed"
    report={"schema_version":1,"status":status,"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"source_generated_at":payload.get("generated_at"),"policy":"Supabase pediatric-oncology catalog is authoritative; regenerate every active section; aggregate descendant and secondary-category content; repair missing/thin/non-indexable/canonical-broken published pages; never publish archived or consolidated drafts.","published_pages":len(model["items"]),"active_categories":len(model["categories"]),"top_level_categories":len(model["roots"]),"minimum_database_arabic_words":quality.get("minimum_arabic_words"),"minimum_database_references":quality.get("minimum_references"),"repairs_applied":len(repairs),"repairs":repairs,"sections_generated":len(model["categories"]),"section_quality":section_quality,"failures":failures}
    write(root/REPORT,json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    if status!="passed": raise ValueError(f"Pediatric oncology center publication gate failed: {failures}")
    return report


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--root",default="."); args=parser.parse_args(); token=github_oidc_token(); payload=fetch_catalog(token); report=materialize(Path(args.root),token,payload); print(json.dumps({k:report[k] for k in ("status","published_pages","active_categories","repairs_applied")},ensure_ascii=False)); return 0

if __name__ == "__main__": raise SystemExit(main())
