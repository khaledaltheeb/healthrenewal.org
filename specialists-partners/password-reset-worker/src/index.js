const IDENTITY_RESET_URL = 'https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev/v1/auth/password/reset';
const ADMIN_LOGIN_URL = 'https://healthrenewal.org/specialists-partners/admin/?v=10';
const BUILD_VERSION = '1.0.0';
const MAX_BODY_BYTES = 4096;

export default {
  async fetch(request) {
    const url = new URL(request.url);

    if (request.method === 'GET' && url.pathname === '/health') {
      return json({ok:true, service:'pterminology-password-reset', version:BUILD_VERSION, identityResetUrl:IDENTITY_RESET_URL, time:new Date().toISOString()}, 200);
    }

    if (request.method === 'GET' && ['/', '/password-reset', '/password-reset/'].includes(url.pathname)) {
      return passwordResetPage();
    }

    if (request.method === 'POST' && url.pathname === '/submit') {
      return submitPasswordReset(request);
    }

    return json({error:'not_found', message:'المسار غير موجود.'}, 404);
  }
};

async function submitPasswordReset(request) {
  const requestUrl = new URL(request.url);
  const origin = request.headers.get('origin') || '';
  if (origin && origin !== requestUrl.origin) {
    return json({error:'forbidden_origin', message:'مصدر الطلب غير مسموح.'}, 403);
  }

  if (!(request.headers.get('content-type') || '').includes('application/json')) {
    return json({error:'unsupported_media_type', message:'يجب إرسال البيانات بصيغة JSON.'}, 415);
  }

  const declared = Number(request.headers.get('content-length') || 0);
  if (declared > MAX_BODY_BYTES) {
    return json({error:'payload_too_large', message:'حجم الطلب أكبر من الحد المسموح.'}, 413);
  }

  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > MAX_BODY_BYTES) {
    return json({error:'payload_too_large', message:'حجم الطلب أكبر من الحد المسموح.'}, 413);
  }

  let body;
  try {
    body = JSON.parse(text);
  } catch (_) {
    return json({error:'invalid_json', message:'تعذر قراءة البيانات المرسلة.'}, 400);
  }

  const token = String(body?.token || '').trim();
  const password = String(body?.password || '');
  if (!/^[A-Za-z0-9_-]{32,500}$/.test(token)) {
    return json({error:'invalid_reset_token', message:'رابط إعادة التعيين غير صالح أو انتهت صلاحيته.'}, 401);
  }
  if (!strongPassword(password)) {
    return json({error:'weak_password', message:'كلمة المرور يجب أن تكون بين 12 و128 محرفًا وتحتوي ثلاثة أنواع على الأقل من الأحرف الكبيرة والصغيرة والأرقام والرموز.'}, 400);
  }

  try {
    const upstream = await fetch(IDENTITY_RESET_URL, {
      method:'POST',
      headers:{
        accept:'application/json',
        'content-type':'application/json;charset=UTF-8',
        'x-requested-with':'pterminology-password-reset-worker-v10'
      },
      body:JSON.stringify({token,password}),
      redirect:'manual'
    });
    const responseText = await upstream.text();
    return new Response(responseText, {
      status:upstream.status,
      headers:securityHeaders('application/json; charset=utf-8')
    });
  } catch (_) {
    return json({error:'identity_unavailable', message:'خدمة الهوية غير متاحة مؤقتًا. أعد المحاولة بعد قليل.'}, 502);
  }
}

function strongPassword(value) {
  if (value.length < 12 || value.length > 128) return false;
  const classes = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((rule) => rule.test(value)).length;
  return classes >= 3;
}

