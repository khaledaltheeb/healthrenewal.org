from __future__ import annotations

from typing import Any

from care_guides_v234_core import (
    BASE, BASE_PATH, SECTION_LABELS, SECTION_ORDER, category_map, compact, esc,
    guide_schema, head, index_schema, keyword_text, list_section, valid_date,
)


def guide_page(guide: dict[str, Any], categories: dict[str, dict[str, str]], all_guides: list[dict[str, Any]]) -> str:
    canonical = BASE + "care-guides/" + guide["slug"] + "/"
    category = categories[guide["category"]]
    populated = [(key, guide[key]) for key in SECTION_ORDER if isinstance(guide.get(key), list) and guide[key]]
    sections = "".join(list_section(key, values, idx) for idx, (key, values) in enumerate(populated, 1))
    toc = "".join(f'<li><a href="#section-{idx}">{esc(SECTION_LABELS[key])}</a></li>' for idx, (key, _) in enumerate(populated, 1))
    audience = "".join(f'<span class="care234__chip">{esc(item)}</span>' for item in guide.get("audience", []))
    sources = "".join(
        f'<li><a href="{esc(src["url"])}" rel="noopener noreferrer">{esc(src["publisher"])} — {esc(src["title"])} ({esc(src["year"])})</a></li>'
        for src in guide["sources"]
    )
    related_candidates = [item for item in all_guides if item["slug"] != guide["slug"] and item["category"] == guide["category"]]
    if len(related_candidates) < 3:
        related_candidates += [item for item in all_guides if item["slug"] != guide["slug"] and item not in related_candidates]
    related = "".join(
        f'<a href="{BASE_PATH}care-guides/{esc(item["slug"])}/">{esc(item.get("short_title", item["title"]))}</a>'
        for item in related_candidates[:3]
    )
    review_date = guide.get("reviewed_at") if valid_date(guide.get("reviewed_at")) else "غير موثق"
    review_text = (
        f"آخر مراجعة تحريرية موثقة: {review_date}. "
        + ("لا توجد مراجعة اختصاصية بشرية موثقة لهذا الدليل." if not guide.get("external_specialist_review") else "توجد مراجعة اختصاصية موثقة.")
    )
    keywords = keyword_text(guide, category["label"])
    schema = guide_schema(guide, canonical, category["label"])
    emergency = guide.get("emergency_note") or "عند وجود خطر مباشر أو تدهور حاد استخدم خدمات الطوارئ المحلية."
    return (
        head(guide["title"], guide["summary"], canonical, keywords, schema, modified=guide.get("reviewed_at", ""))
        + '<body><a class="skip-link" href="#main-content">انتقل إلى المحتوى</a>'
        + '<main id="main-content" class="care234">'
        + '<nav class="care234__breadcrumbs" aria-label="مسار الصفحة"><ol>'
        + f'<li><a href="{BASE_PATH}">الرئيسية</a></li><li><a href="{BASE_PATH}care-guides/">أدلة الرعاية</a></li><li aria-current="page">{esc(guide.get("short_title", guide["title"]))}</li></ol></nav>'
        + '<header class="care234__hero">'
        + f'<p class="care234__eyebrow">{esc(category["label"])} · دليل عملي غير تشخيصي</p><h1>{esc(guide["title"])}</h1>'
        + f'<p class="care234__lead">{esc(guide["summary"])}</p><div class="care234__chips" aria-label="الفئات المستفيدة">{audience}</div>'
        + '<div class="care234__actions">'
        + '<a class="care234__button care234__button--primary" href="#section-1">ابدأ بالخطوات العملية</a>'
        + f'<a class="care234__button" href="{BASE_PATH}care-guides/">استعرض كل الأدلة</a>'
        + f'<a class="care234__button" href="{BASE_PATH}encyclopedia/?q={esc(guide.get("short_title", guide["title"]))}">ابحث في الموسوعة</a>'
        + '</div></header>'
        + f'<aside class="care234__notice" role="note"><strong>عند الخطر أو التدهور الحاد:</strong> {esc(emergency)}</aside>'
        + '<aside class="care234__notice care234__notice--method" role="note"><strong>طريقة الاستخدام:</strong> لا تطبق كل البنود دفعة واحدة. اختر خطوة آمنة، اتفق مع الشخص قدر الإمكان، واطلب مساعدة مهنية عندما تستمر الصعوبة أو تتعطل الحياة.</aside>'
        + '<div class="care234__layout"><article class="care234__article">'
        + sections
        + f'<section class="care234__sources"><h2>مصادر مؤسسية للمراجعة</h2><ul>{sources}</ul>'
        + '<p>المصادر روابط أصلية للمراجعة ولا تعني أن الجهة الناشرة راجعت هذه الصياغة العربية أو اعتمدتها.</p>'
        + f'<p class="care234__review">{esc(review_text)}</p>'
        + '<p class="care234__review">هذا الدليل للتثقيف والدعم العام، ولا يستبدل التقييم أو العلاج الفردي. عند وجود خطر مباشر استخدم خدمات الطوارئ المحلية.</p></section>'
        + f'<section class="care234__section"><h2>أدلة مرتبطة</h2><div class="care234__related">{related}</div></section>'
        + '</article><aside class="care234__toc" aria-label="محتويات الدليل"><h2>في هذا الدليل</h2><ol>'
        + toc + '<li><a href="#sources">المصادر والمراجعة</a></li></ol></aside></div></main>'
        + '</body></html>'
    ).replace('<section class="care234__sources">', '<section id="sources" class="care234__sources">', 1)


