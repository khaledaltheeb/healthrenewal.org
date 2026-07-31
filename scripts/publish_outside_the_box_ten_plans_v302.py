#!/usr/bin/env python3
"""Publish ten evidence-bounded operational plans for each outside-the-box condition.

The extension is deliberately generated after v254. It does not diagnose, prescribe,
or claim external clinical accreditation. It expands every condition page with ten
distinct decision/support plans and emits a machine-auditable API contract.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
FRAMEWORK_PATH = ROOT / "content" / "v302" / "outside-the-box-ten-plan-framework-ar.json"
CSS_PATH = ROOT / "assets" / "css" / "outside-the-box-ten-plans-v302.css"

BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
SECTION = "outside-the-box"
VERSION = 302
UPDATED = "2026-07-27"
PLAN_COUNT = 10
MARKER_START = "<!-- outside-the-box-ten-plans-v302:start -->"
MARKER_END = "<!-- outside-the-box-ten-plans-v302:end -->"
HUB_START = "<!-- outside-the-box-ten-plans-v302-hub:start -->"
HUB_END = "<!-- outside-the-box-ten-plans-v302-hub:end -->"
STYLE_MARKER = "<!-- outside-the-box-ten-plans-v302:style -->"
METHODOLOGY_SLUG = "ten-plan-methodology"


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def ul(items: Iterable[str], class_name: str = "") -> str:
    cls = f' class="{e(class_name)}"' if class_name else ""
    return f"<ul{cls}>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"


def ol(items: Iterable[str]) -> str:
    return "<ol>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ol>"


def load_sources() -> tuple[dict[str, Any], dict[str, Any]]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    framework = json.loads(FRAMEWORK_PATH.read_text(encoding="utf-8"))
    if framework.get("version") != VERSION:
        raise ValueError("Ten-plan framework version must be 302")
    conditions = data.get("conditions", [])
    if len(conditions) != 100:
        raise ValueError(f"Ten-plan publisher requires exactly 100 conditions, found {len(conditions)}")
    if len(framework.get("plan_families", [])) != PLAN_COUNT:
        raise ValueError("Ten-plan framework must define exactly ten plan families")
    orders = [item.get("order") for item in framework["plan_families"]]
    if orders != list(range(1, PLAN_COUNT + 1)):
        raise ValueError("Plan family order must be contiguous from 1 through 10")
    if len({item["id"] for item in framework["plan_families"]}) != PLAN_COUNT:
        raise ValueError("Plan family IDs must be unique")
    return data, framework


def valid_source_keys(data: dict[str, Any], keys: Iterable[str]) -> list[str]:
    valid = [key for key in dedupe(keys) if key in data["sources"]]
    return valid


def condition_sources(data: dict[str, Any], condition: dict[str, Any]) -> list[str]:
    cluster = data["clusters"][condition["cluster"]]
    keys = [*condition["source_keys"], *cluster["source_keys"]]
    for protocol_key in condition["protocol_keys"]:
        keys.extend(data["protocols"][protocol_key]["source_keys"])
    return valid_source_keys(data, keys)


def with_fallback_sources(
    data: dict[str, Any], condition: dict[str, Any], preferred: Iterable[str]
) -> list[str]:
    keys = valid_source_keys(data, [*preferred, *condition_sources(data, condition)])
    if len(keys) < 2:
        raise ValueError(f"Condition {condition['slug']} has fewer than two usable sources")
    return keys[:8]


def common_review_timing() -> list[str]:
    return [
        "الأسبوع 0: تثبيت الهدف وخط الأساس والموافقة وخطة السلامة.",
        "الأسبوع 2: فحص قابلية التنفيذ والقبول والعبء وأي أثر غير مرغوب.",
        "الأسبوع 6: قراءة الاتجاه مع جودة التنفيذ وتحديد الاستمرار أو التعديل.",
        "الأسبوع 12: فحص الفائدة الوظيفية والتعميم عبر سياق أو شريك ثانٍ.",
        "الأسبوع 24: قرار صيانة أو خفض دعم أو انتقال أو إحالة وإعادة تقييم.",
    ]


def universal_fidelity() -> list[str]:
    return [
        "توثيق من نفذ الخطة ومتى وكم مرة وما التغيير الوحيد الذي حدث.",
        "فحص جودة التنفيذ بعينة مباشرة أو قائمة تحقق قصيرة، لا بالانطباع.",
        "تسجيل الرفض أو الضيق أو الأثر غير المرغوب بوصفه نتيجة أساسية.",
    ]


def common_adaptations(condition: dict[str, Any], cluster: dict[str, Any]) -> list[str]:
    return [
        "تكييف طريقة العرض والاستجابة وفق وسيلة التواصل والحس والحركة؛ لا تُخفض أولوية الهدف تلقائيًا.",
        f"اختيار مهمة ترتبط بمحور «{condition['focus'][0]}» وتحدث في حياة الشخص فعلًا.",
        f"مقارنة الأداء في سياقين مع توثيق الحواجز والتيسيرات في مجال {cluster['title']}.",
    ]


def make_plan(
    *,
    plan_id: str,
    order: int,
    title: str,
    kind: str,
    goal: str,
    when_to_use: list[str],
    do_not_use: list[str],
    prerequisites: list[str],
    baseline: list[str],
    steps: list[str],
    dose: str,
    outcomes: list[str],
    fidelity: list[str],
    adaptations: list[str],
    team: list[str],
    stop_rule: str,
    evidence_relation: str,
    source_keys: list[str],
    review_timing: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": plan_id,
        "order": order,
        "title": title,
        "kind": kind,
        "goal": goal,
        "when_to_use": when_to_use,
        "do_not_use": do_not_use,
        "prerequisites": prerequisites,
        "baseline": baseline,
        "steps": steps,
        "dose": dose,
        "outcomes": outcomes,
        "fidelity": fidelity,
        "adaptations": adaptations,
        "team": team,
        "stop_rule": stop_rule,
        "evidence_relation": evidence_relation,
        "source_keys": source_keys,
        "review_timing": review_timing or common_review_timing(),
        "review_status": "مراجعة منهجية داخلية؛ تخصيص ومراجعة مختص الحالة إلزاميان قبل التطبيق",
    }


def build_plans(data: dict[str, Any], framework: dict[str, Any], condition: dict[str, Any]) -> list[dict[str, Any]]:
    cluster = data["clusters"][condition["cluster"]]
    team = cluster["team"]
    focus = condition["focus"]
    baseline = cluster["baseline"]
    family = {item["id"]: item for item in framework["plan_families"]}
    plans: list[dict[str, Any]] = []

    plans.append(
        make_plan(
            plan_id="clarification-safety",
            order=1,
            title=f"خطة التحقق التشخيصي والسلامة — {condition['title_ar']}",
            kind=family["clarification-safety"]["kind"],
            goal=(
                "تحديد ما إذا كانت الحالة موثقة بتقييم مهني مناسب، وما الذي لا يزال فرضية، "
                "وما إذا كان الألم أو التغير الطبي أو حاجز الوصول أو الخطر يسبق أي تدخل."
            ),
            when_to_use=[
                "عند بدء الخدمة أو انتقال الشخص بين فرق أو مؤسسات.",
                "عندما تتعارض التقارير أو تظهر فجوة بين الدرجة والأداء اليومي.",
                "عند تغير مفاجئ في المهارة أو السلوك أو الوعي أو الحركة أو التواصل.",
            ],
            do_not_use=[
                "لا تستخدم الصفحة لإثبات التشخيص أو الأهلية.",
                "لا تؤخر الطوارئ أو الإحالة الطبية لجمع خط أساس إضافي.",
                "لا تفسر اختلاف اللغة أو الثقافة أو الوصول بوصفه اضطرابًا تلقائيًا.",
            ],
            prerequisites=[
                "موافقة الشخص أو وليه وفق النظام المحلي وإتاحة طريقة للفهم والرفض.",
                "جمع التقارير الأصلية وتواريخها وأسماء الأدوات والنسخ والمستخدمين.",
                "مسار واضح للتصعيد الطبي أو النفسي أو الوقائي عند ظهور خطر.",
            ],
            baseline=dedupe([*cluster["initial_assessment"][:3], *condition["assessment_extras"][:2]]),
            steps=[
                "اكتب سؤال الإحالة والقرار الذي سيترتب عليه بلغة تشغيلية.",
                "افصل بين التشخيص الموثق والاشتباه والوصف الوظيفي.",
                "راجع التاريخ الصحي والنمائي والتعليمي والدوائي والتواصلي.",
                "افحص العوامل المطلوب استبعادها قبل نسبة الأثر للحالة.",
                "اجمع معلومة من الشخص أو الأسرة وملاحظة في مهمة حقيقية وأداة مناسبة عند الحاجة.",
                "وثق مؤشرات التصعيد ومن المسؤول عن كل إحالة والمدة القصوى للانتظار.",
                "اختم المرحلة بملخص: ما نعرفه، ما لا نعرفه، وما القرار الآمن التالي.",
            ],
            dose="مرحلة دخول مركزة تمتد عادة من لقاء واحد إلى ثلاثة لقاءات، مع تصعيد فوري عند الخطر بدل الالتزام بجدول ثابت.",
            outcomes=[
                "وضوح حالة التشخيص ومصدره وحدوده.",
                "إغلاق أو إحالة العوامل الطبية والبيئية العاجلة.",
                "سؤال وظيفي واحد صالح لبناء الخطة التالية.",
            ],
            fidelity=universal_fidelity(),
            adaptations=common_adaptations(condition, cluster),
            team=team,
            stop_rule="أوقف مسار الخدمة المعتاد وفعّل الطوارئ أو الحماية أو الإحالة المتخصصة عند أي مؤشر عاجل من مؤشرات العائلة الوظيفية.",
            evidence_relation="خطة تحقق وسلامة قائمة على التقييم المتعدد المصادر وICF وحدود القياس؛ ليست أداة تشخيص جديدة.",
            source_keys=with_fallback_sources(data, condition, [*cluster["source_keys"], "who-icf", "nice-complex"]),
        )
    )

    plans.append(
        make_plan(
            plan_id="shared-functional-goal",
            order=2,
            title=f"خطة الهدف الوظيفي المشترك وخط الأساس — {condition['title_ar']}",
            kind=family["shared-functional-goal"]["kind"],
            goal=condition["outcome_goal"],
            when_to_use=[
                "بعد وضوح السلامة وسؤال الإحالة.",
                "عندما توجد أهداف عامة مثل «تحسين الحالة» ولا يمكن قياسها.",
                "عندما تختلف أولوية الشخص عن أولوية الأسرة أو المؤسسة.",
            ],
            do_not_use=[
                "لا تجعل الدرجة المعيارية وحدها هدفًا نهائيًا.",
                "لا تضع هدف امتثال أو إخفاء اختلاف لا يوسع حياة الشخص.",
                "لا تجمع أهدافًا متعددة في مؤشر واحد غامض.",
            ],
            prerequisites=[
                "طريقة تواصل تسمح للشخص بالمشاركة أو التعبير عن القبول والرفض.",
                "تحديد سياق وشريك ومهمة حقيقية.",
                "تعريف مستوى المساعدة والتلميحات الحالية.",
            ],
            baseline=dedupe([*baseline, f"قياس مباشر لمحور {focus[0]} في ثلاث فرص أو نقاط متكافئة على الأقل."]),
            steps=[
                "ابدأ بما يريد الشخص أن يصبح ممكنًا أو أقل عبئًا في حياته.",
                "حوّل الأولوية إلى سلوك أو أداء مرئي في سياق محدد.",
                "حدد المقام: عدد الفرص أو الزمن أو المهمة التي ستقاس.",
                "اجمع ثلاث إلى خمس نقاط خط أساس متكافئة متى كان ذلك آمنًا.",
                "اكتب مستويات هدف فردية من −2 إلى +2 قبل بدء التدخل.",
                "حدد حد العبء المقبول وقاعدة التوقف ومتى يعاد التفاوض على الهدف.",
                "احصل على اتفاق الفريق وحدد صاحب القرار ومسؤول جمع البيانات.",
            ],
            dose="جلسة تخطيط مشتركة ثم خط أساس متكرر خلال أسبوع إلى أسبوعين بحسب سرعة تغير المهارة وسلامة الانتظار.",
            outcomes=[
                "هدف يحدد السلوك والسياق والمساعدة والمؤشر والمدة.",
                "خط أساس يمكن مقارنته بقياسات لاحقة دون تغيير المهمة جذريًا.",
                "توثيق موقف الشخص والعبء المقبول والقرار المشترك.",
            ],
            fidelity=universal_fidelity(),
            adaptations=common_adaptations(condition, cluster),
            team=team,
            stop_rule="أعد صياغة الهدف إذا لم يعد ذا معنى للشخص، أو إذا احتاج تحقيقه إلى ضيق أو إكراه أو مخاطرة غير مقبولة.",
            evidence_relation="خطة أهداف فردية وقياس متكرر؛ تستخدم GAS وICF بحذر ولا تحول الهدف الفردي إلى معيار تشخيصي.",
            source_keys=with_fallback_sources(data, condition, ["who-icf", "gas", "wwc-scd", "scribe"]),
        )
    )

    plans.append(
        make_plan(
            plan_id="access-environment",
            order=3,
            title=f"خطة الإتاحة وإعادة تصميم البيئة والمهمة — {condition['title_ar']}",
            kind=family["access-environment"]["kind"],
            goal=(
                f"اختبار ما إذا كان تعديل حاجز واحد في البيئة أو طريقة المهمة يرفع {focus[0]} "
                f"أو {focus[1]} دون خفض التوقعات أو زيادة العبء."
            ),
            when_to_use=[
                "عندما يتغير الأداء بوضوح بين الأماكن أو الشركاء.",
                "عندما تتطلب المهمة طريقة استجابة لا تناسب التواصل أو الحس أو الحركة.",
                "قبل تفسير الأداء المنخفض بوصفه نقص قدرة ثابتًا.",
            ],
            do_not_use=[
                "لا تستخدم التكييف لعزل الشخص أو سحب فرص التعلم والمشاركة.",
                "لا تغير عدة عناصر في الوقت نفسه إذا كان الهدف تفسير الأثر.",
                "لا تعتبر الهدوء الظاهري نجاحًا إذا انخفضت المشاركة أو زاد الانسحاب.",
            ],
            prerequisites=[
                "ملاحظة المهمة في بيئتها الطبيعية.",
                "تحديد حاجز واحد قابل للتغيير وآمن وقابل للعكس.",
                "مؤشر أداء واحد ومؤشر عبء أو قبول.",
            ],
            baseline=dedupe([*baseline[:3], "أداء المهمة قبل التكييف وتحت شروط موثقة."]),
            steps=[
                "ارسم مسار المهمة وحدد نقطة التعطل والحاجز المحتمل.",
                "اسأل الشخص عن التيسيرات الناجحة والمزعجة إن أمكن.",
                "اختر تعديلًا واحدًا: عرض، وقت، ضوضاء، إضاءة، وضعية، أداة، أو طريقة استجابة.",
                "ثبت هدف المهمة وقارن الأداء قبل التعديل وبعده.",
                "قِس الاستقلال والدقة والزمن والمشاركة والعبء.",
                "احتفظ بالتعديل المفيد، وعدله أو أزله إذا لم يضف فائدة.",
                "وثق التعميم في سياق ثانٍ ومن المسؤول عن توفير التكييف.",
            ],
            dose="تجربة قابلة للعكس لمدة أسبوعين غالبًا، مع قياس في كل فرصة مهمة ومراجعة مبكرة إذا ظهر ضرر أو انسحاب.",
            outcomes=[
                "انخفاض حاجز موثق بدل زيادة تدريب غير ضروري.",
                "تحسن في النشاط أو المشاركة أو الاستقلال.",
                "قائمة تكييفات مفيدة وغير مفيدة قابلة للنقل بين البيئات.",
            ],
            fidelity=universal_fidelity(),
            adaptations=common_adaptations(condition, cluster),
            team=team,
            stop_rule="أوقف التكييف إذا حد من الحركة أو التعلم أو التواصل أو الاختيار، أو زاد التعب أو الألم أو الضيق.",
            evidence_relation="إطار إتاحة قائم على ICF والتصميم الشامل والتربية الدامجة؛ أثر التعديل يُختبر داخل الحالة.",
            source_keys=with_fallback_sources(data, condition, ["who-icf", "udl", "unicef-inclusive", "who-rehab"]),
        )
    )

    plans.append(
        make_plan(
            plan_id="communication-choice",
            order=4,
            title=f"خطة التواصل والاختيار وحق الرفض — {condition['title_ar']}",
            kind=family["communication-choice"]["kind"],
            goal="ضمان وسيلة مفهومة وموثوقة لطلب الاحتياجات والألم والمساعدة، وللتعبير عن الاختيار والرفض والتوقف.",
            when_to_use=[
                "عندما لا يستطيع الشخص إظهار موافقته أو رفضه بطريقة يفهمها الفريق.",
                "عندما يتغير السلوك مع صعوبة التعبير عن الألم أو الحمل الحسي أو المهمة.",
                "عند استخدام التواصل المعزز والبديل أو الإشارة أو وسائل وصول متعددة.",
            ],
            do_not_use=[
                "لا تشترط الكلام المنطوق للوصول إلى التعليم أو الاختيار.",
                "لا تسحب وسيلة AAC بحجة أنها تمنع الكلام.",
                "لا تفسر غياب الاستجابة السريعة على أنه غياب فهم أو قرار.",
            ],
            prerequisites=[
                "تقييم طريقة الوصول الحركي والحسي واللغوي عند الحاجة.",
                "اختيار مفردات وظيفية تشمل نعم/لا/توقف/ألم/مساعدة.",
                "تدريب شريكين على الانتظار والاستجابة وإصلاح الفشل التواصلي.",
            ],
            baseline=[
                "عدد الرسائل المستقلة من فرص محددة.",
                "نجاح نعم/لا أو الاختيار تحت أسئلة معروفة الإجابة.",
                "زمن الاستجابة وعدد محاولات الإصلاح.",
                "قدرة الشخص على طلب التوقف والألم والمساعدة.",
            ],
            steps=[
                "حدد وسيلة أو أكثر يستطيع الشخص الوصول إليها بثبات.",
                "اختبر نعم/لا والاختيار في مواقف منخفضة المخاطر.",
                "أضف مفردات الرفض والألم والمساعدة قبل مفردات الامتثال.",
                "درّب الشركاء على نمذجة الوسيلة والانتظار وعدم التخمين السريع.",
                "ادمج الوسيلة في روتينين طبيعيين بدل حصرها في جلسة.",
                "قِس المبادرة والفهم والإصلاح والقبول لا عدد الرموز وحده.",
                "راجع المطابقة التقنية واللغوية إذا ظل الاستخدام منخفضًا.",
            ],
            dose="فرص قصيرة متكررة يوميًا داخل الروتين، مع مراجعة أسبوعية لجودة استجابة الشركاء لمدة 6–8 أسابيع.",
            outcomes=[
                "طريقة موثوقة للرفض وطلب المساعدة.",
                "زيادة الرسائل الوظيفية المستقلة أو المدعومة.",
                "انخفاض فشل التواصل والاضطرار إلى التخمين.",
            ],
            fidelity=universal_fidelity(),
            adaptations=common_adaptations(condition, cluster),
            team=team,
            stop_rule="أوقف أي طريقة تواصل تسبب ألمًا أو فشل وصول متكررًا، ولا تستخدم مساعدة جسدية قسرية لإنتاج استجابة.",
            evidence_relation="خطة وصول تواصلي وقرار مدعوم؛ تحتاج تقييمًا متخصصًا عندما تكون الاحتياجات معقدة.",
            source_keys=with_fallback_sources(data, condition, ["asha", "who-icf", "dec", "aaidd"]),
        )
    )

    for direct_index, protocol_key in enumerate(condition["protocol_keys"], start=1):
        protocol = data["protocols"][protocol_key]
        order = direct_index + 4
        family_id = f"direct-protocol-{direct_index}"
        plan_focus = focus[direct_index - 1]
        plans.append(
            make_plan(
                plan_id=family_id,
                order=order,
                title=f"{family[family_id]['title']}: {protocol['title']}",
                kind=family[family_id]["kind"],
                goal=f"اختبار أثر «{protocol['title']}» على {plan_focus} ضمن هدف {condition['title_ar']} المحدد مسبقًا.",
                when_to_use=[
                    f"عندما يطابق تحليل الخطأ أو الحاجة محور «{plan_focus}».",
                    "بعد تثبيت خط أساس وسلامة وقبول وطريقة قياس.",
                    "عندما يستطيع الفريق تنفيذ الجرعة ومراقبة الجودة والآثار غير المرغوبة.",
                ],
                do_not_use=[
                    "لا يطبق لمجرد أن التشخيص موجود دون هدف وظيفي مطابق.",
                    "لا يخلط مع تغييرات متعددة غير معلنة ثم ينسب الأثر لهذا البروتوكول.",
                    "لا يستبدل العلاج الطبي أو النفسي أو التأهيلي المرخص عندما يكون مطلوبًا.",
                ],
                prerequisites=[
                    f"تعريف تشغيلي لمحور «{plan_focus}».",
                    "ثلاث نقاط خط أساس متكافئة متى كان ذلك آمنًا.",
                    "تدريب المنفذ وتوثيق الجرعة وجودة التنفيذ.",
                ],
                baseline=dedupe([*baseline[:3], f"مؤشر مباشر خاص بـ {plan_focus}."]),
                steps=list(protocol["steps"]),
                dose=protocol["dose"],
                outcomes=[
                    protocol["measure"],
                    f"تغير ذو معنى في {plan_focus} داخل مهمة حقيقية.",
                    "تعميم أو صيانة مع دعم أقل دون زيادة العبء.",
                ],
                fidelity=[
                    "قائمة تحقق تغطي كل خطوة أساسية في البروتوكول.",
                    "حساب الجرعة الفعلية لا الجرعة المخطط لها فقط.",
                    "تسجيل أي تدخل متزامن أو تغير دوائي أو بيئي يؤثر في التفسير.",
                ],
                adaptations=common_adaptations(condition, cluster),
                team=team,
                stop_rule=protocol["stop_rule"],
                evidence_relation=protocol["evidence_relation"],
                source_keys=with_fallback_sources(data, condition, [*protocol["source_keys"], *condition["source_keys"]]),
            )
        )

    plans.append(
        make_plan(
            plan_id="team-coaching-fidelity",
            order=8,
            title=f"خطة تدريب الأسرة والفريق وجودة التنفيذ — {condition['title_ar']}",
            kind=family["team-coaching-fidelity"]["kind"],
            goal="رفع اتساق تنفيذ الخطة وتقليل العبء ومنع اختلاف التعليمات والتلميحات بين الشركاء والبيئات.",
            when_to_use=[
                "عندما تختلف النتائج بوضوح حسب المنفذ.",
                "عندما تكون الخطة معقدة أو مرهقة أو كثيرة الخطوات.",
                "عند نقل المهارة من المختص إلى المنزل أو المدرسة أو المجتمع.",
            ],
            do_not_use=[
                "لا تحول الأسرة إلى معالج بدوام كامل.",
                "لا تقيم الالتزام دون قياس واقعي للوقت والموارد والضغط.",
                "لا تلوم الشخص أو الأسرة على فشل خطة غير قابلة للتنفيذ.",
            ],
            prerequisites=[
                "اختيار مهارة واحدة وروتين واحد للبدء.",
                "قائمة تحقق قصيرة قابلة للملاحظة.",
                "اتفاق على الحد الأقصى المقبول للوقت والعبء.",
            ],
            baseline=[
                "جودة التنفيذ الحالية لعينة واحدة على الأقل.",
                "ثقة المنفذ من 0 إلى 4.",
                "الوقت والعبء وعدد الخطوات التي تُنسى.",
                "نتيجة الشخص تحت منفذين أو سياقين.",
            ],
            steps=[
                "اشرح المنطق والهدف بلغة بسيطة مرتبطة بحياة الشخص.",
                "نمذج الخطة في الروتين الحقيقي.",
                "دع المنفذ يجرب بينما يلاحظ المدرب دون مقاطعة مفرطة.",
                "قدم تغذية راجعة محددة على خطوة أو خطوتين فقط.",
                "بسّط الخطة أو غير المواد إذا كان العبء مرتفعًا.",
                "أعد القياس حتى يصل التنفيذ إلى مستوى متفق عليه.",
                "خطط للتعميم مع الحفاظ على حق الشخص في الرفض والتوقف.",
            ],
            dose="تدريب أسبوعي قصير لمدة 4–8 أسابيع مع ممارسة موجزة داخل الروتين ومراجعة عبء الأسرة في كل لقاء.",
            outcomes=[
                "جودة تنفيذ مستقرة ومعلنة.",
                "انخفاض التباين بين المنفذين دون تحويل الخطة إلى طاعة.",
                "ثقة أعلى وعبء مقبول واستمرار النتيجة الوظيفية.",
            ],
            fidelity=universal_fidelity(),
            adaptations=common_adaptations(condition, cluster),
            team=team,
            stop_rule="خفف أو أوقف التدريب إذا زاد ضغط الأسرة أو عطّل العلاقة أو تجاوز نطاق الممارسة أو لم يعد الشخص موافقًا.",
            evidence_relation="خطة تنفيذ وتدريب ضمن الروتين؛ نجاحها يقاس بجودة التنفيذ ورفاه الأسرة ونتيجة الشخص معًا.",
            source_keys=with_fallback_sources(data, condition, ["who-cst", "dec", "wwc-scd", "gas"]),
        )
    )

    plans.append(
        make_plan(
            plan_id="participation-strengths",
            order=9,
            title=f"خطة المشاركة واكتشاف القدرات والفرص — {condition['title_ar']}",
            kind=family["participation-strengths"]["kind"],
            goal=(
                "اكتشاف اهتمام أو قدرة فردية قابلة للتطوير في نشاط واقعي، ثم إزالة الحواجز أمام "
                "المشاركة في التعليم أو الرياضة أو الفن أو التقنية أو العمل أو المجتمع."
            ),
            when_to_use=[
                "عندما يركز ملف الخدمة على العجز ولا يوثق ما يختاره الشخص أو يجيده.",
                "عند التخطيط للدمج أو النشاط اللامنهجي أو الانتقال إلى الرشد والعمل.",
                "عندما تظهر قدرة في سياق واحد ولا تتاح فرصة لاختبارها أو تطويرها.",
            ],
            do_not_use=[
                "لا تفترض موهبة حسابية أو فنية أو رياضية بسبب التشخيص.",
                "لا تستخدم القدرة لتبرير سحب التكييف أو الدعم.",
                "لا تحول الاهتمام الخاص إلى تدريب قسري أو مشروع للآخرين.",
            ],
            prerequisites=[
                "مقابلة اهتمام واختيار بوسيلة تواصل مناسبة.",
                "عينة أداء فعلية في أكثر من نشاط أو مستوى صعوبة.",
                "تحديد الحواجز البيئية والتواصلية والمادية والاجتماعية.",
            ],
            baseline=[
                "الاختيار والمبادرة والاستمرار في النشاط.",
                "الأداء أو الإنتاج تحت مستوى دعم موثق.",
                "الفرح أو الرضا أو العبء كما يعبر عنه الشخص.",
                "عدد فرص المشاركة الفعلية لا عدد الجلسات النظرية.",
            ],
            steps=[
                "اجمع قائمة اهتمامات من الشخص والأسرة وملاحظة السلوك في مواقف حقيقية.",
                "قدم ثلاثة إلى خمسة أنشطة متنوعة دون افتراض مسبق للموهبة.",
                "قِس الاختيار والمثابرة والتعلم والرضا ومستوى الدعم.",
                "حدد قدرة ناشئة واحدة أو اهتمامًا مستمرًا يستحق فرصة أعمق.",
                "أزل حاجزًا واحدًا: أداة، تواصل، نقل، تكلفة، تدريب شريك، أو قواعد مشاركة.",
                "اربط النشاط بمسار حقيقي مثل نادٍ أو أولمبياد خاص أو صف دامج أو تدريب مهني عندما يلائم الشخص.",
                "راجع ما إذا اتسعت المشاركة والهوية والاختيار، لا الأداء التنافسي وحده.",
            ],
            dose="دورة استكشاف من 6–12 أسبوعًا تتضمن فرصًا حقيقية متعددة، ثم قرار تطوير أو تغيير المسار بناءً على الاختيار والبيانات.",
            outcomes=[
                "ملف قدرات واهتمامات فردي مدعوم بعينات لا بصورة نمطية.",
                "زيادة فرص المشاركة الفعلية والعلاقات والانتماء.",
                "مسار تطوير واضح مع التكييفات والموارد والمسؤوليات.",
            ],
            fidelity=[
                "تنوع الفرص وعدم حصر الشخص في نشاط اختاره الفريق مسبقًا.",
                "توثيق الاختيار والرضا والرفض إلى جانب الأداء.",
                "فصل القدرة الفردية عن الادعاءات العامة حول التشخيص.",
            ],
            adaptations=common_adaptations(condition, cluster),
            team=team,
            stop_rule="أوقف أو غيّر النشاط إذا أصبح قسريًا أو مؤلمًا أو مستغلًا أو أدى إلى سحب دعم ضروري أو تجاهل اختيار الشخص.",
            evidence_relation="خطة مشاركة ونقاط قوة وفق ICF والحقوق والتعليم الدامج؛ إثبات القدرة يتم على مستوى الفرد والسياق.",
            source_keys=with_fallback_sources(data, condition, ["who-icf", "unicef-inclusive", "aaidd", "dec"]),
        )
    )

    plans.append(
        make_plan(
            plan_id="maintenance-transition",
            order=10,
            title=f"خطة الصيانة والتعميم والانتقال وإعادة القرار — {condition['title_ar']}",
            kind=family["maintenance-transition"]["kind"],
            goal="الحفاظ على الفائدة ذات المعنى، واختبار التعميم، وخفض الدعم بأمان، ووضع بديل واضح عند تغير الاحتياج أو غياب الاستجابة.",
            when_to_use=[
                "بعد ظهور استجابة أولية أو عند بلوغ نقطة قرار.",
                "قبل انتقال صف أو منزل أو خدمة أو عمل أو مرحلة عمرية.",
                "عندما تتوقف النتيجة أو تعود الصعوبة بعد خفض الدعم.",
            ],
            do_not_use=[
                "لا تسحب الدعم لمجرد تحسن الدرجة في جلسة.",
                "لا تعتبر التعميم تلقائيًا دون اختباره.",
                "لا تستمر بخطة مسطحة النتائج لأن الفريق استثمر وقتًا فيها.",
            ],
            prerequisites=[
                "تعريف مستوى الفائدة الذي يستحق الصيانة.",
                "مسبار تعميم وسياق صيانة محددان مسبقًا.",
                "خطة بديلة وإحالة محتملة ومسؤول متابعة.",
            ],
            baseline=[
                "أفضل مستوى مستقر تحقق أثناء التطبيق.",
                "الأداء في سياق أو شريك جديد.",
                "مستوى التلميح والدعم والعبء الحالي.",
                "رأي الشخص في الاستمرار أو التغيير.",
            ],
            steps=[
                "حدد العناصر الفعالة فعليًا ولا تحافظ على الحزمة كاملة دون سبب.",
                "اختبر المهارة أو التكييف مع شريك أو مكان أو مهمة جديدة.",
                "اخفض التلميح أو الجرعة تدريجيًا مع مسبار عودة.",
                "ضع خطة مكتوبة للأدوات والأشخاص والمسؤوليات عند الانتقال.",
                "راقب مؤشرات التراجع والآثار الطبية أو البيئية الجديدة.",
                f"إذا غابت الاستجابة رغم تنفيذ جيد، طبّق البديل المحدد للحالة: {condition['alternative']}",
                "اختم بدورة قرار جديدة: استمرار أو تعديل أو توقف أو إحالة أو هدف جديد.",
            ],
            dose="مسبار صيانة كل 2–4 أسابيع أولًا ثم فواصل أطول حسب استقرار المهارة، ومراجعة كاملة عند أي انتقال أو تدهور.",
            outcomes=[
                "فائدة مستمرة في سياق طبيعي لا في جلسة فقط.",
                "تعميم موثق أو معرفة واضحة بحدوده.",
                "خفض دعم آمن أو انتقال منظم أو بديل مبرر.",
            ],
            fidelity=universal_fidelity(),
            adaptations=common_adaptations(condition, cluster),
            team=team,
            stop_rule="أعد التقييم أو صعّد الإحالة عند فقد مهارة أو خطر أو ألم أو تدهور جديد، ولا تفسر التراجع تلقائيًا كضعف دافعية.",
            evidence_relation="خطة صيانة وانتقال قائمة على القياس المتكرر وICF والقرار المشترك؛ لا تفترض ثبات الاحتياج أو القدرة عبر الزمن.",
            source_keys=with_fallback_sources(data, condition, ["who-icf", "who-rehab", "gas", "wwc-scd", *condition["source_keys"]]),
        )
    )

    if len(plans) != PLAN_COUNT or [plan["order"] for plan in plans] != list(range(1, 11)):
        raise ValueError(f"Condition {condition['slug']} did not produce exactly ten ordered plans")
    if len({plan["id"] for plan in plans}) != PLAN_COUNT:
        raise ValueError(f"Condition {condition['slug']} plan IDs are not unique")
    for plan in plans:
        if len(plan["steps"]) < 5:
            raise ValueError(f"Plan {condition['slug']}:{plan['id']} has fewer than five steps")
        if len(plan["source_keys"]) < 2:
            raise ValueError(f"Plan {condition['slug']}:{plan['id']} has fewer than two sources")
    return plans


def render_sources(data: dict[str, Any], keys: list[str]) -> str:
    items = []
    for key in keys:
        source = data["sources"][key]
        items.append(
            f'<li><a href="{e(source["url"])}" target="_blank" rel="noopener noreferrer">'
            f'{e(source["organization"])} — {e(source["title"])}</a>'
            f'<span>{e(source["use"])}</span></li>'
        )
    return '<ol class="otb10-sources">' + "".join(items) + "</ol>"


def render_plan(data: dict[str, Any], condition: dict[str, Any], plan: dict[str, Any]) -> str:
    return f"""<article class="otb10-plan" data-ten-plan="{e(plan['id'])}">
