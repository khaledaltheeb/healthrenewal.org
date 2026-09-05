(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const names=['phq1','phq2i','phq3','phq4','phq5','phq6','phq7','phq8','phq9'];
function selected(name){const el=$(`input[name="${name}"]:checked`);return el?Number(el.value):null}
function calculate(){
  const vals=names.map(selected), complete=vals.every(v=>v!==null);
  const phq2vals=vals.slice(0,2); const phq2complete=phq2vals.every(v=>v!==null);
  $('#phq2').textContent=phq2complete?`${phq2vals.reduce((a,b)=>a+b,0)} / 6`:'— / 6';
  if(!complete){$('#phq-total').textContent='— / 27';$('#phq-band').textContent=`أُجيب عن ${vals.filter(v=>v!==null).length}/9 بنود. لا تعتمد المجموع قبل الإكمال.`}
  else{
    const total=vals.reduce((a,b)=>a+b,0); $('#phq-total').textContent=`${total} / 27`;
    const band=total<=4?'حد أدنى/قليل':total<=9?'خفيف':total<=14?'متوسط':total<=19?'متوسط الشدة إلى مرتفع':'شديد';
    $('#phq-band').textContent=`نطاق الأعراض: ${band}. الفحص لا يثبت تشخيصًا.`;
  }
  const item9=vals[8]; const safety=item9!==null&&item9>0; $('#phq-safety').hidden=!safety;
  if(safety){$('#phq-live').textContent='تنبيه سلامة: إجابة البند التاسع تحتاج استيضاحًا مباشرًا وآمنًا.'}
}
$$('#phq-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calculate));
$('#phq-clear')?.addEventListener('click',()=>{$$('#phq-sheet input').forEach(el=>{if(el.type==='radio'||el.type==='checkbox')el.checked=false;else el.value=''});$$('#phq-sheet textarea').forEach(el=>el.value='');$$('#phq-sheet select').forEach(el=>el.selectedIndex=0);calculate()});
$('#phq-print')?.addEventListener('click',()=>window.print());
calculate();
})();