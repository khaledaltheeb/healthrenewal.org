from __future__ import annotations

import html
import json
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://healthrenewal.org/"
PATH_PREFIX = "/"
CLAIMS_PATH = ROOT / "data" / "verified-institutional-claims.json"
URGENT_PATH = ROOT / "data" / "urgent-help-governance.json"
DISABILITY_PATH = ROOT / "data" / "disability-dignity-safety.json"


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"Missing trust policy source: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_sources(
    claims: dict[str, Any],
    urgent: dict[str, Any],
    disability: dict[str, Any],
) -> None:
    if claims.get("policy", {}).get("default_publishable") is not False:
        raise SystemExit("Institutional claims registry must default to deny")
    if urgent.get("default_publishable") is not False:
        raise SystemExit("Urgent-help governance must default to deny")
    if disability.get("default_publishable") is not False:
        raise SystemExit("Disability dignity policy must default to deny")
    if claims.get("policy", {}).get("required_status_for_publication") != "verified":
        raise SystemExit("Institutional claims publication status must be verified")
    if urgent.get("services"):
        for entry in urgent["services"]:
            if entry.get("status") != "verified":
                raise SystemExit("Unverified urgent-help service found in public source")
    if disability.get("review_status") not in {"needs-external-review", "externally-reviewed"}:
        raise SystemExit("Disability policy review status is missing or invalid")


def latest_date(*values: str) -> str:
    valid = sorted(value for value in values if isinstance(value, str) and len(value) == 10)
    return valid[-1] if valid else date.today().isoformat()


def public_status_label(value: str) -> str:
    labels = {
        "needs-external-review": "تحتاج مراجعة خارجية متخصصة",
        "externally-reviewed": "تمت مراجعتها خارجيًا",
        "verified": "موثقة",
    }
    return labels.get(value, "حالة المراجعة معلنة داخل السياسة")


def make_page(
    claims: dict[str, Any],
    urgent: dict[str, Any],
    disability: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    canonical = BASE + "trust/"
    updated_at = latest_date(
        claims.get("updated_at", ""),
        urgent.get("updated_at", ""),
        disability.get("updated_at", ""),
    )
    claims_entries = claims.get("claims", [])
    verified_claims = [item for item in claims_entries if item.get("status") == "verified"]
    urgent_services = urgent.get("services", [])
    verified_services = [item for item in urgent_services if item.get("status") == "verified"]
    fallback = urgent.get("fallback_when_local_service_unverified", [])
    dignity = disability.get("required_principles", {})
    dignity_labels = {
        "person_not_diagnosis": "عدم اختزال الشخص في التشخيص",
        "respect_language_preference": "احترام تفضيل الشخص للغة التي تصفه",
        "balance_needs_and_strengths": "عرض الاحتياجات ونقاط القوة معًا",
        "consent_and_assent": "احترام الموافقة والمشاركة والرفض",
        "aac_and_accessible_communication": "دعم التواصل البديل والمعزز والإتاحة",
        "privacy_and_data_minimization": "تقليل البيانات وحماية الخصوصية",
        "safeguarding_and_abuse_awareness": "الانتباه للإساءة والاستغلال والحماية",
        "neutral_genetic_and_reproductive_information": "حياد المعلومات الوراثية والإنجابية",
    }
    dignity_items = [
        label for key, label in dignity_labels.items() if dignity.get(key) is True
    ]
    fallback_items = "".join(f"<li>{e(item)}</li>" for item in fallback)
    dignity_items_html = "".join(f"<li>{e(item)}</li>" for item in dignity_items)

    if verified_claims:
        claims_summary = (
            f"يوجد {len(verified_claims)} ادعاء مؤسسي موثق ومقيد بنطاق نشر وتاريخ مراجعة. "
            "لا تعرض هذه الصفحة أسماء أو تفاصيل حساسة؛ كل استخدام علني يخضع للسجل."
        )
    else:
        claims_summary = (
            "لا يوجد حاليًا أي ادعاء منشور عن خبير أو شريك أو اعتماد أو عضوية أو أثر "
            "مصرح به داخل السجل. غياب الدليل يعني منع النشر، لا السماح بصياغة ضمنية."
        )

    if verified_services:
        urgent_summary = (
            f"يوجد {len(verified_services)} سجل خدمة اجتاز شروط التحقق، "
            "لكن عرضه العام يظل مقيدًا بالبلد والنطاق وتاريخ المراجعة."
        )
    else:
        urgent_summary = (
            "لا ينشر الموقع حاليًا رقمًا أو جهة مساعدة عاجلة بوصفها معتمدة أو صالحة لكل بلد. "
            "تظهر فقط إرشادات عامة محدودة عند غياب خدمة محلية موثقة."
        )

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "name": "الثقة والمنهج التحريري",
                "description": "منهج وسياسات الثقة والسلامة والخصوصية والتصحيح في منصة مصطلحات علم النفس.",
                "url": canonical,
                "inLanguage": "ar",
                "dateModified": updated_at,
                "isPartOf": {"@type": "WebSite", "name": "مصطلحات علم النفس", "url": BASE},
            },
            {
                "@type": "Organization",
                "name": "مصطلحات علم النفس",
                "url": BASE,
                "sameAs": [
                    "https://www.instagram.com/pterminology/",
                    "https://www.youtube.com/@psychology-term",
                ],
            },
        ],
    }

    html_text = f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>الثقة والمنهج التحريري | مصطلحات علم النفس</title>
