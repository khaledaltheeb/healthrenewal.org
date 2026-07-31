#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from women_sector_content_v244 import (
    ARTICLE_COMMON,
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
DEFAULT_SOURCE = ROOT / "content" / "sectors-v10" / "women.json"
REPORT_NAME = "women-sector-v244.json"
HUB_MARKER = 'data-women-sector-v244="1"'
ARTICLE_MARKER = "data-women-article-v244"


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
        raise ValueError("women_page_missing_head")
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
    source = strip(source, r'<style\b[^>]*data-women-style-v244=["\']1["\'][^>]*>.*?</style>')
    source = strip(source, r'<script\b[^>]*data-women-(?:hub|article)-schema-v244=["\'][^"\']+["\'][^>]*>.*?</script>')
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
        raise ValueError("women_page_missing_body")
    return changed


def source_list(limit: int | None = None) -> str:
    rows = SOURCES if limit is None else SOURCES[:limit]
    return "".join(f'<li><a href="{esc(url)}" rel="noopener noreferrer">{esc(name)}</a></li>' for name, url in rows)


def faq_html() -> str:
    return "".join(f"<details><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>" for question, answer in FAQS)


def cards_html(articles: list[dict[str, Any]]) -> str:
    return "".join(
        f'''<article class="wv-card wv-guide"><p class="wv-meta">دليل تطبيقي مؤسسي</p><h3>{esc(item["title"])}</h3><p>{esc(item["summary"])}</p><a href="{BASE_PATH}/sectors/women/{esc(item["slug"])}/">اقرئي الدليل الكامل</a></article>'''
        for item in articles
    )


