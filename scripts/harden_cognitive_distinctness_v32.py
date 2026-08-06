from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

VERSION = 32

HELPER = r'''
function v32DistinctCognitiveTrial(d,stage,index,sessionSeed,rnd,ri,pick,symbols,arrows){
 const mode=d.mode||d.category||'',slug=d.slug||'';
 const stableHash=value=>{let hash=2166136261;for(const char of String(value)){hash^=char.charCodeAt(0);hash=Math.imul(hash,16777619)}return hash>>>0};
 const uniqueValues=items=>[...new Set(items.map(String))];
 const sequenceOptions=(tokens,pool,separator=' ')=>{
  const answer=tokens.join(separator),variants=[];
  const add=value=>{value=Array.isArray(value)?value.join(separator):String(value);if(value!==answer&&!variants.includes(value))variants.push(value)};
  if(tokens.length>1){const swapped=[...tokens];[swapped[0],swapped[1]]=[swapped[1],swapped[0]];add(swapped);add([...tokens.slice(1),tokens[0]]);add([...tokens].reverse())}
  for(let position=tokens.length-1;position>=0&&variants.length<3;position--){
   for(const replacement of pool){if(replacement===tokens[position])continue;const changed=[...tokens];changed[position]=replacement;add(changed);if(variants.length>=3)break}
  }
  return shuffle([answer,...variants.slice(0,3)],rnd);
 };
 if(mode==='choice_reaction'){
  const target=pick(arrows),minimum=Math.max(220,520-stage*45),maximum=980+stage*150;
  return{kind:'reaction',prompt:`اختر اتجاه السهم الظاهر: <span style="font-size:${2+stage*.15}em;font-weight:900">${target}</span>`,answer:target,options:[...arrows],delay:ri(minimum,maximum),choiceReactionMapping:'arrow-direction',reactionForeperiodMin:minimum,reactionForeperiodMax:maximum,explanation:`الاتجاه المطابق هو ${target}.`};
 }
 if(mode==='visual_reaction'){
  const positions=['أعلى اليمين','أسفل اليمين','أسفل اليسار','أعلى اليسار'],answer=pick(positions),targetSize=[32,28,24,20,18][stage],minimum=Math.max(220,540-stage*45),maximum=1000+stage*150;
  const cells=positions.map(position=>`<span style="display:grid;place-items:center;width:2.5rem;height:2.5rem;border:1px solid #9fb8b4">${position===answer?`<b style="font-size:${targetSize}px">●</b>`:'&nbsp;'}</span>`).join('');
  return{kind:'reaction',prompt:`حدّد موضع الإشارة داخل الشبكة: <span aria-label="شبكة بصرية ذات إشارة واحدة" style="display:inline-grid;grid-template-columns:repeat(2,2.5rem);gap:.25rem;vertical-align:middle">${cells}</span>`,answer,options:[...positions],delay:ri(minimum,maximum),visualReactionTargetSize:targetSize,visualReactionPosition:answer,reactionForeperiodMin:minimum,reactionForeperiodMax:maximum,explanation:`ظهرت الإشارة في موضع ${answer}.`};
 }
 if(mode==='simple_reaction'){
  const target=pick(symbols),minimum=Math.max(250,600-stage*50),maximum=1100+stage*180;
  return{kind:'reaction',singleResponse:true,prompt:`ظهرت الإشارة ${target}. اضغط الزر الآن.`,answer:'اضغط الآن',options:['اضغط الآن'],delay:ri(minimum,maximum),reactionForeperiodMin:minimum,reactionForeperiodMax:maximum,explanation:'سُجل الزمن من ظهور الإشارة حتى بدء الضغط؛ لا يتضمن زمن الانتظار قبل ظهورها.'};
 }
 if(mode==='sustained_attention'){
  const targetPool=symbols.slice(0,6),targetRnd=seeded(stableHash(`${slug}|${stage}|${Number(sessionSeed)||0}|target`)),target=targetPool[Math.floor(targetRnd()*targetPool.length)],cycle=[2,3,4,5,6][stage],offset=stableHash(`${slug}|${stage}|${Number(sessionSeed)||0}|offset`)%cycle,isTarget=(index+offset)%cycle===0,shown=isTarget?target:pick(targetPool.filter(value=>value!==target));
  return{prompt:`الهدف الثابت لهذه المرحلة هو ${target}. ظهر الآن ${shown}. هل هو الهدف؟`,answer:isTarget?'نعم':'لا',options:['نعم','لا'],sustainedTarget:target,targetPresent:isTarget,targetCycle:cycle,explanation:isTarget?`ظهر الهدف الثابت ${target}.`:`ظهر مشتت، والهدف الثابت هو ${target}.`};
 }
 if(mode==='visual_search'){
  const dissimilar=[['●','▲','■','◆'],['★','⬟','✚','⬢']],similar=[['●','○','◉','◎'],['▲','△','▴','▵'],['■','□','▣','▢'],['◆','◇','◈','⬙']],family=pick(stage<2?dissimilar:similar),target=pick(family),distractor=pick(family.filter(value=>value!==target)),size=[12,18,24,30,36][stage],row=shuffle([target,...Array(size-1).fill(distractor)],rnd);
  return{prompt:`ما الرمز الوحيد المختلف؟ ${row.join(' ')}`,answer:target,options:shuffle(family,rnd),visualSearchSetSize:size,visualSearchSimilarity:stage<2?'منخفض':'مرتفع',explanation:`الرمز ${target} ظهر مرة واحدة بين مشتتات ${distractor}.`};
 }
 if(mode==='word_categories'){
  const banks=[
   {members:['تفاح','موز','برتقال','عنب','كمثرى','خوخ'],answer:'فواكه',wrong:['خضروات','حبوب','أدوات مطبخ']},
   {members:['قلم','دفتر','مسطرة','ممحاة','مبراة','حقيبة'],answer:'أدوات مدرسية',wrong:['أثاث مدرسي','مواد غذائية','وسائل نقل']},
   {members:['ركض','سباحة','تسلق','دراجات','تنس','مشي'],answer:'أنشطة حركية',wrong:['مشاعر','مهن صحية','أماكن عامة']},
   {members:['طبيب','ممرض','صيدلي','مسعف','معالج','أخصائي تغذية'],answer:'مهن صحية',wrong:['أدوات طبية','أماكن علاج','أمراض']},
   {members:['ميزان','مسطرة','ساعة','مقياس حرارة','كوب مدرج','عداد'],answer:'أدوات قياس',wrong:['أجهزة ترفيه','مواد بناء','أدوات كتابة']}
  ],bank=pick(banks),count=Math.min(bank.members.length,2+stage),members=shuffle(bank.members,rnd).slice(0,count);
  return{prompt:`ما الفئة الأدق التي تجمع: ${members.join('، ')}؟`,answer:bank.answer,options:shuffle([bank.answer,...bank.wrong],rnd),categoryMemberCount:count,explanation:`الفئة الأدق المشتركة هي ${bank.answer}.`};
 }
 if(mode==='semantic_fluency'){
  const banks=[
   {category:'حيوانات بحرية',seeds:['حوت','دلفين','قرش','أخطبوط','فقمة'],answer:'سلحفاة بحرية',wrong:['حصان','صقر','جمل']},
   {category:'مدن أردنية',seeds:['عمّان','إربد','العقبة','السلط','الكرك'],answer:'جرش',wrong:['دمشق','الإسكندرية','دبي']},
   {category:'أدوات مطبخ',seeds:['ملعقة','قدر','سكين','مصفاة','مقلاة'],answer:'مغرفة',wrong:['مطرقة','مسطرة','وسادة']},
   {category:'وسائل نقل',seeds:['حافلة','قطار','سفينة','دراجة','طائرة'],answer:'سيارة',wrong:['خزانة','نافذة','مصباح']},
   {category:'مشاعر',seeds:['فرح','حزن','خوف','غضب','دهشة'],answer:'خجل',wrong:['طاولة','مطر','قلم']}
  ],bank=pick(banks),seedCount=Math.min(bank.seeds.length,2+stage),seeds=shuffle(bank.seeds,rnd).slice(0,seedCount);
  return{prompt:`استرجاع دلالي موجّه: بعد ${seeds.join('، ')}، أي كلمة أخرى تنتمي إلى فئة «${bank.category}»؟`,answer:bank.answer,options:shuffle([bank.answer,...bank.wrong],rnd),guidedSemanticRetrieval:true,semanticSeedCount:seedCount,explanation:`${bank.answer} مثال إضافي صحيح من فئة ${bank.category}. هذه مهمة اختيار موجّه وليست اختبار طلاقة لفظية معياريًا.`};
 }
 if(mode==='attention_switch'){
  const colors=[['أحمر','#b42318'],['أزرق','#175cd3'],['أخضر','#067647'],['بنفسجي','#6941c6']],color=pick(colors),shape=pick(symbols.slice(0,6));
  const ruleAt=trial=>{
   if(stage===0)return'color';
   if(stage===1)return Math.floor(Math.max(0,trial)/3)%2===0?'color':'shape';
   if(stage===2)return Math.floor(Math.max(0,trial)/2)%2===0?'color':'shape';
   if(stage===3)return Math.max(0,trial)%2===0?'color':'shape';
   return (stableHash(`${slug}|${stage}|${Number(sessionSeed)||0}|${Math.max(0,trial)}`)>>>7)%2===0?'color':'shape';
  };
  const current=ruleAt(index),previous=ruleAt(index-1),switchTrial=index>0&&current!==previous,answer=current==='color'?color[0]:shape;
  return{prompt:`إشارة القاعدة: ${current==='color'?'لون':'شكل'}. <span style="color:${color[1]};font-size:2em;font-weight:900">${shape}</span>`,answer,options:current==='color'?colors.map(item=>item[0]):symbols.slice(0,6),attentionRule:current,previousAttentionRule:index>0?previous:'none',switchTrial,explanation:`طُبقت قاعدة ${current==='color'?'اللون':'الشكل'}${switchTrial?' بعد تبدل القاعدة':' دون تبدل عن المحاولة السابقة'}.`};
 }
 if(['digit_span_forward','digit_span_backward','letter_span','spatial_span'].includes(mode)){
  const length=3+stage;
  let pool,sequence,answerTokens,separator=' ',study,prompt;
  if(mode==='digit_span_forward'||mode==='digit_span_backward'){
   pool=['1','2','3','4','5','6','7','8','9'];sequence=shuffle(pool,rnd).slice(0,length);answerTokens=mode==='digit_span_backward'?[...sequence].reverse():sequence;study=sequence.join(' – ');prompt=mode==='digit_span_backward'?'اختر تسلسل الأرقام بالترتيب المعكوس':'اختر تسلسل الأرقام بالترتيب نفسه';
  }else if(mode==='letter_span'){
   pool=['ب','ت','ر','س','ك','م','ن','هـ','و','ي'];sequence=shuffle(pool,rnd).slice(0,length);answerTokens=sequence;study=sequence.join(' – ');prompt='اختر تسلسل الحروف بالترتيب نفسه';
  }else{
   pool=['1','2','3','4','5','6','7','8','9'];sequence=shuffle(pool,rnd).slice(0,length);answerTokens=sequence;separator=' → ';study=`المسار: ${sequence.join(' → ')}`;prompt='اختر مسار المواقع بالترتيب نفسه';
  }
  const answer=answerTokens.join(separator),options=sequenceOptions(answerTokens,pool,separator),studyMs=Math.max(1900,3400-stage*300);
  return{study,studyMs,prompt,answer,options,spanLength:length,spanDirection:mode==='digit_span_backward'?'backward':'forward',uniqueStudyTokens:new Set(sequence).size,explanation:`التسلسل الصحيح هو ${answer}.`};
 }
 return null;
}
'''

