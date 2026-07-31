const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
const BUILD_VERSION = '6.0.0';
const MAX_BODY_BYTES = 64_000;
const MAX_MESSAGE_LENGTH = 3_000;
const PASSWORD_ITERATIONS = 310_000;
const SESSION_HOURS = 12;
const RESET_MINUTES = 30;
const MAGIC_LINK_MINUTES = 15;
const USER_ROLES = ['owner','admin','reviewer','moderator','specialist'];
const USER_STATUSES = ['invited','active','suspended','archived'];
const CONVERSATION_STATUSES = ['open','closed','blocked','archived'];

export default {
  async scheduled(_event, env, ctx) {
    if (!env.DB) return;
    const now = new Date().toISOString();
    const oneDayAgo = new Date(Date.now() - 86_400_000).toISOString();
    const sevenDaysAgo = new Date(Date.now() - 7 * 86_400_000).toISOString();
    const ninetyDaysAgo = new Date(Date.now() - 90 * 86_400_000).toISOString();
    ctx.waitUntil(env.DB.batch([
      env.DB.prepare(`DELETE FROM specialist_login_tokens WHERE expires_at <= ? OR (used_at IS NOT NULL AND used_at < ?)` ).bind(now, oneDayAgo),
      env.DB.prepare(`DELETE FROM specialist_sessions WHERE expires_at <= ? OR (revoked_at IS NOT NULL AND revoked_at < ?)` ).bind(now, sevenDaysAgo),
      env.DB.prepare(`DELETE FROM identity_sessions WHERE expires_at <= ? OR (revoked_at IS NOT NULL AND revoked_at < ?)` ).bind(now, sevenDaysAgo),
      env.DB.prepare(`DELETE FROM password_reset_tokens WHERE expires_at <= ? OR (used_at IS NOT NULL AND used_at < ?)` ).bind(now, sevenDaysAgo),
      env.DB.prepare(`DELETE FROM specialist_message_requests WHERE created_at < ?`).bind(ninetyDaysAgo),
      env.DB.prepare(`DELETE FROM rate_limits WHERE bucket < strftime('%Y-%m-%dT%H','now','-30 day')`)
    ]));
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const cors = corsHeaders(request.headers.get('origin') || '', env);
    if (request.method === 'OPTIONS') return new Response(null, {status:204, headers:cors});

    try {
      if (request.method === 'GET' && url.pathname === '/health') return await health(env, cors);
      if (request.method === 'POST' && url.pathname === '/v1/internal/bootstrap-owner') {
        return await bootstrapOwner(request, env, ctx, cors);
      }

      if (request.method === 'POST' && url.pathname === '/v1/auth/login') return await passwordLogin(request, env, cors);
      if (request.method === 'POST' && url.pathname === '/v1/auth/password/request') return await requestPasswordReset(request, env, ctx, cors);
      if (request.method === 'POST' && url.pathname === '/v1/auth/password/reset') return await resetPassword(request, env, cors);

      // Backward-compatible passwordless specialist login.
      if (request.method === 'POST' && url.pathname === '/v1/specialist/session/request') return await requestMagicSession(request, env, ctx, cors);
      if (request.method === 'POST' && url.pathname === '/v1/specialist/session/verify') return await verifyMagicSession(request, env, cors);

      if (!url.pathname.startsWith('/v1/')) return json({error:'not_found', message:'المسار غير موجود.'}, 404, cors);
      const actor = await requireIdentity(request, env);

      if (request.method === 'POST' && url.pathname === '/v1/auth/logout') return await logout(env, cors, actor);
      if (request.method === 'POST' && url.pathname === '/v1/specialist/session/revoke') return await logout(env, cors, actor);
      if (request.method === 'GET' && url.pathname === '/v1/auth/session') return identitySession(cors, actor);
      if (request.method === 'GET' && url.pathname === '/v1/account/me') return await accountMe(env, cors, actor);
      if (request.method === 'PATCH' && url.pathname === '/v1/account/me') return await updateAccount(request, env, cors, actor);
      if (request.method === 'POST' && url.pathname === '/v1/account/password/change') return await changePassword(request, env, cors, actor);
      if (request.method === 'GET' && url.pathname === '/v1/account/profile-draft') return await getProfileDraft(env, cors, actor);
      if (request.method === 'PATCH' && url.pathname === '/v1/account/profile-draft') return await saveProfileDraft(request, env, cors, actor);
      if (request.method === 'POST' && url.pathname === '/v1/account/profile-draft/submit') return await submitProfileDraft(env, cors, actor);

      if (request.method === 'GET' && url.pathname === '/v1/specialist/me') return await specialistMe(env, cors, actor);
      if (request.method === 'GET' && url.pathname === '/v1/specialist/conversations') return await listSpecialistConversations(url, env, cors, actor);
      const conversationMatch = url.pathname.match(/^\/v1\/specialist\/conversations\/([a-z0-9-]+)$/i);
      if (conversationMatch && request.method === 'GET') return await getSpecialistConversation(env, cors, actor, conversationMatch[1]);
      if (conversationMatch && request.method === 'PATCH') return await updateSpecialistConversation(request, env, cors, actor, conversationMatch[1]);
      const messageMatch = url.pathname.match(/^\/v1\/specialist\/conversations\/([a-z0-9-]+)\/messages$/i);
      if (messageMatch && request.method === 'POST') return await createSpecialistMessage(request, env, ctx, cors, actor, messageMatch[1]);

      if (url.pathname.startsWith('/v1/admin/')) {
        requireRole(actor, ['owner','admin','reviewer','moderator']);
        if (request.method === 'GET' && url.pathname === '/v1/admin/overview') return await identityOverview(env, cors, actor);
        if (request.method === 'POST' && url.pathname === '/v1/admin/core-session') return await createCoreSession(env, cors, actor);
        if (request.method === 'GET' && url.pathname === '/v1/admin/users') return await listUsers(url, env, cors, actor);
        if (request.method === 'POST' && url.pathname === '/v1/admin/users') return await createUser(request, env, ctx, cors, actor);
        const userMatch = url.pathname.match(/^\/v1\/admin\/users\/([a-z0-9-]+)$/i);
        if (userMatch && request.method === 'PATCH') return await updateUser(request, env, cors, actor, userMatch[1]);
        if (userMatch && request.method === 'DELETE') return await archiveUser(request, env, cors, actor, userMatch[1]);
        const resetMatch = url.pathname.match(/^\/v1\/admin\/users\/([a-z0-9-]+)\/password-reset$/i);
        if (resetMatch && request.method === 'POST') return await adminPasswordReset(env, ctx, cors, actor, resetMatch[1]);
        const verifyMatch = url.pathname.match(/^\/v1\/admin\/users\/([a-z0-9-]+)\/verify$/i);
        if (verifyMatch && request.method === 'POST') return await verifyUser(env, cors, actor, verifyMatch[1]);
        if (request.method === 'GET' && url.pathname === '/v1/admin/profile-drafts') return await listProfileDrafts(url, env, cors, actor);
        const draftMatch = url.pathname.match(/^\/v1\/admin\/profile-drafts\/([a-z0-9-]+)$/i);
        if (draftMatch && request.method === 'PATCH') return await reviewProfileDraft(request, env, cors, actor, draftMatch[1]);
        if (request.method === 'GET' && url.pathname === '/v1/admin/identity-audit') return await listIdentityAudit(url, env, cors, actor);
      }

      return json({error:'not_found', message:'المسار غير موجود.'}, 404, cors);
    } catch (error) {
      console.error('specialist_identity_worker_error', error);
      const status = Number(error.status) || 500;
      return json({error:error.code || 'internal_error', message:status === 500 ? 'حدث خطأ داخلي.' : error.message}, status, cors);
    }
  }
};

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://healthrenewal.org').split(',').map(v => v.trim()).filter(Boolean);
  const headers = {
    'access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers':'authorization,content-type,idempotency-key,x-requested-with,x-bootstrap-key',
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
  if (origin && allowed.includes(origin)) headers['access-control-allow-origin'] = origin;
  return headers;
}