def hub_main(data: dict[str, Any]) -> str:
    sections = "".join(f'<section class="wv-section" id="{esc(section_id)}"><div class="wv-wrap"><h2>{esc(title)}</h2>{body}</div></section>' for section_id, title, body in HUB_SECTIONS)
    return f'''<main class="women-v244" {HUB_MARKER}>
<section class="wv-hero"><div class="wv-wrap"><p class="wv-meta">مركز عربي مؤسسي للتوعية والقرار الآمن</p><h1>الصحة النفسية للمرأة عبر مراحل الحياة</h1><div class="wv-lead">{HUB_INTRO}</div><div class="wv-note"><strong>قاعدة السلامة:</strong> عند وجود نية أو خطة لإيذاء النفس أو الطفل أو الآخرين، أو ارتباك شديد، أو فقدان للاتصال بالواقع، أو عنف يجعل المكان غير آمن، لا تنتظري موعدًا روتينيًا. اطلبي الطوارئ المحلية أو توجهي إلى أقرب قسم طوارئ ولا تبقي وحدك.</div><nav class="wv-nav" aria-label="أقسام مركز المرأة"><a href="#principles">المبادئ</a><a href="#life-course">مراحل الحياة</a><a href="#observe">الملاحظة</a><a href="#perinatal">الحمل والولادة</a><a href="#cycle">الدورة</a><a href="#menopause">منتصف العمر</a><a href="#safety">السلامة</a><a href="#triage">المساعدة</a><a href="#guides">الأدلة</a><a href="#sources">المصادر</a></nav></div></section>
{sections}
<section class="wv-section" id="appointment"><div class="wv-wrap"><h2>الاستعداد لموعد مهني مفيد</h2><div class="wv-grid"><article class="wv-card"><h3>قصة زمنية مختصرة</h3><p>اكتبي متى بدأت الأعراض وما الذي تغير قبلها، وما إذا كانت ترتبط بالدورة أو الحمل أو الولادة أو دواء أو مرض أو عنف أو ضغط جديد. اذكري النوبات السابقة والعلاج الذي ساعد أو لم يساعد.</p></article><article class="wv-card"><h3>الأثر الوظيفي</h3><p>حددي ما تعطل في النوم والأكل والنظافة والعمل والدراسة والرعاية والعلاقات واتخاذ القرار. وصف الأثر أدق من استخدام كلمات عامة مثل متعبة أو متوترة.</p></article><article class="wv-card"><h3>القائمة الطبية</h3><p>أحضري الأدوية والمكملات ووسائل منع الحمل أو العلاجات الهرمونية والحساسية والأمراض والفحوص الحديثة. لا توقفي علاجًا ولا تغيري جرعة قبل المناقشة.</p></article><article class="wv-card"><h3>خطة ومراجعة</h3><p>اسألي عن الاحتمالات والفحوص والبدائل والفوائد والمخاطر وكيف سيقاس التحسن ومتى تكون المراجعة وما العلامات التي تستدعي اتصالًا مبكرًا.</p></article></div></div></section>
<section class="wv-section" id="family"><div class="wv-wrap"><h2>دور الأسرة والشريك دون سيطرة</h2><p>الدعم الجيد لا يعني مراقبة المرأة أو اتخاذ القرار عنها. يبدأ بالاستماع من دون تقليل أو لوم، ثم سؤالها عن المساعدة العملية الأكثر فائدة. قد يكون المطلوب حماية النوم أو رعاية طفل أو نقل مهمة منزلية أو مرافقة إلى موعد أو المساعدة في الوصول إلى خدمة.</p><p>تجنبوا عبارات مثل كل النساء يمررن بهذا أو عليك أن تكوني قوية أو المهم أن الطفل بخير. استخدموا بدلًا منها: أصدق أن ما تمرين به صعب، وسأبقى معك ونحن نطلب المساعدة. عند خطر مباشر لا تعتمدوا على الوعود وحدها ولا تتركوها وحدها.</p></div></section>
<section class="wv-section" id="inclusion"><div class="wv-wrap"><h2>الإتاحة والدمج</h2><p>يجب أن تكون خدمات صحة المرأة متاحة للنساء ذوات الاحتياجات الخاصة والاختلافات العصبية، مع لغة واضحة ووقت كاف ومواد مكتوبة وبيئة أقل إثارة حسية ومترجمة لغة إشارة وتسهيلات للحركة والتواصل ومرافقة تختارها المرأة. لا يفترض غياب الأهلية أو الاستقلال بسبب الإعاقة.</p><p>تراعى كذلك الثقافة واللغة والهجرة والوضع الاقتصادي والمسؤوليات الأسرية والخصوصية الرقمية. إزالة الحواجز مسؤولية الخدمة والأسرة والمجتمع، لا عبء إضافي على المرأة التي تطلب المساعدة.</p></div></section>
<section class="wv-section" id="guides"><div class="wv-wrap"><h2>عشرون دليلًا تطبيقيًا</h2><p>تغطي الأدلة التحولات الإنجابية والدورة ومنتصف العمر والاختلاف العصبي والعمل والرعاية والجسد والعلاقات والسلامة. كل دليل يشرح المؤشرات والملاحظة وما ينبغي مناقشته طبيًا ونفسيًا وكيفية الاستعداد للموعد وحدود الطوارئ.</p><div class="wv-grid">{cards_html(data["articles"])}</div></div></section>
<section class="wv-section wv-faq" id="faq"><div class="wv-wrap"><h2>أسئلة شائعة</h2>{faq_html()}</div></section>
<section class="wv-section" id="sources"><div class="wv-wrap"><h2>المصادر المؤسسية</h2><p>اختيرت المصادر من جهات صحية ومهنية رسمية. الروابط مرجعية ولا تعني أن الصفحة العربية ترجمة حرفية أو اعتمادًا من تلك الجهات. روجع النطاق في {REVIEWED_AT} ويجب تحديثه عند تغير الإرشادات.</p><ol>{source_list()}</ol></div></section>
<section class="wv-section" id="methodology"><div class="wv-wrap"><h2>المنهجية وحدود المحتوى</h2><p>بني المركز للتوعية والاستعداد للمقابلة واتخاذ قرار طلب المساعدة. لا يستخدم أعراضًا منفردة لإثبات تشخيص، ولا يقدم جرعات أو قرارات دوائية، ولا يفترض أن الهرمونات أو النوع الاجتماعي يفسران كل حالة. تفصل الصفحات بين التحري والتشخيص وتعرض الطوارئ بوضوح وتراعي الخصوصية والعنف والاختلافات الجسدية والعصبية والاجتماعية.</p><p class="wv-meta">الإصدار المؤسسي {VERSION} — آخر مراجعة بنيوية ومصدرية: {REVIEWED_AT}.</p></div></section>
</main>'''


