#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from family_tools_v1_common import *

def schema(tool: dict, source_map: dict) -> str:
    route = f"{ROOT_ROUTE}{tool['slug']}/"
    faq = [
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}}
        for q, a in faq_pairs(tool)
    ]
    citations = [source_map[s]["url"] for s in tool["source_refs"]]
    payload = {
      "@context":"https://schema.org",
      "@graph":[
        {"@type":"Article","@id":ORIGIN+route+"#article","headline":tool["title"],"description":tool["description"],"url":ORIGIN+route,"inLanguage":"ar","datePublished":"2026-08-02","dateModified":"2026-08-02","isAccessibleForFree":True,"citation":citations,"author":{"@type":"Organization","name":"منصة الصحة النفسية وذوي الاحتياجات الخاصة"},"publisher":{"@type":"Organization","name":"منصة الصحة النفسية وذوي الاحتياجات الخاصة"}},
        {"@type":"BreadcrumbList","@id":ORIGIN+route+"#breadcrumb","itemListElement":[
          {"@type":"ListItem","position":1,"name":"الرئيسية","item":ORIGIN+"/"},
          {"@type":"ListItem","position":2,"name":"دليل الأسرة","item":ORIGIN+"/family-guide/"},
          {"@type":"ListItem","position":3,"name":"أدوات التربية الخاصة","item":ORIGIN+ROOT_ROUTE},
          {"@type":"ListItem","position":4,"name":tool["title"],"item":ORIGIN+route}
        ]},
        {"@type":"FAQPage","@id":ORIGIN+route+"#faq","mainEntity":faq}
      ]
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def faq_pairs(tool: dict) -> list[tuple[str, str]]:
    return [
      (f"متى نستخدم {tool['title']}؟", CATEGORY_GUIDANCE.get(tool["category"], "تستخدم الأداة عندما تحتاج الأسرة والفريق إلى تنظيم القرار ومراجعته.")),
      ("هل تنتج الأداة تشخيصًا أو قرارًا نهائيًا؟", "لا. هي أداة تنظيم وتخطيط وتعليم، ولا تستبدل التقييم الفردي أو المتطلبات القانونية أو الحكم المهني المتعدد المصادر."),
      ("كيف نعرف أن الخطة تحتاج تعديلًا؟", "تعدل عندما لا يتحسن المؤشر رغم تنفيذ كافٍ، أو يظهر ضرر أو ضغط زائد، أو تكشف البيانات أن الحاجز والهدف أو طريقة القياس غير ملائمة.")
    ]


def page(tool: dict, source_map: dict, all_tools: list[dict]) -> str:
    route = f"{ROOT_ROUTE}{tool['slug']}/"
    steps_html = "\n".join(f'<article class="step"><h3>{esc(title)}</h3><p>{esc(body)}</p></article>' for title, body in tool["steps"])
    quality_html = "\n".join(f"<li>{esc(x)}</li>" for x in COMMON_SECTIONS["quality"])
    avoid_html = "\n".join(f"<li>{esc(x)}</li>" for x in COMMON_SECTIONS["avoid"])
    rules = [
      "استمر إذا تحسن المؤشر الوظيفي المهم للشخص عبر أكثر من موقف وبقي الضغط مقبولًا.",
      "راجع جودة التنفيذ قبل الحكم على فاعلية الفكرة أو قدرة الشخص.",
      "غيّر متغيرًا رئيسيًا واحدًا في كل دورة قصيرة عندما يكون ذلك آمنًا، حتى يمكن تفسير النتيجة.",
      "اطلب تقييمًا أوسع عند التغير المفاجئ أو الاشتباه بألم أو فقد مهارة أو خطر على الشخص أو الآخرين."
    ]
    rules_html = "\n".join(f"<li>{esc(x)}</li>" for x in rules)
    fields = "\n".join(
      f'<label for="f{i}">{esc(label)}</label><textarea id="f{i}" name="f{i}" placeholder="اكتب معلومات مختصرة قابلة للمراجعة"></textarea>'
      for i, label in enumerate(tool["form_fields"], 1)
    )
    faq_html = "\n".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faq_pairs(tool))
    sources_html = "\n".join(
      f'<article class="source-card"><a href="{esc(source_map[s]["url"])}" rel="noopener noreferrer">{esc(source_map[s]["title"])}</a><p>{esc(source_map[s]["publisher"])}</p></article>'
      for s in tool["source_refs"]
    )
    related_candidates = [x for x in all_tools if x["slug"] != tool["slug"]]
    related_candidates.sort(key=lambda x: (x["category"] != tool["category"], x["title"]))
    related = "".join(f'<a href="../{esc(x["slug"])}/">{esc(x["title"])}</a>' for x in related_candidates[:5])
    toc = [
      ("scope","الغرض وحدود الاستخدام"),("framework","الإطار العلمي والحقوقي"),("prepare","التحضير"),("steps","خطوات التطبيق"),
      ("example","مثال تطبيقي"),("quality","ضبط الجودة"),("decision","قواعد القرار"),("form","النموذج القابل للطباعة"),("sources","المراجع")
    ]
    toc_html = "".join(f'<li><a href="#{a}">{b}</a></li>' for a,b in toc)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(tool['title'])} | أدوات التربية الخاصة ودليل الأسرة</title>
