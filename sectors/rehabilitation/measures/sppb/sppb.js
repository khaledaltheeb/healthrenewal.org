(()=>{
'use strict';
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const num=id=>{const e=document.getElementById(id);if(!e||String(e.value).trim()==='')return null;const v=Number(e.value);return Number.isFinite(v)?v:null};
const checked=id=>Boolean(document.getElementById(id)?.checked);
const out=(id,v)=>{const e=document.getElementById(id);if(e)e.textContent=v};
const r2=v=>Math.round(v*100)/100;
function balanceScore(){
  const side=num('sppb-side'),semi=num('sppb-semi'),tandem=num('sppb-tandem');
  if(side===null)return null;
  if(side<10)return 0;
  if(semi===null)return null;
  if(semi<10)return 1;
  if(tandem===null)return null;
  if(tandem>=10)return 4;
  if(tandem>=3)return 3;
  return 2;
}
function gaitScore(){
  if(checked('sppb-gait-unable'))return {score:0,time:null};
  const vals=[num('sppb-gait1'),num('sppb-gait2')].filter(v=>v!==null&&v>0);
  if(!vals.length)return null;
  const t=r2(Math.min(...vals));
  const d=$('#sppb-distance')?.value||'4';
  let score;
  if(d==='3') score=t<=3.61?4:t<=4.65?3:t<=6.52?2:1;
  else score=t<=4.81?4:t<=6.20?3:t<=8.70?2:1;
  return {score,time:t};
}
function chairScore(){
  if(checked('sppb-chair-unable')||checked('sppb-chair-arms'))return {score:0,time:null};
  const raw=num('sppb-chair-time');
  if(raw===null)return null;
  const t=r2(raw);
  const score=t<=11.19?4:t<=13.69?3:t<=16.69?2:t<=60?1:0;
  return {score,time:t};
}
function recalc(){
  const b=balanceScore(),g=gaitScore(),c=chairScore();
  out('sppb-balance-score',b===null?'—':`${b} / 4`);
  out('sppb-gait-score',g===null?'—':`${g.score} / 4${g.time===null?'':` · أسرع زمن ${g.time.toFixed(2)} ث`}`);
  out('sppb-chair-score',c===null?'—':`${c.score} / 4${c.time===null?'':` · ${c.time.toFixed(2)} ث`}`);
  const total=b!==null&&g!==null&&c!==null?b+g.score+c.score:null;
  out('sppb-total',total===null?'—':`${total} / 12`);
  const note=$('#sppb-hierarchy');
  if(note){
    if(num('sppb-side')!==null&&num('sppb-side')<10)note.textContent='وفق التسلسل الرسمي: إذا لم يُحفظ الوقوف جنبًا إلى جنب 10 ثوانٍ، ينتهي قسم التوازن وتكون درجته 0.';
    else if(num('sppb-side')>=10&&num('sppb-semi')!==null&&num('sppb-semi')<10)note.textContent='وفق التسلسل الرسمي: إذا لم يُحفظ شبه الترادف 10 ثوانٍ، ينتهي قسم التوازن وتكون درجته 1.';
    else note.textContent='أدخل الأزمنة بالتسلسل الهرمي: جنبًا إلى جنب ← شبه ترادف ← ترادف.';
  }
}
$$('input,select,textarea').forEach(e=>{e.addEventListener('input',recalc);e.addEventListener('change',recalc)});
$('#sppb-print')?.addEventListener('click',()=>window.print());
$('#sppb-clear')?.addEventListener('click',()=>{$$('input,textarea').forEach(e=>{if(e.type==='checkbox')e.checked=false;else e.value=''});$$('select').forEach(e=>e.selectedIndex=0);recalc()});
recalc();
})();