DEFINITION_UPDATES = {
    "choice-reaction": {
        "instrument_type": "مهمة زمن اختيار بين أربعة اتجاهات",
        "summary": "يُطابق المشارك اتجاه سهم بصري بأحد أربعة بدائل بعد فترة انتظار متغيرة؛ تجمع المهمة زمن الكشف واختيار الاستجابة.",
    },
    "visual-reaction": {
        "instrument_type": "مهمة زمن اختيار موضع إشارة بصرية",
        "summary": "تظهر إشارة واحدة داخل شبكة رباعية ويحدد المشارك موضعها؛ يصغر الهدف تدريجيًا عبر المراحل دون تحويل المهمة إلى بحث بصري كثيف.",
    },
    "simple-reaction": {
        "instrument_type": "مهمة زمن استجابة أحادية الزر داخل المتصفح",
        "summary": "تظهر إشارة بعد فترة انتظار متغيرة، ثم يستخدم المشارك زر استجابة واحدًا. الزمن تقني داخل الجهاز وليس قياسًا عصبيًا معياريًا.",
    },
    "sustained-attention": {
        "instrument_type": "مهمة يقظة متتابعة بهدف ثابت لكل مرحلة",
        "summary": "يبقى رمز الهدف ثابتًا خلال المرحلة وتقل نسبة ظهوره تدريجيًا، لتمييزها عن البحث البصري في مصفوفة.",
    },
    "visual-search": {
        "instrument_type": "بحث بصري عن عنصر وحيد مختلف",
        "summary": "تزداد كثافة المصفوفة والتشابه البصري بين الهدف والمشتتات عبر المراحل.",
    },
    "word-categories": {
        "instrument_type": "تصنيف دلالي موجّه",
        "summary": "يُستنتج اسم الفئة الأدق من مجموعة أمثلة، مع زيادة عدد الأمثلة وتقارب البدائل.",
    },
    "semantic-fluency": {
        "instrument_type": "استرجاع دلالي موجّه متعدد الخيارات",
        "summary": "تُختار كلمة إضافية صحيحة بعد أمثلة من فئة محددة. ليست هذه الصيغة اختبار طلاقة لفظية حرًا أو معياريًا.",
    },
    "attention-switch": {
        "instrument_type": "مهمة تبديل قاعدة بين اللون والشكل",
        "summary": "تتدرج المراحل من ثبات القاعدة إلى تبدلات متكررة ثم غير متوقعة، ويُوسم كل انتقال كتكرار أو تبديل.",
    },
    "digit-span-forward": {
        "instrument_type": "استدعاء تسلسل رقمي أمامي بعد إخفاء العرض",
    },
    "digit-span-backward": {
        "instrument_type": "استدعاء تسلسل رقمي معكوس بعد إخفاء العرض",
    },
    "letter-span": {
        "instrument_type": "استدعاء تسلسل حروف بعد إخفاء العرض",
    },
    "spatial-span": {
        "instrument_type": "استدعاء مسار مواقع بعد إخفاء العرض",
    },
}

