import identityWorker from './index-v10.js';

const BUILD_VERSION = '10.1.0';
const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
const PASSWORD_ITERATIONS = 310_000;
const MAX_BODY_BYTES = 64_000;

export default {
  async scheduled(event, env, ctx) {
    if (typeof identityWorker.scheduled === 'function') return identityWorker.scheduled(event, env, ctx);
  },

  async fetch(request, env, ctx) {
    const origin = request.headers.get('origin') || '';
    if (request.method === 'OPTIONS') return new Response(null, {status:204, headers:corsHeaders(origin, env)});

    const url = new URL(request.url);
    if (request.method === 'POST' && url.pathname === '/v1/auth/password/reset') {
      const body = await request.clone().json().catch(() => ({}));
      if (!strictPassword(body.password)) {
        return json({error:'weak_password', message:'استخدم 12 محرفًا على الأقل ومزيجًا من الحروف والأرقام والرموز. تدعم السياسة الحروف العربية.'},400,corsHeaders(origin,env));
      }
    }

    if (request.method === 'POST' && url.pathname === '/v1/account/password/change') {
      try {
        return await changePassword(request,env,corsHeaders(origin,env));
      } catch (error) {
        const status=Number(error.status)||500;
        return json({error:error.code||'internal_error',message:status===500?'حدث خطأ داخلي.':error.message},status,corsHeaders(origin,env));
      }
    }

    const response = await identityWorker.fetch(request, env, ctx);
    if (request.method === 'GET' && url.pathname === '/health') {
      const data = await response.clone().json().catch(() => ({}));
      const checks = {...(data.checks || {}), corsPreflight:true, strictPasswordPolicy:true, accountPasswordPolicy:true};
      const ok = data.ok === true && Object.values(checks).every(Boolean);
      return json({...data,ok,version:BUILD_VERSION,checks},ok?200:503,corsHeaders(origin,env));
    }
    return response;
  }
};

