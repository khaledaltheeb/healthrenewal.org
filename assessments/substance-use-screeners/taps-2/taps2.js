(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
function wireA11y(){
  $$('.taps-domain').forEach(section=>{
    $$('input[type="radio"]',section).forEach(input=>{
      const row=input.closest('.form-row');
      const item=(row?.querySelector('div')?.textContent||'سؤال TAPS').trim();
      input.setAttribute('aria-label',`${item} — ${input.value==='yes'?'نعم':'لا'}`);
    });
  });
}
function scoreSection(section){
  const groups=[...new Set($$('input[type="radio"]',section).map(x=>x.name))];
  const vals=groups.map(name=>$(`input[name="${name}"]:checked`,section)?.value??null);
  const scoreEl=$('[data-score]',section),note=$('[data-note]',section),max=Number(section.dataset.max||groups.length);
  if(vals.some(v=>v===null)){scoreEl.textContent=`— / ${max}`;note.textContent=`أُجيب عن ${vals.filter(v=>v!==null).length}/${groups.length} أسئلة. لا تعتمد الدرجة قبل الإكمال.`;return null}
  const total=vals.filter(v=>v==='yes').length;
  scoreEl.textContent=`${total} / ${max}`;
  note.textContent=total===0?'لا توجد إجابة إيجابية في هذا المجال.':total===1?'درجة 1: إشارة خطر/استخدام مشكل محتملة؛ فسّرها حسب المادة والسياق.':`درجة ${total}: ارتفاع عدد المؤشرات يستدعي تقييمًا إضافيًا؛ لا يمثل تشخيصًا تلقائيًا.`;
  return total;
}
function syncDomains(){
  const active=new Set($$('#domain-select input:checked').map(x=>x.value));
  $$('.taps-domain').forEach(section=>{section.hidden=!active.has(section.dataset.domain);if(!section.hidden)scoreSection(section)});
  $('#taps2-live').textContent=active.size?`تم اختيار ${active.size} مجال/مجالات للمتابعة.`:'لم يتم اختيار أي مجال بعد.';
}
$$('#domain-select input[type="checkbox"]').forEach(el=>el.addEventListener('change',syncDomains));
$$('#taps2-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',()=>{const section=el.closest('.taps-domain');if(section)scoreSection(section)}));
$('#taps2-clear')?.addEventListener('click',()=>{$$('#taps2-sheet input').forEach(el=>{if(el.type==='radio'||el.type==='checkbox')el.checked=false;else el.value=''});$$('#taps2-sheet textarea').forEach(el=>el.value='');$$('#domain-select input').forEach(el=>el.checked=false);$$('.taps-domain').forEach(section=>{section.hidden=true;const score=$('[data-score]',section),note=$('[data-note]',section);if(score)score.textContent=`— / ${section.dataset.max}`;if(note)note.textContent=''});syncDomains()});
$('#taps2-print')?.addEventListener('click',()=>window.print());
wireA11y();syncDomains();
})();