DEFINITION_RE = re.compile(
    r'(<script type="application/json" id="lab-definition">)(.*?)(</script>)',
    re.S,
)


def load_definition(source: str) -> dict:
    match = DEFINITION_RE.search(source)
    if not match:
        raise ValueError("missing lab-definition")
    return json.loads(match.group(2).replace("<\\/", "</"))


def write_definition(source: str, definition: dict) -> str:
    payload = json.dumps(definition, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    updated, count = DEFINITION_RE.subn(
        lambda match: match.group(1) + payload + match.group(3),
        source,
        count=1,
    )
    if count != 1:
        raise ValueError("definition replacement failed")
    return updated


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise SystemExit(f"Expected one {label} target, found {source.count(old)}")
    return source.replace(old, new, 1)


def patch_runtime(site: Path) -> dict:
    site = site.resolve()
    runtime = site / "assets" / "js" / "lab-v12.js"
    if not runtime.is_file():
        raise SystemExit(f"missing runtime: {runtime}")
    source = runtime.read_text(encoding="utf-8")

    if "function v32DistinctCognitiveTrial(" not in source:
        source = replace_once(
            source,
            "\nfunction makeTrial(d,stage,index,sessionSeed=0){",
            "\n" + HELPER + "\nfunction makeTrial(d,stage,index,sessionSeed=0){",
            "makeTrial insertion",
        )

    if "const distinctV32=v32DistinctCognitiveTrial" not in source:
        old = "arrows=['↑','→','↓','←'];const gradedV212="
        new = (
            "arrows=['↑','→','↓','←'];"
            "const distinctV32=v32DistinctCognitiveTrial(d,stage,index,sessionSeed,rnd,ri,pick,symbols,arrows);"
            "if(distinctV32)return v202Finish(d,stage,rnd,distinctV32);"
            "const gradedV212="
        )
        source = replace_once(source, old, new, "distinct trial dispatch")

    if "singleResponse=data.singleResponse===true" not in source:
        old = "function v202Finish(d,stage,rnd,data){let answer=String(data.answer),options=[...new Map((data.options||[]).map(x=>[v202Val(x),x])).values()];"
        new = "function v202Finish(d,stage,rnd,data){let answer=String(data.answer),options=[...new Map((data.options||[]).map(x=>[v202Val(x),x])).values()],singleResponse=data.singleResponse===true;"
        source = replace_once(source, old, new, "single response declaration")
        old = "for(const item of fallback){if(options.length>=4)break;if(String(item)!==answer&&!options.some(x=>v202Val(x)===String(item)))options.push(v202Opt(item))}options=shuffle(options,rnd);"
        new = "if(singleResponse){options=[options.find(x=>v202Val(x)===answer)||v202Opt(answer)]}else{for(const item of fallback){if(options.length>=4)break;if(String(item)!==answer&&!options.some(x=>v202Val(x)===String(item)))options.push(v202Opt(item))}}options=shuffle(options,rnd);"
        source = replace_once(source, old, new, "single response fallback")
        old = "if(values.length<2)throw new Error(`Insufficient choices after repair: ${d.slug}`);"
        new = "if(values.length<(singleResponse?1:2))throw new Error(`Insufficient choices after repair: ${d.slug}`);"
        source = replace_once(source, old, new, "single response minimum")

    runtime.write_text(source, encoding="utf-8")

    pages = sorted((site / "cognitive-lab").glob("*/index.html"))
    updated_pages = []
    found = set()
    for page in pages:
        source_page = page.read_text(encoding="utf-8")
        definition = load_definition(source_page)
        slug = str(definition.get("slug") or page.parent.name)
        if slug not in DEFINITION_UPDATES:
            continue
        found.add(slug)
        definition.update(DEFINITION_UPDATES[slug])
        definition["distinctness_version"] = VERSION
        updated = write_definition(source_page, definition)
        if updated != source_page:
            page.write_text(updated, encoding="utf-8")
            updated_pages.append(page.relative_to(site).as_posix())

    missing = sorted(set(DEFINITION_UPDATES) - found)
    report = {
        "version": VERSION,
        "status": "passed" if not missing else "failed",
        "runtime": runtime.relative_to(site).as_posix(),
        "specialized_modes": sorted(DEFINITION_UPDATES),
        "specialized_mode_count": len(DEFINITION_UPDATES),
        "updated_pages": updated_pages,
        "missing_pages": missing,
        "single_response_reaction": "singleResponse:true" in source,
        "sustained_visual_separated": "sustainedTarget:target" in source
        and "visualSearchSetSize:size" in source,
        "category_semantic_separated": "guidedSemanticRetrieval:true" in source,
        "attention_switch_metadata": "switchTrial" in source,
        "span_study_hidden": "spanLength:length" in source
        and "اختر تسلسل الأرقام بالترتيب نفسه" in source,
        "span_unique_tokens": "uniqueStudyTokens:new Set(sequence).size" in source,
    }
    if not all(
        value is True
        for key, value in report.items()
        if key
        in {
            "single_response_reaction",
            "sustained_visual_separated",
            "category_semantic_separated",
            "attention_switch_metadata",
            "span_study_hidden",
            "span_unique_tokens",
        }
    ):
        report["status"] = "failed"
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "cognitive-distinctness-v32.json").write_text(
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