def list_html(values: list[Any]) -> str:
    return "".join(f"<li>{esc(value)}</li>" for value in values)


def article_main(item: dict[str, Any]) -> str:
    slug = str(item["slug"])
    profile = profile_for(slug)
    signals = list_html(item.get("signals", []))
    questions = list_html(list(profile["questions"]))
    steps = "".join(f'<article class="wv-card"><h3>{esc(step)}</h3><p>حوّلي هذه الخطوة إلى إجراء محدد له وقت ومسؤول وطريقة لمراجعة الأثر، بدل بقائها نصيحة عامة.</p></article>' for step in item.get("steps", []))
    phrases = "".join(f'<p class="wv-quote">«{esc(value)}»</p>' for value in item.get("phrases", []))
    aside = "".join(f'<a href="#{target}">{label}</a>' for target, label in (("understand", "الفهم"), ("signals", "المؤشرات"), ("medical", "الجسد والتقييم"), ("observe", "المتابعة"), ("plan", "الخطة"), ("appointment", "الموعد"), ("safety", "السلامة"), ("sources", "المصادر")))
    return f'''<main class="women-v244" {ARTICLE_MARKER}="{esc(slug)}"><header class="wv-article-head"><div class="wv-wrap"><p class="wv-meta"><a href="{BASE_PATH}/sectors/women/">مركز الصحة النفسية للمرأة</a> / دليل تطبيقي</p><h1>{esc(item["title"])}</h1><p class="wv-lead">{esc(item["summary"])}</p><div class="wv-note">هذا الدليل للتوعية والاستعداد للتقييم، وليس للتشخيص الذاتي أو تغيير الأدوية. تعامل أفكار إيذاء النفس أو الطفل أو الآخرين والارتباك الشديد وفقدان الاتصال بالواقع والخطر الناتج عن العنف كحالات تستحق استجابة عاجلة.</div></div></header><div class="wv-wrap wv-section wv-layout"><article>
<section id="understand"><h2>فهم الموضوع دون اختزال</h2><p>{esc(profile["context"])}</p><p>{esc(ARTICLE_COMMON["overview"])}</p><p>استخدمي لغة تصف التجربة بدل تثبيت هوية مرضية. وصف التغير في النوم والطاقة والتركيز والعلاقات والوظيفة اليومية يساعد أكثر من الحكم على الذات. وجود معاناة حقيقية لا يعني بالضرورة تشخيصًا واحدًا، وغياب التشخيص لا يلغي الحاجة إلى دعم وتكييفات عملية.</p></section>
<section class="wv-section" id="signals"><h2>مؤشرات تستحق الملاحظة</h2><ul>{signals}</ul><p>تزداد أهمية المؤشر عندما يتكرر أو يزداد أو يعطل وظيفة مهمة أو يترافق مع أعراض أخرى. راقبي أيضًا تغير الشهية والطاقة والتركيز والألم والدورة والنوم والاندفاع واستخدام المواد والعزلة والتعرض للعنف. لا تنتظري اكتمال كل المؤشرات لطلب المساعدة إذا كان التعطل واضحًا.</p></section>
<section class="wv-section" id="medical"><h2>ما الذي ينبغي مناقشته طبيًا ونفسيًا؟</h2><p>{esc(profile["medical"])}</p><p>حضري قائمة الأدوية والمكملات ووسائل منع الحمل أو العلاجات الهرمونية إن وجدت، والتغييرات الحديثة، والتاريخ العائلي والنفسي، والحمل أو الرضاعة أو الدورة أو انقطاع الطمث بحسب السياق. اذكري ما يهمك من آثار جانبية أو خصوصية أو تكلفة أو وصول أو مسؤوليات رعاية؛ فالخطة التي لا تناسب الواقع يصعب استمرارها.</p></section>
<section class="wv-section" id="observe"><h2>متابعة لمدة أسبوعين</h2><p>{esc(ARTICLE_COMMON["monitor"])}</p><table class="wv-table"><thead><tr><th>المجال</th><th>ما يسجل</th><th>الفائدة</th></tr></thead><tbody><tr><td>الشدة والمدة</td><td>درجة من صفر إلى عشرة وعدد الساعات.</td><td>تمييز اللحظة العابرة من النمط المتكرر.</td></tr><tr><td>النوم والطاقة</td><td>فرصة النوم والاستيقاظات والتعب أو قلة الحاجة للنوم.</td><td>كشف التغيرات التي تحتاج تقييمًا أسرع.</td></tr><tr><td>الجسد والمرحلة</td><td>ألم ونزف ودورة وحمل ورضاعة وهبات ساخنة ودواء.</td><td>ربط الأعراض بالسياق دون افتراض السببية.</td></tr><tr><td>الوظيفة والخطر</td><td>الرعاية والعمل والأكل والنظافة وأفكار الإيذاء والعنف.</td><td>تحديد مستوى الرعاية والأمان.</td></tr></tbody></table></section>
<section class="wv-section" id="plan"><h2>خطة عملية متدرجة</h2><p>{esc(ARTICLE_COMMON["plan"])}</p><div class="wv-grid">{steps}</div><h3>ما ينبغي تجنبه</h3><div class="wv-card wv-warn"><p>{esc(item.get("avoid", "استخدام الصفحة بدل التقييم المهني عند استمرار التعطل أو وجود خطر."))}</p><p>تجنبي أيضًا إيقاف دواء أو بدءه أو تغيير الجرعة من دون مقدم رعاية مؤهل، واستخدام اختبار أو تجربة شخص آخر كدليل نهائي على التشخيص.</p></div></section>
<section class="wv-section" id="communication"><h2>عبارات تساعد على طلب الدعم</h2>{phrases}<p class="wv-quote">«أحتاج أن تشرح لي الخيارات والفوائد والمخاطر بلغة واضحة، ثم نختار خطة يمكن متابعتها.»</p><p class="wv-quote">«الأعراض تؤثر في هذه الوظائف تحديدًا، وأريد خطة وموعد مراجعة لا طمأنة عامة فقط.»</p><p>للأسرة: اسألوا عن المساعدة العملية التي تخفف اليوم بدل إعطاء محاضرة أو مقارنة تجربتها بغيرها. احترموا رفضها للحديث في لحظة معينة، مع عدم تجاهل الخطر المباشر.</p></section>
<section class="wv-section" id="appointment"><h2>أسئلة للموعد المهني</h2><ul>{questions}</ul><p>اطلبي خطة قابلة للقياس: ما الهدف؟ ما البدائل؟ ما العلامات التي تستدعي اتصالًا مبكرًا؟ متى المراجعة؟ ومن تتصلين به خارج أوقات الدوام؟ إذا كان الوصول محدودًا، اسألي عن الرعاية الأولية أو الخدمات عن بعد أو الجمعيات الموثوقة أو خيارات التكلفة الأقل.</p></section>
<section class="wv-section" id="inclusion"><h2>تكييف الدعم والدمج</h2><p>{esc(ARTICLE_COMMON["inclusion"])}</p><p>تراعى اللغة والثقافة والوضع الاقتصادي والهجرة والمسؤوليات الأسرية والخصوصية الرقمية. الهدف إزالة الحواجز لا مطالبة المرأة بالتكيف وحدها مع خدمة غير ميسرة.</p></section>
<section class="wv-section" id="safety"><h2>متى تصبح الاستجابة عاجلة؟</h2><div class="wv-card wv-danger"><p>{esc(ARTICLE_COMMON["safety"])}</p><p><strong>الإجراء:</strong> لا تبقي وحدك، واطلبي الطوارئ المحلية أو توجهي إلى أقرب قسم طوارئ. أبعدي الوسائل الخطرة إن أمكن بأمان، ولا تدخلي في مواجهة تزيد خطر العنف.</p></div></section>
<section class="wv-section" id="sources"><h2>المصادر والمنهجية</h2><p>اعتمد الدليل على مبادئ من جهات صحية ومهنية رسمية، ثم صيغ عربيًا للتوعية العامة. لا يمثل ترجمة حرفية أو اعتمادًا من الجهات المذكورة، وتكيف الرعاية مع القوانين والخدمات المحلية والتاريخ الصحي الفردي.</p><ol>{source_list(8)}</ol><p class="wv-meta">الإصدار {VERSION} — مراجعة بنيوية ومصدرية: {REVIEWED_AT}.</p></section>
</article><aside class="wv-card wv-aside" aria-label="فهرس الدليل"><h2>في هذا الدليل</h2>{aside}<hr><a href="{BASE_PATH}/sectors/women/">العودة إلى مركز المرأة</a></aside></div></main>'''


