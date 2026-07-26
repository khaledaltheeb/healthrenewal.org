#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from family_sector_content_v249 import (
    BASE,
    BASE_PATH,
    FAQS,
    HUB_INTRO,
    HUB_SECTIONS,
    REVIEWED_AT,
    SOURCES,
    STYLE,
    VERSION,
    profile_for,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "content" / "sectors-v10" / "family.json"
REPORT_NAME = "family-sector-v249.json"
HUB_MARKER = 'data-family-sector-v249="1"'
ARTICLE_MARKER = "data-family-article-v249"


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in self.stack for tag in ("script", "style", "svg", "template", "noscript")):
            return
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.parts.append(value)


def visible_words(source: str) -> int:
    parser = TextParser()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts), flags=re.UNICODE))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def strip(source: str, pattern: str) -> str:
    return re.sub(pattern, "", source, flags=re.I | re.S)


def add_before_head(source: str, value: str) -> str:
    changed, count = re.subn(r"</head\s*>", value + "</head>", source, count=1, flags=re.I)
    if count != 1:
        raise ValueError("family_page_missing_head")
    return changed


def set_title(source: str, value: str) -> str:
    return add_before_head(strip(source, r"<title\b[^>]*>.*?</title>"), f"<title>{esc(value)}</title>")


def set_meta(source: str, key: str, value: str, *, prop: bool = False) -> str:
    attr = "property" if prop else "name"
    source = strip(source, rf'<meta\b[^>]*\b{attr}=["\']{re.escape(key)}["\'][^>]*>')
    return add_before_head(source, f'<meta {attr}="{esc(key)}" content="{esc(value)}">')


def set_link(source: str, rel: str, href: str, *, hreflang: str | None = None) -> str:
    if hreflang:
        pattern = rf'<link\b[^>]*\brel=["\']{re.escape(rel)}["\'][^>]*\bhreflang=["\']{re.escape(hreflang)}["\'][^>]*>'
    else:
        pattern = rf'<link\b[^>]*\brel=["\']{re.escape(rel)}["\'][^>]*>'
    source = strip(source, pattern)
    extra = f' hreflang="{esc(hreflang)}"' if hreflang else ""
    return add_before_head(source, f'<link rel="{esc(rel)}"{extra} href="{esc(href)}">')


def json_schema(payload: dict[str, Any], marker: str) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'<script type="application/ld+json" {marker}>{data}</script>'


def normalize_head(source: str, *, title: str, description: str, canonical: str, keywords: str, article: bool) -> str:
    source = strip(source, r'<style\b[^>]*data-family-style-v249=["\']1["\'][^>]*>.*?</style>')
    source = strip(source, r'<script\b[^>]*data-family-(?:hub|article)-schema-v249=["\'][^"\']+["\'][^>]*>.*?</script>')
    source = add_before_head(source, STYLE)
    source = set_title(source, title)
    source = set_meta(source, "description", description)
    source = set_meta(source, "keywords", keywords)
    source = set_meta(source, "robots", "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1")
    source = set_meta(source, "googlebot", "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1")
    source = set_meta(source, "author", "منصة مصطلحات علم النفس")
    source = set_meta(source, "og:locale", "ar_AR", prop=True)
    source = set_meta(source, "og:type", "article" if article else "website", prop=True)
    source = set_meta(source, "og:title", title, prop=True)
    source = set_meta(source, "og:description", description, prop=True)
    source = set_meta(source, "og:url", canonical, prop=True)
    source = set_meta(source, "article:modified_time", REVIEWED_AT, prop=True)
    source = set_meta(source, "twitter:card", "summary_large_image")
    source = set_meta(source, "twitter:title", title)
    source = set_meta(source, "twitter:description", description)
    source = set_link(source, "canonical", canonical)
    source = set_link(source, "alternate", canonical, hreflang="ar")
    source = set_link(source, "alternate", canonical, hreflang="x-default")
    return source


