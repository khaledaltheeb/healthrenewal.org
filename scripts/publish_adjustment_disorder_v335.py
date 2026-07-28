from __future__ import annotations

import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://khaledaltheeb.github.io/pterminology-site/"
SLUG = "encyclopedia/adjustment-disorder/"
URL = BASE + SLUG
TITLE = "اضطراب التكيف: الأعراض والفروق والعلاج | موسوعة الصحة النفسية"
DESCRIPTION = (
    "دليل عربي موثوق عن اضطراب التكيف بعد الضغوط الحياتية: العلامات، الفروق عن الحزن "
    "والاكتئاب واضطراب ما بعد الصدمة، متى تطلب المساعدة، وما الذي تقوله الأدلة عن العلاج."
)


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_page() -> str:
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "MedicalWebPage",
                "@id": URL + "#webpage",
                "url": URL,
                "name": TITLE,
                "description": DESCRIPTION,
                "inLanguage": "ar",
                "datePublished": "2026-07-28",
                "dateModified": "2026-07-29",
                "about": {"@type": "MedicalCondition", "name": "اضطراب التكيف"},
                "citation": [
                    "https://dictionary.apa.org/adjustment-disorder",
                    "https://pubmed.ncbi.nlm.nih.gov/37992766/",
                    "https://pubmed.ncbi.nlm.nih.gov/35176345/",
                    "https://pubmed.ncbi.nlm.nih.gov/29958336/",
                ],
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": "هل اضطراب التكيف هو نفسه الاكتئاب؟",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "لا. قد يتضمن مزاجًا منخفضًا، لكن التشخيص يرتبط باستجابة لضاغط محدد وبنمط زمني وأثر وظيفي، مع ضرورة استبعاد اضطرابات أخرى مثل الاكتئاب الجسيم."
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "هل يختفي اضطراب التكيف وحده؟",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "قد تتحسن الأعراض مع زوال الضاغط أو اكتساب مهارات تكيف، لكن استمرار التعطل أو ظهور خطر أو أعراض شديدة يستلزم تقييمًا مهنيًا."
                        },
                    },
                    {
                        "@type": "Question",
                        "name": "ما العلاج الأكثر دعمًا بالدليل؟",
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "text": "العلاج النفسي القصير والمنظم هو الخيار الأكثر دراسة، لكن جودة الأدلة ما تزال محدودة وغير متجانسة، ولا توجد طريقة واحدة مثبتة للجميع."
                        },
                    },
                ],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "الموسوعة", "item": BASE + "encyclopedia/"},
                    {"@type": "ListItem", "position": 3, "name": "اضطراب التكيف", "item": URL},
                ],
            },
        ],
    }
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(TITLE)}</title>
<meta name="description" content="{esc(DESCRIPTION)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<link rel="canonical" href="{URL}">
<link rel="alternate" hreflang="ar" href="{URL}">
<link rel="alternate" hreflang="x-default" href="{URL}">
<meta property="og:locale" content="ar_AR">
<meta property="og:type" content="article">
<meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة">
<meta property="og:title" content="{esc(TITLE)}">
<meta property="og:description" content="{esc(DESCRIPTION)}">
<meta property="og:url" content="{URL}">
<meta property="og:image" content="{BASE}assets/social-card-v334.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(TITLE)}">
<meta name="twitter:description" content="{esc(DESCRIPTION)}">
<meta name="twitter:image" content="{BASE}assets/social-card-v334.png">
<link rel="stylesheet" href="{BASE}assets/css/theme-v10.css">
<link rel="stylesheet" href="{BASE}assets/css/encyclopedia-v13.css">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")}</script>
</head>
<body>
<a class="skip" href="#main">تجاوز إلى المحتوى</a>
<main id="main" class="ency-v13" data-v335-page="adjustment-disorder">
<nav class="ency-v13__crumbs" aria-label="مسار التنقل"><a href="{BASE}">الرئيسية</a> ← <a href="{BASE}encyclopedia/">الموسوعة</a> ← اضطراب التكيف</nav>
<header class="ency-v13__hero">
<div class="ency-v13__meta"><span class="ency-v13__tag">اضطرابات مرتبطة بالضغط</span><span class="ency-v13__tag">مراجعة الأدلة: 2026</span></div>
<h1>اضطراب التكيف: كيف نميّزه عن استجابة الضغط الطبيعية؟</h1>
<p>استجابة نفسية أو سلوكية لضاغط حياتي محدد تصبح أشد مما يُتوقع في السياق أو تسبب تعطيلًا واضحًا في الدراسة أو العمل أو العلاقات. لا يكفي وجود ضغط أو حزن عابر للتشخيص.</p>
</header>
<article class="ency-v13__article">
<section><h2>ما اضطراب التكيف؟</h2><p>يظهر اضطراب التكيف بعد حدث أو تغير ضاغط يمكن تحديده، مثل فقد وظيفة، انفصال، مرض، انتقال كبير أو نزاع مستمر. قد يغلب عليه القلق أو انخفاض المزاج أو اضطراب السلوك، وقد تختلط هذه الصور. وفق وصف الجمعية الأمريكية لعلم النفس، يحتفظ الدليل التشخيصي الحديث به ضمن طيف استجابات الضغط بدل اعتباره مجرد فئة متبقية.</p><p>التشخيص مهني؛ يعتمد على العلاقة الزمنية بالضاغط، شدة المعاناة، الأثر الوظيفي، والسياق الثقافي والاجتماعي، مع استبعاد حالات أخرى أو استجابة حزن متوقعة.</p></section>
<section><h2>العلامات والأثر الوظيفي</h2><ul><li>قلق أو توتر أو اجترار مرتبط بالحدث الضاغط.</li><li>مزاج منخفض أو بكاء أو فقد الدافعية.</li><li>صعوبة النوم أو التركيز أو أداء المسؤوليات.</li><li>انسحاب اجتماعي أو خلافات متزايدة أو تراجع دراسي أو مهني.</li><li>عند بعض المراهقين: سلوك اندفاعي أو مخالف للقواعد.</li></ul><p>لا توجد قائمة إلكترونية تشخّص الحالة. الأهم هو التغير عن خط الأساس ومدى التعطيل واستمرار الأعراض.</p></section>
<section><h2>الفروق التي تمنع الخلط</h2><h3>استجابة الضغط الطبيعية</h3><p>الانزعاج المتوقع بعد حدث صعب قد يكون شديدًا لكنه لا يسبب دائمًا تعطيلًا مستمرًا أو يتجاوز ما يفسره السياق.</p><h3>الاكتئاب الجسيم</h3><p>قد يتضمن أعراضًا أوسع وأكثر ثباتًا ولا يشترط أن تبقى مرتبطة بضاغط واحد. وجود فقد المتعة الشامل أو أفكار الموت أو تدهور واضح يحتاج تقييمًا مباشرًا.</p><h3>اضطراب ما بعد الصدمة</h3><p>يرتبط بتعرض من نوع محدد للتهديد الشديد ويتضمن أنماطًا مثل إعادة المعايشة والتجنب والشعور المستمر بالخطر. ليس كل حدث ضاغط صدمة بالمعنى التشخيصي.</p><h3>الحزن</h3><p>الحزن بعد الفقد استجابة إنسانية، وقد يتقلب في موجات. يُبحث عن اضطراب آخر عندما تكون الصورة غير متناسبة مع السياق أو شديدة التعطيل أو تتضمن مخاطر.</p></section>
<section><h2>عوامل مرتبطة وليست أسبابًا حتمية</h2><p>وجدت مراجعة منهجية شملت 70 دراسة وأكثر من 3.4 ملايين مشارك ارتباطات مع شدة الضغط، المرض أو الإصابة الجسدية، انخفاض الدعم الاجتماعي، البطالة، وصعوبات نفسية سابقة. هذه عوامل تنبؤية على مستوى المجموعات ولا تسمح بالحكم على فرد بعينه.</p></section>
<section><h2>متى تُطلب المساعدة؟</h2><ul><li>عندما يستمر التعطل أو يزداد بدل أن يتحسن.</li><li>عند الغياب المتكرر عن الدراسة أو العمل أو تدهور العلاقات والرعاية الذاتية.</li><li>عند استخدام مواد أو سلوكيات خطرة للتعامل مع الضغط.</li><li>فورًا عند وجود أفكار لإيذاء النفس أو الآخرين، فقدان السيطرة، أو خطر مباشر؛ الأولوية لخدمة الطوارئ المحلية.</li></ul></section>
<section><h2>ما خيارات الدعم والعلاج؟</h2><p>يركز العلاج عادة على فهم الضاغط، حل المشكلات القابلة للتغيير، تقليل التجنب، تنظيم النوم والروتين، بناء الدعم، وتعلم مهارات التكيف. قد تُستخدم تدخلات معرفية سلوكية أو علاج داعم أو تدخلات رقمية موجهة.</p><div class="ency-v13__callout"><strong>قوة الدليل:</strong> المراجعات تشير إلى نتائج واعدة للعلاجات النفسية والتدخلات المدعومة بالتقنية، لكن عدد الدراسات وجودتها وتجانسها ما تزال محدودة. لا يصح تقديم علاج واحد بوصفه الأفضل للجميع، ولا ينبغي استخدام الدواء تلقائيًا لمجرد وجود ضيق بعد حدث ضاغط.</div><p>تُعالج المشكلات المصاحبة وفق تقييم مستقل. أي قرار دوائي يحتاج طبيبًا يوازن الفوائد والمخاطر والتشخيصات البديلة.</p></section>
<section><h2>خطة عملية أولية</h2><ol><li>اكتب الحدث أو الضغط المستمر وتاريخ بدايته.</li><li>حدد أكثر مجالين تضررًا: النوم، الدراسة، العمل، العلاقات أو الرعاية الذاتية.</li><li>افصل بين ما يمكن تغييره وما يحتاج قبولًا ودعمًا وتدرجًا.</li><li>اختر خطوة صغيرة قابلة للقياس خلال أسبوع.</li><li>راجع التقدم، واطلب تقييمًا إذا لم يتحسن الأداء أو زادت الخطورة.</li></ol></section>
<section><h2>أسئلة شائعة</h2><h3>هل اضطراب التكيف هو نفسه الاكتئاب؟</h3><p>لا. قد يتضمن مزاجًا منخفضًا، لكن علاقته بضاغط محدد ونمطه الزمني والأثر الوظيفي جزء أساسي من التقييم.</p><h3>هل يختفي وحده؟</h3><p>قد تتحسن الأعراض مع زوال الضاغط أو اكتساب مهارات تكيف، لكن الاستمرار أو الشدة أو الخطر تستلزم مساعدة مهنية.</p><h3>هل كل ضغط شديد يعني اضطراب تكيف؟</h3><p>لا. التشخيص يتطلب معاناة أو تعطيلًا يتجاوز الاستجابة المتوقعة في السياق، مع استبعاد تفسيرات أخرى.</p></section>
<section class="ency-v13__sources"><h2>المصادر الأصلية والمراجعات</h2><ul><li><a href="https://dictionary.apa.org/adjustment-disorder" rel="noopener noreferrer">APA Dictionary of Psychology: Adjustment disorder</a></li><li><a href="https://pubmed.ncbi.nlm.nih.gov/37992766/" rel="noopener noreferrer">Fernández-Buendía et al. 2024 — مراجعة منهجية وتحليل أولي للعلاجات المدعومة بالتقنية، PMID 37992766، DOI 10.1016/j.jad.2023.11.059</a></li><li><a href="https://pubmed.ncbi.nlm.nih.gov/35176345/" rel="noopener noreferrer">O'Donnell et al. 2022 — مراجعة عوامل التنبؤ لدى البالغين، PMID 35176345، DOI 10.1016/j.jad.2022.02.038</a></li><li><a href="https://pubmed.ncbi.nlm.nih.gov/29958336/" rel="noopener noreferrer">O'Donnell et al. 2018 — مراجعة العلاجات النفسية والدوائية، PMID 29958336، DOI 10.1002/jts.22295</a></li></ul><p>هذه الصفحة للتثقيف ولا تستبدل التقييم أو العلاج الفردي.</p></section>
<section><h2>روابط داخلية</h2><ul><li><a href="{BASE}encyclopedia/">الموسوعة النفسية</a></li><li><a href="{BASE}hubs/topic-009/">مركز الضغط النفسي</a></li><li><a href="{BASE}tips/">نصائح الصحة النفسية</a></li><li><a href="{BASE}comparisons/">المقارنات النفسية</a></li></ul></section>
</article>
</main>
</body>
</html>'''


def append_to_sitemap(site: Path) -> int:
    sitemap = site / "sitemap.xml"
    if not sitemap.is_file():
        raise SystemExit(f"Missing sitemap: {sitemap}")
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    tree = ET.parse(sitemap)
    root = tree.getroot()
    urls = [node.text or "" for node in root.findall(f".//{{{namespace}}}loc")]
    if URL not in urls:
        node = ET.SubElement(root, f"{{{namespace}}}url")
        ET.SubElement(node, f"{{{namespace}}}loc").text = URL
        ET.SubElement(node, f"{{{namespace}}}lastmod").text = "2026-07-29"
        ET.SubElement(node, f"{{{namespace}}}changefreq").text = "monthly"
        ET.SubElement(node, f"{{{namespace}}}priority").text = "0.8"
        tree.write(sitemap, encoding="utf-8", xml_declaration=True)
    return 1


def inject_index_link(site: Path) -> int:
    index = site / "encyclopedia" / "index.html"
    if not index.is_file():
        raise SystemExit(f"Missing encyclopedia index: {index}")
    text = index.read_text(encoding="utf-8")
    if URL in text or "adjustment-disorder" in text:
        return 0
    card = f'''<section class="ency-v13__card" data-v335-card="adjustment-disorder"><h2><a href="{URL}">اضطراب التكيف</a></h2><p>دليل موثوق يشرح الاستجابة للضغوط، الفروق عن الحزن والاكتئاب واضطراب ما بعد الصدمة، ومتى تُطلب المساعدة.</p></section>'''
    marker = re.search(r"</main>", text, flags=re.I)
    if marker is None:
        raise SystemExit("Encyclopedia index has no closing main element")
    text = text[: marker.start()] + card + "\n" + text[marker.start() :]
    index.write_text(text, encoding="utf-8")
    return 1


def publish(site: Path) -> dict[str, object]:
    target = site / "encyclopedia" / "adjustment-disorder" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_page(), encoding="utf-8")
    report = {
        "version": 335,
        "page": SLUG,
        "canonical": URL,
        "index_links_added": inject_index_link(site),
        "sitemap_urls_added": append_to_sitemap(site),
        "sources": 4,
    }
    report_path = site / "api" / "adjustment-disorder-v335.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    import sys

    root = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    print(json.dumps(publish(root), ensure_ascii=False, indent=2))