function passwordResetPage() {
  const nonce = randomNonce();
  const html = `<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="referrer" content="no-referrer">
<title>تعيين كلمة المرور | بوابة Cloudflare الآمنة</title>
<style nonce="${nonce}">
:root{font-family:Tahoma,Arial,sans-serif;color:#123f42;background:#f2faf8;line-height:1.75}*{box-sizing:border-box}body{margin:0;min-height:100vh;background:linear-gradient(180deg,#f8fcfb,#eaf6f4)}main{min-height:100vh;display:grid;place-items:center;padding:24px 14px}.card{width:min(700px,100%);background:#fff;border:1px solid #bedbd7;border-radius:26px;padding:clamp(24px,5vw,52px);box-shadow:0 24px 70px rgba(8,79,76,.13)}.eyebrow{text-align:center;color:#08736e;font-weight:700;margin:0}.mark{width:72px;height:72px;border-radius:22px;background:#08736e;color:#fff;display:grid;place-items:center;font-size:2rem;font-weight:700;margin:0 auto 10px}h1{text-align:center;font-size:clamp(2rem,5vw,3.3rem);line-height:1.2;margin:8px 0 12px}.intro{text-align:center;color:#526e70;margin:0 auto 24px;max-width:570px}.status{border:1px solid #a9cfca;background:#eff9f7;border-radius:16px;padding:14px 16px;margin-bottom:22px;font-weight:700}.status[data-state=error]{border-color:#e0a3aa;background:#fff2f3;color:#922d39}.status[data-state=success]{border-color:#78b58a;background:#eef9f0;color:#145b2b}form{display:grid;gap:12px}label{font-weight:700}input{width:100%;border:1px solid #aac9c6;border-radius:14px;padding:15px 16px;font:inherit;direction:ltr}input:focus{outline:3px solid rgba(0,109,103,.16);border-color:#006d67}.hint{margin:-4px 0 4px;color:#5b7072;font-size:.92rem}button,a.action{display:inline-flex;justify-content:center;align-items:center;border:0;border-radius:14px;padding:14px 20px;font:inherit;font-weight:700;background:#006d67;color:#fff;text-decoration:none;cursor:pointer}button:disabled{opacity:.65;cursor:wait}.actions{margin-top:18px}.note{text-align:center;color:#647a7c;font-size:.9rem;margin:24px 0 0}@media(max-width:520px){main{padding:14px 9px}.card{padding:24px 18px;border-radius:20px}}
</style>
</head>
<body>
<main><section class="card" aria-labelledby="title">
<div class="mark" aria-hidden="true">✓</div>
<p class="eyebrow">بوابة Cloudflare الآمنة · الإصدار 10</p>
<h1 id="title">تعيين كلمة مرور جديدة</h1>
<p class="intro">هذه الصفحة تعمل مباشرة على Cloudflare ولا تعتمد على GitHub Pages أو ملفات المتصفح القديمة.</p>
<div id="status" class="status" tabindex="-1" aria-live="polite">جارٍ التحقق من الرابط…</div>
<form id="form" hidden novalidate>
<label for="password">كلمة المرور الجديدة</label>
<input id="password" type="password" minlength="12" maxlength="128" autocomplete="new-password" required>
<p class="hint">12 محرفًا على الأقل، وثلاثة أنواع على الأقل من: أحرف كبيرة، أحرف صغيرة، أرقام، رموز.</p>
<label for="confirm">تأكيد كلمة المرور</label>
<input id="confirm" type="password" minlength="12" maxlength="128" autocomplete="new-password" required>
<button id="save" type="submit">حفظ كلمة المرور</button>
</form>
<div id="actions" class="actions" hidden><a class="action" href="${ADMIN_LOGIN_URL}">الانتقال إلى تسجيل الدخول</a></div>
<p class="note">لا تُرسل كلمة المرور بالبريد، ولا تُحفظ في الصفحة، ويُستهلك الرابط بعد نجاح الحفظ.</p>
</section></main>
<script nonce="${nonce}">
(() => {
  'use strict';
  const form=document.getElementById('form');
  const statusBox=document.getElementById('status');
  const save=document.getElementById('save');
  const actions=document.getElementById('actions');
  let token='';
  const setStatus=(message,state='loading')=>{statusBox.textContent=message;statusBox.dataset.state=state;statusBox.focus?.();};
  const strong=(value)=>value.length>=12&&value.length<=128&&[/[a-z]/,/[A-Z]/,/\\d/,/[^A-Za-z0-9]/].filter(rule=>rule.test(value)).length>=3;
  function init(){
    const params=new URLSearchParams(location.hash.replace(/^#/,''));
    token=params.get('resetToken')||'';
    history.replaceState(null,document.title,location.pathname+location.search);
    if(!/^[A-Za-z0-9_-]{32,500}$/.test(token)){setStatus('الرابط غير مكتمل أو انتهت صلاحيته. استخدم أحدث رسالة وصلت إلى بريدك.','error');return;}
    form.hidden=false;
    setStatus('تم تحميل رمز إعادة التعيين. أدخل كلمة المرور الجديدة ثم احفظها.','success');
  }
  form.addEventListener('submit',async(event)=>{
    event.preventDefault();
    if(!form.reportValidity())return;
    const password=document.getElementById('password').value;
    const confirm=document.getElementById('confirm').value;
    if(password!==confirm){setStatus('كلمتا المرور غير متطابقتين.','error');return;}
    if(!strong(password)){setStatus('كلمة المرور لا تحقق متطلبات القوة الموضحة.','error');return;}
    save.disabled=true;
    setStatus('جارٍ حفظ كلمة المرور مباشرة في خدمة الهوية…');
    try{
      const response=await fetch('/submit',{method:'POST',headers:{accept:'application/json','content-type':'application/json;charset=UTF-8','x-requested-with':'pterminology-password-reset-worker-v10'},body:JSON.stringify({token,password}),cache:'no-store',credentials:'omit',redirect:'error',referrerPolicy:'no-referrer'});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.message||('تعذر حفظ كلمة المرور (HTTP '+response.status+').'));
      token='';form.reset();form.hidden=true;actions.hidden=false;setStatus(data.message||'تم تعيين كلمة المرور بنجاح. يمكنك تسجيل الدخول الآن.','success');
    }catch(error){setStatus(error.message||'تعذر حفظ كلمة المرور.','error');}
    finally{save.disabled=false;}
  });
  init();
})();
</script>
</body></html>`;

  return new Response(html, {
    status:200,
    headers:{
      ...securityHeaders('text/html; charset=utf-8'),
      'content-security-policy':`default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`
    }
  });
}

function json(payload, status=200) {
  return new Response(JSON.stringify(payload), {status, headers:securityHeaders('application/json; charset=utf-8')});
}

function securityHeaders(contentType) {
  return {
    'content-type':contentType,
    'cache-control':'no-store, no-cache, must-revalidate, max-age=0',
    'pragma':'no-cache',
    'expires':'0',
    'referrer-policy':'no-referrer',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY',
    'cross-origin-resource-policy':'same-origin',
    'strict-transport-security':'max-age=31536000; includeSubDomains'
  };
}

function randomNonce() {
  const bytes=new Uint8Array(18);
  crypto.getRandomValues(bytes);
  let text='';
  for(const byte of bytes) text+=String.fromCharCode(byte);
  return btoa(text).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}
