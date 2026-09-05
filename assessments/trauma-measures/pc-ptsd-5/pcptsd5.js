(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const symptoms=$('#pc-symptoms');
function checked(name){return $(`input[name="${name}"]:checked`)?.value??null}
function calculate(){
  const exposure=checked('pc-exposure');
  if(exposure==='no'){
    symptoms.hidden=true;
    $$('input[type="radio"]',symptoms).forEach(el=>el.checked=false);
    $('#pc-total').textContent='0 / 5';
    $('#pc-status').textContent='لا يوجد تعرض مُبلّغ عنه: ينتهي PC‑PTSD‑5 هنا بدرجة 0.';
    return;
  }
  symptoms.hidden=exposure!=='yes';
  if(exposure!=='yes'){$('#pc-total').textContent='— / 5';$('#pc-status').textContent='ابدأ بسؤال التعرض.';return}
  const vals=[1,2,3,4,5].map(n=>checked(`pc${n}`));
  const answered=vals.filter(v=>v!==null).length;
  if(answered<5){$('#pc-total').textContent='— / 5';$('#pc-status').textContent=`أُجيب عن ${answered}/5 بنود. لا تعتمد النتيجة قبل الإكمال.`;return}
  const total=vals.filter(v=>v==='yes').length;
  $('#pc-total').textContent=`${total} / 5`;
  $('#pc-status').textContent=total>=4?'بلغت النتيجة المرجع العام 4؛ هذا فحص إيجابي يحتاج تقييمًا إضافيًا ولا يثبت التشخيص.':'أقل من المرجع العام 4؛ لا تستبعد PTSD إذا كان الاشتباه السريري قائمًا، لأن العتبة تعتمد على الفئة والغرض.';
}
$$('#pc-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calculate));
$('#pc-clear')?.addEventListener('click',()=>{$$('#pc-sheet input').forEach(el=>{if(el.type==='radio'||el.type==='checkbox')el.checked=false;else el.value=''});$$('#pc-sheet textarea').forEach(el=>el.value='');calculate()});
$('#pc-print')?.addEventListener('click',()=>window.print());
calculate();
})();