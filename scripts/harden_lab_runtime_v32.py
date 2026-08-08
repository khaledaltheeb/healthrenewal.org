from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ASSESSMENT_BLOCK = r'''function documentedBand(type,raw){
 if(type==='phq9'){if(raw<5)return['أعراض قليلة أو معدومة','0–4'];if(raw<10)return['أعراض خفيفة','5–9'];if(raw<15)return['أعراض متوسطة','10–14'];if(raw<20)return['أعراض متوسطة الشدة إلى شديدة','15–19'];return['أعراض شديدة','20–27']}
 if(type==='gad7'){if(raw<5)return['أعراض قليلة أو معدومة','0–4'];if(raw<10)return['أعراض خفيفة','5–9'];if(raw<15)return['أعراض متوسطة','10–14'];return['أعراض شديدة','15–21']}
 return['نتيجة وصفية','']
}
function assessmentScore(d,answers){
 const vals=Object.entries(answers||{}).map(([index,value])=>[Number(index),Number(value)]).filter(([,value])=>Number.isFinite(value));
 const answered=vals.length,raw=vals.reduce((sum,[,value])=>sum+value,0),type=d.score_type||'monitor';
 if(type==='audit_guided')return{type,answered,raw:null,percent:null,max:null,label:'مراجعة إرشادية غير محسوبة'};
 if(type==='who5'){const max=(d.questions||[]).length*5;return{type,answered,raw,max,percent:Math.round(raw*4),label:'مؤشر العافية النفسية'};}
 const max=(d.questions||[]).reduce((sum,item)=>sum+(((item&&item.options)||d.options||[]).length-1),0);
 return{type,answered,raw,max,percent:Math.round(raw/Math.max(1,max)*100),label:type==='monitor'?'مؤشر متابعة وصفي':'شدة الأعراض المبلغ عنها'};
}
function showAssessmentResult(d,state,final=false){
 const box=q('.result-card');if(!box)return;
 const score=assessmentScore(d,state.answers),total=(d.questions||[]).length,complete=score.answered===total,partial=!complete;
 let heading='',primary='',interpretation='',range='',safety='';
 if(score.type==='phq9'||score.type==='gad7'){
  const band=documentedBand(score.type,score.raw),name=score.type==='phq9'?'PHQ-9':'GAD-7';
  heading=`${name}: ${band[0]}`;range=band[1];primary=`<div class="result-score">${score.raw} / ${score.max}</div>`;
  interpretation=`هذا وصف لشدة الأعراض المبلغ عنها ضمن فترة الأداة، وليس تشخيصًا. ${partial?'النتيجة مؤقتة لأن بعض البنود لم تُجب بعد؛ لا تستخدم نطاق الشدة قبل الإكمال.':'اربط المجموع بالتعطل اليومي والسياق والتقييم المهني عند الحاجة.'}`;
 }else if(score.type==='who5'){
  heading='WHO-5 — العافية النفسية الحالية';primary=`<div class="result-score">${score.percent} / 100</div>`;
  interpretation=`الدرجة الخام ${score.raw} من ${score.max}، وحُولت بضربها في أربعة. الدرجة الأعلى تعكس عافية أفضل؛ النتيجة لا تستبعد اضطرابًا أو خطرًا ولا تقدم تشخيصًا.`;
 }else if(score.type==='audit_guided'){
  heading='اكتملت المراجعة الإرشادية لمحاور AUDIT';primary=`<div class="result-score">${score.answered} / ${total}</div>`;
  interpretation='لم تُحسب درجة AUDIT رسمية لأن بدائل الإجابة والترميز في هذه الصفحة إرشادية وليست التطبيق الأصلي بندًا بندًا. لا تستخدم هذه الصفحة لتحديد اعتماد أو خطة انسحاب.';
 }else{
  heading='مؤشر متابعة وصفي داخل هذه الأداة';primary=`<div class="result-score">${score.percent}%</div>`;
  interpretation=`الدرجة الخام ${score.raw} من ${score.max}. النسبة لتتبع نمطك أنت عبر ظروف متقاربة فقط؛ لا توجد نقاط قطع أو فئات خفيف/متوسط/شديد لهذه الأداة الأصلية غير المعيارية.`;
 }
 if(d.slug==='phq-9-plus'&&Number((state.answers||{})[8]||0)>0){
  safety='<aside class="lab-safety-alert" role="alert"><strong>تنبيه سلامة مستقل:</strong> أي إجابة أعلى من صفر في بند أفكار الموت أو إيذاء النفس تحتاج تواصلًا بشريًا مباشرًا وتقييمًا للسياق. إذا كان الخطر وشيكًا أو لا تستطيع ضمان سلامتك، تواصل فورًا مع شخص موثوق أو مختص أو خدمات الطوارئ المحلية، ولا تبق وحدك.</aside>';
 }
 box.innerHTML=`<span class="lab-v12__badge">${final?'النتيجة النهائية':'نتيجة مؤقتة'}</span><h2>${heading}</h2>${primary}<p><strong>الإكمال:</strong> ${score.answered} من ${total}${range?` · <strong>النطاق الخام:</strong> ${range}`:''}</p><p>${interpretation}</p>${safety}<p><small>الأداة للتثقيف أو المتابعة ولا تستبدل التقييم المهني أو قرار العلاج.</small></p>`;
 box.dataset.visible='true';box.hidden=false;box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'});
}
function assessmentEngine(host,d){
 const loaded=load(d),state=loaded&&typeof loaded==='object'?loaded:{stage:0,answers:{}};state.stage=Number.isInteger(state.stage)?state.stage:0;state.answers=state.answers&&typeof state.answers==='object'?state.answers:{};
 const totalStages=4,per=Math.ceil((d.questions||[]).length/totalStages);
 function currentBounds(){const start=state.stage*per;return[start,Math.min((d.questions||[]).length,start+per)]}
 function collect(){qa('input:checked',host).forEach(input=>{state.answers[Number(input.name.slice(1))]=Number(input.value)});save(d,state)}
 function missingInStage(){const[start,end]=currentBounds(),missing=[];for(let index=start;index<end;index++)if(!Object.prototype.hasOwnProperty.call(state.answers,index))missing.push(index);return missing}
 function announceError(missing){const node=q('.lab-inline-error',host);if(!node)return;if(!missing.length){node.hidden=true;node.textContent='';return}node.hidden=false;node.textContent=`أكمل ${missing.length} بندًا قبل الانتقال. تم نقل التركيز إلى أول بند ناقص.`;const input=q(`input[name="q${missing[0]}"]`,host);input?.focus()}
 function render(){
  state.stage=clamp(state.stage,0,totalStages-1);const[start,end]=currentBounds(),items=(d.questions||[]).slice(start,end);
  host.innerHTML=`<div class="lab-engine"><div class="stage-bar" aria-hidden="true"><span style="width:${((state.stage+1)/totalStages)*100}%"></span></div><div class="stage-meta"><strong>المرحلة ${state.stage+1} من ${totalStages}</strong><span>${Object.keys(state.answers).length}/${(d.questions||[]).length} إجابة</span></div><p class="lab-inline-error" role="alert" aria-live="assertive" tabindex="-1" hidden></p><form class="assessment-form" novalidate>${items.map((item,offset)=>{const index=start+offset,opts=(item&&item.options)||d.options||['لا ينطبق','قليلًا','أحيانًا','غالبًا','بدرجة شديدة'],text=typeof item==='string'?item:item.text;return`<fieldset class="question" data-question-index="${index}"><legend>${index+1}. ${text}</legend><div class="answer-grid">${opts.map((option,value)=>`<label><input type="radio" name="q${index}" value="${value}" ${String(state.answers[index])===String(value)?'checked':''}><span>${typeof option==='object'?(option.label||option.value):option}</span></label>`).join('')}</div></fieldset>`}).join('')}</form><div class="game-actions">${button('السابق','secondary prev')}${button(state.stage===totalStages-1?'إنهاء وإظهار النتيجة':'المرحلة التالية','next')}${button('إظهار النتيجة الحالية','secondary interim')}${button('حفظ وتوقف','secondary pause')}${button('بدء جديد','secondary restart')}</div><section class="result-card" aria-live="polite" aria-atomic="true"></section></div>`;
  qa('input',host).forEach(input=>input.addEventListener('change',event=>{state.answers[Number(event.target.name.slice(1))]=Number(event.target.value);save(d,state);announceError([])}));
  const prev=q('.prev',host);prev.disabled=state.stage===0;prev.onclick=()=>{collect();state.stage=Math.max(0,state.stage-1);save(d,state);render();q('input',host)?.focus()};
  q('.next',host).onclick=()=>{collect();const missing=missingInStage();if(missing.length){announceError(missing);return}if(state.stage<totalStages-1){state.stage++;save(d,state);render();host.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});q('input',host)?.focus()}else showAssessmentResult(d,state,true)};
  q('.interim',host).onclick=()=>{collect();showAssessmentResult(d,state,false)};
  q('.pause',host).onclick=()=>{collect();alert('تم حفظ تقدمك محليًا على هذا الجهاز. لا تُرسل الإجابات إلى خادم.')};
  q('.restart',host).onclick=()=>{if(confirm('هل تريد مسح الإجابات والبدء من جديد؟')){clear(d);state.stage=0;state.answers={};render();q('input',host)?.focus()}};
 }
 render();
}
function seeded(seed){'''