<header><span>الخطة {plan['order']} من 10</span><h3>{e(plan['title'])}</h3><p>{e(plan['goal'])}</p></header>
<div class="otb10-grid">
<section><h4>متى تستخدم؟</h4>{ul(plan['when_to_use'])}</section>
<section><h4>متى لا تستخدم؟</h4>{ul(plan['do_not_use'])}</section>
<section><h4>المتطلبات السابقة</h4>{ul(plan['prerequisites'])}</section>
<section><h4>خط الأساس</h4>{ul(plan['baseline'])}</section>
</div>
<section class="otb10-steps"><h4>خطوات التنفيذ</h4>{ol(plan['steps'])}</section>
<div class="otb10-grid">
<section><h4>الجرعة أو الوتيرة</h4><p>{e(plan['dose'])}</p></section>
<section><h4>مؤشرات النتيجة</h4>{ul(plan['outcomes'])}</section>
<section><h4>جودة التنفيذ</h4>{ul(plan['fidelity'])}</section>
<section><h4>التكييفات والوصول</h4>{ul(plan['adaptations'])}</section>
</div>
<div class="otb10-grid">
<section><h4>الفريق والمسؤوليات</h4>{ul(plan['team'])}</section>
<section><h4>موعد إعادة القرار</h4>{ul(plan['review_timing'])}</section>
</div>
<div class="otb10-alert"><h4>قاعدة التوقف أو التصعيد</h4><p>{e(plan['stop_rule'])}</p></div>
<div class="otb10-evidence"><h4>صلة الخطة بالدليل</h4><p>{e(plan['evidence_relation'])}</p>{render_sources(data, plan['source_keys'])}<p><strong>حالة المراجعة:</strong> {e(plan['review_status'])}.</p></div>
</article>"""


def render_condition_block(
    data: dict[str, Any], framework: dict[str, Any], condition: dict[str, Any], plans: list[dict[str, Any]]
) -> str:
    cards = "".join(render_plan(data, condition, plan) for plan in plans)
    schema = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"الخطط العشر لـ {condition['title_ar']}",
        "numberOfItems": PLAN_COUNT,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": plan["order"],
                "name": plan["title"],
                "url": BASE + SECTION + "/" + condition["slug"] + "/#plan-" + plan["id"],
            }
            for plan in plans
        ],
    }
    return f"""{MARKER_START}
