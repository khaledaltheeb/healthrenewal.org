(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
function val(n){const el=$(`input[name="q${n}"]:checked`);return el?Number(el.value):null}
function calc(){const v=[1,2,3,4].map(val),complete=v.every(x=>x!==null);if(!complete){$('#phq4-total').textContent='— / 12';$('#phq4-band').textContent=`أُجيب عن ${v.filter(x=>x!==null).length}/4 بنود.`;$('#phq4-gad2').textContent='— / 6';$('#phq4-phq2').textContent='— / 6';return}const gad=v[0]+v[1],phq=v[2]+v[3],total=gad+phq;$('#phq4-gad2').textContent=`${gad} / 6`;$('#phq4-phq2').textContent=`${phq} / 6`;$('#phq4-total').textContent=`${total} / 12`;const band=total<=2?'حد أدنى/لا ضيق':total<=5?'خفيف':total<=8?'متوسط':'شديد';const flags=[];if(gad>=3)flags.push('GAD‑2 بلغ عتبة الفحص 3');if(phq>=3)flags.push('PHQ‑2 بلغ عتبة الفحص 3');$('#phq4-band').textContent=`النطاق: ${band}. ${flags.length?flags.join('؛ '):'لم يبلغ أي مقياس فرعي عتبة 3.'} لا يثبت ذلك تشخيصًا.`}
$$('#phq4-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calc));
$('#phq4-clear')?.addEventListener('click',()=>{$$('#phq4-sheet input').forEach(el=>{if(el.type==='radio')el.checked=false;else el.value=''});$$('#phq4-sheet textarea').forEach(el=>el.value='');calc()});
$('#phq4-print')?.addEventListener('click',()=>window.print());
calc();
})();