def replace_mains(source: str, main: str) -> str:
    matches = list(re.finditer(r"<main\b[^>]*>.*?</main\s*>", source, flags=re.I | re.S))
    if matches:
        return source[: matches[0].start()] + main + source[matches[-1].end() :]
    footer = re.search(r"<footer\b", source, flags=re.I)
    if footer:
        return source[: footer.start()] + main + source[footer.start() :]
    changed, count = re.subn(r"</body\s*>", main + "</body>", source, count=1, flags=re.I)
    if count != 1:
        raise ValueError("family_page_missing_body")
    return changed


def source_list(limit: int | None = None) -> str:
    rows = SOURCES if limit is None else SOURCES[:limit]
    return "".join(f'<li><a href="{esc(url)}" rel="noopener noreferrer">{esc(name)}</a></li>' for name, url in rows)


def faq_html() -> str:
    return "".join(f"<details><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>" for question, answer in FAQS)


def cards_html(articles: list[dict[str, Any]]) -> str:
    return "".join(
        f'''<article class="fv-card fv-guide"><p class="fv-meta">دليل أسري تطبيقي</p><h3>{esc(item["title"])}</h3><p>{esc(item["summary"])}</p><a href="{BASE_PATH}/sectors/family/{esc(item["slug"])}/">اقرأ الدليل الكامل</a></article>'''
        for item in articles
    )