<section class="otb-section otb10-section" id="ten-plans" data-ten-plans-version="302">
<div class="otb-wrap">
<p class="otb-eyebrow">الطبقة التشغيلية الموسعة · الإصدار 302</p>
<h2>عشر خطط كاملة قابلة للتخصيص والقياس</h2>
<p class="otb-lead">{e(framework['plan_definition'])}</p>
<div class="otb10-summary">
<div><strong>10</strong><span>خطط مختلفة الوظيفة</span></div>
<div><strong>13</strong><span>حقلًا إلزاميًا لكل خطة</span></div>
<div><strong>0–24</strong><span>أسابيع كنقاط قرار لا وعد نتيجة</span></div>
<div><strong>مراجعة خارجية</strong><span>مطلوبة قبل الاعتماد السريري</span></div>
</div>
<div class="otb-notice warning"><strong>قاعدة علمية:</strong> لا يلزم تطبيق الخطط العشر كلها. يختار الفريق أقل مجموعة لازمة لتحقيق هدف الشخص، ويمنع خلط تدخلات متعددة دون توثيق لأنها تعطل تفسير الاستجابة.</div>
<div class="otb10-plans">{cards}</div>
<script type="application/ld+json">{compact_json(schema)}</script>
</div></section>
{MARKER_END}"""


def replace_block(text: str, start: str, end: str, block: str, before_pattern: str) -> str:
    pattern = re.compile(r"\s*" + re.escape(start) + r".*?" + re.escape(end) + r"\s*", re.DOTALL)
    text = pattern.sub("\n", text)
    match = re.search(before_pattern, text)
    if not match:
        raise ValueError(f"Could not find insertion point for marker {start}")
    return text[: match.start()] + block + "\n" + text[match.start() :]


def ensure_css(text: str) -> str:
    link = STYLE_MARKER + f'<link rel="stylesheet" href="{BASE_PATH}assets/css/{CSS_PATH.name}">'
    text = text.replace(link, "")
    if "</head>" not in text:
        raise ValueError("Missing </head> while adding ten-plan stylesheet")
    return text.replace("</head>", link + "</head>", 1)


def patch_condition_page(
    path: Path, data: dict[str, Any], framework: dict[str, Any], condition: dict[str, Any], plans: list[dict[str, Any]]
) -> None:
    text = path.read_text(encoding="utf-8")
    text = ensure_css(text)
    if 'href="#ten-plans"' not in text:
        marker = '<a href="#protocols">4 الأفكار</a>'
        if marker not in text:
            raise ValueError(f"Missing local protocol navigation in {path}")
        text = text.replace(marker, marker + '<a href="#ten-plans">10 الخطط</a>', 1)
    block = render_condition_block(data, framework, condition, plans)
    text = replace_block(
        text,
        MARKER_START,
        MARKER_END,
        block,
        r'<section class="otb-section"\s+id="expected">',
    )
    text = text.replace(
        "مسار مؤسسي لمقدم الخدمة حول",
        "مسار مؤسسي موسع يتضمن عشر خطط لمقدم الخدمة حول",
    )
    path.write_text(text, encoding="utf-8")


def render_methodology(data: dict[str, Any], framework: dict[str, Any]) -> str:
    family_cards = "".join(
        f"""<article><span>{item['order']}</span><h2>{e(item['title'])}</h2>
