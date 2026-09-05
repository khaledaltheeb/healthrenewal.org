(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const number=(id)=>{const el=document.getElementById(id);if(!el)return null;const v=Number(el.value);return Number.isFinite(v)?v:null};
const set=(id,text)=>{const el=document.getElementById(id);if(el)el.textContent=text};
const fmt=(n,d=2)=>Number.isFinite(n)?n.toFixed(d):'—';
function announce(text){const el=$('#live');if(el)el.textContent=text}
function calc10m(){const distance=number('walk-distance')||10;const t1=number('walk-t1'),t2=number('walk-t2');const vals=[t1,t2].filter(v=>v>0);if(!vals.length){set('walk-result','—');return}const mean=vals.reduce((a,b)=>a+b,0)/vals.length;const speed=distance/mean;set('walk-result',`${fmt(speed,2)} م/ث · متوسط الزمن ${fmt(mean,2)} ث`)}
function calcPSFS(){const vals=$$('.psfs-score').map(el=>Number(el.value)).filter(Number.isFinite);if(!vals.length){set('psfs-result','—');return}set('psfs-result',`${fmt(vals.reduce((a,b)=>a+b,0)/vals.length,2)} / 10 (${vals.length} أنشطة)`)}
function calcNPRS(){const now=number('pain-now'),best=number('pain-best'),worst=number('pain-worst'),avg=number('pain-average');const vals=[now,best,worst,avg].filter(v=>v!==null);set('nprs-result',vals.length?`المتوسط المسجل: ${fmt(vals.reduce((a,b)=>a+b,0)/vals.length,1)} / 10`:'—')}
function calcTUG(){const vals=[number('tug-t1'),number('tug-t2')].filter(v=>v>0);if(!vals.length){set('tug-result','—');return}const best=Math.min(...vals);const mean=vals.reduce((a,b)=>a+b,0)/vals.length;set('tug-result',`أفضل زمن ${fmt(best,2)} ث · المتوسط ${fmt(mean,2)} ث`)}
function calcFTSST(){const t=number('fts-time');set('fts-result',t&&t>0?`${fmt(t,2)} ثانية`:'—')}
function calcChair(){const reps=number('chair-reps');set('chair-result',reps!==null?`${Math.max(0,Math.floor(reps))} وقوف صحيح خلال 30 ثانية`:'—')}
function calcBalance(){const rows=['side','semi','tandem','single'];const vals=rows.map(k=>number(`bal-${k}`)).filter(v=>v!==null);if(!vals.length){set('balance-result','—');return}const min=Math.min(...vals);const completed=vals.filter(v=>v>=10).length;set('balance-result',`${completed}/4 وضعيات بلغت 10 ثوانٍ · أقل زمن ${fmt(min,1)} ث`)}
function recalc(){calcTUG();calcChair();calcBalance();calc10m();calcFTSST();calcNPRS();calcPSFS()}
$$('input,select,textarea').forEach(el=>{el.addEventListener('input',recalc);el.addEventListener('change',recalc)});
$$('.nprs-choice').forEach(btn=>btn.addEventListener('click',()=>{const target=document.getElementById(btn.dataset.target);if(target){target.value=btn.dataset.value;$$(`.nprs-choice[data-target="${btn.dataset.target}"]`).forEach(x=>x.setAttribute('aria-pressed',String(x===btn)));recalc()}}));
$$('[data-print]').forEach(btn=>btn.addEventListener('click',()=>{const id=btn.dataset.print;$$('.measure').forEach(x=>x.classList.toggle('print-target',x.id===id));window.print();setTimeout(()=>$$('.measure').forEach(x=>x.classList.remove('print-target')),200)}));
$$('[data-clear]').forEach(btn=>btn.addEventListener('click',()=>{const root=document.getElementById(btn.dataset.clear);if(!root)return;$$('input,textarea,select',root).forEach(el=>{if(el.tagName==='SELECT')el.selectedIndex=0;else if(el.type==='checkbox'||el.type==='radio')el.checked=false;else el.value=''});$$('[aria-pressed="true"]',root).forEach(el=>el.setAttribute('aria-pressed','false'));recalc();announce('تم مسح بيانات الورقة محليًا.')}));
const search=$('#measure-search'), filter=$('#rights-filter');function filterCards(){const q=(search?.value||'').trim().toLowerCase();const f=filter?.value||'all';$$('[data-catalog-card]').forEach(card=>{const text=(card.textContent||'').toLowerCase();const okq=!q||text.includes(q);const okf=f==='all'||card.dataset.status===f;card.hidden=!(okq&&okf)})}search?.addEventListener('input',filterCards);filter?.addEventListener('change',filterCards);
recalc();
})();