<meta name="description" content="كيف تُدار المصادر والمراجعة والخصوصية والمساعدة العاجلة وكرامة الأشخاص ذوي الإعاقة والادعاءات المؤسسية في منصة مصطلحات علم النفس.">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_AR">
<meta property="og:title" content="الثقة والمنهج التحريري | مصطلحات علم النفس">
<meta property="og:description" content="سياسات معلنة للسلامة والخصوصية والتصحيح ومنع الادعاءات غير الموثقة.">
<meta property="og:url" content="{canonical}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")}</script>
<style>
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#173f45;background:linear-gradient(140deg,#fff8fb,#e5fbf7,#eeeaff)}}a{{color:#086e69}}a:focus-visible{{outline:3px solid #168f88;outline-offset:4px}}main{{width:min(1080px,92%);margin:auto;padding:28px 0 64px}}nav{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}}nav a,.button{{display:inline-block;padding:10px 15px;border:1px solid #b9dfda;border-radius:14px;background:#fff;text-decoration:none;font-weight:800}}header,section{{background:rgba(255,255,255,.96);border:1px solid #c7e8e3;border-radius:24px;padding:clamp(19px,4vw,38px);margin:16px 0;box-shadow:0 16px 44px rgba(40,100,100,.09)}}header{{background:linear-gradient(135deg,#ffe5ef,#dffaf7,#eee9ff)}}h1{{font-size:clamp(2rem,6vw,4rem);line-height:1.25;margin:.2em 0}}h2{{color:#7b3658}}h3{{color:#086e69}}.lead{{font-size:1.12rem;color:#496d70}}.status{{border-right:6px solid #168f88;background:#eefbf8}}.warning{{border-right:6px solid #c04a71;background:#fff1f5}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card{{border:1px solid #c7e8e3;border-radius:18px;padding:18px;background:#fff}}.card strong{{display:block;color:#7b3658;margin-bottom:6px}}code{{direction:ltr;unicode-bidi:embed}}footer{{padding:24px 0;color:#496d70}}@media(max-width:820px){{.grid{{grid-template-columns:1fr}}nav{{display:grid}}}}@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}
</style>
</head>
<body>
<main>
<nav aria-label="التنقل الرئيسي"><a href="{PATH_PREFIX}">الرئيسية</a><a href="{PATH_PREFIX}encyclopedia/">الموسوعة</a><a href="{PATH_PREFIX}care-guides/">أدلة التعامل</a><a href="{PATH_PREFIX}daily-tools/">الأدوات اليومية</a></nav>
<header>
<p><strong>مركز الثقة والمنهج</strong></p>
<h1>كيف نمنع الادعاءات غير الموثقة ونحمي القارئ؟</h1>
<p class="lead">هذه الصفحة تشرح القواعد القابلة للاختبار التي تحكم النشر في المشروع. وجود سياسة أو اختبار آلي لا يعني مراجعة سريرية أو قانونية خارجية، ولا يمنح اعتمادًا مهنيًا.</p>
<p><strong>آخر تحديث موحد:</strong> <time datetime="{e(updated_at)}">{e(updated_at)}</time></p>
</header>

