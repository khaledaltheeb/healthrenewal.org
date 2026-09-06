(()=>{
  'use strict';
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const maxima={grasp:18,grip:12,pinch:18,gross:9};
  const labels={grasp:'القبض/Grasp',grip:'الإمساك/Grip',pinch:'القرص/Pinch',gross:'الحركة الكبيرة/Gross'};

  function valuesFor(subscale){
    return $$(`.arat-score[data-subscale="${subscale}"]`).map(el=>String(el.value).trim()===''?null:Number(el.value));
  }
  function write(id,text){const el=$(id);if(el)el.textContent=text;}
  function validScores(xs){return xs.every(v=>Number.isInteger(v)&&v>=0&&v<=3);}

  function recalc(){
    const status=$('#arat-status')?.value||'testable';
    const statusBox=$('#arat-status-note');
    if(status!=='testable'){
      for(const sub of Object.keys(maxima)) write(`#arat-${sub}-result`,'—');
      write('#arat-total','—');
      write('#arat-completion','الاختبار غير قابل للتفسير كدرجة معيارية في الحالة الحالية.');
      if(statusBox){statusBox.textContent=status==='not-testable'?'الحالة: غير قابل للاختبار — لا تُحسب الدرجة.':'الحالة: أوقف لأسباب السلامة/التعب — لا تُحسب الدرجة.';statusBox.className='notice warn';}
      return;
    }
    if(statusBox){statusBox.textContent='الحالة: قابل للاختبار. لا يظهر المجموع الكلي حتى تُسجل البنود الـ19.';statusBox.className='notice';}

    let completed=0,total=0,allComplete=true;
    for(const [sub,max] of Object.entries(maxima)){
      const xs=valuesFor(sub),done=xs.filter(v=>v!==null).length;
      completed+=done;
      if(validScores(xs)){
        const sum=xs.reduce((a,b)=>a+b,0);
        total+=sum;
        write(`#arat-${sub}-result`,`${sum} / ${max}`);
      }else{
        allComplete=false;
        write(`#arat-${sub}-result`,`${done}/${xs.length} بنود مسجلة`);
      }
    }
    write('#arat-completion',`${completed}/19 بندًا مسجلًا.`);
    write('#arat-total',allComplete&&completed===19?`${total} / 57`:'—');
  }

  $$('.arat-score').forEach(el=>el.addEventListener('change',recalc));
  ['#arat-status','#arat-arm','#arat-dominance'].forEach(s=>$(s)?.addEventListener('change',recalc));
  $('#arat-print')?.addEventListener('click',()=>window.print());
  $('#arat-clear')?.addEventListener('click',()=>{
    $$('input,textarea').forEach(el=>el.value='');
    $$('select').forEach(el=>el.selectedIndex=0);
    recalc();
    const live=$('#arat-live');if(live)live.textContent='تم مسح ورقة ARAT محليًا.';
  });
  recalc();
})();
