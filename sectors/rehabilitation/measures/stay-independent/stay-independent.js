(()=>{
'use strict';
const $$=(s,r=document)=>[...r.querySelectorAll(s)];
const $=(s,r=document)=>r.querySelector(s);
function score(){
  const rows=$$('#si-items .form-row');
  let total=0,answered=0;
  const key={fall:null,unsteady:null,worry:null};
  rows.forEach((row,i)=>{
    const checked=$(`input[name="si${i+1}"]:checked`,row);
    if(!checked)return;
    answered++;
    const yes=checked.value==='yes';
    if(yes) total+=Number(row.dataset.weight||0);
    if(row.dataset.key) key[row.dataset.key]=yes;
  });
  $('#si-score').textContent=`${total} / 14`;
  const complete=answered===12;
  let interpretation=`تمت الإجابة عن ${answered}/12 بندًا. لا تعتمد الدرجة قبل إكمال البنود.`;
  if(complete){
    const fell=key.fall===true;
    interpretation=total>=4?'النتيجة تبلغ عتبة CDC للفحص (4 فأكثر): يلزم تقييم عوامل خطر السقوط.':(fell?'المجموع أقل من 4، لكن وجود سقوط خلال السنة الماضية يبقي الشخص ضمن مسار تقييم الخطر في STEADI.':'المجموع أقل من 4 ولا يوجد سقوط مُبلّغ عنه؛ استمر في الوقاية وأعد التقييم عند تغير الحالة.');
  }
  $('#si-interpretation').textContent=interpretation;
  const keyAnswered=[key.fall,key.unsteady,key.worry].filter(v=>v!==null).length;
  $('#si-key-result').textContent=keyAnswered<3?`أُجيب عن ${keyAnswered}/3.`:([key.fall,key.unsteady,key.worry].some(Boolean)?'إجابة «نعم» على سؤال مفتاحي واحد على الأقل: يحتاج خطر السقوط إلى متابعة.':'جميع الأسئلة المفتاحية الثلاثة «لا».');
}
$$('#si-items input').forEach(el=>el.addEventListener('change',score));
$('#si-clear')?.addEventListener('click',()=>{$$('#stay-independent-sheet input').forEach(el=>{if(el.type==='radio'||el.type==='checkbox')el.checked=false;else el.value=''});$$('#stay-independent-sheet textarea').forEach(el=>el.value='');score()});
$('#si-print')?.addEventListener('click',()=>window.print());
score();
})();