<section class="status">
<h2>الحدود الأساسية</h2>
<ul>
<li>المحتوى للتثقيف والدعم العام، وليس تشخيصًا فرديًا أو بديلًا للطبيب أو المعالج.</li>
<li>لا يقدم الموقع تعليمات لبدء دواء أو إيقافه أو تعديل جرعته.</li>
<li>لا تُنسب مراجعة أو شراكة أو عضوية أو اعتماد إلى شخص أو جهة دون سجل موثق وموافقة.</li>
<li>الأدوات المحلية لا ترسل بيانات المستخدم إلى خادم ما لم تُذكر آلية مختلفة بوضوح ويوافق عليها المستخدم.</li>
<li>تُعلن حالة المراجعة كما هي، بما في ذلك الحاجة إلى مراجعة خارجية متخصصة.</li>
</ul>
</section>

<section>
<h2>حالة منظومة الثقة</h2>
<div class="grid">
<div class="card"><strong>الادعاءات المؤسسية</strong><span>قاعدة منع افتراضي نشطة. لا يُنشر ادعاء إلا بحالة <code>verified</code> ودليل وتاريخ مراجعة ونطاق محدد.</span></div>
<div class="card"><strong>المساعدة العاجلة</strong><span>{e(public_status_label(urgent.get("review_status", "")))}. لا تُنشر أرقام أو خدمات غير موثقة أو خارج نطاقها الجغرافي.</span></div>
<div class="card"><strong>كرامة الإعاقة وسلامة المحتوى</strong><span>{e(public_status_label(disability.get("review_status", "")))}. القواعد تمنع الوصم والإكراه والاستغلال والادعاءات العلاجية المطلقة.</span></div>
</div>
</section>

<section>
<h2>الخبراء والشركاء والاعتمادات والأثر</h2>
<p>{e(claims_summary)}</p>
<p>المراسلة أو طلب التعاون أو تلقي اهتمام أولي لا تعني وجود شراكة. أعداد الزيارات والمتابعين لا تُعرض بوصفها دليلًا على أثر صحي أو اجتماعي.</p>
</section>

<section class="warning">
<h2>المساعدة العاجلة ومعلومات الأزمات</h2>
<p>{e(urgent_summary)}</p>
<ul>{fallback_items}</ul>
<p>لا يقيّم الموقع مستوى الخطر الفردي، ولا ينتج درجة خطر سريرية، ولا يضمن توفر خدمة أو سريتها أو تكلفتها دون مصدر رسمي حديث.</p>
</section>

<section>
<h2>كرامة الأشخاص ذوي الإعاقة</h2>
<p>يُراجع المحتوى المتعلق بالإعاقة واضطرابات النمو العصبي والمتلازمات الوراثية وفق مبادئ تمنع اختزال الإنسان في التشخيص أو استخدام الخوف والشفقة للترويج.</p>
<ul>{dignity_items_html}</ul>
<p>عند تغير السلوك، تسبق فرضية التفسير النفسي مراجعة الألم أو المرض وتأثيرات الدواء والنوم والسمع والبصر والبيئة الحسية وعوائق التواصل والتغيرات الحديثة.</p>
</section>

<section>
<h2>المصادر والمراجعة والتصحيح</h2>
<ul>
<li>تعطى الأولوية للمصادر الأولية الرسمية والإرشادات المهنية والبحوث الأصلية عند ملاءمتها.</li>
<li>يجب تمييز المعلومة العامة عن القرار الطبي أو القانوني الفردي.</li>
<li>تُسجل تواريخ المراجعة، وتزال الادعاءات المنتهية أو المسحوبة من الواجهات العامة.</li>
<li>لا تُحذف الآثار التدقيقية الضرورية لفهم سبب التصحيح أو السحب.</li>
<li>يمكن الإبلاغ عن خطأ تقني أو تحريري عبر <a href="https://github.com/khaledaltheeb/healthrenewal.org/issues" rel="noopener noreferrer">سجل مشكلات المشروع</a>.</li>
</ul>
</section>