function json(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {status, headers:{...JSON_HEADERS, ...extraHeaders}});
}
function fail(message, status = 400, code = 'invalid_request') {
  const error = new Error(message); error.status = status; error.code = code; throw error;
}
function cleanString(value, max = 200, required = false) {
  const text = String(value ?? '').trim();
  if (required && !text) fail('أحد الحقول المطلوبة فارغ.', 400, 'missing_field');
  if (text.length > max) fail('أحد الحقول تجاوز الحد المسموح.', 400, 'field_too_long');
  return text;
}
function validEmail(value) {
  const email = cleanString(value, 254, true).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) fail('البريد الإلكتروني غير صالح.', 400, 'invalid_email');
  return email;
}
function validId(value, label = 'المعرف') {
  const id = cleanString(value, 90, true);
  if (!/^[a-z0-9][a-z0-9-]{2,89}$/i.test(id)) fail(`${label} غير صالح.`, 400, 'invalid_id');
  return id;
}
function validPhone(value) {
  const phone = cleanString(value, 24, false).replace(/[\s()-]/g, '');
  if (!phone) return null;
  if (!/^\+[1-9]\d{7,14}$/.test(phone)) fail('رقم الهاتف يجب أن يكون بصيغة دولية مثل +9627...', 400, 'invalid_phone');
  return phone;
}
function boundedInteger(value, fallback, min, max) {
  const n = Number.parseInt(String(value ?? ''), 10);
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : fallback;
}
function safeJson(value, fallback = {}) { try { return JSON.parse(value); } catch (_) { return fallback; } }
function requestIp(request) { return request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for') || 'unknown'; }
function randomToken(bytes = 32) { const a = new Uint8Array(bytes); crypto.getRandomValues(a); return toBase64Url(a); }
function toBase64Url(bytes) { let s=''; for (const b of bytes) s += String.fromCharCode(b); return btoa(s).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); }
function fromBase64Url(value) { const padded = String(value).replace(/-/g,'+').replace(/_/g,'/') + '==='.slice((String(value).length + 3) % 4); const s=atob(padded); return Uint8Array.from(s, c => c.charCodeAt(0)); }
async function sha256(value) { const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(value))); return Array.from(new Uint8Array(d), b => b.toString(16).padStart(2,'0')).join(''); }
function constantTimeEqual(a, b) { a=String(a||''); b=String(b||''); let x=a.length^b.length; const n=Math.max(a.length,b.length); for(let i=0;i<n;i++) x|=(a.charCodeAt(i)||0)^(b.charCodeAt(i)||0); return x===0; }

async function parseJson(request) {
  if (!(request.headers.get('content-type') || '').includes('application/json')) fail('يجب إرسال البيانات بصيغة JSON.', 415, 'unsupported_media_type');
  const declared = Number(request.headers.get('content-length') || 0);
  if (declared > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.', 413, 'payload_too_large');
  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.', 413, 'payload_too_large');
  try { const parsed=JSON.parse(text); if(!parsed || Array.isArray(parsed) || typeof parsed!=='object') fail('جسم الطلب غير صالح.',400,'invalid_json'); return parsed; }
  catch (e) { if (e?.code) throw e; fail('تعذر قراءة البيانات المرسلة.',400,'invalid_json'); }
}

async function rateLimit(request, env, scope, limit, identity = '') {
  if (!env.DB || !env.RATE_LIMIT_SALT) fail('خدمة الحماية غير جاهزة.', 503, 'rate_limit_unavailable');
  const key = `${scope}:${await sha256(`${scope}|${identity || requestIp(request)}|${env.RATE_LIMIT_SALT}`)}`;
  const bucket = new Date().toISOString().slice(0,13);
  await env.DB.prepare(`INSERT INTO rate_limits (key,bucket,count,updated_at) VALUES (?,?,1,?) ON CONFLICT(key,bucket) DO UPDATE SET count=count+1,updated_at=excluded.updated_at`).bind(key,bucket,new Date().toISOString()).run();
  const row = await env.DB.prepare(`SELECT count FROM rate_limits WHERE key=? AND bucket=?`).bind(key,bucket).first();
  if (Number(row?.count || 0) > limit) fail('تم تجاوز عدد المحاولات المسموح مؤقتًا.',429,'rate_limited');
}

async function verifyTurnstile(tokenValue, request, env, allowedActions = []) {
  if (!env.TURNSTILE_SECRET) fail('خدمة التحقق غير جاهزة.',503,'turnstile_unavailable');
  const token = cleanString(tokenValue, 2048, true);
  const form = new FormData();
  form.set('secret', env.TURNSTILE_SECRET); form.set('response', token); form.set('remoteip', requestIp(request)); form.set('idempotency_key', crypto.randomUUID());
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {method:'POST', body:form});
  const result = await response.json().catch(() => ({}));
  const hosts = String(env.TURNSTILE_EXPECTED_HOSTNAMES || 'khaledaltheeb.github.io').split(',').map(v=>v.trim()).filter(Boolean);
  const actionOk = !result.action || !allowedActions.length || allowedActions.includes(result.action);
  if (!response.ok || result.success !== true || !hosts.includes(result.hostname) || !actionOk) fail('تعذر التحقق من الاستخدام البشري.',400,'turnstile_failed');
}

async function health(env, cors) {
  const checks = {database:false, accountSchema:false, identitySchema:false, email:Boolean(env.RESEND_API_KEY && env.FROM_EMAIL), turnstile:Boolean(env.TURNSTILE_SECRET), rateLimitSalt:Boolean(env.RATE_LIMIT_SALT), accountBase:Boolean(env.ACCOUNT_BASE_URL), adminBase:Boolean(env.ADMIN_BASE_URL), coreApi:Boolean(env.CORE_API_BASE), bootstrapKey:Boolean(env.ADMIN_API_KEY)};
  try {
    await env.DB.prepare('SELECT 1 AS ok').first(); checks.database = true;
    const schema = await env.DB.prepare(`SELECT COUNT(*) AS count FROM sqlite_master WHERE type='table' AND name IN ('providers_private','conversations','messages','specialist_login_tokens','specialist_sessions','identity_users','identity_sessions','password_reset_tokens','provider_account_drafts','identity_audit_log')`).first();
    checks.accountSchema = Number(schema?.count || 0) >= 5;
    checks.identitySchema = Number(schema?.count || 0) === 10;
  } catch (e) { console.error('identity_health_db_error', e); }
  const ready = Object.values(checks).every(Boolean);
  return json({ok:ready, service:'pterminology-specialist-identity', version:BUILD_VERSION, checks, time:new Date().toISOString()}, ready ? 200 : 503, cors);
}