def hub_schema(data: dict[str, Any]) -> str:
    items = [{"@type": "ListItem", "position": index, "url": f"{BASE}/sectors/women/{item['slug']}/", "name": item["title"]} for index, item in enumerate(data["articles"], 1)]
    payload = {"@context": "https://schema.org", "@graph": [{"@type": "CollectionPage", "url": f"{BASE}/sectors/women/", "name": "الصحة النفسية للمرأة عبر مراحل الحياة", "inLanguage": "ar", "dateModified": REVIEWED_AT}, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE}/"}, {"@type": "ListItem", "position": 2, "name": "الصحة النفسية للمرأة", "item": f"{BASE}/sectors/women/"}]}, {"@type": "ItemList", "numberOfItems": len(items), "itemListElement": items}, {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": question, "acceptedAnswer": {"@type": "Answer", "text": answer}} for question, answer in FAQS]}]}
    return json_schema(payload, 'data-women-hub-schema-v244="1"')


def article_schema(item: dict[str, Any]) -> str:
    slug = item["slug"]
    payload = {"@context": "https://schema.org", "@graph": [{"@type": "Article", "headline": item["title"], "description": item["summary"], "url": f"{BASE}/sectors/women/{slug}/", "inLanguage": "ar", "dateModified": REVIEWED_AT, "author": {"@type": "Organization", "name": "منصة مصطلحات علم النفس"}}, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE}/"}, {"@type": "ListItem", "position": 2, "name": "الصحة النفسية للمرأة", "item": f"{BASE}/sectors/women/"}, {"@type": "ListItem", "position": 3, "name": item["title"], "item": f"{BASE}/sectors/women/{slug}/"}]}]}
    return json_schema(payload, f'data-women-article-schema-v244="{esc(slug)}"')


def validate_source(data: dict[str, Any]) -> list[dict[str, Any]]:
    articles = data.get("articles")
    if not isinstance(articles, list) or len(articles) != 20:
        raise ValueError(f"women_source_requires_20_articles:{len(articles) if isinstance(articles, list) else 'invalid'}")
    slugs: list[str] = []
    for item in articles:
        if not isinstance(item, dict):
            raise ValueError("women_article_not_object")
        missing = [key for key in ("slug", "title", "summary", "signals", "steps", "phrases", "avoid") if key not in item]
        if missing:
            raise ValueError(f"women_article_missing_fields:{missing}")
        slug = str(item["slug"])
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"invalid_women_slug:{slug}")
        slugs.append(slug)
    if len(slugs) != len(set(slugs)):
        raise ValueError("duplicate_women_slugs")
    return articles


