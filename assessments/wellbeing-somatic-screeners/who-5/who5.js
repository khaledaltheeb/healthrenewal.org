(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const labels={5:'طوال الوقت',4:'معظم الوقت',3:'أكثر من نصف الوقت',2:'أقل من نصف الوقت',1:'بعض الوقت',0:'في أي وقت من الأوقات: لا'};
function wireA11y(){
  $$('#who5-sheet tbody tr').forEach((row,i)=>{
    const item=(row.querySelector('td')?.textContent||`البند ${i+1}`).trim();
    $$('input[type="radio"]',row).forEach(input=>input.setAttribute('aria-label',`${item} — ${labels[input.value]||input.value}`));
  });
}
function selected(n){const el=$(`input[name="w${n}"]:checked`);return el?Number(el.value):null}
function calc(){
  const vals=[1,2,3,4,5].map(selected), answered=vals.filter(v=>v!==null).length;
  if(answered<5){
    $('#who5-raw').textContent='— / 25';
    $('#who5-pct').textContent='— / 100';
    $('#who5-status').textContent=`أُجيب عن ${answered}/5 بنود. لا تعتمد الدرجة قبل الإكمال.`;
    return;
  }
  const raw=vals.reduce((a,b)=>a+b,0), pct=raw*4;
  $('#who5-raw').textContent=`${raw} / 25`;
  $('#who5-pct').textContent=`${pct} / 100`;
  $('#who5-status').textContent=raw<13?`النتيجة أقل من الحد المقترح 13/25 (${pct}%). قد يشير ذلك إلى رفاه منخفض ويستدعي تقييمًا أوسع؛ لا يثبت تشخيصًا.`:`النتيجة ليست أقل من الحد المقترح 13/25 (${pct}%). هذا لا يستبعد اضطرابًا إذا كانت هناك أعراض أو صعوبة وظيفية.`;
}
wireA11y();
$$('#who5-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calc));
$('#who5-clear')?.addEventListener('click',()=>{$$('#who5-sheet input').forEach(el=>{if(el.type==='radio')el.checked=false;else el.value=''});$$('#who5-sheet textarea').forEach(el=>el.value='');calc()});
$('#who5-print')?.addEventListener('click',()=>window.print());
calc();
})();