(()=>{
  'use strict';
  const $=(s)=>document.querySelector(s);
  const val=(id)=>{
    const el=$(id);
    if(!el||String(el.value).trim()==='') return null;
    const v=Number(el.value);
    return Number.isFinite(v)&&v>0?v:null;
  };

  function side(prefix){
    const out=$(`#${prefix}-result`);
    if(!out) return;
    const status=$(`#${prefix}-status`)?.value||'قابل للاختبار';
    if(status!=='قابل للاختبار'){
      out.textContent=status+' — لا تُفسَّر الأزمنة المسجلة كنتيجة معيارية.';
      return;
    }
    const trials=[val(`#${prefix}-t1`),val(`#${prefix}-t2`),val(`#${prefix}-t3`)].filter(v=>v!==null);
    if(!trials.length){out.textContent='—';return;}
    const best=Math.min(...trials);
    const mean=trials.reduce((a,b)=>a+b,0)/trials.length;
    out.textContent=`أفضل زمن ${best.toFixed(2)} ث · المتوسط ${mean.toFixed(2)} ث · ${trials.length} محاولة/محاولات`;
  }

  function qc(){
    const ids=['#hpt-qc-board','#hpt-qc-side','#hpt-qc-sequence','#hpt-qc-timer','#hpt-qc-practice'];
    const done=ids.filter(id=>$(id)?.checked).length;
    const out=$('#hpt-qc-result');
    if(out) out.textContent=done===5
      ?'تم توثيق عناصر الاتساق الخمسة.'
      :'تم توثيق '+done+'/5 من عناصر الاتساق؛ فسّر المقارنة الطولية بحذر إذا تغيّر الجهاز أو التدريب أو التعليمات.';
  }

  function recalc(){side('hpt-right');side('hpt-left');qc();}

  document.querySelectorAll('input,select,textarea').forEach(el=>{
    el.addEventListener('input',recalc);
    el.addEventListener('change',recalc);
  });
  $('#hpt-print')?.addEventListener('click',()=>window.print());
  $('#hpt-clear')?.addEventListener('click',()=>{
    document.querySelectorAll('input,textarea,select').forEach(el=>{
      if(el.tagName==='SELECT') el.selectedIndex=0;
      else if(el.type==='checkbox'||el.type==='radio') el.checked=false;
      else el.value='';
    });
    recalc();
    const live=$('#hpt-live');
    if(live) live.textContent='تم مسح ورقة 9HPT محليًا.';
  });
  recalc();
})();