<p><strong>الوظيفة:</strong> {e(item['purpose'])}</p><p><strong>النوع:</strong> <code>{e(item['kind'])}</code></p></article>"""
        for item in framework["plan_families"]
    )
    fields = ul(framework["required_fields"])
    evidence = ul(framework["evidence_rules"])
    gates = ul(framework["review_gates"])
    conditions = "".join(
        f'<li><a href="../{e(item["slug"])}/#ten-plans">{item["rank"]}. {e(item["title_ar"])}</a></li>'
        for item in data["conditions"]
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": framework["title"],
        "inLanguage": "ar",
        "dateModified": UPDATED,
        "url": BASE + SECTION + "/" + METHODOLOGY_SLUG + "/",
        "about": ["ICF", "الخطط الفردية", "القياس المتكرر", "الأشخاص ذوو الاحتياجات الخاصة"],
    }
    return f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(framework['title'])} | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
<meta name="description" content="منهجية إنشاء عشر خطط كاملة لكل واحدة من مئة حالة، مع حقول التنفيذ والقياس والسلامة والمراجعة والمصادر.">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{BASE}{SECTION}/{METHODOLOGY_SLUG}/">
<link rel="stylesheet" href="{BASE_PATH}assets/css/outside-the-box-v254.css">
<link rel="stylesheet" href="{BASE_PATH}assets/css/{CSS_PATH.name}">
<script type="application/ld+json">{compact_json(schema)}</script></head>
<body class="otb-page"><a class="otb-skip" href="#main">تجاوز إلى المحتوى</a>
<header class="otb-header"><div class="otb-wrap otb-header-inner"><a class="otb-brand" href="{BASE_PATH}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a>
<nav class="otb-nav"><a href="../">المسارات المئة</a><a href="../methodology/">المنهجية الأساسية</a><a aria-current="page" href="./">منهجية الخطط العشر</a><a href="../evidence-standard/">معيار الأدلة</a></nav></div></header>
<main id="main"><section class="otb-page-hero"><div class="otb-wrap"><p class="otb-eyebrow">100 حالة × 10 خطط = 1000 مثيل خطة قابل للتدقيق</p>
<h1>{e(framework['title'])}</h1><p class="otb-lead">{e(framework['plan_definition'])}</p>
<div class="otb-notice"><strong>حالة النشر:</strong> {e(framework['scope']['status'])}.</div></div></section>
<section class="otb-section"><div class="otb-wrap"><h2>الخطط العشر ووظيفة كل خطة</h2><div class="otb10-family-grid">{family_cards}</div></div></section>
<section class="otb-section otb-soft"><div class="otb-wrap"><div class="otb-split"><div><h2>الحقول الإلزامية</h2>{fields}</div><div><h2>قواعد الدليل</h2>{evidence}</div></div></div></section>
<section class="otb-section"><div class="otb-wrap"><h2>بوابات المراجعة قبل الاعتماد السريري</h2>{gates}
<p class="otb-callout">وجود الخطط في الموقع لا يعني أن الخطط العشر واجبة التطبيق مع كل شخص. الاختيار فردي، ويجب أن يمر عبر التقييم والقرار المشترك والسلامة ونطاق الممارسة.</p></div></section>
<section class="otb-section otb-soft"><div class="otb-wrap"><h2>الوصول المباشر إلى الحالات المئة</h2><ol class="otb10-condition-index">{conditions}</ol></div></section>
</main><footer class="otb-footer"><div class="otb-wrap"><p>المحتوى للتخطيط والتثقيف المهني، ولا يستبدل التقييم أو العلاج أو القرار القانوني المحلي.</p></div></footer>
</body></html>"""


