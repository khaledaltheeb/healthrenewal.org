(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const n=id=>{const e=document.getElementById(id);if(!e||String(e.value).trim()==='')return null;const v=Number(e.value);return Number.isFinite(v)?v:null};
const put=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
const f=(v,d=1)=>Number.isFinite(v)?v.toFixed(d):'—';
function wireLabels(){let i=0;$$('.field').forEach(x=>{const l=$('label',x),c=$('input,select,textarea',x);if(!l||!c)return;if(!c.id)c.id=`perf-auto-${++i}`;if(!l.htmlFor)l.htmlFor=c.id})}
function distance(prefix){const course=n(`${prefix}-course`),laps=n(`${prefix}-laps`),partial=n(`${prefix}-partial`);if(course===null||laps===null){put(`${prefix}-result`,'—');return}const total=course*Math.max(0,laps)+(partial||0);put(`${prefix}-result`,`${f(total,1)} متر`)}
function fsst(){const vals=[n('fsst-t1'),n('fsst-t2')].filter(v=>v!==null&&v>0);put('fsst-result',vals.length?`أفضل زمن ${f(Math.min(...vals),2)} ثانية`:'—')}
function sls(){for(const side of ['r','l']){const vals=[n(`sls-${side}1`),n(`sls-${side}2`)].filter(v=>v!==null&&v>=0);put(`sls-${side}-result`,vals.length?`${f(Math.max(...vals),1)} ث`:'—')}}
function step2(){const r=n('step2-reps');put('step2-result',r!==null?`${Math.max(0,Math.floor(r))} رفعة ركبة مسجلة`:'—')}
function step15(){const r=n('step15-r'),l=n('step15-l');put('step15-result',r!==null||l!==null?`يمين: ${r===null?'—':Math.max(0,Math.floor(r))} · يسار: ${l===null?'—':Math.max(0,Math.floor(l))}`:'—')}
function grip(){for(const side of ['r','l']){const vals=[1,2,3].map(i=>n(`grip-${side}${i}`)).filter(v=>v!==null&&v>=0);put(`grip-${side}-result`,vals.length?`المتوسط ${f(vals.reduce((a,b)=>a+b,0)/vals.length,1)} · الأفضل ${f(Math.max(...vals),1)}`:'—')}}
function recalc(){distance('walk6');distance('walk2');fsst();sls();step2();step15();grip()}
wireLabels();$$('input,select,textarea').forEach(e=>{e.addEventListener('input',recalc);e.addEventListener('change',recalc)});
$$('[data-print]').forEach(b=>b.addEventListener('click',()=>{const id=b.dataset.print;$$('.measure').forEach(x=>x.classList.toggle('print-target',x.id===id));window.print();setTimeout(()=>$$('.measure').forEach(x=>x.classList.remove('print-target')),200)}));
$$('[data-clear]').forEach(b=>b.addEventListener('click',()=>{const root=document.getElementById(b.dataset.clear);if(!root)return;$$('input,textarea,select',root).forEach(e=>{if(e.tagName==='SELECT')e.selectedIndex=0;else e.value=''});recalc()}));
recalc();
})();