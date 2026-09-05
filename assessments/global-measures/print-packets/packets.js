(()=>{
'use strict';
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
let active=null;
function printSection(id){
  active=id;
  $$('.section').forEach(section=>section.classList.toggle('packet-print-target',section.id===id));
  document.body.dataset.packetPrint='single';
  window.print();
  setTimeout(()=>{delete document.body.dataset.packetPrint;$$('.section').forEach(s=>s.classList.remove('packet-print-target'));active=null},250);
}
$$('[data-print-section]').forEach(btn=>btn.addEventListener('click',()=>printSection(btn.dataset.printSection)));
$('#print-all')?.addEventListener('click',()=>window.print());
const style=document.createElement('style');style.textContent='@media print{body[data-packet-print="single"] .section:not(.packet-print-target){display:none!important}body[data-packet-print="single"] .hero,body[data-packet-print="single"] .notice{display:none!important}.packet-print-target{display:block!important}}';document.head.appendChild(style);
})();