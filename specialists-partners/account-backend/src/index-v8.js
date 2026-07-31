import baseWorker from './index.js';

const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
const BUILD_VERSION = '8.0.0';
const RESET_MINUTES = 30;
const MAX_BODY_BYTES = 64_000;

export default {
  async scheduled(event, env, ctx) {
    if (typeof baseWorker.scheduled === 'function') return baseWorker.scheduled(event, env, ctx);
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const cors = corsHeaders(request.headers.get('origin') || '', env);
    if (request.method === 'OPTIONS') return new Response(null, {status:204, headers:cors});

    try {
      if (request.method === 'GET' && url.pathname === '/health') return await health(request, env, ctx, cors);
      if (request.method === 'POST' && url.pathname === '/v1/auth/password/request') return await requestPasswordReset(request, env, cors);
      if (request.method === 'POST' && url.pathname === '/v1/internal/owner-password-reset') return await ownerPasswordReset(request, env, cors);
      return await baseWorker.fetch(request, env, ctx);
    } catch (error) {
      console.error('specialist_recovery_v8_error', error);
      const status = Number(error.status) || 500;
      return json({error:error.code || 'internal_error', message:status === 500 ? 'حدث خطأ داخلي.' : error.message}, status, cors);
    }
  }
};

async function health(request, env, ctx, cors) {
  const upstream = await baseWorker.fetch(request, env, ctx);
  const data = await upstream.json().catch(() => ({}));
  const checks = {
    ...(data.checks || {}),
    passwordResetBase:Boolean(validHttpsBase(env.PASSWORD_RESET_BASE_URL)),
    resendConfigured:Boolean(env.RESEND_API_KEY && env.FROM_EMAIL),
    recoveryOverlay:true
  };
  const ok = data.ok === true && Object.values(checks).every(Boolean);
  return json({...data, ok, version:BUILD_VERSION, checks}, ok ? 200 : 503, cors);
}

async function requestPasswordReset(request, env, cors) {
  await rateLimit(request, env, 'password-reset-ip-v8', 8);
  const body = await parseJson(request);
  await verifyTurnstile(body.turnstileToken, request, env, ['password_reset','account_login']);
  const email = validEmail(body.email);
  await rateLimit(request, env, 'password-reset-email-v8', 5, email);
  const requestId = crypto.randomUUID();
  const user = await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) AND status IN ('active','invited') LIMIT 1`).bind(email).first();

  if (user) {
    const purpose = user.status === 'invited' ? 'setup' : 'reset';
    try {
      const delivery = await issuePasswordReset(env, user, purpose, null, requestId);
      await identityAudit(env, null, 'password_email_sent', user.id, user.provider_id, {requestId, purpose, expiresAt:delivery.expiresAt, providerMessageId:delivery.providerMessageId});
    } catch (error) {
      await identityAudit(env, null, 'password_email_failed', user.id, user.provider_id, {requestId, purpose, error:safeError(error), providerDetail:error.providerDetail || null});
      fail('تعذر إرسال رسالة الاستعادة الآن. أعد المحاولة بعد دقائق.', 503, 'email_delivery_failed');
    }
  } else {
    await sleep(250 + Math.floor(Math.random() * 150));
  }

  return json({ok:true, requestId, message:'إذا كان البريد مرتبطًا بحساب، فسيصل رابط آمن خلال دقائق.'}, 202, cors);
}

async function ownerPasswordReset(request, env, cors) {
  requireBootstrapKey(request, env);
  const email = validEmail(env.OWNER_EMAIL || 'pterminology@gmail.com');
  const user = await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) AND status IN ('active','invited') LIMIT 1`).bind(email).first();
  if (!user) fail('حساب المالك غير موجود.', 404, 'owner_not_found');
  const requestId = crypto.randomUUID();
  const purpose = user.status === 'invited' ? 'setup' : 'reset';
  try {
    const delivery = await issuePasswordReset(env, user, purpose, user.id, requestId);
    await identityAudit(env, user.id, 'password_email_probe_sent', user.id, user.provider_id, {requestId, purpose, expiresAt:delivery.expiresAt, providerMessageId:delivery.providerMessageId});
    return json({ok:true, requestId, delivery:'sent', expiresAt:delivery.expiresAt, providerMessageId:delivery.providerMessageId}, 200, cors);
  } catch (error) {
    await identityAudit(env, user.id, 'password_email_probe_failed', user.id, user.provider_id, {requestId, purpose, error:safeError(error), providerDetail:error.providerDetail || null});
    const status = Number(error.status) || 503;
    return json({error:error.code || 'email_send_failed', message:error.message || 'تعذر تسليم البريد.', providerDetail:error.providerDetail || safeError(error)}, status, cors);
  }
}