def hub_main(data: dict[str, Any]) -> str:
    articles = data["articles"]
    sections = "".join(
        f'<section class="fv-section" id="{esc(section_id)}"><div class="fv-wrap"><h2>{esc(title)}</h2>{body}</div></section>'
        for section_id, title, body in HUB_SECTIONS
    )
    return f'''<main class="family-v249" {HUB_MARKER}>
<section class="fv-hero"><div class="fv-wrap"><p class="fv-meta">مركز عربي مؤسسي للعلاقات والرعاية الأسرية</p><h1>الصحة النفسية للأسرة: الأمان والتواصل والرعاية والقرار الآمن</h1><div class="fv-lead">{HUB_INTRO}</div><div class="fv-note"><strong>قاعدة السلامة:</strong> عند وجود عنف جارٍ، أو نية أو خطة لإيذاء النفس أو الآخرين، أو ارتباك شديد أو فقدان الاتصال بالواقع، لا تنتظر الأسرة اجتماعًا أو موعدًا روتينيًا. تُطلب الطوارئ المحلية أو أقرب قسم طوارئ، وتُتجنب المواجهة التي قد تزيد الخطر.</div><nav class="fv-nav" aria-label="أقسام مركز الأسرة"><a href="#principles">المبادئ</a><a href="#map">خريطة المشكلة</a><a href="#communication">التواصل</a><a href="#conflict">الإصلاح</a><a href="#children">حماية الأطفال</a><a href="#care">الرعاية</a><a href="#transitions">التحولات</a><a href="#triage">المساعدة</a><a href="#guides">الأدلة</a><a href="#sources">المصادر</a></nav></div></section>
{sections}
<section class="fv-section" id="agreement"><div class="fv-wrap"><h2>اتفاق أسري قصير قابل للتطبيق</h2><div class="fv-grid"><article class="fv-card"><h3>ما الذي نحميه؟</h3><p>تختار الأسرة ثلاث قواعد فقط: لا إهانة ولا تهديد ولا عنف، ويحق لأي شخص طلب توقف مؤقت مع وقت محدد للعودة. تُكتب القواعد بلغة واضحة وتُشرح بما يناسب العمر وطريقة التواصل.</p></article><article class="fv-card"><h3>كيف نتخذ القرار؟</h3><p>يحدد الموضوع ومن يتأثر به وما الذي يمكن لكل شخص اختياره. لا تُساوى المشاركة بتحميل الطفل أو الشخص المحتاج إلى دعم مسؤولية قرار الكبار.</p></article><article class="fv-card"><h3>كيف نقيس الأثر؟</h3><p>تُسجل مرات التصعيد ومدته، والقدرة على العودة، والأثر في النوم والعمل والدراسة والرعاية. تُراجع البيانات بعد أسبوعين بدل الحكم من يوم جيد أو سيئ.</p></article><article class="fv-card"><h3>متى ننتقل لخدمة؟</h3><p>عند استمرار التعطل أو الخوف أو تكرار الأذى، تُحدد خدمة مناسبة: رعاية أولية أو مختص نفسي أو اجتماعي أو أسري أو خدمة حماية أو طوارئ بحسب مستوى الخطر.</p></article></div></div></section>
<section class="fv-section" id="appointment"><div class="fv-wrap"><h2>الاستعداد لموعد مهني مفيد</h2><p>تحضر الأسرة خطًا زمنيًا مختصرًا للمشكلة، وما الذي يسبقها ويخففها، وأثرها في الوظائف اليومية، والمحاولات السابقة، والأمراض والأدوية والمواد والنوم والألم والضغوط والتحولات. تُذكر وجهات النظر المختلفة دون تحويل الموعد إلى محاكمة، ويُطلب وقت منفرد عندما توجد معلومات حساسة أو خوف.</p><p>تُسأل الخدمة عن طبيعة التقييم، ومن سيشارك، وكيف تُحفظ الخصوصية، وما الهدف القابل للقياس، والبدائل والفوائد والمخاطر، وموعد المراجعة، وما الذي يستدعي اتصالًا مبكرًا. لا يُفترض أن العلاج الأسري مناسب تلقائيًا عند العنف أو السيطرة القسرية؛ السلامة والتقييم المنفرد يسبقان القرار.</p></div></section>
<section class="fv-section" id="inclusion"><div class="fv-wrap"><h2>الإتاحة والدمج داخل الأسرة والخدمات</h2><p>تُتاح المشاركة للأشخاص ذوي الاحتياجات الخاصة عبر لغة واضحة ووقت كاف ووسائل تواصل بديلة وبيئة أقل إثارة حسية وتسهيلات للحركة والقراءة ولغة الإشارة عند الحاجة. لا تُفسر صعوبة الكلام أو التواصل البصري أو التنظيم الحسي على أنها رفض أو قلة احترام، ولا تُتخذ القرارات عن الشخص ما دام يستطيع المشاركة بدعم مناسب.</p><p>يُراجع أثر التحيز المرتبط بالعمر أو الجنس أو الدخل أو الحالة الاجتماعية أو المرض، وتُحمى الخصوصية عند الاعتماد على مرافق أو مترجم. تسأل الأسرة والخدمة الشخص مباشرة عن تفضيلاته بدل الحديث عنه فقط.</p></div></section>
<section class="fv-section" id="guides"><div class="fv-wrap"><h2>الأدلة التطبيقية العشرون</h2><p>كل دليل يشرح المؤشرات والملاحظة والخطوات والعبارات المفيدة وما يجب تجنبه، ثم يقدم خطة لمدة أسبوعين وحدودًا للسلامة وطلب المساعدة. الأدلة للتثقيف والتنظيم ولا تثبت تشخيصًا.</p><div class="fv-grid">{cards_html(articles)}</div></div></section>
<section class="fv-section" id="faq"><div class="fv-wrap"><h2>أسئلة شائعة</h2>{faq_html()}</div></section>
<section class="fv-section" id="sources"><div class="fv-wrap"><h2>المنهجية والمصادر المؤسسية</h2><p>بُني المحتوى من إرشادات ومنصات مؤسسية، ثم صيغ عربيًا للتثقيف واتخاذ القرار الآمن. لا تعني الإحالة إلى المصدر اعتماد المنصة من الجهة المذكورة، ولا تُعد الصفحة ترجمة حرفية أو بديلًا عن التقييم المهني المحلي.</p><ul>{source_list()}</ul><p>آخر مراجعة داخلية: {REVIEWED_AT}. تُراجع الروابط والحدود المهنية ضمن بوابات الإنتاج، ويُمنع الادعاء بالتشخيص أو العلاج المضمون.</p></div></section>
</main>'''


def list_html(values: list[Any]) -> str:
    return "".join(f"<li>{esc(value)}</li>" for value in values)