<meta name="description" content="{esc(tool['description'])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{ORIGIN}{route}">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta property="og:title" content="{esc(tool['title'])}"><meta property="og:description" content="{esc(tool['summary'])}"><meta property="og:url" content="{ORIGIN}{route}"><meta property="og:image" content="{ORIGIN}/assets/brand/social-card.svg">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(tool['title'])}"><meta name="twitter:description" content="{esc(tool['summary'])}"><meta name="twitter:image" content="{ORIGIN}/assets/brand/social-card.svg">
<meta name="copyright" content="© 2026 Khaled Altheeb"><meta name="rights" content="All rights reserved"><link rel="license" href="../../../copyright/"><link rel="stylesheet" href="../../../assets/platform/platform-core.css?v=1.1.0"><script defer src="../../../assets/platform/platform-core.js?v=1.1.0"></script>
<script type="application/ld+json">{schema(tool, source_map)}</script>{STYLE}</head>
<body class="pt-platform" data-content-family="special-education-tools-v1"><a class="skip" href="#main">انتقل إلى المحتوى</a>
<header class="site-header"><div class="wrap head"><a class="brand" href="../../../">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav class="nav"><a href="../../">دليل الأسرة</a><a href="../">مركز الأدوات</a><a href="../../../special-needs/">مركز الاحتياجات الخاصة</a><a href="../../../trust/">المنهجية</a></nav></div></header>
<main id="main"><nav class="wrap breadcrumbs" aria-label="مسار التنقل"><a href="../../../">الرئيسية</a> / <a href="../../">دليل الأسرة</a> / <a href="../">أدوات التربية الخاصة</a> / <span aria-current="page">{esc(tool['title'])}</span></nav>
<section class="hero"><div class="wrap"><p class="kicker">{esc(tool['category'])} · أداة قابلة للطباعة</p><h1>{esc(tool['title'])}</h1><p class="lead">{esc(tool['summary'])}</p><p class="notice"><strong>حدود الاستخدام:</strong> هذه أداة تثقيف وتنظيم ودعم قرار مشترك. لا تشخّص، ولا تستبدل تقييمًا فرديًا أو متطلبات بلدك، ولا تبرر الإكراه أو سحب التواصل أو تجاهل الألم. عند خطر مباشر أو تغير مفاجئ أو فقد مهارة، اطلب مساعدة مهنية أو عاجلة مناسبة.</p><div class="toolbar"><a class="button" href="#form">استخدم النموذج</a><button class="secondary" type="button" onclick="window.print()">طباعة أو حفظ PDF</button></div><p class="meta">مراجعة داخلية: 2 أغسطس 2026 · المراجعة الخارجية المتخصصة موصى بها · المراجعة التالية: 2 فبراير 2027</p></div></section>
<section class="section"><div class="wrap"><div class="card"><h2>محتويات الصفحة</h2><ol class="toc">{toc_html}</ol></div></div></section>
<section class="section alt" id="scope"><div class="wrap"><p class="kicker">الغرض العملي</p><h2>ما المشكلة التي تعالجها الأداة؟</h2><p>{esc(tool['focus'])}</p><p>{esc(CATEGORY_GUIDANCE.get(tool['category'], 'تستخدم الأداة لتنظيم قرار تعليمي أو وظيفي قابل للمراجعة.'))}</p><p>لا ينبغي استخدام النموذج لإنتاج أوراق أكثر دون تغيير الممارسة. قيمته في جعل السؤال والبيانات والخطوة التالية مفهومة للشخص والأسرة والمعلم والفريق. ابدأ بأصغر قرار مفيد، واحتفظ فقط بالمعلومات التي ستؤثر في الاختيار أو السلامة أو المتابعة.</p></div></section>
<section class="section" id="framework"><div class="wrap"><p class="kicker">الأساس المنهجي</p><h2>إطار حقوقي ووظيفي ودامج</h2><p>{esc(COMMON_SECTIONS['rights'])}</p><p>تختلف الأنظمة القانونية وأسماء الخطط بين الدول، لذلك تقدم الصفحة مبادئ قابلة للنقل ولا تدعي أنها نموذج قانوني موحد. على المدرسة والأسرة مراجعة اللوائح المحلية، مع الحفاظ على مبادئ عدم التمييز والمشاركة والوصول والتواصل والقرار المشترك.</p></div></section>
<section class="section alt" id="prepare"><div class="wrap"><p class="kicker">قبل البدء</p><h2>المعلومات الدنيا اللازمة</h2><p>{esc(COMMON_SECTIONS['before'])}</p><div class="grid"><div class="card"><h3>مصادر بيانات مناسبة</h3><ul><li>صوت الشخص وتفضيلاته ورفضه.</li><li>ملاحظة في مهمة حقيقية.</li><li>عينة عمل أو سجل زمني مختصر.</li><li>معلومات الأسرة والمعلم والشركاء.</li><li>نتائج تقييم مهني ذات صلة مع فهم حدودها.</li></ul></div><div class="card"><h3>أسئلة البداية</h3><ul><li>ما النتيجة اليومية التي نريد تحسينها؟</li><li>ما الذي يحدث الآن وبأي مقدار من المساعدة؟</li><li>ما الحاجز الذي يمكن تغييره؟</li><li>كيف سيعبّر الشخص عن القبول أو الرفض؟</li><li>ما البيانات الكافية لاتخاذ القرار التالي؟</li></ul></div></div></div></section>
<section class="section" id="steps"><div class="wrap"><p class="kicker">من الملاحظة إلى العمل</p><h2>سبع خطوات تطبيقية</h2><div class="steps">{steps_html}</div><p>بعد الخطوة السابعة، لخص الخطة في صفحة واحدة يمكن الرجوع إليها. لا تنقل كل الملاحظات الخام إلى جميع الأطراف؛ شارك ما يلزم للتنفيذ والقرار فقط. عند اختلاف الفريق، حدد نوع البيانات التي يمكن أن تحسم الخلاف بدل تكرار المواقف العامة.</p></div></section>
<section class="section alt" id="example"><div class="wrap"><p class="kicker">مثال توضيحي</p><h2>كيف تتحول الفكرة إلى قرار؟</h2><div class="example"><p>{esc(tool['example'])}</p></div><p>المثال لا يقدم وصفة ولا يفترض أن النتيجة نفسها تنطبق على شخص آخر. وظيفته توضيح طريقة التفكير: فصل الملاحظة عن التفسير، تعديل البيئة، تعليم مهارة ذات معنى، ثم قياس الفائدة والضرر في دورة قصيرة.</p></div></section>
<section class="section" id="quality"><div class="wrap"><p class="kicker">مراجعة قبل الاعتماد</p><h2>قائمة ضبط الجودة</h2><ul class="checklist">{quality_html}</ul><h3>أخطاء يجب تجنبها</h3><ul class="avoid">{avoid_html}</ul><h3>أدوار الفريق</h3><p>{esc(COMMON_SECTIONS['roles'])}</p></div></section>
<section class="section alt" id="decision"><div class="wrap"><p class="kicker">قواعد مسبقة</p><h2>متى نستمر أو نعدّل أو نوقف؟</h2><p>{esc(COMMON_SECTIONS['decision'])}</p><ul class="rules">{rules_html}</ul><table class="quality-table"><thead><tr><th>الحالة</th><th>الإجراء</th><th>المعلومة المطلوبة</th></tr></thead><tbody><tr><td>تحسن واضح ومستقر</td><td>استمرار مع تخفيف الدعم تدريجيًا إن كان ذلك هدفًا آمنًا.</td><td>أكثر من نقطة بيانات وموقف واحد.</td></tr><tr><td>لا تغير مع تنفيذ ضعيف</td><td>إصلاح التدريب والوقت والمواد قبل تغيير الهدف.</td><td>سجل جودة التنفيذ.</td></tr><tr><td>لا تغير مع تنفيذ كافٍ</td><td>مراجعة الفرضية أو التدريس أو المقياس والتكييفات.</td><td>بيانات الأداء والسياق وصوت الشخص.</td></tr><tr><td>ضرر أو خطر أو تراجع مفاجئ</td><td>إيقاف الإجراء غير الآمن وطلب تقييم مناسب.</td><td>وصف زمني دقيق وعوامل الصحة والسلامة.</td></tr></tbody></table></div></section>
<section class="section" id="form"><div class="wrap"><p class="kicker">نموذج عملي</p><h2>{esc(tool['title'])}</h2><p class="notice">لا تُرسل البيانات إلى خادم الموقع. اطبع النموذج أو احفظه PDF على جهاز موثوق، واستخدم رمزًا بدل الاسم الكامل عند الحاجة.</p><form class="card tool-form" onsubmit="return false"><div class="tool-row"><div><label for="date">التاريخ</label><input id="date" type="date"></div><div><label for="code">اسم مختصر أو رمز</label><input id="code" autocomplete="off"></div></div>{fields}<div class="toolbar"><button type="button" onclick="window.print()">طباعة أو حفظ PDF</button><button type="reset" class="secondary">مسح النموذج</button></div></form><p class="print-only">نسخة مطبوعة من: {esc(tool['title'])} — healthrenewal.org</p></div></section>
<section class="section alt"><div class="wrap"><p class="kicker">أسئلة شائعة</p><h2>توضيحات قبل الاستخدام</h2>{faq_html}</div></section>
<section class="section" id="sources"><div class="wrap"><p class="kicker">مصادر أصلية ورسمية</p><h2>المراجع التي بني عليها الإطار</h2><p>تدعم هذه المراجع المبادئ العامة للحقوق والمشاركة والتقييم الوظيفي والتخطيط والتقنيات. لا يعني الاستشهاد بها أن الجهة الناشرة راجعت هذه الصفحة أو اعتمدتها. يجب اختيار الأدوات والاختبارات والتدخلات الفردية وفق سؤال محدد وخبرة مهنية ونظام محلي.</p><div class="sources">{sources_html}</div></div></section>
<section class="section alt"><div class="wrap"><h2>أدوات مرتبطة</h2><div class="related">{related}</div><div class="toolbar"><a class="button" href="../">جميع أدوات التربية الخاصة</a><a class="button secondary" href="../../">العودة إلى دليل الأسرة</a></div></div></section>
</main><footer class="footer"><div class="wrap">© منصة الصحة النفسية وذوي الاحتياجات الخاصة · محتوى تثقيفي لا يستبدل التقييم الفردي.</div></footer></body></html>'''


def hub(payload: dict) -> str:
    tools = payload["tools"]
    cards = "\n".join(
      f'<article class="tool-card"><p><span class="tag">{esc(t["category"])}</span></p><h2>{esc(t["title"])}</h2><p>{esc(t["summary"])}</p><a class="button" href="{esc(t["slug"])}/">فتح الأداة</a></article>'
      for t in tools
    )
    categories = Counter(t["category"] for t in tools)
    category_text = "".join(f'<span class="tag">{esc(k)}: {v}</span>' for k,v in sorted(categories.items()))
    schema_payload = {"@context":"https://schema.org","@type":"CollectionPage","name":payload["title"],"description":"مركز عربي يضم 15 أداة طويلة وقابلة للطباعة للتربية الخاصة ودعم الأسرة.","url":ORIGIN+ROOT_ROUTE,"inLanguage":"ar","numberOfItems":len(tools),"dateModified":"2026-08-02"}
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>مركز أدوات التربية الخاصة ودعم الأسرة | 15 أداة عملية</title><meta name="description" content="خمسة عشر دليلًا وأداة عربية طويلة قابلة للطباعة للخطة التربوية الفردية، الأهداف، القياس، التكييفات، AAC، السلوك، التكنولوجيا المساندة والانتقال للرشد."><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{ORIGIN}{ROOT_ROUTE}"><meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta property="og:title" content="مركز أدوات التربية الخاصة ودعم الأسرة"><meta property="og:description" content="15 أداة طويلة وقابلة للطباعة تحول المعلومات إلى قرارات وخطط قابلة للقياس."><meta property="og:url" content="{ORIGIN}{ROOT_ROUTE}"><meta property="og:image" content="{ORIGIN}/assets/brand/social-card.svg"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="مركز أدوات التربية الخاصة ودعم الأسرة"><meta name="twitter:description" content="15 أداة طويلة وقابلة للطباعة للتعليم الدامج ودعم الأسرة."><meta name="twitter:image" content="{ORIGIN}/assets/brand/social-card.svg"><meta name="copyright" content="© 2026 Khaled Altheeb"><meta name="rights" content="All rights reserved"><link rel="license" href="../../copyright/"><link rel="stylesheet" href="../../assets/platform/platform-core.css?v=1.1.0"><script defer src="../../assets/platform/platform-core.js?v=1.1.0"></script><script type="application/ld+json">{json.dumps(schema_payload,ensure_ascii=False,separators=(',',':'))}</script>{STYLE}</head><body class="pt-platform"><a class="skip" href="#main">انتقل إلى المحتوى</a><header class="site-header"><div class="wrap head"><a class="brand" href="../../">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav class="nav"><a href="../">دليل الأسرة</a><a href="../../special-needs/">مركز الاحتياجات الخاصة</a><a href="../../learning-paths/">مسارات التعلم</a><a href="../../trust/">المنهجية</a></nav></div></header><main id="main"><nav class="wrap breadcrumbs"><a href="../../">الرئيسية</a> / <a href="../">دليل الأسرة</a> / <span aria-current="page">أدوات التربية الخاصة</span></nav><section class="hero"><div class="wrap"><p class="kicker">من المعرفة إلى ممارسة قابلة للقياس</p><h1>مركز أدوات التربية الخاصة ودعم الأسرة</h1><p class="lead">مجموعة مترابطة من 15 دليلًا ونموذجًا طويلًا تساعد الأسرة والطالب والمعلم وفريق التربية الخاصة على التخطيط والقياس والوصول والتواصل واتخاذ القرار المشترك. كل أداة تشرح المنطق والخطوات والمخاطر والأدوار، ثم تقدم نموذجًا قابلًا للطباعة.</p><p class="notice"><strong>حد الاستخدام:</strong> الأدوات تثقيفية وتنظيمية، ولا تشخص أو تستبدل تقييمًا فرديًا أو اللوائح المحلية. الأولوية لصوت الشخص وكرامته وسلامته وحقه في التواصل والتعليم الدامج.</p><div>{category_text}</div></div></section><section class="section"><div class="wrap"><p class="kicker">15 صفحة موسعة</p><h2>اختر الأداة بحسب القرار المطلوب</h2><div class="grid">{cards}</div></div></section><section class="section alt"><div class="wrap"><h2>كيف تستخدم المركز؟</h2><div class="grid"><div class="card"><h3>1. ابدأ بالسؤال</h3><p>حدد القرار المطلوب والنتيجة المهمة للشخص، ولا تبدأ باسم اختبار أو تدخل.</p></div><div class="card"><h3>2. اجمع خط أساس صغيرًا</h3><p>استخدم صوت الشخص ومثالًا حقيقيًا وملاحظة وبيانات كافية، لا ملفًا ضخمًا لا يقرأ.</p></div><div class="card"><h3>3. جرّب وراجع</h3><p>حدد مسؤولًا ومؤشر فائدة وضرر وموعدًا للمراجعة، ثم وثق القرار التالي.</p></div></div></div></section><section class="section"><div class="wrap"><h2>الأسس المشتركة</h2><p>{esc(COMMON_SECTIONS['rights'])}</p><p>المركز لا يساوي بين التعليم الدامج ووجود الطالب في المبنى فقط؛ المشاركة تعني الوصول إلى المنهج والتواصل والعلاقات والاختيار والدعم المناسب مع الأقران. كما لا يجعل الأسرة بديلًا عن الخدمات، بل شريكًا في المعلومات والقرار والمتابعة.</p></div></section></main><footer class="footer"><div class="wrap">© منصة الصحة النفسية وذوي الاحتياجات الخاصة</div></footer></body></html>'''