def update_robots(site: Path) -> bool:
    path = site / "robots.txt"
    current = path.read_text(encoding="utf-8") if path.is_file() else "User-agent: *\nAllow: /\n"
    if re.search(r"(?im)^\s*Disallow:\s*/sectors/women/?\s*$", current):
        raise ValueError("robots_disallows_women_sector")
    if "# women-sector-v244" in current:
        return False
    block = "\n# women-sector-v244\nAllow: /sectors/women/\nSitemap: https://healthrenewal.org/sitemap.xml\n"
    path.write_text(current.rstrip() + block, encoding="utf-8")
    return True


def upgrade(site: Path, source_file: Path = DEFAULT_SOURCE) -> dict[str, Any]:
    site = Path(site)
    source_file = Path(source_file)
    if not site.is_dir():
        raise ValueError(f"site_missing:{site}")
    data = json.loads(source_file.read_text(encoding="utf-8"))
    articles = validate_source(data)
    hub_path = site / "sectors" / "women" / "index.html"
    if not hub_path.is_file():
        raise ValueError(f"women_hub_missing:{hub_path}")
    hub = normalize_head(hub_path.read_text(encoding="utf-8"), title="الصحة النفسية للمرأة عبر مراحل الحياة | دليل عربي مؤسسي", description="مركز عربي شامل للصحة النفسية للمرأة: الحمل وما بعد الولادة، الدورة، انقطاع الطمث، العمل والرعاية، الاختلاف العصبي، العنف والسلامة وطلب المساعدة.", canonical=f"{BASE}/sectors/women/", keywords="الصحة النفسية للمرأة, اكتئاب ما بعد الولادة, القلق أثناء الحمل, الاضطراب المزعج السابق للحيض, انقطاع الطمث والصحة النفسية, العنف ضد المرأة, الاحتراق النفسي", article=False)
    hub = replace_mains(hub, hub_main(data))
    hub = add_before_head(hub, hub_schema(data))
    hub_path.write_text(hub, encoding="utf-8")

    enriched = 0
    words: dict[str, int] = {}
    for item in articles:
        slug = str(item["slug"])
        path = site / "sectors" / "women" / slug / "index.html"
        if not path.is_file():
            raise ValueError(f"women_article_missing:{slug}")
        source = path.read_text(encoding="utf-8")
        already = f'{ARTICLE_MARKER}="{slug}"' in source
        source = normalize_head(source, title=f"{item['title']} | الصحة النفسية للمرأة", description=f"{item['summary']} دليل عملي للمؤشرات والملاحظة والاستعداد للموعد والدعم وحدود السلامة دون تشخيص ذاتي.", canonical=f"{BASE}/sectors/women/{slug}/", keywords=f"{item['title']}, الصحة النفسية للمرأة, صحة المرأة, الدعم النفسي, طلب المساعدة, التوعية النفسية", article=True)
        source = replace_mains(source, article_main(item))
        source = add_before_head(source, article_schema(item))
        path.write_text(source, encoding="utf-8")
        enriched += 0 if already else 1
        words[slug] = visible_words(source)

    robots_updated = update_robots(site)
    combined = hub + "\n" + "\n".join((site / "sectors" / "women" / str(item["slug"]) / "index.html").read_text(encoding="utf-8") for item in articles)
    report = {"version": VERSION, "status": "passed", "source_articles": len(articles), "article_pages_enriched": enriched, "hub_words": visible_words(hub), "minimum_article_words": min(words.values()), "maximum_article_words": max(words.values()), "hub_h1": len(re.findall(r"<h1\b", hub, flags=re.I)), "hub_h2": len(re.findall(r"<h2\b", hub, flags=re.I)), "faq_items": len(FAQS), "institutional_sources": len(SOURCES), "robots_updated": robots_updated, "banned_term_present": "معاقين" in combined, "diagnostic_claim_present": any(term in combined for term in ("هذا يعني أنك مصابة", "يؤكد التشخيص", "العلاج مضمون")), "reviewed_at": REVIEWED_AT, "article_words": words}
    if report["hub_h1"] != 1 or report["hub_words"] < 2200 or report["minimum_article_words"] < 700 or report["banned_term_present"] or report["diagnostic_claim_present"]:
        raise ValueError({"women_sector_v244_contract_failed": report})
    if hub.lower().count('rel="canonical"') != 1 or "noindex" in hub.lower():
        raise ValueError("women_hub_indexability_contract")
    for item in articles:
        source = (site / "sectors" / "women" / str(item["slug"]) / "index.html").read_text(encoding="utf-8")
        if len(re.findall(r"<h1\b", source, flags=re.I)) != 1 or source.lower().count('rel="canonical"') != 1 or "noindex" in source.lower():
            raise ValueError(f"women_article_indexability_contract:{item['slug']}")
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade the institutional women mental-health sector")
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    upgrade(args.site, args.source)


if __name__ == "__main__":
    main()
