(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const responseLabels={0:'لم يزعجني',1:'أزعجني قليلًا',2:'أزعجني كثيرًا',na:'غير منطبق'};
function wireA11y(){$$('#phq15-sheet tbody tr').forEach((row,i)=>{const item=(row.querySelector('td')?.textContent||`البند ${i+1}`).trim();$$('input[type="radio"]',row).forEach(input=>{if(!input.hasAttribute('aria-label'))input.setAttribute('aria-label',`${item} — ${responseLabels[input.value]||input.value}`)})})}
function selected(n){const el=$(`input[name="p15_${n}"]:checked`);if(!el)return null;return el.value==='na'?'na':Number(el.value)}
function calc(){const vals=Array.from({length:15},(_,i)=>selected(i+1));const item4na=vals[3]==='na';const numeric=vals.filter(v=>typeof v==='number');const missing=vals.filter(v=>v===null).length;$('#phq15-na-note').hidden=!item4na;if(missing){$('#phq15-total').textContent='—';$('#phq15-band').textContent=`هناك ${missing} بند/بنود بلا إجابة. لا يُحسب مجموع.`;return}if(item4na){const subtotal=numeric.reduce((a,b)=>a+b,0);$('#phq15-total').textContent=`${subtotal} / 28 (14 بندًا)`;$('#phq15-band').textContent='هذا subtotal غير معياري هنا؛ لا تُطبق نقاط القطع 5/10/15 دون بروتوكول محدد لمعالجة البند غير المنطبق.';return}if(numeric.length!==15){$('#phq15-total').textContent='—';$('#phq15-band').textContent='لا يمكن حساب المجموع.';return}const total=numeric.reduce((a,b)=>a+b,0);$('#phq15-total').textContent=`${total} / 30`;const band=total<=4?'حد أدنى':total<=9?'منخفض/خفيف':total<=14?'متوسط':'مرتفع';$('#phq15-band').textContent=`عبء الأعراض: ${band}. لا تحدد الدرجة سبب الأعراض.`}
wireA11y();$$('#phq15-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calc));
$('#phq15-clear')?.addEventListener('click',()=>{$$('#phq15-sheet input').forEach(el=>{if(el.type==='radio')el.checked=false;else el.value=''});$$('#phq15-sheet textarea').forEach(el=>el.value='');calc()});
$('#phq15-print')?.addEventListener('click',()=>window.print());
calc();
})();