def article_main(item: dict[str, Any]) -> str:
    slug = str(item["slug"])
    title = str(item["title"])
    summary = str(item["summary"])
    signals = list(item.get("signals") or [])
    steps = list(item.get("steps") or [])
    phrases = list(item.get("phrases") or [])
    avoid = str(item.get("avoid") or "تحويل الخطة إلى لوم أو ضغط إضافي")
    profile = profile_for(slug)
    questions = list(profile["questions"])
    return f'''<main class="family-v249" {ARTICLE_MARKER}="{esc(slug)}">
<section class="fv-hero"><div class="fv-wrap"><p class="fv-meta">دليل أسري تطبيقي غير تشخيصي</p><h1>{esc(title)}</h1><p class="fv-lead">{esc(summary)}</p><div class="fv-note"><strong>حد السلامة:</strong> إذا ظهر عنف أو تهديد أو نية للإيذاء أو فقدان الاتصال بالواقع أو عجز عن رعاية الاحتياجات الأساسية، تُوقف التجربة المنزلية ويُطلب دعم عاجل أو متخصص بحسب الحالة المحلية.</div><nav class="fv-nav" aria-label="أقسام الدليل"><a href="#understand">الفهم</a><a href="#observe">الملاحظة</a><a href="#steps">الخطوات</a><a href="#language">العبارات</a><a href="#followup">المتابعة</a><a href="#help">طلب المساعدة</a></nav></div></section>
<section class="fv-section" id="understand"><div class="fv-wrap"><h2>فهم الموضوع داخل سياق الأسرة</h2><p>{esc(profile["context"])}</p><p>يركز هذا الدليل على «{esc(title)}» بوصفه مسارًا للتنظيم والتواصل، لا اختبارًا يحدد من المخطئ ولا أداة لتشخيص فرد. قد تتداخل الصحة الجسدية والنوم والألم والأدوية والمواد والضغط المالي والعمل والرعاية والتاريخ النفسي والتحولات، لذلك تُجمع المعلومات قبل افتراض سبب واحد.</p><p>{esc(summary)} ويُترجم هذا الهدف إلى سلوك يمكن ملاحظته واتفاق صغير يمكن مراجعته. لا يُطلب من الأسرة تغيير كل شيء في وقت واحد، لأن كثرة التعليمات ترفع الضغط وتخفي أثر كل خطوة.</p></div></section>
<section class="fv-section" id="observe"><div class="fv-wrap"><h2>مؤشرات تستحق الملاحظة المنظمة</h2><ul>{list_html(signals)}</ul><p>{esc(profile["assessment"])}</p><p>تُسجل الملاحظات لمدة أسبوعين: وقت الموقف، وما سبقه، ومن كان حاضرًا، وما قيل أو فُعل، ومدته، وكيف انتهى، وأثره في النوم والأكل والعمل والدراسة والرعاية والعلاقات. يُفصل الوصف عن التفسير؛ فعبارة «توقف الحديث وغادر الشخص عشر دقائق» أدق من «لا يهتم بنا».</p><p>لا تُستخدم المتابعة للمراقبة القهرية أو جمع الأدلة ضد شخص. يطّلع كل مشارك على الهدف بقدر مناسب، وتُحفظ المعلومات الحساسة، ويُستخدم تسجيل منفرد عند وجود خوف أو سيطرة.</p></div></section>
<section class="fv-section" id="steps"><div class="fv-wrap"><h2>خطوات عملية مرتبة</h2><ol>{list_html(steps)}</ol><p>ابدؤوا بخطوة واحدة وحددوا من يملك تنفيذها ومتى وأين. تُكيف الخطوة للعمر واللغة والقدرة الحسية والمعرفية والوقت المتاح. إذا لم تنجح، يُسأل: هل كانت كبيرة؟ هل كان التوقيت غير مناسب؟ هل توجد حاجة جسدية أو خطر أو عائق في البيئة؟</p><p>يُمنع تحويل الاتفاق إلى اختبار طاعة أو عقاب. المشاركة الحقيقية تعني سؤال المتأثرين عما يجعل الخطة أسهل، وإتاحة خيار آمن، ومراجعة أثرها بدل فرض الاستمرار لأن الكبار قرروها.</p></div></section>
<section class="fv-section" id="language"><div class="fv-wrap"><h2>لغة تساعد على الاتصال</h2><div class="fv-grid"><article class="fv-card"><h3>عبارات مقترحة</h3><ul>{list_html(phrases)}</ul><p>يمكن تعديل العبارة لتناسب ثقافة الأسرة وطريقة التواصل، مع الحفاظ على الوضوح والاحترام وعدم الوعيد.</p></article><article class="fv-card"><h3>ما يجب تجنبه</h3><p>{esc(avoid)}</p><p>تُتجنب التعميمات مثل دائمًا وأبدًا، والمقارنات، وكشف الأسرار، والسخرية من المشاعر، واستخدام الأطفال رسلًا، والتهديد بترك العلاقة أو الحرمان من الرعاية لإجبار الشخص.</p></article></div></div></section>
<section class="fv-section" id="questions"><div class="fv-wrap"><h2>أسئلة تعمق الفهم</h2><ul>{list_html(questions)}</ul><p>لا تُطرح الأسئلة كلها دفعة واحدة. يُختار سؤال واحد في وقت هادئ، ويُعطى الشخص وقتًا أو طريقة بديلة للإجابة. لا يُضغط على الإفصاح إذا كان قد يزيد الخطر.</p></div></section>
<section class="fv-section" id="roles"><div class="fv-wrap"><h2>توزيع الأدوار ومنع الحمل غير العادل</h2><p>تكتب الأسرة المهام المرئية وغير المرئية المرتبطة بالموضوع: التذكر والتخطيط والاتصال والمتابعة والتهدئة والنقل والرعاية. لكل مهمة مالك واضح وبديل عند الغياب، ويُراعى العمر والقدرة والوقت. المساعدة العابرة لا تكفي إذا بقي شخص واحد مسؤولًا عن اكتشاف الحاجة وطلب المساعدة ومراقبة التنفيذ.</p><p>يُحفظ حق الأطفال في المشاركة دون تحمل مسؤولية مشاعر الكبار، وحق مقدم الرعاية في الراحة، وحق الشخص الذي يحتاج دعمًا في الاختيار والاستقلال الممكن. تُراجع العدالة لا المساواة الحسابية فقط، لأن الاحتياجات والقدرات تختلف.</p></div></section>
<section class="fv-section" id="followup"><div class="fv-wrap"><h2>خطة متابعة لمدة أسبوعين</h2><p><strong>الأيام 1–3:</strong> جمع خط أساس بسيط وتحديد موقف واحد وهدف واحد وقاعدة سلامة. <strong>الأيام 4–7:</strong> تطبيق الخطوة المتفق عليها في مواقف محددة، وتسجيل السهولة والأثر وأي عائق.</p><p><strong>الأيام 8–11:</strong> سؤال كل متأثر عما ساعد وما أزعج، وتعديل عنصر واحد فقط مثل التوقيت أو العبارة أو البيئة أو توزيع المهمة. <strong>الأيام 12–14:</strong> مقارنة التكرار والمدة والأثر بخط الأساس، وتحديد الاستمرار أو التبسيط أو طلب خدمة.</p><p>يُعد التحسن انخفاضًا في الأذى والتصعيد، وزيادة في الوضوح والعودة للحوار وأداء الوظائف اليومية، لا اختفاء كل مشاعر صعبة. إذا تراجع الأمان أو زاد التعطل، لا تنتظر الأسرة نهاية الأسبوعين.</p></div></section>
<section class="fv-section" id="help"><div class="fv-wrap"><h2>متى تصبح المساعدة المهنية مهمة؟</h2><p>تُطلب مساعدة مبكرة عندما تستمر المشكلة أو تتكرر، أو تعطل النوم أو الأكل أو المدرسة أو العمل أو الرعاية، أو يظهر انسحاب شديد أو خوف أو استخدام مواد أو أعراض جسدية ونفسية متداخلة. يبدأ المسار برعاية أولية أو مختص نفسي أو اجتماعي أو أسري أو خدمة مدرسية بحسب الموضوع.</p><p>عند العنف أو السيطرة القسرية أو الخوف من الانتقام، تكون خطة السلامة والتواصل المنفرد مع خدمة مؤهلة أسبق من الجلسة المشتركة. وعند نية أو خطة للإيذاء أو ارتباك شديد أو فقدان الاتصال بالواقع أو عنف جارٍ، تُطلب الطوارئ المحلية أو أقرب قسم طوارئ.</p><p>يحضر الموعد خط زمني وملاحظات الأثر والأدوية والأمراض والنوم والمواد والمحاولات السابقة والأسئلة. اسألوا عن الهدف والبدائل وكيف ستقاس الاستجابة ومتى تُراجع الخطة.</p></div></section>
<section class="fv-section"><div class="fv-wrap"><h2>مصادر مؤسسية مختارة</h2><ul>{source_list(6)}</ul><p>آخر مراجعة داخلية: {REVIEWED_AT}. المحتوى للتثقيف وتنظيم طلب المساعدة، ولا يثبت تشخيصًا ولا يوصي بقرار دوائي فردي ولا يَعِد بنتيجة علاجية.</p></div></section>
</main>'''


