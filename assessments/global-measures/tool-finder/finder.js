(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
let tools=[], selected=new Map();
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labelize=s=>String(s).replaceAll('-',' ');
async function load(){
  try{
    const res=await fetch('/content/global-measures-v1/catalog.json',{credentials:'same-origin'});
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const data=await res.json(); tools=(data.tools||[]).filter(x=>x.actual===true);
    populate(); render();
  }catch(err){$('#finder-count').textContent='تعذر تحميل كتالوج المقاييس الآن.';$('#finder-results').innerHTML='<div class="notice danger">تعذر تحميل بيانات الكتالوج. افتح بوابة المقاييس مباشرة أو أعد المحاولة لاحقًا.</div>';console.error(err)}
}
function fillSelect(id,values){const el=$(id);[...values].sort((a,b)=>a.localeCompare(b,'ar')).forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=labelize(v);el.appendChild(o)})}
function populate(){
  fillSelect('#finder-domain',new Set(tools.flatMap(x=>x.domain||[])));
  fillSelect('#finder-pop',new Set(tools.flatMap(x=>x.population||[])));
  fillSelect('#finder-mode',new Set(tools.map(x=>x.mode).filter(Boolean)));
  $('#finder-count').textContent=`${tools.length} أداة/بطارية فعلية في الكتالوج.`;
}
function matches(t){
  const q=$('#finder-q').value.trim().toLowerCase(),d=$('#finder-domain').value,p=$('#finder-pop').value,m=$('#finder-mode').value;
  const hay=[t.name,t.acronym,...(t.domain||[]),...(t.population||[]),t.mode,t.period,t.score].join(' ').toLowerCase();
  return (!q||hay.includes(q))&&(!d||(t.domain||[]).includes(d))&&(!p||(t.population||[]).includes(p))&&(!m||t.mode===m);
}
function render(){
  const list=tools.filter(matches),root=$('#finder-results');root.replaceChildren();
  list.forEach(t=>{
    const card=document.createElement('article');card.className='card result-card';card.dataset.id=t.id;
    card.innerHTML=`<div class="measure-head"><div><span class="status full">فعلي · ${esc(t.score)}</span><h3><a href="${esc(t.route)}">${esc(t.acronym||t.name)}</a></h3><p>${esc(t.name)}</p></div><label><input type="checkbox" data-pick="${esc(t.id)}" ${selected.has(t.id)?'checked':''}> أضف للحزمة</label></div><div class="chips">${(t.domain||[]).map(x=>`<span class="chip">${esc(labelize(x))}</span>`).join('')}</div><p class="meta">الفئة: ${esc((t.population||[]).map(labelize).join(' · '))}<br>النوع: ${esc(labelize(t.mode))} · الفترة: ${esc(labelize(t.period))}<br>الحقوق: ${esc(labelize(t.rights_state))}</p><div class="tool-actions"><a class="button primary" href="${esc(t.route)}">فتح الأداة</a></div>`;
    root.appendChild(card);
  });
  $('#finder-empty').hidden=list.length>0;$('#finder-count').textContent=`${list.length} نتيجة من ${tools.length} أداة فعلية.`;
  $$('[data-pick]',root).forEach(el=>el.addEventListener('change',()=>toggle(el.dataset.pick,el.checked)));
}
function toggle(id,on){const t=tools.find(x=>x.id===id);if(!t)return;if(on)selected.set(id,t);else selected.delete(id);renderPacket()}
function renderPacket(){const root=$('#packet-list');root.replaceChildren();if(!selected.size){root.innerHTML='<span class="meta">لم تختر أدوات بعد.</span>';return}[...selected.values()].forEach(t=>{const span=document.createElement('span');span.className='packet-item';span.innerHTML=`<a href="${esc(t.route)}">${esc(t.acronym||t.name)}</a> <button type="button" aria-label="إزالة ${esc(t.acronym||t.name)}" data-remove="${esc(t.id)}">×</button>`;root.appendChild(span)});$$('[data-remove]',root).forEach(b=>b.addEventListener('click',()=>{selected.delete(b.dataset.remove);render();renderPacket()}))}
async function copyPacket(){if(!selected.size)return;const text=[...selected.values()].map(t=>`${t.acronym||t.name}: ${location.origin}${t.route}`).join('\n');try{await navigator.clipboard.writeText(text);$('#packet-copy').textContent='تم النسخ';setTimeout(()=>$('#packet-copy').textContent='نسخ روابط الحزمة',1500)}catch{window.prompt('انسخ الروابط:',text)}}
['#finder-q','#finder-domain','#finder-pop','#finder-mode'].forEach(id=>$(id).addEventListener(id==='#finder-q'?'input':'change',render));
$('#packet-clear').addEventListener('click',()=>{selected.clear();render();renderPacket()});$('#packet-print').addEventListener('click',()=>window.print());$('#packet-copy').addEventListener('click',copyPacket);
load();
})();