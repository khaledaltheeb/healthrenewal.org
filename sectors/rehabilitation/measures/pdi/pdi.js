(()=>{
'use strict';
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const $=(s,r=document)=>r.querySelector(s);
function calculate(){
  const values=$$('.pdi-score').map(el=>String(el.value).trim()===''?null:Number(el.value));
  values.forEach((v,i)=>{if(v!==null&&(v<0||v>10||!Number.isInteger(v))){$$('.pdi-score')[i].setCustomValidity('أدخل عددًا صحيحًا من 0 إلى 10.')}else{$$('.pdi-score')[i].setCustomValidity('')}});
  const valid=values.filter(v=>v!==null&&Number.isFinite(v)&&v>=0&&v<=10);
  if(valid.length!==7){$('#pdi-total').textContent='— / 70';$('#pdi-status').textContent=`تم إدخال ${valid.length}/7 مجالات. لا يُحسب المجموع الكامل مع بند مفقود.`;return;}
  const total=valid.reduce((a,b)=>a+b,0);
  const max=Math.max(...valid), maxIndex=valid.indexOf(max)+1;
  $('#pdi-total').textContent=`${total} / 70`;
  $('#pdi-status').textContent=`أعلى درجة مجال: ${max}/10 (المجال ${maxIndex}). لا توجد نقطة قطع معيارية ثابتة؛ فسّر النمط والتغير الطولي.`;
}
$$('.pdi-score').forEach(el=>el.addEventListener('input',calculate));
$('#pdi-clear')?.addEventListener('click',()=>{$$('#pdi-sheet input').forEach(el=>el.value='');$$('#pdi-sheet textarea').forEach(el=>el.value='');calculate()});
$('#pdi-print')?.addEventListener('click',()=>window.print());
calculate();
})();