def hub_schema(data: dict[str, Any]) -> str:
    url = f"{BASE}/sectors/family/"
    articles = data["articles"]
    graph = [
        {"@type": "CollectionPage", "@id": url + "#page", "url": url, "name": "الصحة النفسية للأسرة", "description": data["subtitle"], "inLanguage": "ar", "dateModified": REVIEWED_AT},
        {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"}, {"@type": "ListItem", "position": 2, "name": "الصحة النفسية للأسرة", "item": url}]},
        {"@type": "ItemList", "@id": url + "#guides", "numberOfItems": len(articles), "itemListElement": [{"@type": "ListItem", "position": i, "url": f'{BASE}/sectors/family/{item["slug"]}/', "name": item["title"]} for i, item in enumerate(articles, 1)]},
        {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQS]},
    ]
    return json_schema({"@context": "https://schema.org", "@graph": graph}, 'data-family-hub-schema-v249="graph"')


def article_schema(item: dict[str, Any]) -> str:
    url = f'{BASE}/sectors/family/{item["slug"]}/'
    payload = {"@context": "https://schema.org", "@type": "Article", "headline": item["title"], "description": item["summary"], "url": url, "mainEntityOfPage": url, "inLanguage": "ar", "dateModified": REVIEWED_AT, "author": {"@type": "Organization", "name": "منصة مصطلحات علم النفس"}, "publisher": {"@type": "Organization", "name": "منصة مصطلحات علم النفس"}, "isPartOf": {"@type": "CollectionPage", "name": "الصحة النفسية للأسرة", "url": f"{BASE}/sectors/family/"}}
    return json_schema(payload, f'{ARTICLE_MARKER}-schema="{esc(item["slug"])}"')