async function passwordKey(password, salt, pepper, iterations = PASSWORD_ITERATIONS) {
  const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(`${password}\u0000${pepper}`), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({name:'PBKDF2', hash:'SHA-256', salt, iterations}, material, 256);
  return toBase64Url(new Uint8Array(bits));
}
function passwordPepper(env) { return String(env.PASSWORD_PEPPER || env.RATE_LIMIT_SALT || ''); }
function validatePassword(password) {
  const value = String(password || '');
  if (value.length < 12 || value.length > 128) fail('كلمة المرور يجب أن تكون بين 12 و128 محرفًا.',400,'weak_password');
  const classes = [/[a-z]/.test(value),/[A-Z]/.test(value),/\d/.test(value),/[^A-Za-z0-9]/.test(value)].filter(Boolean).length;
  if (classes < 3) fail('استخدم ثلاثة أنواع على الأقل: أحرف صغيرة وكبيرة وأرقام ورموز.',400,'weak_password');
  return value;
}
async function createPasswordRecord(password, env) {
  const value=validatePassword(password), salt=crypto.getRandomValues(new Uint8Array(16)), iterations=PASSWORD_ITERATIONS;
  return {hash:await passwordKey(value,salt,passwordPepper(env),iterations), salt:toBase64Url(salt), iterations};
}
async function verifyPassword(password, user, env) {
  if (!user.password_hash || !user.password_salt || !user.password_iterations) return false;
  const hash = await passwordKey(String(password||''), fromBase64Url(user.password_salt), passwordPepper(env), Number(user.password_iterations));
  return constantTimeEqual(hash,user.password_hash);
}

function bearerToken(request) {
  const match=(request.headers.get('authorization')||'').match(/^Bearer\s+([A-Za-z0-9_-]{32,500})$/i);
  if(!match) fail('يلزم تسجيل الدخول.',401,'authentication_required');
  return match[1];
}
async function createIdentitySession(request, env, user) {
  const raw=randomToken(32), hash=await sha256(raw), now=new Date().toISOString();
  const hours=boundedInteger(env.IDENTITY_SESSION_HOURS,SESSION_HOURS,1,72), expiresAt=new Date(Date.now()+hours*3_600_000).toISOString();
  const ipHash=await sha256(`${requestIp(request)}|${env.RATE_LIMIT_SALT}`), uaHash=await sha256(`${request.headers.get('user-agent')||''}|${env.RATE_LIMIT_SALT}`);
  await env.DB.prepare(`INSERT INTO identity_sessions (id,user_id,token_hash,expires_at,ip_hash,user_agent_hash,created_at,last_used_at) VALUES (?,?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),user.id,hash,expiresAt,ipHash,uaHash,now,now).run();
  return {sessionToken:raw, expiresAt};
}
async function requireIdentity(request, env) {
  const raw=bearerToken(request), hash=await sha256(raw), now=new Date().toISOString();
  const row=await env.DB.prepare(`SELECT s.id AS session_id,s.token_hash,s.expires_at,u.*,p.display_name AS provider_display_name,p.status AS provider_status,p.notification_enabled,p.accepts_new_requests FROM identity_sessions s JOIN identity_users u ON u.id=s.user_id LEFT JOIN providers_private p ON p.provider_id=u.provider_id WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND u.status='active' LIMIT 1`).bind(hash,now).first();
  if(!row || !constantTimeEqual(hash,row.token_hash)) fail('انتهت جلسة الدخول أو لم تعد صالحة.',401,'session_expired');
  await env.DB.prepare(`UPDATE identity_sessions SET last_used_at=? WHERE id=?`).bind(now,row.session_id).run();
  return row;
}
function requireRole(actor, roles) { if(!roles.includes(actor.role)) fail('لا تملك الصلاحية المطلوبة.',403,'forbidden'); }
function identitySession(cors, actor) { return json({user:publicUser(actor),session:{expiresAt:actor.expires_at}},200,cors); }
function publicUser(row) { return {id:row.id,email:row.email,phone:row.phone_e164||null,displayNameAr:row.display_name_ar,displayNameEn:row.display_name_en||null,role:row.role,status:row.status,providerId:row.provider_id||null,verifiedAt:row.verified_at||null,emailVerifiedAt:row.email_verified_at||null,phoneVerifiedAt:row.phone_verified_at||null,emailNotifications:Number(row.email_notifications)===1,newMessageNotifications:Number(row.new_message_notifications)===1,mustChangePassword:Number(row.must_change_password)===1,lastLoginAt:row.last_login_at||null,createdAt:row.created_at,updatedAt:row.updated_at}; }

async function passwordLogin(request, env, cors) {
  await rateLimit(request,env,'identity-login-ip',12);
  const body=await parseJson(request); await verifyTurnstile(body.turnstileToken,request,env,['account_login','specialist_login']);
  const email=validEmail(body.email); await rateLimit(request,env,'identity-login-email',8,email);
  const user=await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) LIMIT 1`).bind(email).first();
  const now=new Date().toISOString();
  if(!user || !['active','invited'].includes(user.status) || (user.locked_until && user.locked_until>now) || !(await verifyPassword(body.password,user,env))) {
    if(user){ const failures=Number(user.failed_login_count||0)+1; const locked=failures>=8?new Date(Date.now()+15*60_000).toISOString():null; await env.DB.prepare(`UPDATE identity_users SET failed_login_count=?,locked_until=?,updated_at=? WHERE id=?`).bind(failures,locked,now,user.id).run(); }
    fail('البريد أو كلمة المرور غير صحيحة.',401,'invalid_credentials');
  }
  if(user.status==='invited') fail('يجب تعيين كلمة المرور من رابط الدعوة أولًا.',403,'setup_required');
  const session=await createIdentitySession(request,env,user);
  await env.DB.prepare(`UPDATE identity_users SET failed_login_count=0,locked_until=NULL,last_login_at=?,updated_at=? WHERE id=?`).bind(now,now,user.id).run();
  await identityAudit(env,user.id,'login_success',user.id,null,{role:user.role});
  return json({ok:true,...session,user:publicUser({...user,last_login_at:now})},200,cors);
}

