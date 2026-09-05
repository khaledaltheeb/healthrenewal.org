(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const responseLabels={0:'أبدًا',1:'قليلًا',2:'بدرجة متوسطة',3:'كثيرًا',4:'بدرجة شديدة جدًا'};
function wireA11y(){
  $$('#pcl-sheet tbody tr').forEach((row,index)=>{
    const item=(row.querySelector('td')?.textContent||`البند ${index+1}`).trim();
    $$('input[type="radio"]',row).forEach(input=>input.setAttribute('aria-label',`${item} — ${responseLabels[input.value]||input.value}`));
  });
}
function selected(n){const el=$(`input[name="pcl${n}"]:checked`);return el?Number(el.value):null}
function sumRange(vals,start,end){return vals.slice(start-1,end).reduce((a,b)=>a+b,0)}
function calculate(){
  const vals=Array.from({length:20},(_,i)=>selected(i+1));
  const answered=vals.filter(v=>v!==null).length;
  const complete=answered===20;
  if(!complete){
    $('#pcl-total').textContent='— / 80';
    $('#pcl-status').textContent=`أُجيب عن ${answered}/20 بندًا. لا تعتمد المجموع قبل الإكمال.`;
    $('#pcl-b').textContent='— / 20'; $('#pcl-c').textContent='— / 8'; $('#pcl-d').textContent='— / 28'; $('#pcl-e').textContent='— / 24';
  } else {
    const total=vals.reduce((a,b)=>a+b,0);
    $('#pcl-total').textContent=`${total} / 80`;
    $('#pcl-b').textContent=`${sumRange(vals,1,5)} / 20`;
    $('#pcl-c').textContent=`${sumRange(vals,6,7)} / 8`;
    $('#pcl-d').textContent=`${sumRange(vals,8,14)} / 28`;
    $('#pcl-e').textContent=`${sumRange(vals,15,20)} / 24`;
    $('#pcl-status').textContent=total>=31?'المجموع يقع ضمن نطاق cut-off بحثي شائع 31–33، لكن لا يُحوَّل إلى تشخيص؛ راجع الفئة والغرض والتقييم السريري.':'المجموع أقل من النطاق البحثي الشائع 31–33؛ لا يستبعد PTSD إذا كان الاشتباه السريري قائمًا.';
  }
  const risky=vals[15]!==null&&vals[15]>=2;
  $('#pcl-risk-note').hidden=!risky;
  if(risky) $('#pcl-live').textContent='مراجعة سريرية: البند 16 يشير إلى مخاطرة أو سلوك قد يسبب ضررًا بدرجة متوسطة أو أعلى.';
}
wireA11y();
$$('#pcl-sheet input[type="radio"]').forEach(el=>el.addEventListener('change',calculate));
$('#pcl-clear')?.addEventListener('click',()=>{$$('#pcl-sheet input').forEach(el=>{if(el.type==='radio'||el.type==='checkbox')el.checked=false;else el.value=''});$$('#pcl-sheet textarea').forEach(el=>el.value='');calculate()});
$('#pcl-print')?.addEventListener('click',()=>window.print());
calculate();
})();