(() => {
'use strict';

const API='https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev';
const SESSION_KEY='ptAdminIdentityV6';
let checkedToken='';

function session(){
  try{
    const value=JSON.parse(sessionStorage.getItem(SESSION_KEY)||'null');
    return value?.token&&Date.parse(value.expiresAt)>Date.now()?value:null;
  }catch(_){return null;}
}

function status(message,state='error'){
  const box=document.getElementById('admin-status');
  if(!box)return;
  box.hidden=false;
  box.dataset.state=state;
  box.textContent=message;
  box.focus?.();
}

function providerMessage(data){
  if(data.senderReady===false){
    if(data.senderCode==='sender_domain_not_verified'){
      return 'تنبيه تشغيلي: مفتاح البريد صالح، لكن نطاق عنوان المرسل غير موثّق. استخدم «إنشاء رابط يدوي» حتى توثيق نطاق مخصص في Resend.';
    }
    if(data.senderCode==='resend_test_sender'){
      return 'تنبيه تشغيلي: عنوان Resend التجريبي غير مناسب لاستعادة حسابات المختصين. استخدم «إنشاء رابط يدوي» حتى إعداد نطاق مرسل موثّق.';
    }
    return 'تنبيه تشغيلي: عنوان مرسل البريد غير جاهز. استخدم «إنشاء رابط يدوي» من بطاقة الحساب.';
  }
  if(data.authValid===false){
    return 'تنبيه تشغيلي: اعتماد مزود البريد غير صالح أو غير متاح. استخدم «إنشاء رابط يدوي» من بطاقة الحساب.';
  }
  return '';
}

async function check(){
  const value=session();
  const consoleBox=document.getElementById('admin-console');
  if(!value?.token||consoleBox?.hidden||value.token===checkedToken)return;
  checkedToken=value.token;
  try{
    const response=await fetch(`${API}/v1/admin/email-provider-status?check=${Date.now()}`,{
      method:'GET',
      headers:{accept:'application/json',authorization:`Bearer ${value.token}`,'x-requested-with':'pterminology-admin-provider-status-v10'},
      cache:'no-store',
      credentials:'omit',
      redirect:'error',
      referrerPolicy:'no-referrer'
    });
    const data=await response.json().catch(()=>({}));
    if(response.status===403)return;
    const message=providerMessage(data);
    if(message)status(message,'error');
  }catch(_){checkedToken='';}
}

function init(){
  const consoleBox=document.getElementById('admin-console');
  if(consoleBox)new MutationObserver(check).observe(consoleBox,{attributes:true,attributeFilter:['hidden']});
  window.addEventListener('pageshow',check);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)check();});
  check();
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
else init();
})();
