(() => {
'use strict';
const state={providers:[],filtered:[]};
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={speech_language:'علاج النطق واللغة والتواصل',audiology:'السمع والسمعيات',special_education:'التربية الخاصة والخطط الفردية',early_intervention:'التدخل المبكر',occupational_therapy:'العلاج الوظيفي والتكامل الحسي',behavior_support:'الدعم السلوكي الإيجابي',learning_support:'صعوبات التعلم والدعم الأكاديمي',autism_support:'دعم اضطراب طيف التوحد',aac:'التواصل المعزز والبديل',family_training:'تدريب الأسرة ومقدمي الرعاية',psychology:'الدعم النفسي المساند',center:'مركز متعدد التخصصات'};
const statusLabels={verified:'موثّق',provisional:'تحقق أولي',pending:'قيد التحقق',unverified:'غير موثّق'};
const norm=value=>String(value||'').trim().toLowerCase();
const has=(items,value)=>!value||(Array.isArray(items)&&items.some(item=>norm(item)===norm(value)));
function card(p){
 const specialties=(p.specialties||[]).map(item=>`<span class="chip">${esc(labels[item]||item)}</span>`).join('');
 const status=p.verification?.status||'pending';
 return `<article class="provider-card"><div class="provider-top"><div><p class="eyebrow">${p.entityType==='center'?'مركز شريك':'مختص'}</p><h3>${esc(p.displayName)}</h3><div class="provider-meta">${esc(p.professionalTitle||p.centerType||'')}</div></div><span class="badge ${esc(status)}">${esc(statusLabels[status]||status)}</span></div><div class="chips">${specialties}</div><dl><dt>الموقع</dt><dd>${esc([p.location?.city,p.location?.country].filter(Boolean).join('، ')||'غير محدد')}</dd><dt>الفئات</dt><dd>${esc((p.ageGroups||[]).join('، ')||'غير محددة')}</dd><dt>طريقة الخدمة</dt><dd>${esc((p.serviceModes||[]).join('، ')||'غير محددة')}</dd><dt>اللغات</dt><dd>${esc((p.languages||[]).join('، ')||'غير محددة')}</dd></dl><p>${esc(p.shortBio||'')}</p><p class="small">آخر تحقق: ${esc(p.verification?.lastVerifiedAt||'لم يُسجّل بعد')}</p></article>`;
}
function render(){
 const list=$('provider-list'),count=$('provider-count'),empty=$('provider-empty');
 if(!list||!count||!empty)return;
 count.textContent=`${state.filtered.length} ملف منشور`;
 list.innerHTML=state.filtered.map(card).join('');
 empty.classList.toggle('hidden',state.filtered.length>0);
}
function filter(){
 const query=norm($('directory-search')?.value),type=$('entity-type')?.value||'',specialty=$('specialty-filter')?.value||'',city=norm($('city-filter')?.value),mode=$('mode-filter')?.value||'',age=$('age-filter')?.value||'',verified=Boolean($('verified-only')?.checked);
 state.filtered=state.providers.filter(p=>{
  const text=norm([p.displayName,p.professionalTitle,p.centerType,p.shortBio,...(p.specialties||[]),p.location?.city,p.location?.country].join(' '));
  return(!query||text.includes(query))&&(!type||p.entityType===type)&&has(p.specialties,specialty)&&(!city||norm(p.location?.city).includes(city))&&has(p.serviceModes,mode)&&has(p.ageGroups,age)&&(!verified||p.verification?.status==='verified');
 });render();
}
function reset(){['directory-search','entity-type','specialty-filter','city-filter','mode-filter','age-filter'].forEach(id=>{if($(id))$(id).value='';});if($('verified-only'))$('verified-only').checked=false;filter();}
function recommendations(need){return({speech:['speech_language','aac','audiology'],hearing:['audiology','speech_language','special_education'],learning:['learning_support','special_education'],autism:['autism_support','special_education','speech_language','occupational_therapy','behavior_support'],development:['early_intervention','speech_language','occupational_therapy','special_education'],behavior:['behavior_support','special_education','family_training'],independence:['occupational_therapy','special_education','family_training'],family:['family_training','special_education'],center:['center']}[need]||['special_education']);}
function match(event){
 event.preventDefault();const need=$('match-need')?.value||'',items=recommendations(need),names=items.map(item=>labels[item]||item);
 const age=$('match-age')?.value||'',mode=$('match-mode')?.value||'',city=norm($('match-city')?.value);
 const matches=state.providers.filter(p=>items.some(item=>has(p.specialties,item)||(item==='center'&&p.entityType==='center'))&&has(p.ageGroups,age)&&has(p.serviceModes,mode)&&(!city||norm(p.location?.city).includes(city))&&p.verification?.status==='verified');
 $('match-result').innerHTML=`<h3>المسار المقترح</h3><p>ابدأ بمراجعة التخصصات التالية، ثم يحدد المختص نطاق التقييم والخدمة بعد جمع المعلومات الوظيفية والتطورية:</p><div class="chips">${names.map(name=>`<span class="chip">${esc(name)}</span>`).join('')}</div><p><strong>الملفات المطابقة المنشورة حاليًا:</strong> ${matches.length}</p><p class="small">هذه مطابقة تنظيمية أولية وليست تشخيصًا أو توصية علاجية فردية.</p>`;
}
async function load(){try{const response=await fetch('data/providers.json',{cache:'no-store'});if(!response.ok)throw new Error('load');const data=await response.json();state.providers=(data.providers||[]).filter(p=>p.publicationStatus==='published');state.filtered=[...state.providers];if($('directory-updated'))$('directory-updated').textContent=data.updatedAt||'غير محدد';render();}catch(error){state.providers=[];state.filtered=[];render();}}
document.addEventListener('DOMContentLoaded',()=>{load();['directory-search','entity-type','specialty-filter','city-filter','mode-filter','age-filter','verified-only'].forEach(id=>$(id)?.addEventListener('input',filter));$('reset-filters')?.addEventListener('click',reset);$('matcher-form')?.addEventListener('submit',match);});
})();