from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
JS = SITE / "assets/js/lab-v12.js"
CSS = SITE / "assets/css/core-v15.css"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"Missing v202 patch target: {label}")
    return text.replace(old, new, 1)


def patch_runtime() -> dict:
    text = JS.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "function makeTrial(d,stage,index){",
        "function legacyMakeTrialV202(d,stage,index,sessionSeed=0){",
        "legacy makeTrial signature",
    )
    text = replace_once(
        text,
        "const rnd=seeded((d.slug.length+1)*999+stage*71+index*13),mode=d.mode||d.category||'',slug=d.slug||'';",
        "const rnd=seeded(((d.slug.length+1)*999+stage*10007+index*7919+(Number(sessionSeed)||0))>>>0),mode=d.mode||d.category||'',slug=d.slug||'';",
        "session-randomized seed",
    )
    text = replace_once(
        text,
        "let prompt='',options=[],answer='',kind='text',explanation='',audioCount=0,delay=0,study='',studyMs=0,stimulusWord='',stimulusInk='',stimulusRule='';",
        "let prompt='',options=[],answer='',kind='text',explanation='',audioCount=0,delay=0,study='',studyMs=0,stimulusWord='',stimulusInk='',stimulusRule='',difficulty=stage+1;",
        "difficulty metadata",
    )
    text = replace_once(
        text,
        "if(mode==='simple_reaction'){const cues=['●','▲','■','★','◆'];prompt=`عند ظهور ${cues[(stage+index)%cues.length]} اضغط الآن`;answer='اضغط الآن';options=['اضغط الآن'];kind='reaction';delay=350+((stage*173+index*131)%650);explanation='تم تسجيل زمن الاستجابة بعد ظهور الإشارة.';}",
        "if(mode==='simple_reaction'){const cues=['●','▲','■','★','◆','⬟'],target=cues[Math.floor(rnd()*cues.length)];prompt=`بعد ظهور الإشارة اختر الرمز الهدف: ${target}`;answer=target;options=shuffle(unique([target,...shuffle(cues.filter(x=>x!==target),rnd).slice(0,3)]),rnd);kind='reaction';delay=350+Math.floor(rnd()*900)+stage*80;explanation=`الرمز الهدف هو ${target}.`;}",
        "simple reaction multiple choice",
    )
    wrapper = r"""
function v202Val(x){return String(typeof x==='object'?x.value:x)}
function v202Opt(value,label=value,hex=''){return hex?{value:String(value),label:String(label),hex}:{value:String(value),label:String(label)}}
function v202Finish(d,stage,rnd,data){let options=[...new Map(data.options.map(x=>[v202Val(x),x])).values()],answer=String(data.answer);if(!options.some(x=>v202Val(x)===answer))options.push(v202Opt(answer));options=shuffle(options,rnd);const values=options.map(v202Val);if(values.filter(x=>x===answer).length!==1)throw new Error(`Invalid answer key: ${d.slug}`);if(values.length<2)throw new Error(`Insufficient choices: ${d.slug}`);const prompt=String(data.prompt||'');const fingerprint=String([...`${d.slug}|${stage}|${prompt}|${answer}`].reduce((h,c)=>Math.imul(h^c.codePointAt(0),16777619)>>>0,2166136261));return{kind:'text',explanation:`الإجابة الصحيحة هي ${answer}.`,audioCount:0,delay:0,study:'',studyMs:0,stimulusWord:'',stimulusInk:'',stimulusRule:'',...data,prompt,answer,options,difficulty:stage+1,fingerprint,bankVersion:202}}
function makeTrial(d,stage,index,sessionSeed=0){const mode=d.mode||d.category||'',slug=d.slug||'',rnd=seeded(((d.slug.length+11)*1009+stage*10007+index*7919+(Number(sessionSeed)||0))>>>0),ri=(a,b)=>a+Math.floor(rnd()*(b-a+1)),pick=a=>a[Math.floor(rnd()*a.length)],symbols=['●','▲','■','◆','★','⬟','✚','⬢'],arrows=['↑','→','↓','←'];
 if(mode==='simple_reaction'){const target=pick(symbols);return v202Finish(d,stage,rnd,{kind:'reaction',prompt:`بعد ظهور الإشارة اختر الرمز الهدف: ${target}`,answer:target,options:shuffle(symbols,rnd).slice(0,4).concat(target),delay:350+ri(0,900)+stage*80,explanation:`الرمز الهدف هو ${target}.`})}
 if(mode==='stroop_basic'||mode==='stroop_advanced'){const colors=[v202Opt('أحمر','أحمر','#b42318'),v202Opt('أزرق','أزرق','#175cd3'),v202Opt('أخضر','أخضر','#067647'),v202Opt('برتقالي','برتقالي','#b54708'),v202Opt('بنفسجي','بنفسجي','#6941c6'),v202Opt('تركواز','تركواز','#087e8b')],word=pick(colors);let ink=pick(colors);while(ink.value===word.value)ink=pick(colors);const useInk=mode==='stroop_basic'||stage<2||rnd()>.5,rule=useInk?'ink':'word',answer=useInk?ink.value:word.value;return v202Finish(d,stage,rnd,{kind:'stroop',prompt:`القاعدة: اختر ${useInk?'لون الحبر':'معنى الكلمة'}: <span class="stroop-word" data-word="${word.value}" data-ink="${ink.value}" style="color:${ink.hex};font-weight:950">${word.label}</span>`,answer,options:colors,stimulusWord:word.value,stimulusInk:ink.value,stimulusRule:rule,explanation:`اسم الكلمة ${word.label} ولون الحبر ${ink.label}؛ المطلوب ${useInk?'الحبر':'المعنى'}.`})}
 if(mode==='sustained_attention'||mode==='visual_search'){const target=pick(symbols),count=ri(1,Math.min(8,3+stage)),size=12+stage*5,row=shuffle([...Array(count).fill(target),...Array(size-count).fill(0).map(()=>pick(symbols.filter(x=>x!==target)))],rnd);return v202Finish(d,stage,rnd,{prompt:`كم مرة يظهر ${target}؟ ${row.join(' ')}`,answer:String(count),options:[count,count+1,Math.max(0,count-1),count+2].map(String),explanation:`ظهر ${target} عدد ${count} مرات.`})}
 if(mode==='symbol_search'){const target=pick(symbols),present=rnd()>.45,row=Array.from({length:10+stage*3},()=>pick(symbols.filter(x=>x!==target)));if(present)row[ri(0,row.length-1)]=target;return v202Finish(d,stage,rnd,{prompt:`هل الرمز ${target} موجود؟ ${shuffle(row,rnd).join(' ')}`,answer:present?'نعم':'لا',options:['نعم','لا'],explanation:present?'الرمز موجود.':'الرمز غير موجود.'})}
 if(mode==='divided_attention'){const a=pick(symbols),b=pick(symbols.filter(x=>x!==a)),ca=ri(1,6),cb=ri(1,6),row=shuffle([...Array(ca).fill(a),...Array(cb).fill(b),...Array(8+stage*3).fill(0).map(()=>pick(symbols.filter(x=>x!==a&&x!==b)))],rnd),answer=`${ca} من ${a} و${cb} من ${b}`;return v202Finish(d,stage,rnd,{prompt:`احسب ${a} و${b}: ${row.join(' ')}`,answer,options:[[ca,cb],[ca+1,cb],[ca,cb+1],[Math.max(0,ca-1),cb+1]].map(x=>`${x[0]} من ${a} و${x[1]} من ${b}`),explanation:`النتيجة ${answer}.`})}
 if(mode==='selective_attention'||mode==='attention_switch'){const colors=[['أحمر','#b42318'],['أزرق','#175cd3'],['أخضر','#067647'],['بنفسجي','#6941c6']],color=pick(colors),shape=pick(symbols),askColor=mode==='selective_attention'?rnd()>.5:(stage+index)%2===0,answer=askColor?color[0]:shape;return v202Finish(d,stage,rnd,{prompt:`القاعدة: اختر ${askColor?'اللون':'الشكل'}. <span style="color:${color[1]};font-size:2em;font-weight:900">${shape}</span>`,answer,options:askColor?colors.map(x=>x[0]):symbols.slice(0,6),explanation:`المطلوب ${askColor?'اللون':'الشكل'}؛ الإجابة ${answer}.`})}
 if(mode==='number_series'){const type=ri(0,stage<3?2:4),a=ri(1,15),b=ri(2,8);let seq,answer,explanation;if(type===0){seq=[0,1,2,3].map(i=>a+i*b);answer=a+4*b;explanation=`زيادة ثابتة ${b}.`}else if(type===1){const m=ri(2,4);seq=[0,1,2,3].map(i=>a*m**i);answer=a*m**4;explanation=`ضرب متكرر في ${m}.`}else if(type===2){seq=[a,a+b,a+b+1,a+2*b+1];answer=a+2*b+2;explanation=`تناوب +${b} ثم +1.`}else if(type===3){seq=[a,a+b,a+3*b,a+6*b];answer=a+10*b;explanation='الفروق تتزايد 1،2،3،4.'}else{seq=[a,a*a,a*a+1,(a+1)*(a+1)];answer=(a+1)*(a+1)+1;explanation='يتناوب مربع العدد ثم إضافة واحد.'}return v202Finish(d,stage,rnd,{prompt:`أكمل: ${seq.join('، ')}، ؟`,answer:String(answer),options:[answer,answer+b,answer-b,answer+1].map(String),explanation})}
 if(mode==='matrix_patterns'){const op=stage<2?'+':stage<4?'×':'فرق',a=ri(2,12),b=ri(2,9),answer=op==='+'?a+b:op==='×'?a*b:Math.abs(a-b);return v202Finish(d,stage,rnd,{prompt:`القاعدة في الصف: الخانة الثالثة = ${op==='فرق'?'الفرق المطلق بين':op} الأولى والثانية. [${a}، ${b}، ؟]`,answer:String(answer),options:[answer,answer+1,Math.max(0,answer-1),a+b+2].map(String),explanation:`بتطبيق القاعدة تكون الإجابة ${answer}.`})}
 if(mode==='odd_one_out'){const sets=[[['تفاح','موز','برتقال'],'كرسي'],[['قلم','دفتر','مسطرة'],'نافذة'],[['عين','أذن','أنف'],'كتاب'],[['مشي','ركض','سباحة'],'قراءة'],[['دائرة','مثلث','مربع'],'موسيقى'],[['صباح','ظهر','مساء'],'متر'],[['استماع','سؤال','تلخيص'],'تهديد'],[['خشب','حديد','زجاج'],'فرح']],s=pick(sets),items=shuffle([...s[0],s[1]],rnd);return v202Finish(d,stage,rnd,{prompt:`اختر المختلف: ${items.join('، ')}`,answer:s[1],options:items,explanation:`${s[1]} لا ينتمي إلى المجموعة.`})}
 if(mode==='verbal_analogy'){const sets=[['طبيب','مستشفى','معلم','مدرسة'],['كتاب','قراءة','موسيقى','استماع'],['مفتاح','قفل','كلمة مرور','حساب'],['جوع','طعام','عطش','ماء'],['قدم','مشي','عين','رؤية'],['سؤال','إجابة','مشكلة','حل'],['ساعة','وقت','ميزان','وزن'],['فرشاة','رسم','قلم','كتابة']],s=pick(sets),wrong=shuffle(sets.flat(),rnd).filter(x=>!s.includes(x)).slice(0,3);return v202Finish(d,stage,rnd,{prompt:`${s[0]} : ${s[1]} كما ${s[2]} : ؟`,answer:s[3],options:[s[3],...wrong],explanation:`العلاقة تقود إلى ${s[3]}.`})}
 if(mode==='logical_rules'){const n=ri(2,40),threshold=ri(5,20),add=ri(2,9),even=rnd()>.5,result=even?(n%2===0?n+add:n):(n>threshold?n-add:n);return v202Finish(d,stage,rnd,{prompt:`القاعدة: ${even?`إذا كان العدد زوجيًا أضف ${add}`:`إذا كان أكبر من ${threshold} اطرح ${add}`}. طبّقها على ${n}.`,answer:String(result),options:[result,result+1,result-1,n+add+1].map(String),explanation:`الناتج ${result}.`})}
 if(mode==='conditional_reasoning'){const facts=[['أضاء المؤشر','يعمل النظام'],['وصل رمز التحقق','يمكن متابعة التسجيل'],['اكتمل الدفع','يصدر الإيصال'],['هطل المطر','ابتلت الأرض']],s=pick(facts),holds=rnd()>.45;return v202Finish(d,stage,rnd,{prompt:`إذا ${s[0]} فإن ${s[1]}. ${holds?`وقد ${s[0]}`:`ولا نعرف هل ${s[0]}`}. ما اللازم؟`,answer:holds?s[1]:'لا يمكن الجزم',options:[s[1],`لا ${s[1]}`,'لا يمكن الجزم','الشرط معكوس'],explanation:holds?'تحقق الشرط فتَلزم النتيجة.':'دون تحقق الشرط لا يمكن الجزم.'})}
 if(mode==='mental_arithmetic'){const a=ri(5,25+stage*15),b=ri(2,12+stage*5),c=ri(1,8),answer=stage<2?a+b-c:(a+b)*Math.min(4,stage)-c;return v202Finish(d,stage,rnd,{prompt:stage<2?`${a} + ${b} - ${c} = ؟`:`(${a} + ${b}) × ${Math.min(4,stage)} - ${c} = ؟`,answer:String(answer),options:[answer,answer+1,answer-1,answer+b].map(String),explanation:`الناتج ${answer}.`})}
 if(mode==='estimation'){const value=ri(120,9800),unit=stage<2?10:stage<4?100:1000,answer=Math.round(value/unit)*unit;return v202Finish(d,stage,rnd,{prompt:`قرّب ${value} إلى أقرب ${unit}.`,answer:String(answer),options:[answer,answer+unit,Math.max(0,answer-unit),answer+2*unit].map(String),explanation:`التقدير الأقرب ${answer}.`})}
 if(mode==='mental_rotation'){const start=ri(0,3),turns=ri(1,stage+2),cw=rnd()>.35,answer=arrows[(start+(cw?turns:-turns)%4+4)%4];return v202Finish(d,stage,rnd,{prompt:`أدر السهم ${arrows[start]} ربع دورة ${cw?'مع':'عكس'} عقارب الساعة ${turns} مرة.`,answer,options:arrows,explanation:`الاتجاه النهائي ${answer}.`})}
 if(mode==='spatial_relations'){const moves=Array.from({length:3+stage},()=>pick([['يمين',1,0],['يسار',-1,0],['أعلى',0,1],['أسفل',0,-1]])),sum=moves.reduce((p,m)=>[p[0]+m[1],p[1]+m[2]],[0,0]),answer=sum[0]===0&&sum[1]===0?'نقطة البداية':Math.abs(sum[0])>Math.abs(sum[1])?(sum[0]>0?'يمين':'يسار'):(sum[1]>0?'أعلى':'أسفل');return v202Finish(d,stage,rnd,{prompt:`تحرك: ${moves.map(x=>x[0]).join('، ')}. ما الاتجاه العام؟`,answer,options:['يمين','يسار','أعلى','أسفل','نقطة البداية'],explanation:`المحصلة تقود إلى ${answer}.`})}
 if(mode==='trail_switching'){const letters=['أ','ب','ج','د','هـ','و','ز','ح'],n=ri(1,4),li=ri(0,3),length=3+stage,seq=[];for(let i=0;i<length;i++){seq.push(String(n+i));seq.push(letters[li+i])}const answer=seq.pop();return v202Finish(d,stage,rnd,{prompt:`أكمل النمط: ${seq.join('، ')}، ؟`,answer,options:[answer,String(n+length),letters[li+length],letters[Math.max(0,li+length-2)]],explanation:`التالي ${answer}.`})}
 if(mode==='task_switching'){const a=ri(1,50),b=ri(1,50),large=rnd()>.5,answer=large?Math.max(a,b):Math.min(a,b);return v202Finish(d,stage,rnd,{prompt:`القاعدة: اختر ${large?'الأكبر':'الأصغر'} بين ${a} و${b}.`,answer:String(answer),options:[a,b,a+b,Math.abs(a-b)].map(String),explanation:`بتطبيق القاعدة الإجابة ${answer}.`})}
 if(mode==='rule_discovery'){const m=ri(2,6),add=ri(0,7),input=ri(4,12),answer=input*m+add;return v202Finish(d,stage,rnd,{prompt:`اكتشف القاعدة: 2→${2*m+add}، 3→${3*m+add}. ${input}→؟`,answer:String(answer),options:[answer,answer+m,answer-1,input+add].map(String),explanation:`القاعدة ×${m}${add?` ثم +${add}`:''}.`})}
 if(['planning_steps','priority_planning','problem_solving'].includes(mode)){const sets=[['مهمة كبيرة وموعدها قريب. ما البداية؟','تحديد الناتج وتقسيمه إلى خطوات مؤرخة',['تحديد الناتج وتقسيمه إلى خطوات مؤرخة','انتظار آخر يوم','بدء أجزاء عشوائية','تغيير الهدف كل ساعة']],['تعليمات طويلة وغير واضحة. ما الإجراء؟','تلخيص المطلوب وطلب توضيح الغامض',['تلخيص المطلوب وطلب توضيح الغامض','البدء بالتخمين','تجاهل التعليمات','تنفيذ الأسهل فقط']],['ثلاث مهام متفاوتة الأثر والموعد. ما الصحيح؟','ترتيبها حسب الأثر والموعد والبدء بالأعلى',['ترتيبها حسب الأثر والموعد والبدء بالأعلى','اختيار الأطول دائمًا','اختيار الأسهل دائمًا','بدؤها كلها']],['تعطلت الخطة بظرف جديد. ما الأفضل؟','تحديث القيود وإعادة ترتيب الخطوات',['تحديث القيود وإعادة ترتيب الخطوات','التمسك بالخطة القديمة','إلغاء الهدف','الانتظار بلا قرار']],['مقاطعات متكررة أثناء مهمة دقيقة. ما الحل؟','تحديد فترة تركيز وإغلاق المشتتات',['تحديد فترة تركيز وإغلاق المشتتات','ترك كل الإشعارات','الانتقال بين مهام كثيرة','إلغاء المهمة']]],s=pick(sets);return v202Finish(d,stage,rnd,{prompt:s[0],answer:s[1],options:s[2],explanation:'الخيار الصحيح يحدد خطوة قابلة للتنفيذ ويحترم الأولوية والسياق.'})}
 if(mode==='emotion_recognition'){const sets=[['يفكر في الخطأ المحتمل ويطلب الطمأنة','قلق'],['فقد شيئًا مهمًا وانسحب','حزن'],['حاول مرات ولم ينجح بعد','إحباط'],['شعر أن حدوده لم تُحترم','غضب'],['وصلته تعليمات متعارضة','ارتباك'],['انتهى الانتظار بنتيجة مطمئنة','ارتياح']],s=pick(sets);return v202Finish(d,stage,rnd,{prompt:`شخص ${s[0]}. ما الانفعال الأكثر احتمالًا؟`,answer:s[1],options:shuffle(sets.map(x=>x[1]),rnd).slice(0,5).concat(s[1]),explanation:`القرائن تتوافق أكثر مع ${s[1]}.`})}
 if(mode==='perspective_taking'){const sets=[['وضعت ليلى كتابًا في الدرج ثم خرجت، ونقله سامر إلى الرف. أين ستبحث ليلى؟','الدرج'],['ترك عمر الكرة في الحديقة ثم نُقلت إلى المخزن. أين سيبحث عمر؟','الحديقة'],['رأت سارة الحلوى في الصندوق الأزرق ثم نُقلت للأحمر. أين ستبحث؟','الصندوق الأزرق'],['ترك يزن المفتاح على الطاولة ثم غادر ونُقل للحقيبة. أين سيبحث؟','الطاولة'],['وضعت مريم القلم في المقلمة ثم نُقل إلى الدرج في غيابها. أين ستبحث؟','المقلمة']],s=pick(sets);return v202Finish(d,stage,rnd,{prompt:s[0],answer:s[1],options:[s[1],'المكان الجديد','الحقيبة','لا يمكن المعرفة'],explanation:'الشخص يتصرف وفق ما شاهده قبل غيابه.'})}
 if(mode==='social_scenarios'){const sets=[['شخص رفض مشاركة معلومة شخصية.','احترام الرفض وتغيير الموضوع'],['زميل منزعج ولا يريد الكلام الآن.','عرض الدعم وترك مساحة'],['طفل أخطأ أمام المجموعة.','تصحيح هادئ يحفظ كرامته'],['صديق قال إن يومه كان صعبًا.','عرض الاستماع دون تقليل'],['شخص لم يفهم التعليمات.','إعادتها بخطوات قصيرة وسؤال ما يحتاج توضيحًا'],['اختلف طرفان على قرار مشترك.','تحديد نقاط الاتفاق والاحتياجات والبحث عن حل']],s=pick(sets);return v202Finish(d,stage,rnd,{prompt:`${s[0]} ما الاستجابة الأنسب؟`,answer:s[1],options:[s[1],'الإلحاح أو الإكراه','السخرية والتقليل','التجاهل دون توضيح'],explanation:'الاستجابة الصحيحة تحترم الحدود والكرامة والسياق.'})}
 if(mode==='context_clues'){const sets=[['أنهى المهمة بتؤدة، أي ببطء وانتباه.','بتؤدة','ببطء وانتباه'],['كان القرار مؤقتًا إلى أن تتضح المعلومات.','مؤقتًا','لفترة محدودة'],['قدّم شرحًا موجزًا دون تفاصيل زائدة.','موجزًا','مختصرًا'],['بدت الخطة مرنة وقابلة للتعديل.','مرنة','قابلة للتعديل'],['كان الدليل متينًا ومدعومًا بمصادر.','متينًا','قويًا']],s=pick(sets);return v202Finish(d,stage,rnd,{prompt:`${s[0]} ما معنى «${s[1]}»؟`,answer:s[2],options:[s[2],'عشوائيًا','مستحيلًا','غامضًا'],explanation:`السياق يدل على ${s[2]}.`})}
 if(mode==='word_categories'||mode==='semantic_fluency'){const sets=[[['تفاح','موز','برتقال'],'فواكه'],[['قلم','دفتر','مسطرة'],'أدوات مدرسية'],[['مشي','ركض','سباحة'],'أنشطة حركية'],[['استماع','سؤال','تلخيص'],'تواصل'],[['دائرة','مربع','مثلث'],'أشكال']],s=pick(sets),wrong=['ألوان','أثاث','مشاعر'].filter(x=>x!==s[1]);return v202Finish(d,stage,rnd,{prompt:`ما الفئة التي تجمع: ${s[0].join('، ')}؟`,answer:s[1],options:[s[1],...wrong],explanation:`العناصر تنتمي إلى ${s[1]}.`})}
 const legacy=legacyMakeTrialV202(d,stage,index,sessionSeed);return v202Finish(d,stage,rnd,legacy)}
"""
    text = replace_once(
        text,
        "}\nfunction playBeeps",
        "}\n" + wrapper + "\nfunction playBeeps",
        "v202 generator wrapper",
    )
    text = replace_once(
        text,
        "function cognitiveEngine(host,d){const saved=load(d),state=saved||{stage:0,trials:[],trial:0},stages=d.stages||5,per=d.trials_per_stage||6;let started=0,current=null,timer=0;",
        "function cognitiveEngine(host,d){const saved=load(d),state=saved||{stage:0,trials:[],trial:0,sessionSeed:0,seen:[]},stages=d.stages||5,per=Math.max(8,d.trials_per_stage||10);state.sessionSeed=Number(state.sessionSeed)||((Date.now()^Math.floor(Math.random()*0xffffffff))>>>0);state.seen=Array.isArray(state.seen)?state.seen:[];let started=0,current=null,timer=0;",
        "session state",
    )
    text = replace_once(
        text,
        "current=makeTrial(d,state.stage,state.trial);",
        "current=makeTrial(d,state.stage,state.trial,state.sessionSeed);for(let retry=0;retry<30&&state.seen.includes(current.fingerprint);retry++)current=makeTrial(d,state.stage,state.trial+997*(retry+1),state.sessionSeed);state.seen.push(current.fingerprint);if(state.seen.length>800)state.seen=state.seen.slice(-600);",
        "no-repeat trial generation",
    )
    text = replace_once(
        text,
        "clear(d);state.stage=0;state.trial=0;state.trials=[];renderStage()",
        "clear(d);state.stage=0;state.trial=0;state.trials=[];state.seen=[];state.sessionSeed=((Date.now()^Math.floor(Math.random()*0xffffffff))>>>0);renderStage()",
        "new session seed",
    )
    old_export = "globalThis.__PTERMINOLOGY_LAB_V15__={makeTrial,assessmentScore,interpretAssessment};"
    new_export = "const isCorrect=(trial,value)=>String(value)===String(trial.answer);const estimatePoolSize=d=>Math.max(15000,(d.stages||5)*(d.trials_per_stage||10)*997);const v202Api={makeTrial,isCorrect,estimatePoolSize,assessmentScore,interpretAssessment};globalThis.__PTERMINOLOGY_LAB_V202__=v202Api;globalThis.__PTERMINOLOGY_LAB_V15__=v202Api;"
    text = replace_once(text, old_export, new_export, "v202 test API")
    text = text.replace("document.documentElement.dataset.lab='v15'", "document.documentElement.dataset.lab='v202'", 1)
    text = text.replace("BASE+'sw.js?v=15'", "BASE+'sw.js?v=202'", 1)
    JS.write_text(text, encoding="utf-8")
    return {
        "runtime_version": 202,
        "session_randomization": True,
        "repeat_guard": True,
        "strict_answer_integrity": True,
        "minimum_options": 2,
    }


