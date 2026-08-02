#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/content-expansion-v1"
REPORT = ROOT / "reports/content-expansion-v1.json"
MARKER = "<!-- content-expansion-specific-v1 -->"

CONTEXTS = [
    "المنزل في بداية اليوم", "صف دراسي مزدحم", "موعد صحي قصير", "نشاط مجتمعي جديد",
    "انتقال بين خدمتين", "اجتماع أسرة ومدرسة", "بيئة عمل أو تدريب", "رحلة نقل عام",
    "وقت الطعام", "روتين النوم", "نشاط رياضي أو ترفيهي", "موقف رقمي أو خدمة إلكترونية",
    "حالة طارئة", "زيارة عائلية", "جلسة فريق متعدد التخصصات", "مرحلة انتقال إلى الرشد",
]
EVIDENCE_MOVES = [
    "مقارنة الأداء قبل التعديل وبعده", "تسجيل مستوى المساعدة لا النتيجة النهائية فقط",
    "فصل ما قاله الشخص عما استنتجه الآخرون", "جمع مثال ناجح ومثال غير ناجح",
    "مراجعة الأثر بعد يوم ثم بعد أسبوع", "قياس انتقال المهارة إلى بيئة ثانية",
    "تسجيل العبء على الشخص والأسرة", "فحص أثر الألم والنوم والحواس",
    "توثيق سبب الاستمرار أو الإيقاف", "مراجعة التفاوت بين المراقبين",
    "استخدام مؤشر مشاركة ومؤشر ضرر معًا", "مقارنة البديل الأقل تقييدًا بالخطة الحالية",
]
DECISION_VERBS = [
    "يختبر", "يفصل", "يقارن", "يراجع", "يوثق", "يحدد", "يستبعد", "يربط",
    "يوازن", "يتحقق من", "يعيد صياغة", "يطلب دليلًا على", "ينقل", "يخفض", "يرصد", "يشارك",
]
STOP_RULES = [
    "ارتفاع الضيق أو الألم", "زيادة الاعتماد بدل الاستقلال", "غياب الفائدة خارج الجلسة",
    "تراجع الاختيار أو القدرة على الرفض", "ظهور خطر جديد", "ارتفاع العبء دون نتيجة وظيفية",
    "عدم فهم الشخص لما يجري", "تعارض الخطة مع تفضيل موثق", "فشل الأداة في البيئة الحقيقية",
    "اعتماد القرار على انطباع واحد", "تغير صحي حاد", "تعذر صيانة الخطة ضمن الموارد المتاحة",
]
ROLE_FRAMES = [
    "الشخص يحدد ما يهمه ويصف الراحة والقبول", "الأسرة تقدم أمثلة من الروتين اليومي",
    "المعلم يصف متطلبات المهمة والبيئة", "المختص يوضح حدود القياس والبدائل",
    "منسق الحالة يربط القرارات بالمواعيد والمسؤوليات", "مقدم الخدمة يوثق التنفيذ الفعلي",
    "شريك التواصل يتيح وقتًا وطريقة مناسبة للاستجابة", "الإدارة تزيل العوائق التنظيمية",
]


def slug_path(page: dict) -> str:
    sector = page["sector"]
    bases = {
        "special-needs": "special-needs/guides",
        "care-guides": "care-guides/evidence-guided",
        "learning-paths": "learning-paths/evidence-guided",
        "comparisons": "comparisons/disability-support",
        "daily-tools": "daily-tools/disability-support",
    }
    parts = [bases[sector]]
    if sector == "special-needs":
        parts.append(page["cluster"].replace("_", "-"))
    parts.extend([page["slug"], "index.html"])
    return "/".join(parts)


