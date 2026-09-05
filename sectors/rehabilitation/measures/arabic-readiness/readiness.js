(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
function augment(){
  const tbody=$('tbody');
  if(tbody&&!$('#readiness-stay-independent')){
    const row=document.createElement('tr');
    row.id='readiness-stay-independent';
    row.setAttribute('data-readiness-row','');
    row.dataset.state='rawafid-operational';
    row.dataset.domain='balance';
    row.innerHTML='<td><strong>Stay Independent</strong><br>STEADI SIB</td><td>السقوط/التوازن</td><td>دراسة AR-SIB عربية منشورة؛ ورقة روافد صياغة تشغيلية مستقلة من المصدر العام وليست النسخة المنشورة حرفيًا.</td><td>CDC Stacks يصنف المصدر الإنجليزي Public Domain؛ رابط دراسة التحقق العربي محفوظ منفصلًا.</td><td><a href="/sectors/rehabilitation/measures/stay-independent/">نموذج كامل 0–14</a></td>';
    const pdi=$$('[data-readiness-row]').find(r=>(r.textContent||'').includes('Pain Disability Index'));
    if(pdi)tbody.insertBefore(row,pdi);else tbody.appendChild(row);
  }
  const pdi=$$('[data-readiness-row]').find(r=>(r.textContent||'').includes('Pain Disability Index'));
  if(pdi){
    const cells=$$('td',pdi);
    if(cells.length>=5){
      cells[3].innerHTML='الأصل موصوف في دراسة 2026 كملكية عامة. <strong>ورقة روافد التشغيلية متاحة</strong>، بينما النسخة MSA المتحققة حرفيًا تبقى مرتبطة بملحقها المصدر.';
      cells[4].innerHTML='<a href="/sectors/rehabilitation/measures/pdi/">فتح PDI التشغيلي الكامل</a><br><small>Exact validated MSA form: source verification pending</small>';
    }
  }
}
augment();
const q=$('#readiness-search'),state=$('#readiness-state'),domain=$('#readiness-domain'),count=$('#readiness-count');
function run(){const text=(q?.value||'').trim().toLowerCase(),s=state?.value||'all',d=domain?.value||'all';let visible=0;$$('[data-readiness-row]').forEach(row=>{const okText=!text||(row.textContent||'').toLowerCase().includes(text);const okState=s==='all'||row.dataset.state===s;const okDomain=d==='all'||row.dataset.domain===d;const show=okText&&okState&&okDomain;row.hidden=!show;if(show)visible++});if(count)count.textContent=`${visible} أداة ظاهرة`}
[q,state,domain].forEach(e=>{e?.addEventListener('input',run);e?.addEventListener('change',run)});run();
})();