def update_robots(site: Path) -> bool:
    path = site / "robots.txt"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    line = f"Allow: {BASE_PATH}/sectors/family/"
    if line in text:
        return False
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + line + "\n", encoding="utf-8")
    return True


def upgrade(site: Path, source_path: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    site = Path(site).resolve()
    source_path = Path(source_path).resolve()
    data = json.loads(source_path.read_text(encoding="utf-8"))
    articles = data.get("articles")
    if not isinstance(articles, list) or len(articles) != 20:
        raise ValueError(f"family_source_requires_twenty_articles:{len(articles) if isinstance(articles, list) else articles}")
    slugs = [str(item.get("slug", "")) for item in articles]
    if len(slugs) != len(set(slugs)) or any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in slugs):
        raise ValueError("family_source_invalid_or_duplicate_slugs")

    hub_path = site / "sectors" / "family" / "index.html"
    if not hub_path.is_file():
        raise ValueError("family_hub_missing")
    hub = hub_path.read_text(encoding="utf-8")
    hub = normalize_head(hub, title="الصحة النفسية للأسرة | الأمان والتواصل والرعاية", description="مركز عربي مؤسسي للصحة النفسية للأسرة: الأمان النفسي والتواصل والحدود وإصلاح الخلاف وحماية الأطفال والرعاية والفقد والطلاق والضغط وطلب المساعدة.", canonical=f"{BASE}/sectors/family/", keywords="الصحة النفسية للأسرة, التواصل الأسري, الأمان النفسي, الحدود الأسرية, الخلافات الأسرية, دعم الوالدين, مقدم الرعاية, الطلاق والفقد")
    hub = replace_mains(hub, hub_main(data))
    hub = add_before_head(hub, hub_schema(data))
    hub_path.write_text(hub, encoding="utf-8")

    words: dict[str, int] = {}
    enriched = 0
    for item in articles:
        slug = str(item["slug"])
        path = site / "sectors" / "family" / slug / "index.html"
        if not path.is_file():
            raise ValueError(f"family_article_missing:{slug}")
        source = path.read_text(encoding="utf-8")
        already = f'{ARTICLE_MARKER}="{slug}"' in source
        source = normalize_head(source, title=f'{item["title"]} | الصحة النفسية للأسرة', description=f'{item["summary"]} دليل عملي للملاحظة والخطوات واللغة والمتابعة وحدود السلامة وطلب المساعدة دون تشخيص ذاتي.', canonical=f"{BASE}/sectors/family/{slug}/", keywords=f'{item["title"]}, الصحة النفسية للأسرة, التواصل الأسري, الدعم النفسي, العلاقات الأسرية, طلب المساعدة')
        source = replace_mains(source, article_main(item))
        source = add_before_head(source, article_schema(item))
        path.write_text(source, encoding="utf-8")
        enriched += 0 if already else 1
        words[slug] = visible_words(source)

    robots_updated = update_robots(site)
    combined = hub + "\n" + "\n".join((site / "sectors" / "family" / slug / "index.html").read_text(encoding="utf-8") for slug in slugs)
    report = {
        "version": VERSION,
        "status": "passed",
        "source_articles": len(articles),
        "article_pages_enriched": enriched,
        "hub_words": visible_words(hub),
        "minimum_article_words": min(words.values()),
        "maximum_article_words": max(words.values()),
        "hub_h1": len(re.findall(r"<h1\b", hub, flags=re.I)),
        "hub_h2": len(re.findall(r"<h2\b", hub, flags=re.I)),
        "faq_items": len(FAQS),
        "institutional_sources": len(SOURCES),
        "robots_updated": robots_updated,
        "banned_term_present": "معاقين" in combined,
        "diagnostic_claim_present": any(term in combined for term in ("هذا يعني أنك", "يؤكد التشخيص", "العلاج مضمون")),
        "reviewed_at": REVIEWED_AT,
        "article_words": words,
    }
    if report["hub_h1"] != 1 or report["hub_words"] < 2500 or report["minimum_article_words"] < 800 or report["banned_term_present"] or report["diagnostic_claim_present"]:
        raise ValueError(f'family_sector_v249_contract_failed:hub={report["hub_words"]}:minimum={report["minimum_article_words"]}:h1={report["hub_h1"]}:banned={report["banned_term_present"]}:diagnostic={report["diagnostic_claim_present"]}')
    if hub.lower().count('rel="canonical"') != 1 or "noindex" in hub.lower():
        raise ValueError("family_hub_indexability_contract")
    for item in articles:
        source = (site / "sectors" / "family" / str(item["slug"]) / "index.html").read_text(encoding="utf-8")
        if len(re.findall(r"<h1\b", source, flags=re.I)) != 1 or source.lower().count('rel="canonical"') != 1 or "noindex" in source.lower():
            raise ValueError(f'family_article_indexability_contract:{item["slug"]}')
        if source.count(f'{ARTICLE_MARKER}="{item["slug"]}"') != 1:
            raise ValueError(f'family_article_marker_contract:{item["slug"]}')

    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade the institutional family mental-health sector")
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    upgrade(args.site, args.source)


if __name__ == "__main__":
    main()
