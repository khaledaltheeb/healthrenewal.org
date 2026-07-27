from __future__ import annotations
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"content"/"v326"/"learning-paths"/"index.json"
REQUIRED_EXISTING_SLUGS={"stress-basics-7-days","family-listening-5-days","grief-support-7-days","caregiver-boundaries-7-days"}
TOOL_MAP={
"foundations":["weekly-function-review","thought-distance-card"],
"stress-regulation":["three-minute-grounding","thought-distance-card","weekly-function-review"],
"anxiety-trauma":["three-minute-grounding","thought-distance-card","weekly-function-review"],
"mood-adjustment":["weekly-function-review","sleep-wind-down-plan","grief-day-plan"],
"sleep-executive":["sleep-wind-down-plan","weekly-function-review"],
"child-family":["child-listening-prompt","caregiver-capacity-check"],
"neurodevelopment":["caregiver-capacity-check","child-listening-prompt","weekly-function-review"],
"caregiving-practice":["caregiver-capacity-check","weekly-function-review","separation-boundary-script"],
"inclusion-independence":["weekly-function-review","caregiver-capacity-check"],
"quality-research":["weekly-function-review"]}
LENSES=[
("الأساس المفاهيمي","تعريف المفهوم وحدوده وما لا يعنيه"),
("الملاحظة والسياق","رصد النمط في مواقف حقيقية مع الفصل بين الوقائع والتفسير"),
("العوامل والدائرة","فهم ما يزيد الصعوبة أو يحافظ عليها وما يمكن تعديله"),
("التطبيق العملي","تحويل الفهم إلى خطوة صغيرة آمنة وقابلة للمراجعة"),
("المراجعة والسلامة","تقييم الأثر وتحديد الحدود ومتى يلزم دعم إضافي")]

def module(title,focus,i):
    lens,desc=LENSES[i]
    return {"position":i+1,"title":focus,"lens":lens,
    "objective":f"أن يشرح المتعلم {focus} ويطبقه على مثال واقعي مرتبط بموضوع «{title}».",
    "explanation":f"تتناول هذه الوحدة {focus}. تُقرأ الفكرة داخل سياق الشخص وعمره وبيئته ووظيفته اليومية، ولا تُستخدم منفردة لإصدار تشخيص أو حكم. يركز جانب «{desc}» على الانتقال من الانطباع العام إلى وصف يمكن مراجعته ومناقشته مع الشخص أو الأسرة أو الفريق.",
    "key_points":[f"ابدأ بوصف ما يمكن ملاحظته في موضوع {focus} قبل تفسير السبب.","قارن التغير بخط الأساس والسياق والمدة والأثر، لا بمثال واحد أو صورة نمطية.","اختر أقل خطوة داعمة تحقق الفائدة وتحافظ على الكرامة والاختيار والسلامة."],
    "application":f"طبّق الوحدة على موقف واحد: اكتب ملاحظة مرتبطة بـ«{focus}»، ثم اذكر تفسيرين محتملين، والعامل الذي يحتاج تحققًا، وخطوة دعم واحدة، ومؤشرًا ستراجعه بعد التنفيذ.",
    "knowledge_check":[f"ما الفرق بين وصف «{focus}» وبين تفسير سببه؟","ما المعلومة الناقصة التي قد تغيّر قرارك أو نوع الدعم؟"]}

def inflate(spec,i):
    modules=[module(spec["title"],focus,n) for n,focus in enumerate(spec["focuses"])]
    return {"id":f"LP-{i:03d}","slug":spec["slug"],"title":spec["title"],"category":spec["category"],
    "audience":spec["audience"],"level":spec.get("level","تمهيدي"),"duration":spec.get("duration","5 وحدات · 45–75 دقيقة"),
    "summary":spec["goal"],"goal":spec["goal"],
    "outcomes":[f"يشرح المفاهيم المركزية في «{spec['title']}» بلغة دقيقة وغير وصمية.","يميز بين الملاحظة والتفسير ومؤشرات الخطر التي تستدعي تقييمًا مهنيًا.","يبني خطوة تطبيق أو دعم قابلة للتنفيذ والمراجعة دون ادعاء تشخيص أو علاج."],
    "modules":modules,"days":[m["title"] for m in modules],
    "checklist":["حددت الهدف والفئة والسياق قبل تطبيق أي خطوة.","فصلت الوقائع الملاحظة عن الافتراضات والتشخيصات.","راعيت تفضيلات الشخص وقدرته ووسيلة تواصله.","اخترت خطوة صغيرة ومؤشر متابعة وموعد مراجعة.","عرفت متى أتوقف وأطلب دعمًا مهنيًا أو عاجلًا."],
    "related_tools":TOOL_MAP[spec["category"]],"source_ids":spec["source_ids"],
    "safety":spec.get("safety","المسار تثقيفي ولا يقدم تشخيصًا أو خطة علاج فردية. عند وجود خطر مباشر أو تدهور شديد أو تعطل مستمر اطلب تقييمًا مهنيًا مناسبًا."),
    "seek_help":"اطلب مساعدة عاجلة محلية عند وجود خطر مباشر على النفس أو الآخرين، واطلب تقييمًا مهنيًا عند استمرار الصعوبة أو تأثيرها الواضح في الأداء اليومي.",
    "faq":[{"question":f"هل يكفي هذا المسار لتشخيص مشكلة مرتبطة بـ«{spec['title']}»؟","answer":"لا. المسار للتثقيف وتنظيم الفهم والتطبيق الأولي، ولا يستبدل تقييمًا فرديًا لدى مختص مؤهل."},{"question":"كيف أستخدم المسار دون تحويله إلى وصفة جامدة؟","answer":"ابدأ بالسياق والهدف وتفضيلات الشخص، وطبّق خطوة صغيرة، ثم راجع الأثر وعدّلها بدل افتراض ملاءمتها للجميع."},{"question":"متى أتوقف عن التعلم الذاتي وأطلب مساعدة؟","answer":"عند وجود خطر مباشر، أو تدهور شديد، أو تعطل مستمر في النوم أو الدراسة أو العمل أو العلاقات أو العناية الذاتية."}],
    "reviewed":"2026-07-28","review_cycle_months":12}

def load_catalog()->dict[str,Any]:
    manifest=json.loads(CATALOG.read_text(encoding="utf-8"));specs=[]
    for category in manifest["categories"]:
        filename=manifest["category_files"][category["id"]]
        data=json.loads((CATALOG.parent/filename).read_text(encoding="utf-8"))
        if data.get("category")!=category["id"]: raise SystemExit(f"Category mismatch in {filename}")
        for spec in data["specs"]:
            spec.setdefault("category",category["id"])
            specs.append(spec)
    manifest["paths"]=[inflate(spec,i) for i,spec in enumerate(specs,1)]
    return manifest
