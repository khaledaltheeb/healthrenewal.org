(()=>{
  'use strict';
  const d=document;
  const match=location.pathname.match(/^\/sectors\/rehabilitation\/patient-guides\/([^/]+)\/?(?:index\.html)?$/);
  if(!match||match[1]==='index.html') return;
  const slug=match[1];

  const pathwayMeta={
    'lower-limb-musculoskeletal':['الطرف السفلي العضلي الهيكلي','/sectors/rehabilitation/outcomes/lower-limb-musculoskeletal/'],
    'upper-limb-hand-function':['وظيفة الطرف العلوي واليد','/sectors/rehabilitation/outcomes/upper-limb-hand-function/'],
    'pain-fatigue-interference':['الألم والتعب وتأثيرهما الوظيفي','/sectors/rehabilitation/outcomes/pain-fatigue-interference/'],
    'sports-return':['العودة للرياضة','/sectors/rehabilitation/outcomes/sports-return/'],
    'older-adults-falls':['كبار السن والسقوط','/sectors/rehabilitation/outcomes/older-adults-falls/'],
    'cardiopulmonary-endurance':['التحمل القلبي الرئوي','/sectors/rehabilitation/outcomes/cardiopulmonary-endurance/'],
    'deconditioning-recovery':['إزالة التكيف واستعادة القدرة','/sectors/rehabilitation/outcomes/deconditioning-recovery/'],
    'neurological-mobility':['الحركة في التأهيل العصبي','/sectors/rehabilitation/outcomes/neurological-mobility/'],
    'cognitive-communication':['الإدراك والتواصل الوظيفي','/sectors/rehabilitation/outcomes/cognitive-communication/'],
    'prosthetic-function':['الوظيفة مع الأطراف الصناعية','/sectors/rehabilitation/outcomes/prosthetic-function/']
  };
  const measureMeta={
    measures:['مكتبة مقاييس التأهيل','/sectors/rehabilitation/measures/'],
    performance:['اختبارات الأداء الوظيفي','/sectors/rehabilitation/measures/performance/'],
    sppb:['SPPB — الأداء البدني القصير','/sectors/rehabilitation/measures/sppb/'],
    'stay-independent':['Stay Independent — فرز مخاطر السقوط','/sectors/rehabilitation/measures/stay-independent/'],
    pdi:['PDI — تداخل الألم مع الوظيفة','/sectors/rehabilitation/measures/pdi/']
  };

  const makeLinks=(ids,meta)=>{
    const box=d.createElement('div');
    box.className='related';
    for(const id of ids||[]){
      const item=meta[id];
      if(!item) continue;
      const a=d.createElement('a');
      a.href=item[1];
      a.textContent=item[0];
      box.append(a);
    }
    return box;
  };

  const boot=async()=>{
    if(d.getElementById('rehab-outcome-followup')) return;
    let registry;
    try{
      const response=await fetch('/assets/rehabilitation/patient-guide-outcome-map-ar.json',{credentials:'same-origin',cache:'force-cache'});
      if(!response.ok) return;
      registry=await response.json();
    }catch(_error){return;}
    const item=registry?.guides?.[slug];
    if(!item) return;

    const main=d.querySelector('main');
    if(!main) return;
    const sections=Array.from(main.querySelectorAll(':scope > section.section'));
    const sources=sections.find((section)=>/^المصادر/.test(section.querySelector('h2')?.textContent?.trim()||''))||sections.at(-1)||null;

    const section=d.createElement('section');
    section.id='rehab-outcome-followup';
    section.className='section';
    section.setAttribute('aria-labelledby','rehab-outcome-followup-title');

    const h2=d.createElement('h2');
    h2.id='rehab-outcome-followup-title';
    h2.textContent='كيف تتابع تقدمك وظيفيًا؟';
    section.append(h2);

    const intro=d.createElement('p');
    intro.textContent='لا تجعل المتابعة رقمًا منفردًا. اربط ما تستطيع فعله فعليًا بالأعراض والسياق، وأعد القياس بالطريقة نفسها قدر الإمكان. المسارات التالية تساعدك على اختيار ما يستحق المتابعة ولا تستبدل التقييم السريري.';
    section.append(intro);

    const grid=d.createElement('div');
    grid.className='grid3';

    const pathCard=d.createElement('article');
    pathCard.className='card';
    const pathTitle=d.createElement('h3');
    pathTitle.textContent='مسار قياس النتيجة';
    pathCard.append(pathTitle,makeLinks(item.pathways,pathwayMeta));

    const measureCard=d.createElement('article');
    measureCard.className='card';
    const measureTitle=d.createElement('h3');
    measureTitle.textContent='مقاييس وأوراق مناسبة';
    measureCard.append(measureTitle,makeLinks(item.measures,measureMeta));

    const trackCard=d.createElement('article');
    trackCard.className='card';
    const trackTitle=d.createElement('h3');
    trackTitle.textContent='ما الذي تسجله؟';
    const trackText=d.createElement('p');
    trackText.textContent=item.track||'حدد هدفًا وظيفيًا مهمًا، وسجّل الأداء والأعراض والسياق ثم أعد القياس في ظروف متشابهة.';
    trackCard.append(trackTitle,trackText);
    grid.append(pathCard,measureCard,trackCard);
    section.append(grid);

    if(item.caution){
      const warning=d.createElement('div');
      warning.className='notice';
      const warningTitle=d.createElement('h3');
      warningTitle.textContent='حد مهم في التفسير';
      const warningText=d.createElement('p');
      warningText.textContent=item.caution;
      warning.append(warningTitle,warningText);
      section.append(warning);
    }

    const footer=d.createElement('p');
    const hub=d.createElement('a');
    hub.href='/sectors/rehabilitation/outcomes/';
    hub.textContent='استعرض جميع مسارات قياس النتائج';
    footer.append(hub,d.createTextNode(' · '));
    const rights=d.createElement('a');
    rights.href='/sectors/rehabilitation/measures/arabic-readiness/';
    rights.textContent='تحقق من جاهزية الأداة والحقوق والترجمة العربية';
    footer.append(rights);
    section.append(footer);

    if(sources&&sources.parentNode===main) main.insertBefore(section,sources);
    else main.append(section);
  };

  if(d.readyState==='loading') d.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();