async function requestPasswordReset(request, env, ctx, cors) {
  await rateLimit(request,env,'password-reset-ip',8);
  const body=await parseJson(request); await verifyTurnstile(body.turnstileToken,request,env,['password_reset','account_login']);
  const email=validEmail(body.email); await rateLimit(request,env,'password-reset-email',5,email);
  const user=await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) AND status IN ('active','invited') LIMIT 1`).bind(email).first();
  if(user) ctx.waitUntil(issuePasswordReset(env,user,user.status==='invited'?'setup':'reset',null));
  return json({ok:true,message:'إذا كان البريد مرتبطًا بحساب، فسيصل رابط آمن خلال دقائق.'},202,cors);
}
async function issuePasswordReset(env, user, purpose='reset', requestedBy=null) {
  const raw=randomToken(32), hash=await sha256(raw), now=new Date().toISOString(), expiresAt=new Date(Date.now()+RESET_MINUTES*60_000).toISOString();
  await env.DB.batch([
    env.DB.prepare(`DELETE FROM password_reset_tokens WHERE user_id=? AND (expires_at<=? OR used_at IS NOT NULL)`).bind(user.id,now),
    env.DB.prepare(`INSERT INTO password_reset_tokens (id,user_id,token_hash,purpose,expires_at,requested_by_user_id,created_at) VALUES (?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),user.id,hash,purpose,expiresAt,requestedBy,now)
  ]);
  const base=['owner','admin','reviewer','moderator'].includes(user.role)?String(env.ADMIN_BASE_URL||env.ACCOUNT_BASE_URL):String(env.ACCOUNT_BASE_URL||'');
  const link=`${base.replace(/#.*$/,'')}#resetToken=${encodeURIComponent(raw)}`;
  await sendEmail(env,{to:[user.email],subject:purpose==='setup'?'تعيين كلمة مرور الحساب':'إعادة تعيين كلمة المرور',html:emailLayout('إدارة كلمة المرور',`<p>مرحبًا ${escapeHtml(user.display_name_ar)}،</p><p>استخدم الرابط التالي خلال ${RESET_MINUTES} دقيقة:</p><p><a href="${escapeHtml(link)}">${purpose==='setup'?'تعيين كلمة المرور':'إعادة تعيين كلمة المرور'}</a></p><p>الرابط لمرة واحدة. تجاهل الرسالة إن لم تطلبها.</p>`),entityType:'identity_user',entityId:user.id,template:`password_${purpose}`,idempotencyKey:`password-${purpose}/${user.id}/${now.slice(0,16)}`});
  await identityAudit(env,requestedBy,'password_link_issued',user.id,user.provider_id,{purpose,expiresAt});
}
async function resetPassword(request, env, cors) {
  await rateLimit(request,env,'password-reset-submit',15);
  const body=await parseJson(request), raw=cleanString(body.token,500,true), hash=await sha256(raw), now=new Date().toISOString();
  const token=await env.DB.prepare(`SELECT t.id AS reset_token_id,t.user_id,t.token_hash,t.purpose,t.expires_at,u.provider_id,u.status AS user_status FROM password_reset_tokens t JOIN identity_users u ON u.id=t.user_id WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>? LIMIT 1`).bind(hash,now).first();
  if(!token || !constantTimeEqual(hash,token.token_hash)) fail('رابط إعادة التعيين غير صالح أو انتهت صلاحيته.',401,'invalid_reset_token');
  const rec=await createPasswordRecord(body.password,env);
  const consumed=await env.DB.prepare(`UPDATE password_reset_tokens SET used_at=? WHERE id=? AND used_at IS NULL`).bind(now,token.reset_token_id).run();
  if(Number(consumed?.meta?.changes||0)!==1) fail('استُخدم الرابط مسبقًا.',409,'reset_token_used');
  await env.DB.batch([
    env.DB.prepare(`UPDATE identity_users SET password_hash=?,password_salt=?,password_iterations=?,password_set_at=?,must_change_password=0,status=CASE WHEN status='invited' THEN 'active' ELSE status END,email_verified_at=COALESCE(email_verified_at,?),failed_login_count=0,locked_until=NULL,updated_at=? WHERE id=?`).bind(rec.hash,rec.salt,rec.iterations,now,now,now,token.user_id),
    env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL`).bind(now,token.user_id)
  ]);
  await identityAudit(env,token.user_id,'password_set',token.user_id,token.provider_id,{purpose:token.purpose});
  return json({ok:true,message:'تم تعيين كلمة المرور. يمكنك تسجيل الدخول الآن.'},200,cors);
}
async function changePassword(request, env, cors, actor) {
  const body=await parseJson(request); const current=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(actor.id).first();
  const requiresSetup=!current.password_hash||Number(current.must_change_password)===1;
  if(!requiresSetup&&!(await verifyPassword(body.currentPassword,current,env))) fail('كلمة المرور الحالية غير صحيحة.',401,'invalid_current_password');
  const rec=await createPasswordRecord(body.newPassword,env), now=new Date().toISOString();
  await env.DB.batch([
    env.DB.prepare(`UPDATE identity_users SET password_hash=?,password_salt=?,password_iterations=?,password_set_at=?,must_change_password=0,updated_at=? WHERE id=?`).bind(rec.hash,rec.salt,rec.iterations,now,now,actor.id),
    env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE user_id=? AND id<>? AND revoked_at IS NULL`).bind(now,actor.id,actor.session_id)
  ]);
  await identityAudit(env,actor.id,'password_changed',actor.id,actor.provider_id,{});
  return json({ok:true},200,cors);
}
async function logout(env,cors,actor){const now=new Date().toISOString();await env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE id=?`).bind(now,actor.session_id).run();await identityAudit(env,actor.id,'logout',actor.id,actor.provider_id,{});return json({ok:true},200,cors);}

async function bootstrapOwner(request, env, ctx, cors) {
  const supplied=cleanString(request.headers.get('x-bootstrap-key'),500,true), expected=String(env.ADMIN_API_KEY||'');
  if(!expected || !constantTimeEqual(supplied,expected)) fail('غير مصرح.',403,'forbidden');
  const email=validEmail(env.OWNER_EMAIL||'pterminology@gmail.com'), phone=validPhone(env.OWNER_PHONE||'+962795945817');
  const nameAr=cleanString(env.OWNER_DISPLAY_NAME_AR||'خالد الذيب',140,true), nameEn=cleanString(env.OWNER_DISPLAY_NAME_EN||'Khaled Altheeb',140,false);
  const now=new Date().toISOString();
  let user=await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) LIMIT 1`).bind(email).first();
  if(!user){
    const id=`owner-${crypto.randomUUID()}`;
    await env.DB.prepare(`INSERT INTO identity_users (id,email,phone_e164,display_name_ar,display_name_en,role,status,must_change_password,verified_at,email_notifications,new_message_notifications,created_at,updated_at) VALUES (?,?,?,?,?,'owner','invited',1,?,1,1,?,?)`).bind(id,email,phone,nameAr,nameEn,now,now,now).run();
    user=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(id).first();
  } else {
    await env.DB.prepare(`UPDATE identity_users SET phone_e164=?,display_name_ar=?,display_name_en=?,role='owner',status=CASE WHEN password_hash IS NULL THEN 'invited' ELSE 'active' END,verified_at=COALESCE(verified_at,?),updated_at=? WHERE id=?`).bind(phone,nameAr,nameEn,now,now,user.id).run();
    user=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(user.id).first();
  }
  if(!user.password_hash) ctx.waitUntil(issuePasswordReset(env,user,'setup',user.id));
  await identityAudit(env,user.id,'owner_bootstrapped',user.id,null,{email,phone});
  return json({ok:true,user:publicUser(user),setupEmailQueued:!user.password_hash},200,cors);
}