def patch_hub(site: Path, data: dict[str, Any], framework: dict[str, Any]) -> None:
    path = site / SECTION / "index.html"
    text = ensure_css(path.read_text(encoding="utf-8"))
    block = f"""{HUB_START}
<section class="otb-section otb10-hub"><div class="otb-wrap">
<p class="otb-eyebrow">التوسعة العلمية الكاملة · الإصدار 302</p><h2>100 حالة، وعشر خطط لكل حالة</h2>
<p>أصبحت كل صفحة حالة تضم عشر خطط تشغيلية موسعة: تحقق وسلامة، هدف وخط أساس، إتاحة، تواصل واختيار، ثلاثة تدخلات مرتبطة بالمصادر، تدريب الفريق، مشاركة واكتشاف قدرات، وصيانة وانتقال.</p>
<div class="otb10-summary"><div><strong>100</strong><span>حالة</span></div><div><strong>10</strong><span>خطط لكل حالة</span></div><div><strong>1000</strong><span>مثيل خطة منشور</span></div><div><strong>13+</strong><span>حقلًا لكل خطة</span></div></div>
<div class="otb-actions"><a class="otb-button" href="{METHODOLOGY_SLUG}/">منهجية الخطط العشر</a><a class="otb-button secondary" href="evidence-standard/">معيار الأدلة والمقاييس</a></div>
<div class="otb-notice warning"><strong>لا تضخيم:</strong> الخطط ليست عشر وصفات علاجية واجبة التطبيق، ولا تدعي الاعتماد السريري الخارجي. يختار الفريق الخطة أو المجموعة الأصغر الملائمة لهدف الشخص.</div>
</div></section>
{HUB_END}"""
    text = replace_block(text, HUB_START, HUB_END, block, r'<section class="otb-section"\s+id="conditions">')
    path.write_text(text, encoding="utf-8")