def index_page(expansion: dict[str, Any], guides: list[dict[str, Any]], blocked_count: int) -> str:
    categories = category_map(expansion)
    cards = []
    for guide in guides:
        category = categories[guide["category"]]
        search = compact(" ".join([guide["title"], guide.get("short_title", ""), guide["summary"], *guide.get("search_intent", []), *guide.get("audience", [])]))
        cards.append(
            f'<article class="care234__card" data-care-card data-category="{esc(guide["category"])}" data-search="{esc(search)}">'
            f'<span class="care234__category">{esc(category["label"])}</span><h3>{esc(guide["title"])}</h3>'
            f'<p>{esc(guide["summary"])}</p><a class="care234__button" href="{BASE_PATH}care-guides/{esc(guide["slug"])}/">فتح الدليل الكامل</a></article>'
        )
    filters = ['<button type="button" data-care-filter="all" aria-pressed="true">كل الأدلة</button>']
    filters += [
        f'<button type="button" data-care-filter="{esc(item["id"])}" aria-pressed="false">{esc(item["label"])}</button>'
        for item in expansion["categories"]
    ]
    category_nav = "".join(
        f'<a href="#library" data-category-jump="{esc(item["id"])}"><strong>{esc(item["label"])}</strong><span>{esc(item["description"])}</span></a>'
        for item in expansion["categories"]
    )
    description = "مكتبة عربية مؤسسية لأدلة الرعاية والدعم النفسي العملي: خطوات قابلة للتنفيذ، ما ينبغي تجنبه، إشارات الخطر، مصادر أصلية، وبحث وتصنيف حسب الموقف."
    keywords = "أدلة الرعاية النفسية، دعم الأسرة، مقدم الرعاية، الصحة النفسية، التعامل مع القلق، الاكتئاب، الوسواس القهري، نوبة الهلع، ثنائي القطب، إيذاء النفس، اضطرابات الأكل، الخرف، مصطلحات علم النفس"
    canonical = BASE + "care-guides/"
    schema = index_schema(expansion, guides)
    source_count = sum(len(g["sources"]) for g in guides)
    return (
        head(expansion["title"], description, canonical, keywords, schema, page_type="website", modified=expansion["reviewed_at"])
        + '<body><a class="skip-link" href="#main-content">انتقل إلى المحتوى</a><main id="main-content" class="care234">'
        + '<nav class="care234__breadcrumbs" aria-label="مسار الصفحة"><ol>'
        + f'<li><a href="{BASE_PATH}">الرئيسية</a></li><li aria-current="page">أدلة الرعاية والدعم</li></ol></nav>'
        + '<header class="care234__hero"><p class="care234__eyebrow">مكتبة عملية للأسرة والأصدقاء ومقدمي الرعاية</p>'
        + f'<h1>{esc(expansion["title"])}</h1><p class="care234__lead">{esc(description)}</p>'
        + '<div class="care234__actions">'
        + '<a class="care234__button care234__button--primary" href="#library">ابحث عن دليل</a>'
        + f'<a class="care234__button" href="{BASE_PATH}start-here/">ابدأ من هنا</a>'
        + f'<a class="care234__button" href="{BASE_PATH}special-needs/">دعم ذوي الاحتياجات الخاصة</a>'
        + '</div><div class="care234__stats">'
        + f'<div class="care234__stat"><strong>{len(guides)}</strong><span>دليلًا منشورًا</span></div>'
        + f'<div class="care234__stat"><strong>{len(expansion["categories"])}</strong><span>مسارات موضوعية</span></div>'
        + f'<div class="care234__stat"><strong>{source_count}</strong><span>إحالة مؤسسية</span></div>'
        + f'<div class="care234__stat"><strong>{blocked_count}</strong><span>دليل محجوب للمراجعة</span></div>'
        + '</div></header>'
        + '<section class="care234__panel"><h2>اختر المسار الأقرب إلى حاجتك</h2><div class="care234__category-nav">'
        + category_nav + '</div></section>'
        + '<aside class="care234__notice" role="note"><strong>السلامة أولًا:</strong> هذه المكتبة لا تدير الطوارئ عن بعد. عند وجود خطر مباشر أو تسمم أو فقدان وعي أو نية لإيذاء النفس أو الآخرين، استخدم خدمات الطوارئ المحلية أو جهة صحية عاجلة.</aside>'
        + '<section class="care234__panel care234__notice--method"><h2>منهجية التحرير والنشر</h2>'
        + '<p>تُنشر الأدلة بعد فحص البنية والمصادر واللغة غير الوصمية وإشارات التصعيد. لا تُنشر المواد الموسومة بأنها تحتاج مراجعة اختصاصية، ولا يُدّعى وجود اعتماد أو مراجعة بشرية متخصصة ما لم تكن موثقة.</p>'
        + '<ul><li>مصدران مؤسسيان على الأقل لكل دليل.</li><li>فصل واضح بين التثقيف والتشخيص والعلاج.</li><li>خطوات عملية وما ينبغي تجنبه وإشارات الخطر.</li><li>تاريخ مراجعة وحالة مراجعة ظاهران للمستخدم.</li></ul></section>'
        + '<section id="library" class="care234__panel"><h2>ابحث في مكتبة الأدلة</h2>'
        + '<label for="care-search"><strong>اكتب الحالة أو الموقف أو الفئة</strong></label>'
        + '<input id="care-search" class="care234__search" type="search" data-care-search autocomplete="off" placeholder="مثال: نوبة هلع، الأسرة، المدرسة، إيذاء النفس">'
        + '<div class="care234__filters" aria-label="تصفية الأدلة">' + "".join(filters) + '</div>'
        + f'<p aria-live="polite">عدد النتائج: <strong data-care-count>{len(guides)}</strong></p>'
        + '<div class="care234__cards">' + "".join(cards) + '</div>'
        + '<p class="care234__empty" data-care-empty hidden>لم يظهر دليل مطابق. جرّب كلمة أوسع أو استعرض كل التصنيفات.</p></section>'
        + '<section class="care234__panel"><h2>كيف تستخدم الدليل بطريقة منهجية؟</h2><ol>'
        + '<li>ابدأ بإشارات الخطر وحدد هل توجد حاجة عاجلة.</li><li>اقرأ قسم الفهم لتجنب الوصم والتفسير المتسرع.</li>'
        + '<li>اختر خطوة واحدة قابلة للتنفيذ بدل تطبيق قائمة كاملة.</li><li>اتفق مع الشخص على الدعم والخصوصية قدر الإمكان.</li>'
        + '<li>راجع الأثر في النوم والدراسة والعمل والعلاقات، واطلب تقييمًا مهنيًا عند استمرار التعطل.</li></ol></section>'
        + f'</main><script defer src="{BASE_PATH}assets/care-guides-v234.js"></script></body></html>'
    )