<section>
<h2>الخصوصية والأدوات التفاعلية</h2>
<p>تُبنى الأدوات الحالية على التخزين المحلي الاختياري وتقليل البيانات وإتاحة التصدير والحذف. لا يجوز جمع أسماء أو أرقام هوية أو تفاصيل علاجية حساسة لمجرد تشغيل أداة تنظيمية عامة.</p>
<p>عند تعذر التخزين المحلي يجب أن تبقى الوظيفة الأساسية قابلة للاستخدام دون إعلان حفظ غير صحيح، وأن تظهر رسالة واضحة للمستخدم.</p>
</section>

<footer>
<p>هذه الصفحة وصف لحوكمة المشروع وليست شهادة اعتماد. حالة السياسات قابلة للتحديث عند اكتمال مراجعات خارجية موثقة.</p>
</footer>
</main>
</body>
</html>'''

    report = {
        "version": 71,
        "page": "trust/index.html",
        "updated_at": updated_at,
        "institutional_claims_total": len(claims_entries),
        "institutional_claims_verified": len(verified_claims),
        "urgent_services_total": len(urgent_services),
        "urgent_services_verified": len(verified_services),
        "urgent_help_review_status": urgent.get("review_status"),
        "disability_review_status": disability.get("review_status"),
        "default_deny": True,
    }
    return html_text, report


def patch_homepage(site: Path) -> None:
    path = site / "index.html"
    if not path.is_file():
        raise SystemExit("Missing generated homepage before trust-center publication")
    text = path.read_text(encoding="utf-8")
    nav_link = '<a href="trust/">الثقة والمنهج</a>'
    if nav_link not in text:
        marker = "</nav></header>"
        if marker not in text:
            raise SystemExit("Homepage navigation marker not found")
        text = text.replace(marker, nav_link + marker, 1)
    footer_link = '<a href="trust/">الثقة والمنهج</a>'
    if text.count(footer_link) < 2:
        marker = "</p></footer>"
        if marker not in text:
            raise SystemExit("Homepage footer marker not found")
        text = text.replace(marker, f' — {footer_link}</p></footer>', 1)
    path.write_text(text, encoding="utf-8")


def write_sitemap(site: Path, updated_at: str) -> None:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    trust_sitemap = site / "sitemap-trust.xml"
    urlset = ET.Element(f"{{{ns}}}urlset")
    url = ET.SubElement(urlset, f"{{{ns}}}url")
    ET.SubElement(url, f"{{{ns}}}loc").text = BASE + "trust/"
    ET.SubElement(url, f"{{{ns}}}lastmod").text = updated_at
    ET.SubElement(url, f"{{{ns}}}changefreq").text = "monthly"
    ET.ElementTree(urlset).write(trust_sitemap, encoding="utf-8", xml_declaration=True)

    main_path = site / "sitemap.xml"
    if not main_path.is_file():
        raise SystemExit("Missing sitemap.xml before trust-center publication")
    tree = ET.parse(main_path)
    root = tree.getroot()
    local = root.tag.rsplit("}", 1)[-1]
    if local == "sitemapindex":
        target = BASE + "sitemap-trust.xml"
        existing = {
            item.text
            for item in root.findall(f"{{{ns}}}sitemap/{{{ns}}}loc")
            if item.text
        }
        if target not in existing:
            node = ET.SubElement(root, f"{{{ns}}}sitemap")
            ET.SubElement(node, f"{{{ns}}}loc").text = target
    elif local == "urlset":
        target = BASE + "trust/"
        existing = {
            item.text for item in root.findall(f"{{{ns}}}url/{{{ns}}}loc") if item.text
        }
        if target not in existing:
            node = ET.SubElement(root, f"{{{ns}}}url")
            ET.SubElement(node, f"{{{ns}}}loc").text = target
            ET.SubElement(node, f"{{{ns}}}lastmod").text = updated_at
    else:
        raise SystemExit(f"Unsupported sitemap root: {local}")
    tree.write(main_path, encoding="utf-8", xml_declaration=True)


def publish(site: Path = SITE) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")
    claims = load_json(CLAIMS_PATH)
    urgent = load_json(URGENT_PATH)
    disability = load_json(DISABILITY_PATH)
    validate_sources(claims, urgent, disability)
    page, report = make_page(claims, urgent, disability)
    out = site / "trust"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    patch_homepage(site)
    write_sitemap(site, report["updated_at"])
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "trust-center-v71.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    publish()