async function accountMe(env,cors,actor){
  const draft=actor.provider_id?await env.DB.prepare(`SELECT * FROM provider_account_drafts WHERE provider_id=?`).bind(actor.provider_id).first():null;
  const profile=actor.provider_id?await env.DB.prepare(`SELECT profile_json,publication_status,verification_status,consent_status,last_verified_at,next_review_at,updated_at FROM provider_profiles WHERE provider_id=?`).bind(actor.provider_id).first():null;
  return json({user:publicUser(actor),provider:actor.provider_id?{id:actor.provider_id,displayName:actor.provider_display_name||actor.display_name_ar,status:actor.provider_status,notificationEnabled:Number(actor.notification_enabled)===1,acceptsNewRequests:Number(actor.accepts_new_requests)===1,profile:profile?safeJson(profile.profile_json,{}):null,publicationStatus:profile?.publication_status||'draft',verificationStatus:profile?.verification_status||'pending',consentStatus:profile?.consent_status||'pending',lastVerifiedAt:profile?.last_verified_at||null,nextReviewAt:profile?.next_review_at||null,updatedAt:profile?.updated_at||null,draft:draft?{status:draft.status,data:safeJson(draft.draft_json,{}),reviewNotes:draft.review_notes||'',submittedAt:draft.submitted_at||null,updatedAt:draft.updated_at}:null}:null,session:{expiresAt:actor.expires_at}},200,cors);
}
async function updateAccount(request,env,cors,actor){
  const body=await parseJson(request), now=new Date().toISOString();
  const nameAr=cleanString(body.displayNameAr??actor.display_name_ar,140,true), nameEn=cleanString(body.displayNameEn??actor.display_name_en,140,false)||null, phone=body.phone===null?null:validPhone(body.phone??actor.phone_e164);
  const emailNotifications=body.emailNotifications===undefined?Number(actor.email_notifications):body.emailNotifications?1:0;
  const newMessageNotifications=body.newMessageNotifications===undefined?Number(actor.new_message_notifications):body.newMessageNotifications?1:0;
  const phoneChanged=(phone||null)!==(actor.phone_e164||null);
  await env.DB.prepare(`UPDATE identity_users SET display_name_ar=?,display_name_en=?,phone_e164=?,phone_verified_at=CASE WHEN ?=1 THEN NULL ELSE phone_verified_at END,email_notifications=?,new_message_notifications=?,updated_at=? WHERE id=?`).bind(nameAr,nameEn,phone,phoneChanged?1:0,emailNotifications,newMessageNotifications,now,actor.id).run();
  if(actor.provider_id){ await env.DB.prepare(`UPDATE providers_private SET display_name=?,notification_enabled=?,updated_at=? WHERE provider_id=?`).bind(nameAr,newMessageNotifications,now,actor.provider_id).run(); }
  await identityAudit(env,actor.id,'account_updated',actor.id,actor.provider_id,{fields:['display_name','phone','notifications']});
  return json({ok:true,updatedAt:now},200,cors);
}
function sanitizeDraft(raw){
  const stringList=(v,max=30,len=180)=>Array.isArray(v)?v.slice(0,max).map(x=>cleanString(x,len,false)).filter(Boolean):[];
  return {displayName:cleanString(raw.displayName,140,false),professionalTitle:cleanString(raw.professionalTitle,180,false)||null,centerType:cleanString(raw.centerType,180,false)||null,shortBio:cleanString(raw.shortBio,1000,false),specialties:stringList(raw.specialties,16,80),services:stringList(raw.services,30,180),ageGroups:stringList(raw.ageGroups,8,80),serviceModes:stringList(raw.serviceModes,8,80),languages:stringList(raw.languages,12,60),serviceAreas:stringList(raw.serviceAreas,30,140),location:{country:cleanString(raw.location?.country,80,false),governorate:cleanString(raw.location?.governorate,100,false)||null,city:cleanString(raw.location?.city,100,false),area:cleanString(raw.location?.area,140,false)||null},availability:{status:['available','limited','unavailable'].includes(raw.availability?.status)?raw.availability.status:'unavailable'},communication:{enabled:raw.communication?.enabled===true,acceptsNewRequests:raw.communication?.acceptsNewRequests===true,typicalResponse:cleanString(raw.communication?.typicalResponse,100,false)||null},contact:{publicUrl:safeHttpUrl(raw.contact?.publicUrl),website:safeHttpUrl(raw.contact?.website),publicEmail:raw.contact?.publicEmail?validEmail(raw.contact.publicEmail):null,publicPhone:raw.contact?.publicPhone?validPhone(raw.contact.publicPhone):null}};
}
function safeHttpUrl(value){const s=cleanString(value,500,false);if(!s)return null;try{const u=new URL(s);if(!['https:','http:'].includes(u.protocol)||u.username||u.password)return null;return u.href;}catch(_){return null;}}
async function getProfileDraft(env,cors,actor){if(!actor.provider_id)fail('الحساب غير مرتبط بملف مهني.',409,'provider_not_linked');const row=await env.DB.prepare(`SELECT * FROM provider_account_drafts WHERE provider_id=?`).bind(actor.provider_id).first();return json({providerId:actor.provider_id,draft:row?{status:row.status,data:safeJson(row.draft_json,{}),reviewNotes:row.review_notes||'',submittedAt:row.submitted_at||null,reviewedAt:row.reviewed_at||null,updatedAt:row.updated_at}:null},200,cors);}
async function saveProfileDraft(request,env,cors,actor){if(!actor.provider_id)fail('الحساب غير مرتبط بملف مهني.',409,'provider_not_linked');const body=await parseJson(request),draft=sanitizeDraft(body),now=new Date().toISOString();await env.DB.prepare(`INSERT INTO provider_account_drafts (provider_id,draft_json,status,review_notes,created_at,updated_at) VALUES (?,?,'draft','',?,?) ON CONFLICT(provider_id) DO UPDATE SET draft_json=excluded.draft_json,status='draft',review_notes='',submitted_at=NULL,reviewed_at=NULL,reviewed_by_user_id=NULL,updated_at=excluded.updated_at`).bind(actor.provider_id,JSON.stringify(draft),now,now).run();await identityAudit(env,actor.id,'profile_draft_saved',actor.id,actor.provider_id,{});return json({ok:true,status:'draft',updatedAt:now},200,cors);}
async function submitProfileDraft(env,cors,actor){if(!actor.provider_id)fail('الحساب غير مرتبط بملف مهني.',409,'provider_not_linked');const now=new Date().toISOString(),result=await env.DB.prepare(`UPDATE provider_account_drafts SET status='submitted',submitted_at=?,updated_at=? WHERE provider_id=?`).bind(now,now,actor.provider_id).run();if(Number(result?.meta?.changes||0)!==1)fail('احفظ مسودة الملف أولًا.',409,'draft_missing');await identityAudit(env,actor.id,'profile_draft_submitted',actor.id,actor.provider_id,{});return json({ok:true,status:'submitted',submittedAt:now},200,cors);}

