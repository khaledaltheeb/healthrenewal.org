(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const labels={0:'أبدًا',1:'نادرًا',2:'بعض الوقت',3:'معظم الوقت',4:'طوال الوقت'};
function wireA11y(){$$('#k10-sheet tbody tr').forEach((row,i)=>{const item=(row.querySelector('td')?.textContent||`البند ${i+1}`).trim();$$('input[type="radio"]',row).forEach(input=>input.setAttribute('aria-label',`${item} — ${labels[input.value]}`))})}
function selected(n){const el=$(`input[name="k10_${n}"]:checked`);return el?Number(el.value):null}
function calc(){const vals=Array.from({length:10},(_,i)=>selected(i+1)),answered=vals.filter(v=>v!==null).length;if(answered<10){$('#k10-total').textContent='— / 40';$('#k10-status').textContent=`أُجيب عن ${answered}/10 بنود. لا تعتمد المجموع قبل الإكمال.`;return}const total=vals.reduce((a,b)=>a+b,0);$('#k10-total').textContent=`${total} / 40`;$('#k10-status').textContent='تم حساب المجموع بنظام 0–40. لا تطبق روافد cut-off أو تصنيف شدة عالميًا؛ فسّر الدرجة حسب المجتمع والغرض ونظام التسجيل.'}
wireA11y();$$('#k10-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calc));
$('#k10-clear')?.addEventListener('click',()=>{$$('#k10-sheet input').forEach(el=>{if(el.type==='radio')el.checked=false;else el.value=''});$$('#k10-sheet textarea').forEach(el=>el.value='');calc()});
$('#k10-print')?.addEventListener('click',()=>window.print());
calc();
})();