async function issuePasswordReset(env, user, purpose='reset', requestedBy=null, requestId=crypto.randomUUID()) {
  const raw = randomToken(32);
  const hash = await sha256(raw);
  const now = new Date().toISOString();
  const expiresAt = new Date(Date.now() + RESET_MINUTES * 60_000).toISOString();
  const tokenId = crypto.randomUUID();
  await env.DB.batch([
    env.DB.prepare(`DELETE FROM password_reset_tokens WHERE user_id=? AND (expires_at<=? OR used_at IS NOT NULL)`).bind(user.id, now),
    env.DB.prepare(`INSERT INTO password_reset_tokens (id,user_id,token_hash,purpose,expires_at,requested_by_user_id,created_at) VALUES (?,?,?,?,?,?,?)`).bind(tokenId, user.id, hash, purpose, expiresAt, requestedBy, now)
  ]);

  const base = validHttpsBase(env.PASSWORD_RESET_BASE_URL);
  if (!base) {
    await env.DB.prepare(`DELETE FROM password_reset_tokens WHERE id=?`).bind(tokenId).run();
    fail('مسار إعادة التعيين غير مهيأ.', 503, 'reset_base_unavailable');
  }
  const link = `${base}?v=10#resetToken=${encodeURIComponent(raw)}`;
  try {
    const result = await sendEmail(env, {
      to:[user.email],
      subject:purpose === 'setup' ? 'تعيين كلمة مرور الحساب' : 'إعادة تعيين كلمة المرور',
      html:emailLayout('إدارة كلمة المرور', `<p>مرحبًا ${escapeHtml(user.display_name_ar)}،</p><p>استخدم الرابط التالي خلال ${RESET_MINUTES} دقيقة:</p><p><a href="${escapeHtml(link)}">${purpose === 'setup' ? 'تعيين كلمة المرور' : 'إعادة تعيين كلمة المرور'}</a></p><p>الرابط لمرة واحدة. تجاهل الرسالة إن لم تطلبها.</p>`),
      idempotencyKey:`password-v8/${purpose}/${user.id}/${requestId}`
    });
    return {expiresAt, providerMessageId:result.id || null};
  } catch (error) {
    await env.DB.prepare(`DELETE FROM password_reset_tokens WHERE id=?`).bind(tokenId).run();
    throw error;
  }
}

async function sendEmail(env, message) {
  if (!env.RESEND_API_KEY || !env.FROM_EMAIL) fail('خدمة البريد غير مهيأة.', 503, 'email_not_configured');
  let lastError = null;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const response = await fetch('https://api.resend.com/emails', {
        method:'POST',
        headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,'content-type':'application/json','idempotency-key':message.idempotencyKey},
        body:JSON.stringify({from:env.FROM_EMAIL,to:message.to,subject:message.subject,html:message.html})
      });
      const text = await response.text();
      let data = {};
      try { data = JSON.parse(text); } catch (_) {}
      if (response.ok) return data;
      lastError = new Error(`resend_http_${response.status}:${String(data.message || text).slice(0,180)}`);
      if (response.status < 500 && response.status !== 429) break;
    } catch (error) {
      lastError = error;
    }
    if (attempt < 3) await sleep(attempt * 750);
  }
  const error = new Error('تعذر تسليم البريد.');
  error.status = 503;
  error.code = 'email_send_failed';
  error.providerDetail = safeError(lastError);
  console.error('identity_email_failed_v8', error.providerDetail);
  throw error;
}

async function verifyTurnstile(tokenValue, request, env, allowedActions = []) {
  if (!env.TURNSTILE_SECRET) fail('خدمة التحقق غير جاهزة.', 503, 'turnstile_unavailable');
  const token = cleanString(tokenValue, 2048, true);
  const form = new FormData();
  form.set('secret', env.TURNSTILE_SECRET);
  form.set('response', token);
  form.set('remoteip', requestIp(request));
  form.set('idempotency_key', crypto.randomUUID());
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {method:'POST', body:form});
  const result = await response.json().catch(() => ({}));
  const hosts = String(env.TURNSTILE_EXPECTED_HOSTNAMES || 'khaledaltheeb.github.io').split(',').map(v=>v.trim()).filter(Boolean);
  const actionOk = !result.action || !allowedActions.length || allowedActions.includes(result.action);
  if (!response.ok || result.success !== true || !hosts.includes(result.hostname) || !actionOk) fail('تعذر التحقق من الاستخدام البشري.', 400, 'turnstile_failed');
}

