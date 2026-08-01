#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://healthrenewal.org/"
ROUTE = "/partners/"
URL = BASE + ROUTE
PARTNERS_LINK = '<a href="partners/">الشركاء والشفافية</a>'


def render_page() -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "الشركاء والتعاون والشفافية",
        "description": "سجل علني يوضح معايير الشراكات والتعاون والإفصاح في منصة الصحة النفسية وذوي الاحتياجات الخاصة.",
        "url": URL,
        "inLanguage": "ar",
        "isPartOf": {
            "@type": "WebSite",
            "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "url": BASE + "/",
        },
    }
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>الشركاء والتعاون والشفافية | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
<meta name="description" content="سجل علني لمعايير الشراكات والتعاون والإفصاح، مع منع عرض أي جهة كشريك رسمي دون اتفاق موثق وساري.">
<link rel="canonical" href="{URL}">
<meta property="og:title" content="الشركاء والتعاون والشفافية">
<meta property="og:description" content="معايير واضحة للإفصاح عن الشراكات والدعم والتعاون المؤسسي.">
<meta property="og:type" content="website">
<meta property="og:url" content="{URL}">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>
:root{{color-scheme:light;--ink:#173f45;--muted:#527276;--line:#c9e9e5;--brand:#08736d;--soft:#f5fbfa;--warn:#fff8e6}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;background:#fff;color:var(--ink);line-height:1.85}}
a{{color:#086e69}}header,footer{{padding:18px max(4vw,20px);background:var(--soft);border-color:var(--line)}}header{{border-bottom:1px solid var(--line)}}footer{{border-top:1px solid var(--line);margin-top:40px}}nav{{display:flex;gap:12px;flex-wrap:wrap}}main{{max-width:1050px;margin:auto;padding:32px max(4vw,20px)}}h1,h2{{line-height:1.35}}.lead{{font-size:1.12rem;color:var(--muted)}}.notice{{background:var(--warn);border:1px solid #ead7a2;border-radius:14px;padding:18px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}article{{border:1px solid var(--line);border-radius:16px;padding:18px;background:#fff}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid var(--line);padding:12px;text-align:right;vertical-align:top}}th{{background:var(--soft)}}@media(max-width:680px){{table,thead,tbody,tr,th,td{{display:block}}thead{{position:absolute;left:-9999px}}td{{border-top:0}}}}
</style>
</head>
<body>
<header>
<strong>منصة الصحة النفسية وذوي الاحتياجات الخاصة</strong>
<nav aria-label="التنقل الرئيسي"><a href="/">الرئيسية</a><a href="/trust/">الثقة والمنهجية</a><a href="/special-needs/">ذوو الاحتياجات الخاصة</a><a href="/care-guides/">أدلة التعامل</a></nav>
</header>
<main>
<h1>الشركاء والتعاون والشفافية</h1>
<p class="lead">هذه الصفحة هي السجل العام الذي يوضح متى وكيف تُعرض الجهات الداعمة أو المتعاونة أو الشريكة، وما المعلومات التي يجب الإفصاح عنها لحماية استقلال المحتوى وثقة القارئ.</p>
<section class="notice" aria-labelledby="current-status"><h2 id="current-status">الحالة الحالية للسجل العام</h2><p><strong>لا توجد جهات مدرجة في سجل الشراكات العام داخل هذا الإصدار.</strong> لا تُعرض أي جهة بصفتها شريكًا رسميًا إلا بعد وجود اتفاق موثق وساري يحدد النطاق والمدة والمسؤوليات، ثم نشر الإفصاح المناسب هنا.</p></section>
<section aria-labelledby="criteria"><h2 id="criteria">شروط إدراج أي شريك أو داعم</h2><div class="grid">
<article><h3>اتفاق موثق</h3><p>وجود وثيقة سارية تحدد الهدف، النطاق، المدة، المسؤوليات، وآلية الإنهاء أو التجديد.</p></article>
<article><h3>استقلال المحتوى</h3><p>لا تمنح الشراكة أي جهة حق فرض تشخيص أو توصية علاجية أو نتيجة تقييم أو حذف معلومة نقدية لازمة.</p></article>
<article><h3>إفصاح المصالح</h3><p>يُوضح الدعم المالي أو العيني أو التقني، وأي تضارب مصالح محتمل، والمواد التي شملها التعاون.</p></article>
<article><h3>حماية البيانات</h3><p>لا تشمل الشراكة مشاركة بيانات شخصية أو صحية إلا ضمن أساس قانوني واضح وضوابط خصوصية وأمن مناسبة.</p></article>
</div></section>
<section aria-labelledby="register"><h2 id="register">حقول السجل عند إضافة جهة</h2><table><thead><tr><th>الحقل</th><th>ما يُنشر</th></tr></thead><tbody>
<tr><td>الجهة</td><td>الاسم القانوني والرابط الرسمي بعد التحقق.</td></tr>
<tr><td>نوع العلاقة</td><td>شريك، داعم، متعاون معرفي، مزود خدمة، أو جهة مانحة.</td></tr>
<tr><td>النطاق</td><td>المشروع أو القسم أو المادة التي يشملها التعاون دون تعميم مضلل.</td></tr>
<tr><td>الفترة</td><td>تاريخ البداية والنهاية أو حالة الاستمرار والمراجعة.</td></tr>
<tr><td>الإفصاح</td><td>الدعم المالي أو العيني أو التقني، وحدود التأثير التحريري.</td></tr>
<tr><td>الحالة</td><td>نشطة، منتهية، معلقة، أو ملغاة مع تاريخ آخر تحديث.</td></tr>
</tbody></table></section>
<section aria-labelledby="collaboration"><h2 id="collaboration">مجالات التعاون المقبولة</h2><p>يمكن أن يشمل التعاون مراجعة علمية مستقلة، إتاحة وتوطين المعرفة، تدريب مقدمي الخدمة، دعم تقني أو بحثي، تمويل معلن، أو إحالة إلى خدمات موثوقة. لا يعني التعاون اعتمادًا سريريًا أو قانونيًا تلقائيًا، ولا يحول المحتوى التثقيفي إلى تشخيص أو علاج فردي.</p></section>
<section aria-labelledby="corrections"><h2 id="corrections">التصحيح والاعتراض</h2><p>عند اكتشاف وصف غير دقيق لعلاقة مؤسسية، تُراجع الوثائق ويُصحح السجل مع توضيح تاريخ التحديث. لا يُستخدم شعار جهة أو علامتها التجارية قبل التحقق من الإذن وشروط الاستخدام.</p></section>
</main>
<footer><p><strong>معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</strong></p><p><a href="/trust/">الثقة والمنهجية</a> · <a href="/">العودة إلى الرئيسية</a></p></footer>
</body>
</html>'''


def patch_homepage(site: Path) -> dict[str, bool]:
    path = site / "index.html"
    if not path.is_file():
        raise SystemExit("Missing generated homepage before partners publication")
    text = path.read_text(encoding="utf-8")
    footer = re.search(r"<footer\b[^>]*>.*?</footer>", text, re.I | re.S)
    if not footer:
        raise SystemExit("Homepage contains no footer for partners integration")
    if PARTNERS_LINK in footer.group(0):
        return {"footer_link_added": False, "homepage_link_verified": True}
    footer_html = footer.group(0)
    footer_links = re.search(r'<div\b[^>]*class=["\'][^"\']*footer-links[^"\']*["\'][^>]*>.*?</div>', footer_html, re.I | re.S)
    if footer_links:
        updated_links = re.sub(r"</div>", PARTNERS_LINK + "</div>", footer_links.group(0), count=1, flags=re.I)
        updated_footer = footer_html[:footer_links.start()] + updated_links + footer_html[footer_links.end():]
    else:
        updated_footer = re.sub(r"</footer>", f'<p class="partners-link">{PARTNERS_LINK}</p></footer>', footer_html, count=1, flags=re.I)
    text = text[:footer.start()] + updated_footer + text[footer.end():]
    path.write_text(text, encoding="utf-8")
    verified = PARTNERS_LINK in re.search(r"<footer\b[^>]*>.*?</footer>", text, re.I | re.S).group(0)
    if not verified:
        raise SystemExit("Partners link is absent from homepage footer")
    return {"footer_link_added": True, "homepage_link_verified": True}


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0] + "}" + name
    return name


def write_sitemaps(site: Path) -> dict[str, object]:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    child_path = site / "sitemap-partners.xml"
    child_root = ET.Element(f"{{{ns}}}urlset")
    item = ET.SubElement(child_root, f"{{{ns}}}url")
    ET.SubElement(item, f"{{{ns}}}loc").text = URL
    ET.SubElement(item, f"{{{ns}}}changefreq").text = "monthly"
    ET.ElementTree(child_root).write(child_path, encoding="utf-8", xml_declaration=True)

    main_path = site / "sitemap.xml"
    if not main_path.is_file():
        raise SystemExit("Main sitemap is missing")
    tree = ET.parse(main_path)
    root = tree.getroot()
    kind = local_name(root.tag)
    changed = False
    if kind == "urlset":
        existing = {(node.text or "").strip() for node in root.findall("{*}url/{*}loc")}
        if URL not in existing:
            node = ET.SubElement(root, qualify(root, "url"))
            ET.SubElement(node, qualify(root, "loc")).text = URL
            changed = True
    elif kind == "sitemapindex":
        child_url = BASE + "/sitemap-partners.xml"
        existing = {(node.text or "").strip() for node in root.findall("{*}sitemap/{*}loc")}
        if child_url not in existing:
            node = ET.SubElement(root, qualify(root, "sitemap"))
            ET.SubElement(node, qualify(root, "loc")).text = child_url
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {kind}")
    if changed:
        tree.write(main_path, encoding="utf-8", xml_declaration=True)
    return {"main_mode": kind, "main_changed": changed, "child_urls": 1}


def publish(site: Path) -> dict[str, object]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    target = site / "partners" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_page(), encoding="utf-8")
    integration = patch_homepage(site)
    sitemap = write_sitemaps(site)
    report = {
        "version": 228,
        "route": ROUTE,
        "url": URL,
        "page": "partners/index.html",
        "public_registry_entries": 0,
        "unverified_partners_claimed": False,
        "sitemap": sitemap,
        **integration,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "partners-v201.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    publish(site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
