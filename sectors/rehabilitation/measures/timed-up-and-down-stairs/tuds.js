(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const n=(id)=>{const el=$(id);if(!el||String(el.value).trim()==='')return null;const v=Number(el.value);return Number.isFinite(v)&&v>0?v:null};
const v=(id)=>($(id)?.value||'').trim();
function protocolComplete(){return ['#tuds-steps','#tuds-riser','#tuds-tread','#tuds-rail-policy','#tuds-start-rule','#tuds-turn-rule','#tuds-stop-rule','#tuds-pace'].every(s=>v(s)!=='');}
function recalc(){
 const out=$('#tuds-result'), note=$('#tuds-note'); if(!out||!note)return;
 const status=v('#tuds-status')||'testable';
 if(status!=='testable'){out.textContent='—';note.textContent=status==='not-testable'?'غير قابل للاختبار — لا تسجل صفر ثانية.':'أوقف لأسباب السلامة/التعب — لا توجد نتيجة زمنية معيارية.';return;}
 const times=[n('#tuds-t1'),n('#tuds-t2'),n('#tuds-t3')].filter(x=>x!==null);
 if(!times.length){out.textContent='—';note.textContent='أدخل زمن محاولة صالحة واحدة على الأقل.';return;}
 const best=Math.min(...times),mean=times.reduce((a,b)=>a+b,0)/times.length;
 out.textContent=`أفضل زمن ${best.toFixed(2)} ث · متوسط ${mean.toFixed(2)} ث · ${times.length} محاولة/محاولات`;
 note.textContent=protocolComplete()?'هوية البروتوكول الأساسية موثقة؛ قارن طوليًا فقط إذا بقي الإعداد نفسه.':'الزمن مسجل، لكن هوية السلم/التوقيت غير مكتملة؛ لا تعتبر المقارنة الطولية مكافئة حتى توثق الإعداد.';
}
$$('input,select,textarea').forEach(el=>{el.addEventListener('input',recalc);el.addEventListener('change',recalc)});
$('#tuds-print')?.addEventListener('click',()=>window.print());
$('#tuds-clear')?.addEventListener('click',()=>{$$('input,textarea').forEach(el=>el.value='');$$('select').forEach(el=>el.selectedIndex=0);recalc();const live=$('#tuds-live');if(live)live.textContent='تم مسح ورقة TUDS محليًا.';});
recalc();
})();
