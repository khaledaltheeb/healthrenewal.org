(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const labels={0:'أبدًا',1:'نادرًا',2:'بعض الوقت',3:'معظم الوقت',4:'طوال الوقت'};
function wireA11y(){$$('#k6-sheet tbody tr').forEach((row,i)=>{const item=(row.querySelector('td')?.textContent||`البند ${i+1}`).trim();$$('input[type="radio"]',row).forEach(input=>input.setAttribute('aria-label',`${item} — ${labels[input.value]}`))})}
function selected(n){const el=$(`input[name="k6_${n}"]:checked`);return el?Number(el.value):null}
function calc(){const vals=Array.from({length:6},(_,i)=>selected(i+1)),answered=vals.filter(v=>v!==null).length;if(answered<6){$('#k6-total').textContent='— / 24';$('#k6-status').textContent=`أُجيب عن ${answered}/6 بنود. لا تعتمد المجموع قبل الإكمال.`;return}const total=vals.reduce((a,b)=>a+b,0);$('#k6-total').textContent=`${total} / 24`;$('#k6-status').textContent=total>=13?'بلغ المجموع المرجع الأمريكي 13+ للضيق النفسي الشديد؛ لا يُعامل كتشخيص أو cut-off عربي عام.':'أقل من المرجع الأمريكي 13؛ لا يستبعد اضطرابًا أو حاجة سريرية إذا كان الاشتباه قائمًا.'}
wireA11y();$$('#k6-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calc));
$('#k6-clear')?.addEventListener('click',()=>{$$('#k6-sheet input').forEach(el=>{if(el.type==='radio')el.checked=false;else el.value=''});$$('#k6-sheet textarea').forEach(el=>el.value='');calc()});
$('#k6-print')?.addEventListener('click',()=>window.print());
calc();
})();