function assertSpecialist(actor){if(!actor.provider_id)fail('الحساب غير مرتبط بملف مهني.',403,'provider_not_linked');if(actor.provider_status!=='active')fail('الملف المهني غير نشط.',403,'provider_inactive');}
async function specialistMe(env,cors,actor){assertSpecialist(actor);return accountMe(env,cors,actor);}
async function listSpecialistConversations(url,env,cors,actor){assertSpecialist(actor);const status=cleanString(url.searchParams.get('status'),20,false);if(status&&!CONVERSATION_STATUSES.includes(status))fail('حالة التصفية غير صالحة.',400,'invalid_status');const limit=boundedInteger(url.searchParams.get('limit'),50,1,100),offset=boundedInteger(url.searchParams.get('offset'),0,0,10_000),where=status?'AND c.status=?':'',bindings=status?[actor.provider_id,status,limit,offset]:[actor.provider_id,limit,offset];const rows=await env.DB.prepare(`SELECT c.id,c.reference_id,c.visitor_name,c.status,c.topic,c.urgency,c.created_at,c.updated_at,c.last_message_at,c.closed_at,(SELECT COUNT(*) FROM messages m WHERE m.conversation_id=c.id) AS message_count,(SELECT substr(m2.body,1,180) FROM messages m2 WHERE m2.conversation_id=c.id ORDER BY m2.created_at DESC LIMIT 1) AS last_message FROM conversations c WHERE c.provider_id=? ${where} ORDER BY c.last_message_at DESC LIMIT ? OFFSET ?`).bind(...bindings).all();const count=await env.DB.prepare(`SELECT COUNT(*) AS count FROM conversations c WHERE c.provider_id=? ${where}`).bind(...(status?[actor.provider_id,status]:[actor.provider_id])).first();return json({conversations:(rows.results||[]).map(r=>({id:r.id,referenceId:r.reference_id,visitorName:r.visitor_name,status:r.status,topic:r.topic,urgency:r.urgency,messageCount:Number(r.message_count||0),lastMessage:r.last_message||'',createdAt:r.created_at,updatedAt:r.updated_at,lastMessageAt:r.last_message_at,closedAt:r.closed_at||null})),pagination:{limit,offset,total:Number(count?.count||0)}},200,cors);}
async function providerConversation(env,actor,idValue){assertSpecialist(actor);const id=validId(idValue,'معرف المحادثة'),row=await env.DB.prepare(`SELECT * FROM conversations WHERE id=? AND provider_id=?`).bind(id,actor.provider_id).first();if(!row)fail('المحادثة غير موجودة.',404,'conversation_not_found');return row;}
async function getSpecialistConversation(env,cors,actor,id){const c=await providerConversation(env,actor,id),messages=await env.DB.prepare(`SELECT id,sender_role,body,created_at FROM messages WHERE conversation_id=? ORDER BY created_at ASC`).bind(c.id).all();return json({conversation:{id:c.id,referenceId:c.reference_id,visitorName:c.visitor_name,status:c.status,topic:c.topic,urgency:c.urgency,context:safeJson(c.context_json,{}),createdAt:c.created_at,updatedAt:c.updated_at,lastMessageAt:c.last_message_at,closedAt:c.closed_at||null},messages:(messages.results||[]).map(m=>({id:m.id,senderRole:m.sender_role,body:m.body,createdAt:m.created_at}))},200,cors);}
async function updateSpecialistConversation(request,env,cors,actor,id){const c=await providerConversation(env,actor,id),body=await parseJson(request),status=cleanString(body.status,20,true);if(!['open','closed'].includes(status))fail('الحالة غير مسموحة.',400,'invalid_status');if(['blocked','archived'].includes(c.status))fail('لا يمكن تعديل المحادثة.',409,'conversation_locked');const now=new Date().toISOString(),closed=status==='closed'?now:null,text=status==='closed'?'تم إغلاق المحادثة.':'تمت إعادة فتح المحادثة.';await env.DB.batch([env.DB.prepare(`UPDATE conversations SET status=?,closed_at=?,closed_by='specialist',updated_at=? WHERE id=?`).bind(status,closed,now,c.id),env.DB.prepare(`INSERT INTO messages (id,conversation_id,sender_role,body,created_at) VALUES (?,?,'system',?,?)`).bind(crypto.randomUUID(),c.id,text,now)]);await identityAudit(env,actor.id,'conversation_status_changed',actor.id,c.id,{status});return json({ok:true,status,updatedAt:now},200,cors);}
async function createSpecialistMessage(request,env,ctx,cors,actor,id){await rateLimit(request,env,'specialist-message',100,actor.id);const c=await providerConversation(env,actor,id),body=await parseJson(request),message=cleanString(body.body,MAX_MESSAGE_LENGTH,true);if(c.status!=='open')fail('المحادثة مغلقة.',409,'conversation_closed');const key=cleanString(request.headers.get('idempotency-key')||body.idempotencyKey,120,true);if(!/^[a-z0-9-]{12,120}$/i.test(key))fail('مفتاح منع التكرار غير صالح.',400,'invalid_idempotency_key');const existing=await env.DB.prepare(`SELECT message_id FROM specialist_message_requests WHERE idempotency_key=? AND provider_id=? AND conversation_id=?`).bind(key,actor.provider_id,c.id).first();if(existing)return json({ok:true,messageId:existing.message_id,duplicate:true},200,cors);const now=new Date().toISOString(),messageId=crypto.randomUUID();await env.DB.batch([env.DB.prepare(`INSERT INTO messages (id,conversation_id,sender_role,body,created_at) VALUES (?,?,'specialist',?,?)`).bind(messageId,c.id,message,now),env.DB.prepare(`UPDATE conversations SET updated_at=?,last_message_at=? WHERE id=?`).bind(now,now,c.id),env.DB.prepare(`INSERT INTO specialist_message_requests (idempotency_key,provider_id,conversation_id,message_id,created_at) VALUES (?,?,?,?,?)`).bind(key,actor.provider_id,c.id,messageId,now)]);if(c.visitor_email){const link=String(env.PORTAL_BASE_URL||'');ctx.waitUntil(sendEmail(env,{to:[c.visitor_email],subject:`رد من المختص — ${c.reference_id}`,html:emailLayout('وصل رد جديد',`<p>وصل رد جديد في المحادثة ${escapeHtml(c.reference_id)}.</p><p><a href="${escapeHtml(link)}">فتح بوابة المحادثة</a></p>`),entityType:'message',entityId:messageId,template:'identity_message_visitor',idempotencyKey:`identity-message/${messageId}`}));}await identityAudit(env,actor.id,'message_created',actor.id,c.id,{messageId});return json({ok:true,messageId,createdAt:now},201,cors);}

async function requestMagicSession(request,env,ctx,cors){await rateLimit(request,env,'magic-login-ip',8);const body=await parseJson(request);await verifyTurnstile(body.turnstileToken,request,env,['specialist_login','account_login']);const email=validEmail(body.email);const provider=await env.DB.prepare(`SELECT provider_id,display_name,email,status,account_enabled FROM providers_private WHERE lower(email)=lower(?) LIMIT 1`).bind(email).first();if(provider&&provider.status==='active'&&Number(provider.account_enabled)===1){const raw=randomToken(32),hash=await sha256(raw),now=new Date().toISOString(),expiresAt=new Date(Date.now()+MAGIC_LINK_MINUTES*60_000).toISOString();await env.DB.prepare(`INSERT INTO specialist_login_tokens (id,provider_id,token_hash,expires_at,request_ip_hash,created_at) VALUES (?,?,?,?,?,?)`).bind(crypto.randomUUID(),provider.provider_id,hash,expiresAt,await sha256(`${requestIp(request)}|${env.RATE_LIMIT_SALT}`),now).run();const link=`${String(env.ACCOUNT_BASE_URL||'').replace(/#.*$/,'')}#loginToken=${encodeURIComponent(raw)}`;ctx.waitUntil(sendEmail(env,{to:[provider.email],subject:'رابط الدخول إلى حساب المختص',html:emailLayout('الدخول إلى حساب المختص',`<p>مرحبًا ${escapeHtml(provider.display_name)}،</p><p><a href="${escapeHtml(link)}">فتح الحساب</a></p><p>ينتهي الرابط خلال ${MAGIC_LINK_MINUTES} دقيقة.</p>`),entityType:'specialist_login',entityId:provider.provider_id,template:'specialist_magic_link',idempotencyKey:`magic/${provider.provider_id}/${now.slice(0,16)}`}));}return json({ok:true,message:'إذا كان البريد مرتبطًا بحساب نشط، فسيصل رابط الدخول خلال دقائق.'},202,cors);}
async function verifyMagicSession(request,env,cors){await rateLimit(request,env,'magic-verify',20);const body=await parseJson(request),raw=cleanString(body.token,500,true),hash=await sha256(raw),now=new Date().toISOString();const row=await env.DB.prepare(`SELECT t.id,t.provider_id,t.token_hash,t.expires_at,p.display_name,p.email,p.status,p.account_enabled FROM specialist_login_tokens t JOIN providers_private p ON p.provider_id=t.provider_id WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>? LIMIT 1`).bind(hash,now).first();if(!row||!constantTimeEqual(hash,row.token_hash)||row.status!=='active'||Number(row.account_enabled)!==1)fail('رابط الدخول غير صالح أو انتهت صلاحيته.',401,'invalid_login_token');const consumed=await env.DB.prepare(`UPDATE specialist_login_tokens SET used_at=? WHERE id=? AND used_at IS NULL AND expires_at>?`).bind(now,row.id,now).run();if(Number(consumed?.meta?.changes||0)!==1)fail('استُخدم رابط الدخول مسبقًا.',409,'login_token_used');let user=await env.DB.prepare(`SELECT * FROM identity_users WHERE provider_id=? OR lower(email)=lower(?) LIMIT 1`).bind(row.provider_id,row.email).first();if(user&&!['active','invited'].includes(user.status))fail('الحساب غير نشط.',403,'account_inactive');if(!user){const id=`specialist-${crypto.randomUUID()}`;await env.DB.prepare(`INSERT INTO identity_users (id,provider_id,email,display_name_ar,role,status,must_change_password,email_verified_at,created_at,updated_at) VALUES (?,?,?,?,'specialist','active',1,?,?,?)`).bind(id,row.provider_id,row.email,row.display_name,now,now,now).run();user=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(id).first();}const session=await createIdentitySession(request,env,user);return json({ok:true,...session,user:publicUser(user),provider:{id:row.provider_id,displayName:row.display_name}},200,cors);}

