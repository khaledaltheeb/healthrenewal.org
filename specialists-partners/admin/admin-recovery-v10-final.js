(() => {
'use strict';

const SESSION_KEY='ptAdminIdentityV6';
const API='https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev';
const nativeFetch=window.fetch.bind(window);
let ownerActive=false;
let activating=false;
let providerWarningShown=false;

window.fetch=async (...args)=>{
  const response=await nativeFetch(...args);
  try{
    const raw=typeof args[0]==='string'?args[0]:args[0]?.url||'';
    const url=new URL(raw,location.href);
    if(url.origin===new URL(API).origin&&url.pathname==='/v1/admin/users'&&String(args[1]?.method||'GET').toUpperCase()==='POST'){
      const data=await response.clone().json().catch(()=>({}));
      if(data.partialSuccess)window.dispatchEvent(new CustomEvent('pt-admin-partial-success',{detail:data}));
    }
  }catch(_){}
  return response;
};

function readSession(){
  try{
    const value=JSON.parse(sessionStorage.getItem(SESSION_KEY)||'null');
    if(value?.token&&Date.parse(value.expiresAt)>Date.now())return value;
  }catch(_){}
  return null;
}

function status(message,state='loading'){
  const box=document.getElementById('admin-status');
  if(!box)return;
  box.hidden=false;
  box.dataset.state=state;
  box.textContent=message;
  box.focus?.();
}

async function api(path,options={}){
  const session=readSession();
  if(!session?.token)throw new Error('يلزم تسجيل الدخول بحساب المالك.');
  const headers=new Headers(options.headers||{});
  headers.set('accept','application/json');
  headers.set('content-type','application/json;charset=UTF-8');
  headers.set('authorization',`Bearer ${session.token}`);
  headers.set('x-requested-with','pterminology-admin-recovery-v10');
  const response=await nativeFetch(`${API}${path}`,{...options,headers,cache:'no-store',credentials:'omit',redirect:'error',referrerPolicy:'no-referrer'});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.message||'تعذر إكمال عملية الاستعادة.');
  return data;
}

function ensureDialog(){
  let dialog=document.getElementById('manual-reset-dialog');
  if(dialog)return dialog;
  dialog=document.createElement('dialog');
  dialog.id='manual-reset-dialog';
  dialog.className='manual-reset-dialog';
  dialog.innerHTML=`<form method="dialog" class="panel"><h2>رابط إعادة تعيين يدوي</h2><p>هذا الرابط لمرة واحدة. أرسله لصاحب الحساب عبر قناة موثوقة، ولا تضعه في ملاحظات عامة.</p><label for="manual-reset-url">الرابط</label><textarea id="manual-reset-url" rows="5" readonly dir="ltr"></textarea><p id="manual-reset-expiry" class="small"></p><div class="actions"><button class="button primary" id="manual-reset-copy" type="button">نسخ الرابط</button><button class="button secondary" value="close">إغلاق</button></div></form>`;
  document.body.append(dialog);
  dialog.querySelector('#manual-reset-copy').addEventListener('click',async()=>{
    const field=dialog.querySelector('#manual-reset-url');
    try{await navigator.clipboard.writeText(field.value);status('تم نسخ الرابط اليدوي.','success');}
    catch(_){field.select();document.execCommand('copy');status('تم نسخ الرابط اليدوي.','success');}
  });
  dialog.addEventListener('close',()=>{dialog.querySelector('#manual-reset-url').value='';});
  return dialog;
}

async function createManualLink(card,button){
  const userId=card.dataset.userId;
  if(!userId)return;
  button.disabled=true;
  status('جارٍ إنشاء رابط يدوي آمن…');
  try{
    const data=await api(`/v1/admin/users/${encodeURIComponent(userId)}/password-reset-link`,{method:'POST',body:'{}'});
    const dialog=ensureDialog();
    dialog.querySelector('#manual-reset-url').value=data.resetUrl||'';
    const expiry=data.expiresAt?new Date(data.expiresAt).toLocaleString('ar-JO',{dateStyle:'medium',timeStyle:'short'}):'—';
    dialog.querySelector('#manual-reset-expiry').textContent=`ينتهي الرابط: ${expiry}`;
    dialog.showModal();
    status('تم إنشاء رابط يدوي، وأصبحت جميع الروابط الأقدم غير صالحة.','success');
  }catch(error){status(error.message||'تعذر إنشاء الرابط اليدوي.','error');}
  finally{button.disabled=false;}
}

function injectButtons(){
  for(const card of document.querySelectorAll('#users-list .admin-card[data-user-id]')){
    const existing=card.querySelector('[data-action="manual-reset-user"]');
    if(!ownerActive){existing?.remove();continue;}
    const actions=card.querySelector('.actions');
    if(!actions||existing)continue;
    const button=document.createElement('button');
    button.className='button secondary';
    button.type='button';
    button.dataset.action='manual-reset-user';
    button.textContent='إنشاء رابط يدوي';
    button.addEventListener('click',()=>createManualLink(card,button));
    actions.insertBefore(button,actions.querySelector('[data-action="archive-user"]'));
  }
}

async function currentRole(){
  const session=readSession();
  if(!session?.token)return '';
  try{
    const response=await nativeFetch(`${API}/v1/auth/session`,{headers:{accept:'application/json',authorization:`Bearer ${session.token}`,'x-requested-with':'pterminology-admin-recovery-v10'},cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer'});
    const data=await response.json().catch(()=>({}));
    return response.ok?String(data.user?.role||''):'';
  }catch(_){return '';}
}

async function showProviderState(){
  if(providerWarningShown)return;
  try{
    const response=await nativeFetch(`${API}/health?deep=1&admin=${Date.now()}`,{cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer'});
    const data=await response.json().catch(()=>({}));
    if(data.emailProvider?.authValid===false){
      providerWarningShown=true;
      status('تنبيه تشغيلي: البريد الآلي غير متاح حاليًا. حساب المالك يستطيع إنشاء رابط يدوي آمن من بطاقة الحساب.','error');
    }
  }catch(_){}
}

async function activate(){
  if(activating)return;
  const consoleBox=document.getElementById('admin-console');
  if(!consoleBox||consoleBox.hidden||!readSession()){
    ownerActive=false;
    injectButtons();
    return;
  }
  activating=true;
  try{
    ownerActive=(await currentRole())==='owner';
    injectButtons();
    await showProviderState();
  }finally{activating=false;}
}

function init(){
  const list=document.getElementById('users-list');
  const consoleBox=document.getElementById('admin-console');
  if(list)new MutationObserver(injectButtons).observe(list,{childList:true,subtree:true});
  if(consoleBox)new MutationObserver(activate).observe(consoleBox,{attributes:true,attributeFilter:['hidden']});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)activate();});
  window.addEventListener('pageshow',activate);
  activate();
}

window.addEventListener('pt-admin-partial-success',(event)=>{
  status(event.detail?.message||'تمت العملية جزئيًا. راجع الحسابات.','error');
  setTimeout(()=>location.reload(),1800);
});

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
else init();
})();