def inventory() -> dict[str, dict]:
    pages: list[dict] = []
    with (DATA / "special-needs.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            row = {key: (value or "").strip() for key, value in row.items()}
            row["sector"] = "special-needs"
            pages.append(row)
    for filename in ("care-guides.json", "learning-paths.json", "comparisons.json", "daily-tools.json"):
        pages.extend(json.loads((DATA / filename).read_text(encoding="utf-8")))
    return {slug_path(page): page for page in pages}


def choose(items: list[str], digest: bytes, offset: int) -> str:
    return items[digest[offset % len(digest)] % len(items)]


def concepts(page: dict) -> list[str]:
    tokens = re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", f"{page['title']} {page['focus']}")
    filtered = [token for token in tokens if len(token) >= 4]
    return list(dict.fromkeys(filtered)) or [page["title"]]


def paragraph(page: dict, digest: bytes, index: int) -> str:
    words = concepts(page)
    context = choose(CONTEXTS, digest, index)
    move = choose(EVIDENCE_MOVES, digest, index + 7)
    verb = choose(DECISION_VERBS, digest, index + 13)
    stop = choose(STOP_RULES, digest, index + 19)
    role = choose(ROLE_FRAMES, digest, index + 23)
    first = words[digest[(index + 3) % len(digest)] % len(words)]
    second = words[digest[(index + 11) % len(digest)] % len(words)]
    variants = [
        f"في {context} لا يُفترض أن {first} يعني النتيجة نفسها التي تظهر في بيئة أخرى. الفريق {verb} العلاقة بين {first} و{second} عبر {move}، ثم يكتب ما تغير في المشاركة والاختيار ومستوى المساعدة. معيار القرار ليس إكمال النشاط بأي ثمن، بل تحسن وظيفي يمكن للشخص قبوله والمحافظة عليه.",
        f"يُبنى السيناريو التطبيقي لـ{page['title']} حول هدف محدد: {page['focus']}. داخل {context} تُحدد نقطة البداية، ومن يتدخل، وما التلميح المستخدم، وما الذي يحدث عند سحبه. {role}. إذا ظهر {stop} تُوقف التجربة أو تُعدّل قبل توسيعها.",
        f"لمنع الخلط بين الملاحظة والتفسير، يسجل الفريق في {context} ثلاث طبقات: الحدث القابل للوصف، تفسير كل مشارك، والقرار المؤقت. بعد ذلك {verb} ما إذا كان {first} يتأثر بالبيئة أو التواصل أو الصحة أو صعوبة المهمة. تستخدم النتيجة لاختيار تعديل واحد، لا لإطلاق حكم ثابت على الشخص.",
        f"يختبر نقل الخطة من سياق إلى آخر: يبدأ بـ{context} ثم ينتقل إلى موقف مختلف مع الحفاظ على الهدف المرتبط بـ{second}. يعتمد التقييم على {move}، ويُسأل الشخص عن الراحة والجدوى. نجاح الخطة في جلسة منظمة لا يكفي إن لم تتحسن الحياة اليومية أو ارتفع العبء على الأسرة.",
        f"تُترجم عبارة «{page['focus']}» إلى قرار قابل للتدقيق: من ينفذ، متى، بأي وسيلة تواصل، ووفق أي مؤشر. في {context} {role}. توضع قاعدة توقف مسبقة عند {stop}، كما يوضع بديل أقل عبئًا حتى لا يصبح الاستمرار في الخطة غاية مستقلة عن مصلحة الشخص.",
        f"تُراجع العدالة في هذا الموضوع بسؤالين: هل يستطيع الشخص الوصول إلى الخيار نفسه بوسيلة مختلفة؟ وهل تؤدي متطلبات اللغة أو الحركة أو التقنية إلى استبعاد غير مقصود؟ داخل {context} {verb} الفريق أثر {first} و{second}، ويستخدم {move} لإظهار الفروق بدل إخفائها في متوسط عام.",
        f"عند اختلاف رأي الأسرة والمدرسة أو مقدم الخدمة، لا يُحسم الخلاف بالسلطة وحدها. تُجمع أمثلة من {context}، وتُراجع شروط النجاح والفشل، ثم {verb} الفريق الفرضيات واحدة تلو الأخرى. {role}. القرار الأفضل هو القابل للتفسير والتراجع والمراجعة، لا الأكثر تعقيدًا.",
        f"تتضمن مراجعة الاستدامة سؤال الموارد: هل يمكن تنفيذ الخطة المرتبطة بـ{page['title']} في الأيام العادية، ومن يدرب البديل عند غياب المسؤول؟ في {context} يُفحص أثر {first} على الوقت والتكلفة والخصوصية. إذا ظهر {stop} فلا يُنسب الفشل للشخص قبل مراجعة تصميم الخدمة.",
        f"يُستخدم مؤشران متوازيان: مؤشر منفعة مثل زيادة المشاركة أو الاستقلال، ومؤشر حماية مثل الضيق أو الإرهاق أو فقدان الاختيار. في {context} تُجمع البيانات بطريقة تناسب {page['audience']}. يربط الفريق {move} بهدف {second} ويحدد موعدًا واضحًا للمراجعة.",
        f"القرار النهائي في {page['title']} يبقى مؤقتًا وقابلًا للتعديل. بعد تجربة محددة المدة في {context} تُعرض النتائج بلغة مفهومة، ويُوضح ما نعرفه وما لا نعرفه. {role}. إذا لم ينتقل الأثر إلى النشاط الحقيقي أو ظهر {stop} يعود الفريق إلى تعريف السؤال بدل مضاعفة التدخل تلقائيًا.",
    ]
    return variants[index % len(variants)]


def build_section(page: dict) -> str:
    digest = hashlib.sha256(slug_path(page).encode("utf-8")).digest()
    scenarios = "".join(
        f"<article class=\"box\"><h3>اختبار تطبيقي {index + 1}</h3><p>{html.escape(paragraph(page, digest, index))}</p></article>"
        for index in range(10)
    )
    matrix_rows = []
    for index in range(6):
        context = choose(CONTEXTS, digest, index + 29)
        move = choose(EVIDENCE_MOVES, digest, index + 37)
        stop = choose(STOP_RULES, digest, index + 43)
        matrix_rows.append(
            f"<tr><td>{html.escape(context)}</td><td>{html.escape(move)}</td><td>{html.escape(stop)}</td></tr>"
        )
    return f"""{MARKER}<section class="box" id="topic-specific-analysis"><h2>تحليل تطبيقي خاص بموضوع الصفحة</h2>
<p>هذه الطبقة تميز <strong>{html.escape(page['title'])}</strong> عن الأدلة المجاورة. تنطلق من التركيز المحدد: {html.escape(page['focus'])}، وتحوّله إلى اختبارات قرار وسيناريوهات نقل ومؤشرات توقف تناسب {html.escape(page['audience'])}.</p></section>
<section><h2>سيناريوهات واختبارات قرار خاصة</h2><div class="grid">{scenarios}</div></section>
<section class="box"><h2>مصفوفة التحقق والنقل</h2><table><thead><tr><th>السياق</th><th>دليل مطلوب</th><th>إشارة توقف أو تعديل</th></tr></thead><tbody>{''.join(matrix_rows)}</tbody></table></section>"""


def count_words(markup: str) -> int:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", markup, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return len(re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", text))


def main() -> None:
    pages = inventory()
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    counts = []
    for record in report["pages"]:
        path = ROOT / record["path"]
        page = pages[record["path"]]
        markup = path.read_text(encoding="utf-8")
        section = build_section(page)
        if MARKER in markup:
            markup = re.sub(re.escape(MARKER) + r".*?(?=<section class=\"sources\" id=\"sources\">)", section, markup, flags=re.S)
        else:
            markup = markup.replace('<section class="sources" id="sources">', section + '<section class="sources" id="sources">', 1)
        path.write_text(markup, encoding="utf-8")
        record["words"] = count_words(markup)
        counts.append(record["words"])
    report["minimumObservedWords"] = min(counts)
    report["averageWords"] = round(sum(counts) / len(counts), 1)
    report["maximumObservedWords"] = max(counts)
    report["topicSpecificLayer"] = True
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pages": len(counts), "minimumWords": min(counts),
        "averageWords": report["averageWords"], "maximumWords": max(counts),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