async function identityOverview(env,cors,actor){const [users,providers,sessions,drafts]=await Promise.all([env.DB.prepare(`SELECT COUNT(*) AS total,SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active,SUM(CASE WHEN verified_at IS NOT NULL THEN 1 ELSE 0 END) AS verified,SUM(CASE WHEN role='owner' THEN 1 ELSE 0 END) AS owners FROM identity_users WHERE status<>'archived'`).first(),env.DB.prepare(`SELECT COUNT(*) AS total,SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active FROM providers_private`).first(),env.DB.prepare(`SELECT COUNT(*) AS active FROM identity_sessions WHERE revoked_at IS NULL AND expires_at>?`).bind(new Date().toISOString()).first(),env.DB.prepare(`SELECT COUNT(*) AS total,SUM(CASE WHEN status='submitted' THEN 1 ELSE 0 END) AS submitted FROM provider_account_drafts`).first()]);return json({users:integerRow(users,['total','active','verified','owners']),providers:integerRow(providers,['total','active']),sessions:{active:Number(sessions?.active||0)},drafts:integerRow(drafts,['total','submitted']),authorization:{role:actor.role,userId:actor.id},generatedAt:new Date().toISOString()},200,cors);}
function integerRow(row,keys){return Object.fromEntries(keys.map(k=>[k,Number(row?.[k]||0)]));}
async function createCoreSession(env,cors,actor){requireRole(actor,['owner','admin','reviewer','moderator']);const credential=(actor.role==='owner'||actor.role==='admin')?env.ADMIN_API_KEY:actor.role==='reviewer'?env.REVIEWER_API_KEY:env.MODERATOR_API_KEY;if(!env.CORE_API_BASE||!credential)fail('خدمة الإدارة الأساسية غير مربوطة لهذا الدور.',503,'core_admin_unavailable');const response=await fetch(`${String(env.CORE_API_BASE).replace(/\/$/,'')}/v1/admin/session`,{method:'POST',headers:{'content-type':'application/json','x-admin-key':credential,'x-requested-with':'pterminology-identity-bridge'},body:JSON.stringify({actorLabel:actor.display_name_ar})});const data=await response.json().catch(()=>({}));if(!response.ok)fail(data.message||'تعذر فتح جلسة الإدارة الأساسية.',response.status||502,'core_session_failed');return json(data,200,cors);}
async function listUsers(url,env,cors,actor){requireRole(actor,['owner','admin','reviewer']);const role=cleanString(url.searchParams.get('role'),20,false),status=cleanString(url.searchParams.get('status'),20,false),q=cleanString(url.searchParams.get('q'),120,false),limit=boundedInteger(url.searchParams.get('limit'),100,1,250),offset=boundedInteger(url.searchParams.get('offset'),0,0,10_000);if(role&&!USER_ROLES.includes(role))fail('الدور غير صالح.',400,'invalid_role');if(status&&!USER_STATUSES.includes(status))fail('الحالة غير صالحة.',400,'invalid_status');const clauses=[],values=[];if(role){clauses.push('u.role=?');values.push(role);}if(status){clauses.push('u.status=?');values.push(status);}if(q){clauses.push('(lower(u.email) LIKE lower(?) OR u.display_name_ar LIKE ? OR u.display_name_en LIKE ? OR u.phone_e164 LIKE ?)');for(let i=0;i<4;i++)values.push(`%${q}%`);}const where=clauses.length?`WHERE ${clauses.join(' AND ')}`:'';const rows=await env.DB.prepare(`SELECT u.*,p.display_name AS provider_display_name,p.status AS provider_status FROM identity_users u LEFT JOIN providers_private p ON p.provider_id=u.provider_id ${where} ORDER BY CASE u.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END,u.display_name_ar LIMIT ? OFFSET ?`).bind(...values,limit,offset).all();return json({items:(rows.results||[]).map(r=>({...publicUser(r),providerDisplayName:r.provider_display_name||null,providerStatus:r.provider_status||null})),limit,offset},200,cors);}
async function createUser(request,env,ctx,cors,actor){requireRole(actor,['owner']);const body=await parseJson(request),email=validEmail(body.email),role=USER_ROLES.includes(body.role)?body.role:'specialist',nameAr=cleanString(body.displayNameAr,140,true),nameEn=cleanString(body.displayNameEn,140,false)||null,phone=validPhone(body.phone),now=new Date().toISOString();if(role==='owner'&&actor.role!=='owner')fail('إضافة مالك تتطلب صلاحية المالك.',403,'owner_required');const exists=await env.DB.prepare(`SELECT id FROM identity_users WHERE lower(email)=lower(?)`).bind(email).first();if(exists)fail('يوجد حساب بهذا البريد.',409,'email_exists');let providerId=null;if(body.createProvider===true||body.providerId){providerId=validId(body.providerId||`provider-${crypto.randomUUID()}`,'معرف المختص');const p=await env.DB.prepare(`SELECT provider_id FROM providers_private WHERE provider_id=?`).bind(providerId).first();if(!p)await env.DB.prepare(`INSERT INTO providers_private (provider_id,email,display_name,status,notification_enabled,accepts_new_requests,account_enabled,created_at,updated_at) VALUES (?,?,?,'active',1,1,1,?,?)`).bind(providerId,email,nameAr,now,now).run();}
  const id=`user-${crypto.randomUUID()}`;await env.DB.prepare(`INSERT INTO identity_users (id,provider_id,email,phone_e164,display_name_ar,display_name_en,role,status,must_change_password,email_notifications,new_message_notifications,created_at,updated_at) VALUES (?,?,?,?,?,?,?,'invited',1,1,1,?,?)`).bind(id,providerId,email,phone,nameAr,nameEn,role,now,now).run();const user=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(id).first();ctx.waitUntil(issuePasswordReset(env,user,'setup',actor.id));await identityAudit(env,actor.id,'user_created',id,providerId,{role,email});return json({ok:true,user:publicUser(user),setupEmailQueued:true},201,cors);}
