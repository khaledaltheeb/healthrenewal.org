(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const q=$('#readiness-search'),state=$('#readiness-state'),domain=$('#readiness-domain'),count=$('#readiness-count');
function run(){const text=(q?.value||'').trim().toLowerCase(),s=state?.value||'all',d=domain?.value||'all';let visible=0;$$('[data-readiness-row]').forEach(row=>{const okText=!text||(row.textContent||'').toLowerCase().includes(text);const okState=s==='all'||row.dataset.state===s;const okDomain=d==='all'||row.dataset.domain===d;const show=okText&&okState&&okDomain;row.hidden=!show;if(show)visible++});if(count)count.textContent=`${visible} أداة ظاهرة`}
[q,state,domain].forEach(e=>{e?.addEventListener('input',run);e?.addEventListener('change',run)});run();
})();