async function changePassword(request,env,cors) {
  await rateLimit(request,env,'account-password-change-v10',12);
  const actor=await requireIdentityBound(request,env);
  const body=await parseJson(request);
  const newPassword=String(body.newPassword||'');
  if(!strictPassword(newPassword)) fail('استخدم 12 محرفًا على الأقل ومزيجًا من الحروف والأرقام والرموز. تدعم السياسة الحروف العربية.',400,'weak_password');
  const requiresSetup=!actor.password_hash||Number(actor.must_change_password)===1;
  if(!requiresSetup&&!(await verifyPassword(body.currentPassword,actor,env))) fail('كلمة المرور الحالية غير صحيحة.',401,'invalid_current_password');
  if(!requiresSetup&&(await verifyPassword(newPassword,actor,env))) fail('يجب أن تختلف كلمة المرور الجديدة عن الحالية.',409,'password_reuse');

  const record=await createPasswordRecord(newPassword,env);
  const now=new Date().toISOString();
  const results=await env.DB.batch([
    env.DB.prepare(`UPDATE identity_users SET password_hash=?,password_salt=?,password_iterations=?,password_set_at=?,must_change_password=0,failed_login_count=0,locked_until=NULL,updated_at=? WHERE id=? AND status='active'`).bind(record.hash,record.salt,record.iterations,now,now,actor.id),
    env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE user_id=? AND id<>? AND revoked_at IS NULL`).bind(now,actor.id,actor.session_id),
    env.DB.prepare(`UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL`).bind(now,actor.id)
  ]);
  if(Number(results?.[0]?.meta?.changes||0)!==1) fail('تعذر حفظ كلمة المرور بأمان.',409,'password_change_commit_failed');
  await identityAudit(env,actor.id,'password_changed',actor.id,actor.provider_id,{otherSessionsRevoked:true,resetLinksRevoked:true});
  return json({ok:true,message:'تم تغيير كلمة المرور وإلغاء الجلسات الأخرى وروابط الاستعادة السابقة.'},200,cors);
}

async function requireIdentityBound(request,env) {
  const raw=bearerToken(request);
  const hash=await sha256(raw);
  const now=new Date().toISOString();
  const row=await env.DB.prepare(`SELECT s.id AS session_id,s.token_hash,s.expires_at,s.ip_hash,s.user_agent_hash,u.* FROM identity_sessions s JOIN identity_users u ON u.id=s.user_id WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND u.status='active' LIMIT 1`).bind(hash,now).first();
  if(!row||!constantTimeEqual(hash,row.token_hash)) fail('انتهت جلسة الدخول أو لم تعد صالحة.',401,'session_expired');
  const uaHash=await sha256(`${request.headers.get('user-agent')||''}|${env.RATE_LIMIT_SALT}`);
  if(!constantTimeEqual(uaHash,row.user_agent_hash)) {
    await env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL`).bind(now,row.session_id).run();
    fail('تغيرت بيئة الجلسة. سجّل الدخول من جديد.',401,'session_binding_mismatch');
  }
  if(String(env.SESSION_BIND_IP||'').toLowerCase()==='strict') {
    const ipHash=await sha256(`${requestIp(request)}|${env.RATE_LIMIT_SALT}`);
    if(!constantTimeEqual(ipHash,row.ip_hash)) {
      await env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL`).bind(now,row.session_id).run();
      fail('تغير عنوان الاتصال. سجّل الدخول من جديد.',401,'session_ip_mismatch');
    }
  }
  await env.DB.prepare(`UPDATE identity_sessions SET last_used_at=? WHERE id=?`).bind(now,row.session_id).run();
  return row;
}

function strictPassword(value) {
  const password = String(value || '');
  if (password.length < 12 || password.length > 128) return false;
  const groups = [
    /\p{L}/u.test(password),
    /\d/u.test(password),
    /[^\p{L}\d\s]/u.test(password)
  ].filter(Boolean).length;
  const latinCaseBonus = /[a-z]/.test(password) && /[A-Z]/.test(password);
  return groups >= 3 || (groups >= 2 && latinCaseBonus);
}

async function createPasswordRecord(password,env) {
  const salt=crypto.getRandomValues(new Uint8Array(16));
  return {hash:await passwordKey(String(password),salt,passwordPepper(env),PASSWORD_ITERATIONS),salt:toBase64Url(salt),iterations:PASSWORD_ITERATIONS};
}

async function verifyPassword(password,user,env) {
  if(!user.password_hash||!user.password_salt||!user.password_iterations)return false;
  const hash=await passwordKey(String(password||''),fromBase64Url(user.password_salt),passwordPepper(env),Number(user.password_iterations));
  return constantTimeEqual(hash,user.password_hash);
}

async function passwordKey(password,salt,pepper,iterations) {
  const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(`${password}\u0000${pepper}`),'PBKDF2',false,['deriveBits']);
  const bits=await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',salt,iterations},material,256);
  return toBase64Url(new Uint8Array(bits));
}

function passwordPepper(env) { return String(env.PASSWORD_PEPPER||env.RATE_LIMIT_SALT||''); }
function bearerToken(request) { const match=(request.headers.get('authorization')||'').match(/^Bearer\s+([A-Za-z0-9_-]{32,500})$/i); if(!match)fail('يلزم تسجيل الدخول.',401,'authentication_required'); return match[1]; }

async function parseJson(request) {
  if(!(request.headers.get('content-type')||'').includes('application/json'))fail('يجب إرسال البيانات بصيغة JSON.',415,'unsupported_media_type');
  const declared=Number(request.headers.get('content-length')||0);
  if(declared>MAX_BODY_BYTES)fail('حجم الطلب أكبر من الحد المسموح.',413,'payload_too_large');
  const text=await request.text();
  if(new TextEncoder().encode(text).byteLength>MAX_BODY_BYTES)fail('حجم الطلب أكبر من الحد المسموح.',413,'payload_too_large');
  try{const parsed=JSON.parse(text);if(!parsed||Array.isArray(parsed)||typeof parsed!=='object')fail('جسم الطلب غير صالح.',400,'invalid_json');return parsed;}
  catch(error){if(error?.code)throw error;fail('تعذر قراءة البيانات المرسلة.',400,'invalid_json');}
}

async function rateLimit(request,env,scope,limit) {
  if(!env.DB||!env.RATE_LIMIT_SALT)fail('خدمة الحماية غير جاهزة.',503,'rate_limit_unavailable');
  const key=`${scope}:${await sha256(`${scope}|${requestIp(request)}|${env.RATE_LIMIT_SALT}`)}`;
  const bucket=new Date().toISOString().slice(0,13);
  await env.DB.prepare(`INSERT INTO rate_limits (key,bucket,count,updated_at) VALUES (?,?,1,?) ON CONFLICT(key,bucket) DO UPDATE SET count=count+1,updated_at=excluded.updated_at`).bind(key,bucket,new Date().toISOString()).run();
  const row=await env.DB.prepare(`SELECT count FROM rate_limits WHERE key=? AND bucket=?`).bind(key,bucket).first();
  if(Number(row?.count||0)>limit)fail('تم تجاوز عدد المحاولات المسموح مؤقتًا.',429,'rate_limited');
}

async function identityAudit(env,actorUserId,eventType,targetUserId,entityId,metadata) {
  await env.DB.prepare(`INSERT INTO identity_audit_log (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at) VALUES (?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),actorUserId,eventType,targetUserId,entityId||null,JSON.stringify(metadata||{}),new Date().toISOString()).run();
}

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://healthrenewal.org').split(',').map(value=>value.trim()).filter(Boolean);
  const headers = {
    'access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers':'authorization,content-type,idempotency-key,x-requested-with,x-bootstrap-key,x-recovery-export-key',
    'access-control-max-age':'86400',
    'cache-control':'no-store',
    'content-security-policy':"default-src 'none'; frame-ancestors 'none'",
    'cross-origin-resource-policy':'same-site',
    'referrer-policy':'no-referrer',
    'strict-transport-security':'max-age=31536000; includeSubDomains',
    'vary':'Origin',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY'
  };
  if (origin && allowed.includes(origin)) headers['access-control-allow-origin']=origin;
  return headers;
}

function json(payload,status=200,headers={}) { return new Response(JSON.stringify(payload),{status,headers:{...JSON_HEADERS,...headers}}); }
function fail(message,status=400,code='invalid_request') { const error=new Error(message);error.status=status;error.code=code;throw error; }
function requestIp(request) { return request.headers.get('cf-connecting-ip')||request.headers.get('x-forwarded-for')||'unknown'; }
function toBase64Url(bytes) { let value='';for(const byte of bytes)value+=String.fromCharCode(byte);return btoa(value).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); }
function fromBase64Url(value) { const text=String(value);const padded=text.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-text.length%4)%4);return Uint8Array.from(atob(padded),char=>char.charCodeAt(0)); }
async function sha256(value) { const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(String(value)));return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join(''); }
function constantTimeEqual(a,b) { a=String(a||'');b=String(b||'');let diff=a.length^b.length;const n=Math.max(a.length,b.length);for(let i=0;i<n;i+=1)diff|=(a.charCodeAt(i)||0)^(b.charCodeAt(i)||0);return diff===0; }