COGNITIVE_RESULT = r'''function cognitiveResult(d,state,final=false){
 const box=q('.result-card');if(!box)return;
 const trials=Array.isArray(state.trials)?state.trials:[],correct=trials.filter(item=>item&&item.correct===true).length,acc=trials.length?Math.round(correct/trials.length*100):0;
 const times=trials.map(item=>Number(item&&item.time)).filter(value=>Number.isFinite(value)&&value>=0).sort((a,b)=>a-b);
 let median=0;if(times.length){const mid=Math.floor(times.length/2);median=times.length%2?times[mid]:(times[mid-1]+times[mid])/2;median=Math.round(median)}
 const speedComponent=times.length?clamp(1200-median,0,1200)/1200*30:0,composite=Math.round(acc*.7+speedComponent);
 box.innerHTML=`<span class="lab-v12__badge">${final?'النتيجة النهائية':'نتيجة مؤقتة'}</span><h2>ملخص أداء هذه الجلسة</h2><div class="result-score">${composite} / 100</div><p><strong>الدقة:</strong> ${acc}% · <strong>الزمن الوسيط الصالح:</strong> ${times.length?median:'—'} مللي ثانية · <strong>المحاولات:</strong> ${trials.length} · <strong>أزمنة صالحة:</strong> ${times.length}</p><p>المؤشر المركب صيغة داخلية: 70% دقة و30% سرعة مطبعة مقابل 1200 مللي ثانية. ليس درجة IQ، ولا معيارًا سريريًا أو سكانيًا، ولا يجوز استخدامه لاتخاذ قرار طبي أو تعليمي أو وظيفي.</p>`;
 box.dataset.visible='true';box.hidden=false;box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'});
}
function cognitiveEngine('''