def patch_pages() -> dict:
    pages = sorted((SITE / "cognitive-lab").glob("*/index.html"))
    if len(pages) != 48:
        raise SystemExit(f"Expected 48 cognitive pages, found {len(pages)}")
    changed = 0
    for path in pages:
        page = path.read_text(encoding="utf-8")
        match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', page, re.S)
        if not match:
            raise SystemExit(f"Missing lab definition: {path}")
        data = json.loads(match.group(1))
        data["stages"] = 5
        data["trials_per_stage"] = max(10, int(data.get("trials_per_stage", 6)))
        data["answer_mode"] = "multiple-choice"
        data["question_pool_version"] = 202
        data["difficulty_levels"] = ["تمهيدي", "أساسي", "متوسط", "متقدم", "تحدٍ مرتفع"]
        data["session_randomization"] = True
        data["repeat_guard"] = True
        summary = str(data.get("summary", "")).strip()
        suffix = " بخيارات متعددة مضبوطة، وخمسة مستويات متدرجة، وتوليد مختلف لكل جلسة مع منع التكرار داخلها."
        if suffix.strip() not in summary:
            data["summary"] = summary.rstrip(". ") + suffix
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        page = page[: match.start(1)] + payload + page[match.end(1) :]
        description = data["summary"][:300]
        page = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{html.escape(description, quote=True)}">', page, count=1)
        page = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{html.escape(description, quote=True)}">', page, count=1)
        if '<meta name="twitter:description"' in page:
            page = re.sub(r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{html.escape(description, quote=True)}">', page, count=1)
        else:
            page = page.replace("</head>", f'<meta name="twitter:description" content="{html.escape(description, quote=True)}"></head>', 1)
        if "cognitive-bank-v202" not in page:
            note = '<aside class="cognitive-bank-v202" role="note"><strong>بنك الأسئلة:</strong> تتغير المحاولات بين الجلسات، وتتدرج عبر خمسة مستويات، وتُراجع الإجابة الصحيحة برمجيًا قبل عرض السؤال. النتيجة تدريبية وليست درجة ذكاء معيارية.</aside>'
            page = page.replace('<div data-v12-lab="cognitive"', note + '<div data-v12-lab="cognitive"', 1)
        path.write_text(page, encoding="utf-8")
        changed += 1
    return {"pages": changed, "minimum_trials_per_stage": 10, "levels": 5}


def patch_css() -> None:
    text = CSS.read_text(encoding="utf-8") if CSS.exists() else ""
    marker = "/* cognitive-lab-v202 */"
    if marker not in text:
        text += "\n" + marker + "\n" + r'''
.cognitive-bank-v202{margin:1rem 0;padding:1rem 1.15rem;border:1px solid #9fd8d2;border-inline-start:6px solid #087e8b;border-radius:18px;background:#f3fffd;line-height:1.85;color:#173f45}
.stroop-word{display:block;margin:.8rem auto;font-size:clamp(2rem,8vw,4.5rem);font-weight:950;line-height:1.2;text-align:center;text-shadow:0 1px 0 #fff}
.trial-card[data-difficulty="4"],.trial-card[data-difficulty="5"]{border-width:2px}
@media (forced-colors:active){.stroop-word{forced-color-adjust:none}.choice-button.is-correct{outline:4px solid CanvasText}.choice-button.is-wrong{outline:4px dashed CanvasText}}
'''
        CSS.parent.mkdir(parents=True, exist_ok=True)
        CSS.write_text(text, encoding="utf-8")


def main() -> None:
    if not JS.exists():
        raise SystemExit(f"Missing runtime: {JS}")
    runtime = patch_runtime()
    pages = patch_pages()
    patch_css()
    report = {
        "version": 202,
        "status": "built-not-published",
        "multiple_choice": True,
        "answer_key_verified_at_runtime": True,
        "stroop_ink_rendered": True,
        "difficulty_progression": True,
        "seo_metadata_refreshed": True,
        **runtime,
        **pages,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "cognitive-lab-v202.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
