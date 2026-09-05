(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const names=['gad1','gad2i','gad3','gad4','gad5','gad6','gad7'];
function selected(name){const el=$(`input[name="${name}"]:checked`);return el?Number(el.value):null}
function calculate(){
  const vals=names.map(selected), complete=vals.every(v=>v!==null);
  const gad2vals=vals.slice(0,2), gad2complete=gad2vals.every(v=>v!==null);
  $('#gad2').textContent=gad2complete?`${gad2vals.reduce((a,b)=>a+b,0)} / 6`:'— / 6';
  if(!complete){$('#gad-total').textContent='— / 21';$('#gad-band').textContent=`أُجيب عن ${vals.filter(v=>v!==null).length}/7 بنود. لا تعتمد المجموع قبل الإكمال.`;return}
  const total=vals.reduce((a,b)=>a+b,0); $('#gad-total').textContent=`${total} / 21`;
  const band=total<=4?'حد أدنى/قليل':total<=9?'خفيف':total<=14?'متوسط':'شديد';
  $('#gad-band').textContent=`نطاق الأعراض: ${band}. الفحص لا يثبت تشخيصًا.`;
}
$$('#gad-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calculate));
$('#gad-clear')?.addEventListener('click',()=>{$$('#gad-sheet input').forEach(el=>{if(el.type==='radio'||el.type==='checkbox')el.checked=false;else el.value=''});$$('#gad-sheet textarea').forEach(el=>el.value='');$$('#gad-sheet select').forEach(el=>el.selectedIndex=0);calculate()});
$('#gad-print')?.addEventListener('click',()=>window.print());
calculate();
})();