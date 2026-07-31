(function(){
'use strict';
const data=window.FAMILY_GUIDE_DATA;
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function list(items,ordered=false){const t=ordered?'ol':'ul';return `<${t}>${(items||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</${t}>`;}
function section(id,num,title,body,cls=''){return `<section class="card ${cls}" id="${id}"><p class="kicker">${num}</p><h2>${esc(title)}</h2>${body}</section>`;}
function faqItems(c){
 const signs=Object.values(c.signs||{}).flatMap(v=>(v||[]).slice(0,1)).join(' ');
 return [
  [`ما هو ${c.title}؟`,c.summary],
  [`ما العلامات التي تستحق التقييم في ${c.title}؟`,signs||c.summary],
  [`ما أول خطوات الأسرة عند الاشتباه بـ${c.title}؟`,(c.first_steps||[]).slice(0,3).join(' ')],
  [`ما الذي يجب تجنبه عند التعامل مع ${c.title}؟`,(c.avoid||[]).slice(0,3).join(' ')],
  ['متى نطلب مساعدة عاجلة؟',(c.urgent||[]).join(' ')],
  ['ما الأسئلة التي نطرحها على المختص؟',(c.questions||[]).join(' ')]
 ];
}
function faqSection(c){return `<section class="card intent-faq" id="faq" data-search-intent-faq="v1"><p class="kicker">11</p><h2>أسئلة شائعة عن ${esc(c.title)}</h2>${faqItems(c).map(([q,a])=>`<article class="faq-item"><h3>${esc(q)}</h3><p>${esc(a)}</p></article>`).join('')}</section>`;}
function setStructuredData(c){
 const canonical=document.querySelector('link[rel="canonical"]')?.href||location.href;
 const graph={
  '@context':'https://schema.org',
  '@graph':[
   {'@type':'MedicalWebPage','@id':canonical+'#webpage',name:`دليل الأسرة: ${c.title}`,url:canonical,inLanguage:'ar',description:c.summary,dateModified:data.reviewed_at||undefined,about:{'@type':'MedicalCondition',name:c.title,alternateName:c.en},isPartOf:{'@type':'CollectionPage',name:'دليل الأسرة للرعاية والدعم',url:'https://healthrenewal.org/family-guide/'},breadcrumb:{'@id':canonical+'#breadcrumb'},mainEntity:{'@id':canonical+'#faq'}},
   {'@type':'BreadcrumbList','@id':canonical+'#breadcrumb',itemListElement:[{'@type':'ListItem',position:1,name:'الرئيسية',item:'https://healthrenewal.org/'},{'@type':'ListItem',position:2,name:'دليل الأسرة',item:'https://healthrenewal.org/family-guide/'},{'@type':'ListItem',position:3,name:c.title,item:canonical}]},
   {'@type':'FAQPage','@id':canonical+'#faq',mainEntity:faqItems(c).map(([q,a])=>({'@type':'Question',name:q,acceptedAnswer:{'@type':'Answer',text:a}}))}
  ]
 };
 let script=document.querySelector('script[type="application/ld+json"]');
 if(!script){script=document.createElement('script');script.type='application/ld+json';document.head.appendChild(script);}
 script.textContent=JSON.stringify(graph);
}
function renderCondition(){
 const root=document.getElementById('condition-root'); if(!root||!data)return;
 const slug=document.body.dataset.condition; const c=data.conditions.find(x=>x.slug===slug);
 if(!c){root.innerHTML='<section class="card warning"><h1>الصفحة غير متاحة</h1><p>تعذر العثور على بيانات الحالة.</p></section>';return;}
 document.title=`دليل الأسرة: ${c.title} | ما الحالة وماذا نفعل؟`;
 const signs=Object.entries(c.signs||{}).map(([k,v])=>`<h3>${esc(k)}</h3>${list(v)}`).join('');
 const related=(c.related||[]).map(([n,u])=>`<li><a href="${esc(u)}">${esc(n)}</a></li>`).join('');
 const sources=(c.sources||[]).map(([n,u])=>`<li><a href="${esc(u)}" rel="external noopener noreferrer">${esc(n)}</a></li>`).join('');
 root.innerHTML=`
 <nav class="wrap breadcrumbs" aria-label="مسار التنقل"><a href="../../../">الرئيسية</a> <span aria-hidden="true">/</span> <a href="../../">دليل الأسرة</a> <span aria-hidden="true">/</span> <span aria-current="page">${esc(c.title)}</span></nav>
 <section class="hero"><div class="wrap"><p class="kicker">دليل الأسرة حسب الحالة</p><h1>${esc(c.title)}</h1><p class="lead">${esc(c.summary)}</p><div class="toolbar"><a class="button" href="../../">العودة إلى دليل الأسرة</a><button type="button" onclick="window.print()">طباعة الدليل</button></div><p class="notice"><b>تنبيه:</b> هذه الصفحة تساعد على فهم الخطوات وتنظيم الأسئلة، ولا تثبت التشخيص ولا تحدد علاجًا أو دواءً لشخص بعينه. الأعراض المفاجئة أو الخطر المباشر تستلزم خدمة طبية أو طوارئ مناسبة.</p></div></section>
 <div class="wrap layout"><aside class="toc"><h2>المحتويات</h2>${[['summary','الملخص'],['signs','العلامات'],['causes','الأسباب'],['related','الأقسام المرتبطة'],['first','ماذا نفعل أولًا؟'],['avoid','ما الذي نتجنبه؟'],['daily','التعامل اليومي'],['plan','الخطة الزمنية'],['team','الفريق والأسئلة'],['faq','الأسئلة الشائعة'],['urgent','علامات عاجلة'],['sources','المراجع']].map(([i,t])=>`<a href="#${i}">${t}</a>`).join('')}</aside><article class="stack">
 ${section('summary','1','ما الحالة؟',`<p><span class="tag">${esc(c.classification)}</span></p><p>${esc(c.summary)}</p><div class="summary-grid"><div><b>الهدف الأول</b><p>فهم أثر الحالة في الشخص نفسه، لا الاكتفاء باسم التشخيص.</p></div><div><b>القاعدة</b><p>ابدأ بالأمان والتواصل والصحة والمشاركة ثم رتّب بقية الأهداف.</p></div><div><b>القياس</b><p>حدد خط أساس، هدفًا وظيفيًا، مدة تجربة، ومراجعة مكتوبة.</p></div></div>`)}
 ${section('signs','2','العلامات والأعراض المحتملة',signs)}
 ${section('causes','3','الأسباب وما نعرفه علميًا',list(c.causes))}
 ${section('related','4','الأقسام ذات الصلة المباشرة',`<ul>${related}</ul><p class="small">وجود رابط لحالة مصاحبة لا يعني أنها موجودة لدى كل شخص؛ كل مجال يحتاج تقييمًا مستقلًا عند ظهور مؤشرات.</p>`)}
 ${section('first','5','ماذا تفعل الأسرة أولًا؟',list(c.first_steps,true),'good')}
 ${section('avoid','6','ما الذي يجب تجنبه؟',list(c.avoid),'warning')}
 ${section('daily','7','كيف نتصرف في الحياة اليومية؟',list(c.daily))}
 ${section('plan','8','أفضل خطة عملية زمنية',`<div class="columns"><div><h3>أول 30 يومًا</h3>${list(c.plan30)}</div><div><h3>خلال 90 يومًا</h3>${list(c.plan90)}</div></div><h3>خلال عام</h3>${list(c.plan_year)}`,'rights')}
 ${section('team','9','الفريق والأسئلة التي تطرح عليه',`<div class="columns"><div><h3>اختصاصات قد تدخل في الخطة</h3>${list(c.professionals)}</div><div><h3>أسئلة للمختص</h3>${list(c.questions)}</div></div>`)}
 ${faqSection(c)}
 ${section('urgent','12','متى نطلب مساعدة عاجلة؟',list(c.urgent),'warning')}
 <section class="source-box" id="sources"><h2>المراجع الأساسية</h2><ul>${sources}</ul><p class="small">آخر مراجعة تحريرية: ${esc(data.reviewed_at)}. تُراجع التوصيات عند تحديث المصدر أو تغير الإرشادات.</p></section>
 </article></div>`;
 root.setAttribute('aria-busy','false');
 setStructuredData(c);
}
function renderIndex(){
 const root=document.getElementById('conditions-grid'); if(!root||!data)return;
 function card(c){return `<article class="condition-card" data-search="${esc((c.title+' '+c.en+' '+c.classification).toLowerCase())}"><span class="tag">${esc(c.classification)}</span><h3>${esc(c.title)}</h3><p>${esc(c.summary)}</p><a class="button" href="conditions/${esc(c.slug)}/">فتح الدليل</a></article>`;}
 root.innerHTML=data.conditions.map(card).join('');
 const input=document.getElementById('condition-search'); const empty=document.getElementById('empty-state');
 if(input) input.addEventListener('input',()=>{const q=input.value.trim().toLowerCase();let visible=0;root.querySelectorAll('[data-search]').forEach(el=>{const show=!q||el.dataset.search.includes(q);el.hidden=!show;if(show)visible++;});if(empty)empty.style.display=visible?'none':'block';});
}
document.addEventListener('DOMContentLoaded',()=>{renderIndex();renderCondition();});
})();
