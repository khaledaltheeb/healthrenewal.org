from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERSION = 32

MONITOR_CONTEXT = r''' const answers=state.answers||{},criticalIndices=Array.isArray(d.critical_item_indices)?d.critical_item_indices.filter(index=>Number.isInteger(index)&&index>=0&&index<total):[];
 const flaggedCritical=criticalIndices.filter(index=>Number(answers[index]||0)>0);
 const flaggedLabels=flaggedCritical.map(index=>typeof d.questions[index]==='string'?d.questions[index]:(d.questions[index]?.text||`البند ${index+1}`));'''

MONITOR_BRANCH = r'''}else if(d.monitor_policy==='safety_flags'){
  heading='مراجعة إشارات الأمان في العلاقة';primary=`<div class="result-score">${flaggedCritical.length} إشارات</div>`;
  interpretation=`لا تنتج هذه الأداة مجموع أمان أو حكمًا على العلاقة. كل تهديد أو إكراه أو عنف أو تقييد قرار يُقرأ مستقلًا عن العدد. ${partial?'بعض البنود غير مجابة؛ لا تعتبر غياب الإشارة نتيجة نهائية.':'استخدم البنود المحددة لتخطيط خطوة أمان ودعم بشري مناسب.'}`;
 }else if(d.monitor_policy==='readiness_gaps'){
  heading='فجوات خطة الأمان والتعافي';primary=`<div class="result-score">${score.raw} / ${score.max}</div>`;
  interpretation=`النسبة الوصفية ${score.percent}% تعكس مقدار الفجوات المبلغ عنها في عناصر الخطة داخل هذه الأداة فقط؛ الأعلى يعني أن عناصر أكثر غير متاحة أو صعبة الاستخدام. لا تقيس شدة الاعتماد أو خطر الانسحاب ولا تحدد علاجًا.`;
 }else{
  heading='مؤشر متابعة وصفي داخل هذه الأداة';primary=`<div class="result-score">${score.percent}%</div>`;
  interpretation=`الدرجة الخام ${score.raw} من ${score.max}. النسبة لتتبع نمطك أنت عبر ظروف متقاربة فقط؛ لا توجد نقاط قطع أو فئات خفيف/متوسط/شديد لهذه الأداة الأصلية غير المعيارية. ${d.monitor_direction||''}`;
 }'''

SAFETY_BLOCK = r''' if(score.type==='monitor'&&flaggedCritical.length){
  const list=flaggedLabels.slice(0,4).map(label=>`<li>${label}</li>`).join('');
  safety+=`<aside class="lab-safety-alert" role="alert"><strong>إشارات تحتاج مراجعة مستقلة الآن:</strong><ul>${list}</ul>${flaggedLabels.length>4?`<p>وهناك ${flaggedLabels.length-4} إشارات إضافية.</p>`:''}<p>لا تعتمد على المجموع. إذا كان هناك خطر مباشر، تهديد، عنف، إكراه، عجز عن ضمان السلامة، أو أعراض صحية عاجلة، تواصل فورًا مع شخص موثوق أو مختص أو خدمات الطوارئ المحلية وانتقل إلى مكان أكثر أمانًا إن أمكن.</p></aside>`;
 }
 if(d.slug==='phq-9-plus'&&Number((state.answers||{})[8]||0)>0){
  safety+='<aside class="lab-safety-alert" role="alert"><strong>تنبيه سلامة مستقل:</strong> أي إجابة أعلى من صفر في بند أفكار الموت أو إيذاء النفس تحتاج تواصلًا بشريًا مباشرًا وتقييمًا للسياق. إذا كان الخطر وشيكًا أو لا تستطيع ضمان سلامتك، تواصل فورًا مع شخص موثوق أو مختص أو خدمات الطوارئ المحلية، ولا تبق وحدك.</aside>';
 }'''


def replace_once(source: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Missing or duplicated monitor runtime target: {label}")
    return updated


def patch_runtime(site: Path) -> dict:
    site = site.resolve()
    runtime = site / "assets" / "js" / "lab-v12.js"
    if not runtime.is_file():
        raise SystemExit(f"Missing laboratory runtime: {runtime}")
    source = runtime.read_text(encoding="utf-8")

    if "flaggedCritical=criticalIndices.filter" not in source:
        source = replace_once(
            source,
            r"(const score=assessmentScore\(d,state\.answers\),total=\(d\.questions\|\|\[\]\)\.length,complete=score\.answered===total,partial=!complete;)",
            r"\1\n" + MONITOR_CONTEXT,
            "monitor context",
        )

    if "d.monitor_policy==='safety_flags'" not in source:
        source = replace_once(
            source,
            r"\}else\{\n  heading='مؤشر متابعة وصفي داخل هذه الأداة';primary=`<div class=\"result-score\">\$\{score\.percent\}%</div>`;\n  interpretation=`الدرجة الخام \$\{score\.raw\} من \$\{score\.max\}\. النسبة لتتبع نمطك أنت عبر ظروف متقاربة فقط؛ لا توجد نقاط قطع أو فئات خفيف/متوسط/شديد لهذه الأداة الأصلية غير المعيارية\.`;\n \}",
            MONITOR_BRANCH,
            "monitor result policies",
        )

    if "إشارات تحتاج مراجعة مستقلة الآن" not in source:
        source = replace_once(
            source,
            r" if\(d\.slug==='phq-9-plus'&&Number\(\(state\.answers\|\|\{\}\)\[8\]\|\|0\)>0\)\{\n  safety='<aside class=\"lab-safety-alert\" role=\"alert\"><strong>تنبيه سلامة مستقل:</strong>.*?</aside>';\n \}",
            SAFETY_BLOCK,
            "critical monitor and PHQ safety",
        )

    runtime.write_text(source, encoding="utf-8")
    report = {
        "version": VERSION,
        "status": "passed",
        "runtime": runtime.relative_to(site).as_posix(),
        "safety_flag_policy": "d.monitor_policy==='safety_flags'" in source,
        "readiness_gap_policy": "d.monitor_policy==='readiness_gaps'" in source,
        "burden_tracking_policy": "d.monitor_direction||''" in source,
        "critical_item_guard": "flaggedCritical=criticalIndices.filter" in source,
        "critical_item_labels": "flaggedLabels.slice(0,4)" in source,
        "no_aggregate_safety_score": "لا تنتج هذه الأداة مجموع أمان" in source,
        "recovery_not_addiction_severity": "لا تقيس شدة الاعتماد أو خطر الانسحاب" in source,
        "direct_risk_escalation": "لا تعتمد على المجموع. إذا كان هناك خطر مباشر" in source,
        "phq9_safety_preserved": "بند أفكار الموت أو إيذاء النفس" in source,
    }
    if not all(
        value is True
        for key, value in report.items()
        if key not in {"version", "status", "runtime"}
    ):
        report["status"] = "failed"
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "monitor-runtime-v32.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if report["status"] != "passed":
        raise SystemExit(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(patch_runtime(args.site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