async function rateLimit(request, env, scope, limit, identity='') {
  if (!env.DB || !env.RATE_LIMIT_SALT) fail('خدمة الحماية غير جاهزة.', 503, 'rate_limit_unavailable');
  const key = `${scope}:${await sha256(`${scope}|${identity || requestIp(request)}|${env.RATE_LIMIT_SALT}`)}`;
  const bucket = new Date().toISOString().slice(0,13);
  await env.DB.prepare(`INSERT INTO rate_limits (key,bucket,count,updated_at) VALUES (?,?,1,?) ON CONFLICT(key,bucket) DO UPDATE SET count=count+1,updated_at=excluded.updated_at`).bind(key,bucket,new Date().toISOString()).run();
  const row = await env.DB.prepare(`SELECT count FROM rate_limits WHERE key=? AND bucket=?`).bind(key,bucket).first();
  if (Number(row?.count || 0) > limit) fail('تم تجاوز عدد المحاولات المسموح مؤقتًا.', 429, 'rate_limited');
}

async function parseJson(request) {
  if (!(request.headers.get('content-type') || '').includes('application/json')) fail('يجب إرسال البيانات بصيغة JSON.', 415, 'unsupported_media_type');
  const declared = Number(request.headers.get('content-length') || 0);
  if (declared > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.', 413, 'payload_too_large');
  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.', 413, 'payload_too_large');
  try {
    const parsed = JSON.parse(text);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') fail('جسم الطلب غير صالح.', 400, 'invalid_json');
    return parsed;
  } catch (error) {
    if (error?.code) throw error;
    fail('تعذر قراءة البيانات المرسلة.', 400, 'invalid_json');
  }
}

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://healthrenewal.org').split(',').map(v=>v.trim()).filter(Boolean);
  const headers = {
    'access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers':'authorization,content-type,idempotency-key,x-requested-with,x-bootstrap-key',
    'access-control-max-age':'86400',
    'cache-control':'no-store',
    'content-security-policy':"default-src 'none'; frame-ancestors 'none'",
    'referrer-policy':'no-referrer',
    'strict-transport-security':'max-age=31536000; includeSubDomains',
    'vary':'Origin',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY'
  };
  if (origin && allowed.includes(origin)) headers['access-control-allow-origin'] = origin;
  return headers;
}

function requireBootstrapKey(request, env) {
  const supplied = cleanString(request.headers.get('x-bootstrap-key'), 500, true);
  const expected = String(env.ADMIN_API_KEY || '');
  if (!expected || !constantTimeEqual(supplied, expected)) fail('غير مصرح.', 403, 'forbidden');
}

async function identityAudit(env, actorUserId, eventType, targetUserId, entityId, metadata) {
  if (!env.DB) return;
  await env.DB.prepare(`INSERT INTO identity_audit_log (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at) VALUES (?,?,?,?,?,?,?)`).bind(crypto.randomUUID(), actorUserId || null, eventType, targetUserId || null, entityId || null, JSON.stringify(metadata || {}), new Date().toISOString()).run();
}

function validHttpsBase(value) {
  try {
    const url = new URL(String(value || ''));
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) return '';
    return url.href.replace(/\/$/, '');
  } catch (_) { return ''; }
}
function validEmail(value) {
  const email = cleanString(value, 254, true).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) fail('البريد الإلكتروني غير صالح.', 400, 'invalid_email');
  return email;
}
function cleanString(value, max=200, required=false) {
  const text = String(value ?? '').trim();
  if (required && !text) fail('أحد الحقول المطلوبة فارغ.', 400, 'missing_field');
  if (text.length > max) fail('أحد الحقول تجاوز الحد المسموح.', 400, 'field_too_long');
  return text;
}
function json(payload, status=200, extraHeaders={}) { return new Response(JSON.stringify(payload), {status, headers:{...JSON_HEADERS, ...extraHeaders}}); }
function fail(message, status=400, code='invalid_request') { const error = new Error(message); error.status=status; error.code=code; throw error; }
function requestIp(request) { return request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for') || 'unknown'; }
function randomToken(bytes=32) { const a=new Uint8Array(bytes); crypto.getRandomValues(a); return toBase64Url(a); }
function toBase64Url(bytes) { let s=''; for (const b of bytes) s += String.fromCharCode(b); return btoa(s).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); }
async function sha256(value) { const d=await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(value))); return Array.from(new Uint8Array(d), b=>b.toString(16).padStart(2,'0')).join(''); }
function constantTimeEqual(a,b) { a=String(a||''); b=String(b||''); let x=a.length^b.length; const n=Math.max(a.length,b.length); for(let i=0;i<n;i++)x|=(a.charCodeAt(i)||0)^(b.charCodeAt(i)||0); return x===0; }
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
function safeError(error) { return String(error?.message || error || 'unknown').slice(0,240); }
function emailLayout(title,body) { return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${escapeHtml(title)}</title></head><body style="font-family:Arial,sans-serif;background:#f4f8f7;color:#123;padding:24px"><main style="max-width:640px;margin:auto;background:white;border:1px solid #d9e8e5;border-radius:16px;padding:24px"><h1 style="color:#075f5b">${escapeHtml(title)}</h1>${body}<hr><p style="font-size:13px;color:#567">منصة الصحة النفسية وذوي الاحتياجات الخاصة</p></main></body></html>`; }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