def patch_runtime(site: Path) -> dict:
    js = site / "assets" / "js" / "lab-v12.js"
    if not js.is_file():
        raise SystemExit(f"missing runtime: {js}")
    source = js.read_text(encoding="utf-8")
    if "function documentedBand(type,raw)" not in source:
        pattern = re.compile(r"function resultBand\(p\)\{.*?function seeded\(seed\)\{", re.S)
        source, count = pattern.subn(ASSESSMENT_BLOCK, source, count=1)
        if count != 1:
            raise SystemExit("assessment runtime block not found exactly once")
    if "const speedComponent=times.length?" not in source:
        pattern = re.compile(r"function cognitiveResult\(d,state,final=false\)\{.*?function cognitiveEngine\(", re.S)
        source, count = pattern.subn(COGNITIVE_RESULT, source, count=1)
        if count != 1:
            raise SystemExit("cognitive result block not found exactly once")
    js.write_text(source, encoding="utf-8")
    report = {
        "version": 32,
        "status": "passed",
        "runtime": js.relative_to(site).as_posix(),
        "assessment_missing_guard": "lab-inline-error" in source and "missingInStage" in source,
        "first_missing_focus": "input?.focus()" in source,
        "phq9_documented_bands": "20–27" in source,
        "gad7_documented_bands": "15–21" in source,
        "who5_direction_correct": "الدرجة الأعلى تعكس عافية أفضل" in source,
        "audit_official_score_disabled": "لم تُحسب درجة AUDIT رسمية" in source,
        "monitor_clinical_bands_disabled": "لا توجد نقاط قطع أو فئات خفيف/متوسط/شديد" in source,
        "phq9_item9_safety": "بند أفكار الموت أو إيذاء النفس" in source,
        "finite_nonnegative_times": "Number.isFinite(value)&&value>=0" in source,
        "even_median_supported": "times[mid-1]+times[mid]" in source,
        "composite_disclosed": "70% دقة و30% سرعة" in source,
        "local_only_copy": "لا تُرسل الإجابات إلى خادم" in source,
    }
    if not all(value is True for key, value in report.items() if key not in {"version", "status", "runtime"}):
        report["status"] = "failed"
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-runtime-v32.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
