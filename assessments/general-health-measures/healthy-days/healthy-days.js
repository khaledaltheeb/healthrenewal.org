(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
function day(id){const el=$(id),raw=el.value.trim();if(raw==='')return null;const n=Number(raw);if(!Number.isInteger(n)||n<0||n>30)return NaN;return n}
function calc(){const p=day('#hd-physical'),m=day('#hd-mental'),l=day('#hd-limited');const invalid=[p,m,l].some(Number.isNaN);if(invalid){$('#hd-unhealthy').textContent='— / 30';$('#hd-healthy').textContent='— / 30';$('#hd-status').textContent='كل عدد أيام يجب أن يكون عددًا صحيحًا من 0 إلى 30.';$('#hd-live').textContent='قيمة غير صالحة: أدخل عددًا من صفر إلى ثلاثين.';return}if(p===null||m===null){$('#hd-unhealthy').textContent='— / 30';$('#hd-healthy').textContent='— / 30';$('#hd-status').textContent='أكمل يومي الصحة الجسدية والنفسية لحساب المؤشرين.';return}const unhealthy=Math.min(30,p+m),healthy=30-unhealthy;$('#hd-unhealthy').textContent=`${unhealthy} / 30`;$('#hd-healthy').textContent=`${healthy} / 30`;const overlap=p+m>30?' مجموع الأيام الجسدية والنفسية تجاوز 30؛ طُبق سقف 30 كما يقتضي المؤشر.':'';$('#hd-status').textContent=`جسدية غير جيدة: ${p} · نفسية غير جيدة: ${m}.${overlap}`;$('#hd-limited-note').textContent=l===null?'أيام تقييد النشاط لم تُسجل بعد، وهي مؤشر منفصل.':`أيام تقييد النشاط: ${l}/30 — لا تدخل في حساب Healthy Days.`}
['#hd-physical','#hd-mental','#hd-limited'].forEach(id=>$(id).addEventListener('input',calc));
$('#hd-clear')?.addEventListener('click',()=>{$$('#hd-sheet input').forEach(el=>{if(el.type==='radio')el.checked=false;else el.value=''});$$('#hd-sheet textarea').forEach(el=>el.value='');calc()});
$('#hd-print')?.addEventListener('click',()=>window.print());
calc();
})();