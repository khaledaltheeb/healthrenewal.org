(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const body=$('#record-body');let seq=0;
const fields=['date','tool','version','language','period','score','unit','protocol','assist','events','safety'];
function makeInput(type='text',placeholder=''){const i=document.createElement('input');i.type=type;i.placeholder=placeholder;return i}
function addRow(prefill={}){
  seq++;const tr=document.createElement('tr');tr.dataset.visit=String(seq);
  const visit=document.createElement('td');visit.textContent=seq===1?'خط الأساس':`متابعة ${seq-1}`;tr.appendChild(visit);
  const specs=[['date','date',''],['tool','text','TUG / PHQ-9 / ...'],['version','text','الإصدار/عدد البنود'],['language','text','ar / en'],['period','text','آخر أسبوعين / الآن'],['score','text','الدرجة'],['unit','text','0–27 / ث / م/ث'],['protocol','text','المسافة/الكرسي/التعليمات'],['assist','text','جهاز/مساعدة'],['events','text','دواء/مرض/حدث'],['safety','text','نعم/لا/غير منطبق']];
  for(const [key,type,ph] of specs){const td=document.createElement('td'),input=makeInput(type,ph);input.dataset.field=key;input.value=prefill[key]??'';input.setAttribute('aria-label',`${visit.textContent} — ${ph||key}`);input.addEventListener('input',recompute);td.appendChild(input);tr.appendChild(td)}
  const flag=document.createElement('td');flag.dataset.flag='';flag.className='flag';flag.textContent='—';tr.appendChild(flag);body.appendChild(tr);relabel();recompute();
}
function relabel(){[...body.rows].forEach((tr,i)=>{tr.dataset.visit=String(i+1);tr.cells[0].textContent=i===0?'خط الأساس':`متابعة ${i}`;$$('input',tr).forEach(inp=>inp.setAttribute('aria-label',`${tr.cells[0].textContent} — ${inp.placeholder||inp.dataset.field}`))})}
function rowData(tr){const out={visit:tr.cells[0].textContent};$$('[data-field]',tr).forEach(i=>out[i.dataset.field]=i.value.trim());return out}
function baseline(){return [...body.rows].map(rowData).find(r=>r.tool&&r.version&&r.language&&r.period&&r.unit&&r.score)}
function comparable(base,row){const keys=['tool','version','language','period','unit'];const mismatches=keys.filter(k=>(base[k]||'').toLowerCase()!==(row[k]||'').toLowerCase());const protocolChanged=(base.protocol||'').toLowerCase()!==(row.protocol||'').toLowerCase();const assistChanged=(base.assist||'').toLowerCase()!==(row.assist||'').toLowerCase();return {mismatches,protocolChanged,assistChanged}}
function recompute(){
  const rows=[...body.rows],base=baseline();
  rows.forEach(tr=>{const f=tr.querySelector('[data-flag]'),r=rowData(tr);if(!r.tool&&!r.score){f.textContent='—';f.className='flag';return}if(!base){f.textContent='أكمل خط أساس صالح';f.className='flag warn';return}if(r===base){f.textContent='خط الأساس';f.className='flag ok';return}const c=comparable(base,r);if(c.mismatches.length){f.textContent=`غير قابل للمقارنة مباشرة: ${c.mismatches.join('، ')}`;f.className='flag warn'}else if(c.protocolChanged||c.assistChanged){const what=[c.protocolChanged?'البروتوكول':'',c.assistChanged?'الجهاز/المساعدة':''].filter(Boolean).join(' و');f.textContent=`قابل بحذر: تغير ${what}`;f.className='flag warn'}else{f.textContent='قابل للمقارنة بروتوكوليًا';f.className='flag ok'}})
}
function payload(){return {schema:'rawafid-measurement-record-v1',exported_at:new Date().toISOString(),record:{id:$('#record-id').value.trim(),goal:$('#record-goal').value.trim(),setting:$('#record-setting').value.trim(),owner:$('#record-owner').value.trim(),notes:$('#record-notes').value.trim()},visits:[...body.rows].map(rowData)}}
function download(name,type,text){const blob=new Blob([text],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function csvCell(v){const s=String(v??'');return /[",\n]/.test(s)?`"${s.replaceAll('"','""')}"`:s}
function exportJson(){download('rawafid-measurement-record.json','application/json;charset=utf-8',JSON.stringify(payload(),null,2))}
function exportCsv(){const rows=payload().visits,headers=['visit',...fields];const lines=[headers.join(','),...rows.map(r=>headers.map(h=>csvCell(r[h])).join(','))];download('rawafid-measurement-record.csv','text/csv;charset=utf-8','\ufeff'+lines.join('\n'))}
function clearAll(){if(!confirm('مسح كل البيانات المدخلة في هذا السجل؟'))return;$$('input,textarea').forEach(x=>x.value='');body.replaceChildren();seq=0;addRow();addRow();addRow()}
$('#record-add').addEventListener('click',()=>addRow());$('#record-print').addEventListener('click',()=>window.print());$('#record-json').addEventListener('click',exportJson);$('#record-csv').addEventListener('click',exportCsv);$('#record-clear').addEventListener('click',clearAll);
addRow();addRow();addRow();
})();