def patch_base_api(site: Path, report: dict[str, Any]) -> None:
    path = site / "api" / "outside-the-box-v254.json"
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["ten_plan_extension"] = {
        "version": VERSION,
        "plans_per_condition": PLAN_COUNT,
        "total_plan_instances": report["total_plan_instances"],
        "methodology_url": BASE + SECTION + "/" + METHODOLOGY_SLUG + "/",
        "external_clinical_review_completed": False,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def register_methodology_sitemap(site: Path) -> None:
    path = site / "sitemap-outside-the-box.xml"
    if not path.is_file():
        raise ValueError("Missing outside-the-box sitemap")
    tree = ET.parse(path)
    root = tree.getroot()
    target = BASE + SECTION + "/" + METHODOLOGY_SLUG + "/"
    existing = {(node.text or "").strip() for node in root.findall("{*}url/{*}loc")}
    if target not in existing:
        url = ET.SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(url, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = target
        ET.SubElement(url, "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod").text = UPDATED
        ET.SubElement(url, "{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq").text = "monthly"
        ET.SubElement(url, "{http://www.sitemaps.org/schemas/sitemap/0.9}priority").text = "0.8"
    tree.write(path, encoding="utf-8", xml_declaration=True)


def copy_css(site: Path) -> None:
    target = site / "assets" / "css"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CSS_PATH, target / CSS_PATH.name)


def validate(site: Path, report: dict[str, Any]) -> None:
    conditions = report["conditions"]
    if len(conditions) != 100:
        raise ValueError("Ten-plan report must contain 100 conditions")
    if report["total_plan_instances"] != 1000:
        raise ValueError("Ten-plan report must contain 1000 plan instances")
    for item in conditions:
        path = site / SECTION / item["slug"] / "index.html"
        text = path.read_text(encoding="utf-8")
        if text.count('data-ten-plan="') != PLAN_COUNT:
            raise ValueError(f"{item['slug']} does not contain exactly ten plan cards")
        for marker in (
            "متى تستخدم؟",
            "متى لا تستخدم؟",
            "المتطلبات السابقة",
            "خط الأساس",
            "خطوات التنفيذ",
            "الجرعة أو الوتيرة",
            "مؤشرات النتيجة",
            "جودة التنفيذ",
            "التكييفات والوصول",
            "الفريق والمسؤوليات",
            "قاعدة التوقف أو التصعيد",
            "صلة الخطة بالدليل",
            "موعد إعادة القرار",
        ):
            if text.count(marker) < PLAN_COUNT:
                raise ValueError(f"{item['slug']} is missing repeated plan field: {marker}")
        if "كل المصابين متفوقون" in text or "شفاء مضمون" in text:
            raise ValueError(f"Unsafe claim detected in {item['slug']}")
    method = site / SECTION / METHODOLOGY_SLUG / "index.html"
    if not method.is_file() or "1000 مثيل خطة" not in method.read_text(encoding="utf-8"):
        raise ValueError("Ten-plan methodology page is missing")
    api = site / "api" / "outside-the-box-ten-plans-v302.json"
    loaded = json.loads(api.read_text(encoding="utf-8"))
    if loaded["plans_per_condition"] != PLAN_COUNT or loaded["total_plan_instances"] != 1000:
        raise ValueError("Ten-plan API contract failed")


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ValueError(f"Missing site output: {site}")
    data, framework = load_sources()
    copy_css(site)
    conditions_report = []
    for condition in data["conditions"]:
        path = site / SECTION / condition["slug"] / "index.html"
        if not path.is_file():
            raise ValueError(f"Base condition page is missing: {condition['slug']}")
        plans = build_plans(data, framework, condition)
        patch_condition_page(path, data, framework, condition, plans)
        conditions_report.append(
            {
                "rank": condition["rank"],
                "slug": condition["slug"],
                "title_ar": condition["title_ar"],
                "cluster": condition["cluster"],
                "plan_count": len(plans),
                "plans": plans,
                "url": BASE + SECTION + "/" + condition["slug"] + "/#ten-plans",
            }
        )

    patch_hub(site, data, framework)
    methodology = site / SECTION / METHODOLOGY_SLUG
    methodology.mkdir(parents=True, exist_ok=True)
    (methodology / "index.html").write_text(render_methodology(data, framework), encoding="utf-8")
    register_methodology_sitemap(site)

    report = {
        "version": VERSION,
        "reviewed_at": UPDATED,
        "status": "passed",
        "review_status": framework["scope"]["status"],
        "condition_count": len(conditions_report),
        "plans_per_condition": PLAN_COUNT,
        "total_plan_instances": len(conditions_report) * PLAN_COUNT,
        "external_clinical_review_completed": False,
        "diagnostic_automation": False,
        "proprietary_test_items_published": False,
        "plan_definition": framework["plan_definition"],
        "required_fields": framework["required_fields"],
        "review_gates": framework["review_gates"],
        "methodology_url": BASE + SECTION + "/" + METHODOLOGY_SLUG + "/",
        "conditions": conditions_report,
    }
    api_dir = site / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    api_path = api_dir / "outside-the-box-ten-plans-v302.json"
    api_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    patch_base_api(site, report)
    validate(site, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    report = publish(args.site)
    print(
        json.dumps(
            {
                "version": report["version"],
                "status": report["status"],
                "condition_count": report["condition_count"],
                "plans_per_condition": report["plans_per_condition"],
                "total_plan_instances": report["total_plan_instances"],
                "external_clinical_review_completed": report["external_clinical_review_completed"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