async function updateUser(request,env,cors,actor,userId){requireRole(actor,['owner']);const id=validId(userId,'معرف المستخدم'),body=await parseJson(request),target=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(id).first();if(!target)fail('الحساب غير موجود.',404,'user_not_found');const role=body.role===undefined?target.role:cleanString(body.role,20,true),status=body.status===undefined?target.status:cleanString(body.status,20,true);if(!USER_ROLES.includes(role)||!USER_STATUSES.includes(status))fail('الدور أو الحالة غير صالح.',400,'invalid_user_state');if(id===actor.id&&(status!=='active'||role!=='owner'))fail('لا يمكنك سحب صلاحية المالك أو إيقاف حسابك من الجلسة نفسها.',409,'self_lockout_prevented');const now=new Date().toISOString(),phone=body.phone===undefined?target.phone_e164:validPhone(body.phone),nameAr=body.displayNameAr===undefined?target.display_name_ar:cleanString(body.displayNameAr,140,true),nameEn=body.displayNameEn===undefined?target.display_name_en:(cleanString(body.displayNameEn,140,false)||null);await env.DB.prepare(`UPDATE identity_users SET display_name_ar=?,display_name_en=?,phone_e164=?,role=?,status=?,email_notifications=?,new_message_notifications=?,updated_at=? WHERE id=?`).bind(nameAr,nameEn,phone,role,status,body.emailNotifications===undefined?Number(target.email_notifications):body.emailNotifications?1:0,body.newMessageNotifications===undefined?Number(target.new_message_notifications):body.newMessageNotifications?1:0,now,id).run();if(status!=='active')await env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL`).bind(now,id).run();await identityAudit(env,actor.id,'user_updated',id,target.provider_id,{role,status});return json({ok:true,updatedAt:now},200,cors);}
async function archiveUser(request,env,cors,actor,userId){requireRole(actor,['owner']);const id=validId(userId,'معرف المستخدم');if(id===actor.id)fail('لا يمكنك حذف حساب المالك الحالي.',409,'self_delete_prevented');const body=await parseJson(request).catch(()=>({})),target=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(id).first();if(!target)fail('الحساب غير موجود.',404,'user_not_found');if(target.role==='owner'){const owners=await env.DB.prepare(`SELECT COUNT(*) AS count FROM identity_users WHERE role='owner' AND status='active'`).first();if(Number(owners?.count||0)<=1)fail('لا يمكن حذف آخر مالك نشط.',409,'last_owner_protected');}const now=new Date().toISOString();await env.DB.batch([env.DB.prepare(`UPDATE identity_users SET status='archived',updated_at=? WHERE id=?`).bind(now,id),env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL`).bind(now,id)]);if(target.provider_id&&body.archiveProvider===true)await env.DB.prepare(`UPDATE providers_private SET status='archived',updated_at=? WHERE provider_id=?`).bind(now,target.provider_id).run();await identityAudit(env,actor.id,'user_archived',id,target.provider_id,{archiveProvider:body.archiveProvider===true});return json({ok:true},200,cors);}
async function adminPasswordReset(env,ctx,cors,actor,userId){requireRole(actor,['owner','admin']);const id=validId(userId,'معرف المستخدم'),user=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=? AND status<>'archived'`).bind(id).first();if(!user)fail('الحساب غير موجود.',404,'user_not_found');ctx.waitUntil(issuePasswordReset(env,user,'admin_reset',actor.id));return json({ok:true,message:'تم إرسال رابط إعادة التعيين.'},202,cors);}
async function verifyUser(env,cors,actor,userId){requireRole(actor,['owner','admin']);const id=validId(userId,'معرف المستخدم'),now=new Date().toISOString(),result=await env.DB.prepare(`UPDATE identity_users SET verified_at=?,updated_at=? WHERE id=? AND status<>'archived'`).bind(now,now,id).run();if(Number(result?.meta?.changes||0)!==1)fail('الحساب غير موجود.',404,'user_not_found');await identityAudit(env,actor.id,'user_verified',id,null,{});return json({ok:true,verifiedAt:now},200,cors);}
async function listProfileDrafts(url,env,cors,actor){requireRole(actor,['owner','admin','reviewer']);const status=cleanString(url.searchParams.get('status'),20,false),where=status?'WHERE d.status=?':'',args=status?[status]:[];const rows=await env.DB.prepare(`SELECT d.*,p.display_name,u.email FROM provider_account_drafts d JOIN providers_private p ON p.provider_id=d.provider_id LEFT JOIN identity_users u ON u.provider_id=d.provider_id ${where} ORDER BY d.updated_at DESC LIMIT 200`).bind(...args).all();return json({items:(rows.results||[]).map(r=>({providerId:r.provider_id,displayName:r.display_name,email:r.email||null,status:r.status,data:safeJson(r.draft_json,{}),reviewNotes:r.review_notes||'',submittedAt:r.submitted_at||null,reviewedAt:r.reviewed_at||null,updatedAt:r.updated_at}))},200,cors);}
async function reviewProfileDraft(request,env,cors,actor,providerId){requireRole(actor,['owner','admin','reviewer']);const id=validId(providerId,'معرف المختص'),body=await parseJson(request),decision=cleanString(body.decision,20,true);if(!['approved','rejected'].includes(decision))fail('قرار المراجعة غير صالح.',400,'invalid_decision');const notes=cleanString(body.reviewNotes,2000,false),now=new Date().toISOString(),row=await env.DB.prepare(`SELECT * FROM provider_account_drafts WHERE provider_id=?`).bind(id).first();if(!row)fail('المسودة غير موجودة.',404,'draft_not_found');await env.DB.prepare(`UPDATE provider_account_drafts SET status=?,review_notes=?,reviewed_at=?,reviewed_by_user_id=?,updated_at=? WHERE provider_id=?`).bind(decision,notes,now,actor.id,now,id).run();await identityAudit(env,actor.id,'profile_draft_reviewed',null,id,{decision});return json({ok:true,status:decision,reviewedAt:now},200,cors);}
async function listIdentityAudit(url,env,cors,actor){requireRole(actor,['owner']);const limit=boundedInteger(url.searchParams.get('limit'),100,1,250),rows=await env.DB.prepare(`SELECT a.*,u.display_name_ar AS actor_name,t.display_name_ar AS target_name FROM identity_audit_log a LEFT JOIN identity_users u ON u.id=a.actor_user_id LEFT JOIN identity_users t ON t.id=a.target_user_id ORDER BY a.created_at DESC LIMIT ?`).bind(limit).all();return json({items:(rows.results||[]).map(r=>({id:r.id,eventType:r.event_type,actorUserId:r.actor_user_id||null,actorName:r.actor_name||null,targetUserId:r.target_user_id||null,targetName:r.target_name||null,entityId:r.entity_id||null,metadata:safeJson(r.metadata_json,{}),createdAt:r.created_at}))},200,cors);}

async function identityAudit(env,actorUserId,eventType,targetUserId,entityId,metadata){if(!env.DB)return;await env.DB.prepare(`INSERT INTO identity_audit_log (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at) VALUES (?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),actorUserId||null,eventType,targetUserId||null,entityId||null,JSON.stringify(metadata||{}),new Date().toISOString()).run();}
async function sendEmail(env,message){if(!env.RESEND_API_KEY||!env.FROM_EMAIL)throw new Error('email_not_configured');const response=await fetch('https://api.resend.com/emails',{method:'POST',headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,'content-type':'application/json','idempotency-key':message.idempotencyKey},body:JSON.stringify({from:env.FROM_EMAIL,to:message.to,subject:message.subject,html:message.html})});if(!response.ok){const text=await response.text();console.error('identity_email_failed',response.status,text.slice(0,500));throw new Error('email_send_failed');}}
function emailLayout(title,body){return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${escapeHtml(title)}</title></head><body style="font-family:Arial,sans-serif;background:#f4f8f7;color:#123;padding:24px"><main style="max-width:640px;margin:auto;background:white;border:1px solid #d9e8e5;border-radius:16px;padding:24px"><h1 style="color:#075f5b">${escapeHtml(title)}</h1>${body}<hr><p style="font-size:13px;color:#567">منصة الصحة النفسية وذوي الاحتياجات الخاصة</p></main></body></html>`;}
function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
