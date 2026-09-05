(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
function selected(n){return $(`input[name="g${n}"]:checked`)?.value??null}
function calc(){const rows=$$('#gds-items .form-row');let answered=0,total=0;rows.forEach((row,i)=>{const v=selected(i+1);if(v===null)return;answered++;if(v===row.dataset.depressionAnswer)total++});if(answered<15){$('#gds-total').textContent='— / 15';$('#gds-status').textContent=`أُجيب عن ${answered}/15 بندًا. لا تعتمد المجموع قبل الإكمال.`;return}$('#gds-total').textContent=`${total} / 15`;const notes=[];if(total>5)notes.push('أعلى من 5: مرجع Stanford يستدعي مقابلة دقيقة');if(total>=8)notes.push('بلغ 7/8 المستخدم كأفضل cut-off في دراسة التحقق العربي');$('#gds-status').textContent=notes.length?`${notes.join('؛ ')}. لا يثبت ذلك تشخيصًا.`:'لم يبلغ المرجعين المعروضين. لا تستبعد الاكتئاب إذا كان الاشتباه السريري قائمًا.'}
$$('#gds-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calc));
$('#gds-clear')?.addEventListener('click',()=>{$$('#gds-sheet input').forEach(el=>{if(el.type==='radio')el.checked=false;else el.value=''});$$('#gds-sheet textarea').forEach(el=>el.value='');$$('#gds-sheet select').forEach(el=>el.selectedIndex=0);calc()});
$('#gds-print')?.addEventListener('click',()=>window.print());
calc();
})();