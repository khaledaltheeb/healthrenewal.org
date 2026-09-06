(()=>{
  'use strict';
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const maxima={grasp:18,grip:12,pinch:18,gross:9};
  const tasks=[
    ['grasp','نقل كتلة كبيرة مرجعية (نحو 10 سم)'],['grasp','نقل كتلة صغيرة مرجعية (نحو 2.5 سم)'],['grasp','نقل كتلة متوسطة مرجعية (نحو 5 سم)'],['grasp','نقل كتلة متوسطة-كبيرة مرجعية (نحو 7.5 سم)'],['grasp','التعامل مع الكرة المرجعية في العدة'],['grasp','التعامل مع الجسم الحجري/المستطيل المرجعي'],
    ['grip','صب الماء بين وعاءين وفق إعداد البروتوكول'],['grip','التعامل مع الأنبوب الأكبر المرجعي'],['grip','التعامل مع الأنبوب الأصغر المرجعي'],['grip','وضع الغسالة/الحلقة على المسمار المرجعي'],
    ['pinch','قرص الجسم الكروي الصغير بين الإبهام والبنصر'],['pinch','قرص الجسم الكروي الأكبر بين الإبهام والبنصر'],['pinch','قرص الجسم الكروي الصغير بين الإبهام والوسطى'],['pinch','قرص الجسم الكروي الأكبر بين الإبهام والوسطى'],['pinch','قرص الجسم الكروي الصغير بين الإبهام والسبابة'],['pinch','قرص الجسم الكروي الأكبر بين الإبهام والسبابة'],
    ['gross','تحريك اليد إلى خلف الرأس'],['gross','تحريك اليد إلى أعلى الرأس'],['gross','تحريك اليد باتجاه الفم']
  ];
  const subLabel={grasp:'Grasp',grip:'Grip',pinch:'Pinch',gross:'Gross'};
  function renderItems(){const body=$('#arat-items');if(!body)return;body.innerHTML=tasks.map((t,i)=>`<tr><td>${i+1}</td><td>${subLabel[t[0]]}</td><td>${t[1]}</td><td><select class="arat-score" data-subscale="${t[0]}" aria-label="درجة البند ${i+1}"><option value="">—</option><option value="0">0</option><option value="1">1</option><option value="2">2</option><option value="3">3</option></select></td><td><input aria-label="ملاحظة البند ${i+1}"></td></tr>`).join('');}
  function valuesFor(subscale){return $$(`.arat-score[data-subscale="${subscale}"]`).map(el=>String(el.value).trim()===''?null:Number(el.value));}
  function write(id,text){const el=$(id);if(el)el.textContent=text;}
  function validScores(xs){return xs.length>0&&xs.every(v=>Number.isInteger(v)&&v>=0&&v<=3);}
  function recalc(){
    const status=$('#arat-status')?.value||'testable',statusBox=$('#arat-status-note');
    if(status!=='testable'){
      for(const sub of Object.keys(maxima))write(`#arat-${sub}-result`,'—');write('#arat-total','—');write('#arat-completion','الاختبار غير قابل للتفسير كدرجة معيارية في الحالة الحالية.');
      if(statusBox){statusBox.textContent=status==='not-testable'?'الحالة: غير قابل للاختبار — لا تُحسب الدرجة.':'الحالة: أوقف لأسباب السلامة/التعب — لا تُحسب الدرجة.';statusBox.className='notice warn';}return;
    }
    if(statusBox){statusBox.textContent='الحالة: قابل للاختبار. لا يظهر المجموع الكلي حتى تُسجل البنود الـ19.';statusBox.className='notice';}
    let completed=0,total=0,allComplete=true;
    for(const [sub,max] of Object.entries(maxima)){const xs=valuesFor(sub),done=xs.filter(v=>v!==null).length;completed+=done;if(validScores(xs)){const sum=xs.reduce((a,b)=>a+b,0);total+=sum;write(`#arat-${sub}-result`,`${sum} / ${max}`);}else{allComplete=false;write(`#arat-${sub}-result`,`${done}/${xs.length} بنود مسجلة`);}}
    write('#arat-completion',`${completed}/19 بندًا مسجلًا.`);write('#arat-total',allComplete&&completed===19?`${total} / 57`:'—');
  }
  renderItems();$$('.arat-score').forEach(el=>el.addEventListener('change',recalc));['#arat-status','#arat-arm','#arat-dominance'].forEach(s=>$(s)?.addEventListener('change',recalc));
  $('#arat-print')?.addEventListener('click',()=>window.print());$('#arat-clear')?.addEventListener('click',()=>{$$('input,textarea').forEach(el=>el.value='');$$('select').forEach(el=>el.selectedIndex=0);recalc();const live=$('#arat-live');if(live)live.textContent='تم مسح ورقة ARAT محليًا.';});recalc();
})();
