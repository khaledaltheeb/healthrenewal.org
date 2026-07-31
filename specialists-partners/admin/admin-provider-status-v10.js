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
    if(data.authValid===false){
      status('تنبيه تشغيلي: البريد الآلي غير متاح. استخدم «إنشاء رابط يدوي» من بطاقة الحساب حتى استبدال اعتماد البريد.','error');
    }
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
