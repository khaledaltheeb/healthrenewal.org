import recoveryWorker from './index-v8.js';

const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
const BUILD_VERSION = '10.0.0';
const MAX_BODY_BYTES = 64_000;
const PASSWORD_ITERATIONS = 310_000;
const SESSION_HOURS = 12;
const RESET_MINUTES = 30;
const USER_ROLES = ['owner','admin','reviewer','moderator','specialist'];

export default {
  async scheduled(event, env, ctx) {
    if (typeof recoveryWorker.scheduled === 'function') return recoveryWorker.scheduled(event, env, ctx);
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const cors = corsHeaders(request.headers.get('origin') || '', env);

    try {
      if (request.method === 'GET' && url.pathname === '/health') return await health(request, env, ctx, cors);
      if (request.method === 'GET' && url.pathname === '/v1/internal/email-provider-status') return await internalEmailProviderStatus(request, env, cors);
      if (request.method === 'POST' && url.pathname === '/v1/internal/owner-recovery-export') return await ownerRecoveryExport(request, env, cors);
      if (request.method === 'POST' && url.pathname === '/v1/internal/bootstrap-owner') return await bootstrapOwner(request, env, cors);
      if (request.method === 'POST' && url.pathname === '/v1/auth/login') return await passwordLogin(request, env, cors);
      if (request.method === 'POST' && url.pathname === '/v1/auth/password/request') return await requestPasswordReset(request, env, cors);
      if (request.method === 'POST' && url.pathname === '/v1/auth/password/reset') return await resetPassword(request, env, cors);

      const manualResetMatch = url.pathname.match(/^\/v1\/admin\/users\/([a-z0-9-]+)\/password-reset-link$/i);
      if (request.method === 'POST' && manualResetMatch) {
        const actor = await requireIdentityBound(request, env);
        return await adminManualPasswordReset(request, env, cors, actor, manualResetMatch[1]);
      }

      const resetMatch = url.pathname.match(/^\/v1\/admin\/users\/([a-z0-9-]+)\/password-reset$/i);
      if (request.method === 'POST' && resetMatch) {
        const actor = await requireIdentityBound(request, env);
        return await adminPasswordReset(request, env, cors, actor, resetMatch[1]);
      }

      if (request.method === 'POST' && url.pathname === '/v1/admin/users') {
        const actor = await requireIdentityBound(request, env);
        return await createUser(request, env, cors, actor);
      }

      if (requiresIdentityBinding(request.method, url.pathname)) await requireIdentityBound(request, env);
      return await recoveryWorker.fetch(request, env, ctx);
    } catch (error) {
      console.error('specialist_identity_v10_error', safeError(error));
      const status = Number(error.status) || 500;
      return json({error:error.code || 'internal_error', message:status === 500 ? 'حدث خطأ داخلي.' : error.message}, status, cors);
    }
  }
};

function requiresIdentityBinding(method, pathname) {
  if (!pathname.startsWith('/v1/')) return false;
  const publicRoutes = new Set([
    'POST /v1/auth/login',
    'POST /v1/auth/password/request',
    'POST /v1/auth/password/reset',
    'POST /v1/specialist/session/request',
    'POST /v1/specialist/session/verify',
    'POST /v1/internal/bootstrap-owner',
    'POST /v1/internal/owner-password-reset',
    'POST /v1/internal/owner-recovery-export'
  ]);
  return !publicRoutes.has(`${method} ${pathname}`);
}

async function health(request, env, ctx, cors) {
  const upstream = await recoveryWorker.fetch(request, env, ctx);
  const data = await upstream.json().catch(() => ({}));
  const deep = new URL(request.url).searchParams.get('deep') === '1';
  const provider = deep ? await probeResend(env) : {configured:Boolean(env.RESEND_API_KEY && env.FROM_EMAIL), authValid:null, access:'not_probed', status:null, code:'not_probed'};
  const checks = {
    ...(data.checks || {}),
    sessionBinding:true,
    singleActiveResetLink:true,
    truthfulAdminDelivery:true,
    manualRecovery:true,
    emailProviderConfigured:provider.configured
  };
  if (deep) checks.emailProviderAuth = provider.authValid === true;
  const ok = data.ok === true && Object.values(checks).every(Boolean);
  return json({
    ...data,
    ok,
    version:BUILD_VERSION,
    checks,
    emailProvider:{configured:provider.configured,authValid:provider.authValid,access:provider.access,status:provider.status,code:provider.code},
    capabilities:{passwordRecoveryEmail:provider.authValid === true,manualRecovery:true}
  }, ok ? 200 : 503, cors);
}

async function internalEmailProviderStatus(request, env, cors) {
  requireBootstrapKey(request, env);
  const provider = await probeResend(env);
  return json({ok:provider.authValid === true, provider:'resend', ...provider}, provider.authValid === true ? 200 : 503, cors);
}

async function probeResend(env) {
  const configured = Boolean(env.RESEND_API_KEY && env.FROM_EMAIL);
  if (!configured) return {configured:false,authValid:false,access:'none',status:null,code:'not_configured'};
  try {
    const response = await fetch('https://api.resend.com/domains', {
      method:'GET',
      headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,'user-agent':'pterminology-specialist-identity/10.0.0','accept':'application/json'}
    });
    const text = await response.text();
    let data = {};
    try { data = JSON.parse(text); } catch (_) {}
    const message = String(data.message || text || '').slice(0,240);
    if (response.ok) return {configured:true,authValid:true,access:'full',status:response.status,code:'ready'};
    if (response.status === 401 && /restricted to only send emails/i.test(message)) {
      return {configured:true,authValid:true,access:'sending_only',status:response.status,code:'ready_sending_only'};
    }
    return {configured:true,authValid:false,access:'unknown',status:response.status,code:classifyProviderError(response.status,message)};
  } catch (error) {
    return {configured:true,authValid:false,access:'unknown',status:null,code:'provider_unreachable',detail:safeError(error)};
  }
}

function classifyProviderError(status, message) {
  const text = String(message || '').toLowerCase();
  if (text.includes('api key is invalid') || text.includes('invalid api key')) return 'invalid_api_key';
  if (status === 401 || status === 403) return 'authentication_failed';
  if (status === 429) return 'rate_limited';
  if (status >= 500) return 'provider_unavailable';
  return 'provider_rejected';
}

async function passwordLogin(request, env, cors) {
  await rateLimit(request, env, 'identity-login-ip-v10', 12);
  const body = await parseJson(request);
  await verifyTurnstile(body.turnstileToken, request, env, ['account_login','specialist_login']);
  const email = validEmail(body.email);
  await rateLimit(request, env, 'identity-login-email-v10', 8, email);
  const user = await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) LIMIT 1`).bind(email).first();
  const now = new Date().toISOString();
  const passwordValid = await verifyPasswordConstantTime(body.password, user, env);
  const activeStatus = user && ['active','invited'].includes(user.status);
  const unlocked = user && (!user.locked_until || user.locked_until <= now);

  if (!user || !activeStatus || !unlocked || !passwordValid || user.status === 'invited') {
    if (user && unlocked) {
      const failures = Number(user.failed_login_count || 0) + 1;
      const lockedUntil = failures >= 8 ? new Date(Date.now() + 15 * 60_000).toISOString() : null;
      await env.DB.prepare(`UPDATE identity_users SET failed_login_count=?,locked_until=?,updated_at=? WHERE id=?`).bind(failures,lockedUntil,now,user.id).run();
    }
    fail('البريد أو كلمة المرور غير صحيحة.', 401, 'invalid_credentials');
  }

  const session = await createIdentitySession(request, env, user);
  await env.DB.prepare(`UPDATE identity_users SET failed_login_count=0,locked_until=NULL,last_login_at=?,updated_at=? WHERE id=?`).bind(now,now,user.id).run();
  await identityAudit(env,user.id,'login_success',user.id,null,{role:user.role,sessionBinding:'user_agent'});
  return json({ok:true,...session,user:publicUser({...user,last_login_at:now})},200,cors);
}

async function requestPasswordReset(request, env, cors) {
  const started = Date.now();
  await rateLimit(request, env, 'password-reset-ip-v10', 8);
  const body = await parseJson(request);
  await verifyTurnstile(body.turnstileToken, request, env, ['password_reset','account_login']);
  const email = validEmail(body.email);
  await rateLimit(request, env, 'password-reset-email-v10', 5, email);

  const provider = await probeResend(env);
  if (provider.authValid !== true) fail('خدمة البريد غير متاحة حاليًا. يجري إصلاحها، ولم يُرسل رابط.',503,'email_service_unavailable');

  const user = await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) AND status IN ('active','invited') LIMIT 1`).bind(email).first();
  const requestId = crypto.randomUUID();
  if (user) {
    const purpose = user.status === 'invited' ? 'setup' : 'reset';
    try {
      const delivery = await issuePasswordReset(env,user,purpose,null,requestId,true,passwordResetBaseForRequest(request,env));
      await identityAudit(env,null,'password_email_sent',user.id,user.provider_id,{requestId,purpose,expiresAt:delivery.expiresAt,providerMessageId:delivery.providerMessageId});
    } catch (error) {
      await identityAudit(env,null,'password_email_failed',user.id,user.provider_id,{requestId,purpose,error:safeError(error),providerDetail:error.providerDetail || null});
      fail('تعذر تسليم رسالة الاستعادة. لم يتم إنشاء رابط صالح.',503,'email_delivery_failed');
    }
  }
  const minimum = 650 + Math.floor(Math.random() * 180);
  if (Date.now() - started < minimum) await sleep(minimum - (Date.now() - started));
  return json({ok:true,requestId,message:'تم قبول الطلب. إذا كان البريد مرتبطًا بحساب فسيصل رابط آمن خلال دقائق.'},202,cors);
}

async function resetPassword(request, env, cors) {
  await rateLimit(request, env, 'password-reset-submit-v10', 15);
  const body = await parseJson(request);
  const raw = cleanString(body.token,500,true);
  const hash = await sha256(raw);
  const now = new Date().toISOString();
  const token = await env.DB.prepare(`SELECT t.id AS reset_token_id,t.user_id,t.token_hash,t.purpose,t.expires_at,u.provider_id,u.status AS user_status FROM password_reset_tokens t JOIN identity_users u ON u.id=t.user_id WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>? AND u.status IN ('active','invited') LIMIT 1`).bind(hash,now).first();
  if (!token || !constantTimeEqual(hash,token.token_hash)) fail('رابط إعادة التعيين غير صالح أو انتهت صلاحيته.',401,'invalid_reset_token');
  const rec = await createPasswordRecord(body.password, env);
  const results = await env.DB.batch([
    env.DB.prepare(`UPDATE password_reset_tokens SET used_at=? WHERE id=? AND used_at IS NULL AND expires_at>?`).bind(now,token.reset_token_id,now),
    env.DB.prepare(`UPDATE identity_users SET password_hash=?,password_salt=?,password_iterations=?,password_set_at=?,must_change_password=0,status=CASE WHEN status='invited' THEN 'active' ELSE status END,email_verified_at=COALESCE(email_verified_at,?),failed_login_count=0,locked_until=NULL,updated_at=? WHERE id=? AND status IN ('active','invited')`).bind(rec.hash,rec.salt,rec.iterations,now,now,now,token.user_id),
    env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL`).bind(now,token.user_id),
    env.DB.prepare(`UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND id<>? AND used_at IS NULL`).bind(now,token.user_id,token.reset_token_id)
  ]);
  if (Number(results?.[0]?.meta?.changes || 0) !== 1 || Number(results?.[1]?.meta?.changes || 0) !== 1) {
    fail('تعذر استهلاك الرابط بأمان. اطلب رابطًا جديدًا.',409,'reset_commit_failed');
  }
  await identityAudit(env,token.user_id,'password_set',token.user_id,token.provider_id,{purpose:token.purpose,allSessionsRevoked:true});
  return json({ok:true,message:'تم تعيين كلمة المرور وإلغاء جميع الجلسات السابقة. يمكنك تسجيل الدخول الآن.'},200,cors);
}

async function adminPasswordReset(request, env, cors, actor, userId) {
  requireRole(actor,['owner','admin']);
  const id = validId(userId,'معرف المستخدم');
  const user = await env.DB.prepare(`SELECT * FROM identity_users WHERE id=? AND status<>'archived'`).bind(id).first();
  if (!user) fail('الحساب غير موجود.',404,'user_not_found');
  enforceResetHierarchy(actor,user,false);
  const provider = await probeResend(env);
  if (provider.authValid !== true) fail('خدمة البريد غير متاحة؛ لم يُرسل رابط. استخدم إنشاء الرابط اليدوي بحساب المالك.',503,'email_service_unavailable');
  try {
    const delivery = await issuePasswordReset(env,user,'admin_reset',actor.id,crypto.randomUUID(),true,passwordResetBaseForRequest(request,env));
    await identityAudit(env,actor.id,'admin_password_email_sent',user.id,user.provider_id,{providerMessageId:delivery.providerMessageId,expiresAt:delivery.expiresAt});
    return json({ok:true,message:'تم إرسال رابط إعادة التعيين.',delivery:'sent',providerMessageId:delivery.providerMessageId},200,cors);
  } catch (error) {
    await identityAudit(env,actor.id,'admin_password_email_failed',user.id,user.provider_id,{error:safeError(error),providerDetail:error.providerDetail || null});
    fail('تعذر إرسال الرابط. لم يبقَ رمز غير مُسلَّم صالحًا.',503,'email_delivery_failed');
  }
}

async function adminManualPasswordReset(request, env, cors, actor, userId) {
  requireRole(actor,['owner']);
  const id = validId(userId,'معرف المستخدم');
  const user = await env.DB.prepare(`SELECT * FROM identity_users WHERE id=? AND status<>'archived'`).bind(id).first();
  if (!user) fail('الحساب غير موجود.',404,'user_not_found');
  enforceResetHierarchy(actor,user,true);
  const delivery = await issuePasswordReset(env,user,'admin_reset',actor.id,crypto.randomUUID(),false,passwordResetBaseForRequest(request,env));
  await identityAudit(env,actor.id,'manual_password_link_created',user.id,user.provider_id,{expiresAt:delivery.expiresAt});
  return json({ok:true,delivery:'manual',resetUrl:delivery.resetUrl,expiresAt:delivery.expiresAt,message:'تم إنشاء رابط يدوي لمرة واحدة. أرسله عبر قناة موثوقة.'},200,cors);
}

function enforceResetHierarchy(actor, target, manual) {
  if (manual && actor.role !== 'owner') fail('إنشاء رابط يدوي يتطلب صلاحية المالك.',403,'owner_required');
  if (actor.role === 'admin' && ['owner','admin'].includes(target.role)) fail('لا يمكن للمدير إعادة تعيين حساب مالك أو مدير آخر.',403,'role_hierarchy_violation');
}

async function createUser(request, env, cors, actor) {
  requireRole(actor,['owner']);
  const body = await parseJson(request);
  const email = validEmail(body.email);
  const role = USER_ROLES.includes(body.role) ? body.role : 'specialist';
  const nameAr = cleanString(body.displayNameAr,140,true);
  const nameEn = cleanString(body.displayNameEn,140,false) || null;
  const phone = validPhone(body.phone);
  const now = new Date().toISOString();
  const exists = await env.DB.prepare(`SELECT id FROM identity_users WHERE lower(email)=lower(?)`).bind(email).first();
  if (exists) fail('يوجد حساب بهذا البريد.',409,'email_exists');

  let providerId = null;
  if (body.createProvider === true || body.providerId) {
    providerId = validId(body.providerId || `provider-${crypto.randomUUID()}`,'معرف المختص');
    const provider = await env.DB.prepare(`SELECT provider_id FROM providers_private WHERE provider_id=?`).bind(providerId).first();
    if (!provider) {
      await env.DB.prepare(`INSERT INTO providers_private (provider_id,email,display_name,status,notification_enabled,accepts_new_requests,account_enabled,created_at,updated_at) VALUES (?,?,?,'active',1,1,1,?,?)`).bind(providerId,email,nameAr,now,now).run();
    }
  }

  const id = `user-${crypto.randomUUID()}`;
  await env.DB.prepare(`INSERT INTO identity_users (id,provider_id,email,phone_e164,display_name_ar,display_name_en,role,status,must_change_password,email_notifications,new_message_notifications,created_at,updated_at) VALUES (?,?,?,?,?,?,?,'invited',1,1,1,?,?)`).bind(id,providerId,email,phone,nameAr,nameEn,role,now,now).run();
  const user = await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(id).first();
  await identityAudit(env,actor.id,'user_created',id,providerId,{role,email});

  const providerStatus = await probeResend(env);
  if (providerStatus.authValid !== true) {
    return json({ok:false,partialSuccess:true,user:publicUser(user),setupEmailQueued:false,emailDelivery:'failed',error:'email_service_unavailable',message:'تم إنشاء الحساب، لكن خدمة البريد غير متاحة ولم يُرسل رابط التفعيل. استخدم الرابط اليدوي من حساب المالك.'},503,cors);
  }
  try {
    const delivery = await issuePasswordReset(env,user,'setup',actor.id,crypto.randomUUID(),true,passwordResetBaseForRequest(request,env));
    await identityAudit(env,actor.id,'user_setup_email_sent',id,providerId,{providerMessageId:delivery.providerMessageId,expiresAt:delivery.expiresAt});
    return json({ok:true,user:publicUser(user),setupEmailQueued:false,emailDelivery:'sent',providerMessageId:delivery.providerMessageId},201,cors);
  } catch (error) {
    await identityAudit(env,actor.id,'user_setup_email_failed',id,providerId,{error:safeError(error),providerDetail:error.providerDetail || null});
    return json({ok:false,partialSuccess:true,user:publicUser(user),setupEmailQueued:false,emailDelivery:'failed',error:'email_delivery_failed',message:'تم إنشاء الحساب، لكن فشل إرسال رابط التفعيل. استخدم الرابط اليدوي من حساب المالك.'},503,cors);
  }
}

async function bootstrapOwner(request, env, cors) {
  requireBootstrapKey(request,env);
  const email = validEmail(env.OWNER_EMAIL || 'pterminology@gmail.com');
  const phone = validPhone(env.OWNER_PHONE || '+962795945817');
  const nameAr = cleanString(env.OWNER_DISPLAY_NAME_AR || 'خالد الذيب',140,true);
  const nameEn = cleanString(env.OWNER_DISPLAY_NAME_EN || 'Khaled Altheeb',140,false);
  const now = new Date().toISOString();
  let user = await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) LIMIT 1`).bind(email).first();
  if (!user) {
    const id = `owner-${crypto.randomUUID()}`;
    await env.DB.prepare(`INSERT INTO identity_users (id,email,phone_e164,display_name_ar,display_name_en,role,status,must_change_password,verified_at,email_notifications,new_message_notifications,created_at,updated_at) VALUES (?,?,?,?,?,'owner','invited',1,?,1,1,?,?)`).bind(id,email,phone,nameAr,nameEn,now,now,now).run();
    user = await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(id).first();
  } else {
    await env.DB.prepare(`UPDATE identity_users SET phone_e164=?,display_name_ar=?,display_name_en=?,role='owner',status=CASE WHEN password_hash IS NULL THEN 'invited' ELSE 'active' END,verified_at=COALESCE(verified_at,?),updated_at=? WHERE id=?`).bind(phone,nameAr,nameEn,now,now,user.id).run();
    user = await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(user.id).first();
  }
  await identityAudit(env,user.id,'owner_bootstrapped',user.id,null,{email});
  if (user.password_hash) return json({ok:true,user:publicUser(user),setupRequired:false},200,cors);
  const provider = await probeResend(env);
  if (provider.authValid !== true) return json({ok:true,user:publicUser(user),setupRequired:true,emailDelivery:'unavailable',message:'حساب المالك مهيأ، لكن البريد غير متاح. استخدم الاستعادة التشغيلية المشفرة.'},200,cors);
  try {
    const delivery = await issuePasswordReset(env,user,'setup',user.id,crypto.randomUUID(),true,passwordResetBaseForRequest(request,env));
    return json({ok:true,user:publicUser(user),setupRequired:true,emailDelivery:'sent',providerMessageId:delivery.providerMessageId},200,cors);
  } catch (error) {
    return json({ok:true,user:publicUser(user),setupRequired:true,emailDelivery:'failed',message:'حساب المالك مهيأ، لكن فشل البريد. استخدم الاستعادة التشغيلية المشفرة.'},200,cors);
  }
}

async function ownerRecoveryExport(request, env, cors) {
  requireBootstrapKey(request,env);
  const supplied = cleanString(request.headers.get('x-recovery-export-key'),500,true);
  const expected = String(env.RECOVERY_EXPORT_KEY || '');
  if (!expected || !constantTimeEqual(supplied,expected)) fail('تصدير الاستعادة غير مفعل أو غير مصرح.',403,'recovery_export_forbidden');
  await rateLimit(request,env,'owner-recovery-export',3,'owner');
  const email = validEmail(env.OWNER_EMAIL || 'pterminology@gmail.com');
  const user = await env.DB.prepare(`SELECT * FROM identity_users WHERE lower(email)=lower(?) AND role='owner' AND status IN ('active','invited') LIMIT 1`).bind(email).first();
  if (!user) fail('حساب المالك غير موجود.',404,'owner_not_found');
  const delivery = await issuePasswordReset(env,user,user.status === 'invited' ? 'setup' : 'admin_reset',user.id,crypto.randomUUID(),false);
  await identityAudit(env,user.id,'owner_recovery_exported',user.id,user.provider_id,{expiresAt:delivery.expiresAt});
  return json({ok:true,resetUrl:delivery.resetUrl,expiresAt:delivery.expiresAt},200,cors);
}

async function issuePasswordReset(env, user, purpose='reset', requestedBy=null, requestId=crypto.randomUUID(), deliver=true, resetBaseOverride='') {
  const raw = randomToken(32);
  const hash = await sha256(raw);
  const now = new Date().toISOString();
  const expiresAt = new Date(Date.now() + RESET_MINUTES * 60_000).toISOString();
  const tokenId = crypto.randomUUID();
  await env.DB.batch([
    env.DB.prepare(`UPDATE password_reset_tokens SET used_at=? WHERE user_id=? AND used_at IS NULL`).bind(now,user.id),
    env.DB.prepare(`INSERT INTO password_reset_tokens (id,user_id,token_hash,purpose,expires_at,requested_by_user_id,created_at) VALUES (?,?,?,?,?,?,?)`).bind(tokenId,user.id,hash,purpose,expiresAt,requestedBy,now)
  ]);
  const base = validHttpsBase(resetBaseOverride || env.PASSWORD_RESET_BASE_URL);
  if (!base) {
    await env.DB.prepare(`DELETE FROM password_reset_tokens WHERE id=?`).bind(tokenId).run();
    fail('مسار إعادة التعيين غير مهيأ.',503,'reset_base_unavailable');
  }
  const resetUrl = `${base}?v=10#resetToken=${encodeURIComponent(raw)}`;
  if (!deliver) return {expiresAt,resetUrl,providerMessageId:null};

  try {
    const result = await sendEmail(env,{
      to:[user.email],
      subject:purpose === 'setup' ? 'تعيين كلمة مرور الحساب' : 'إعادة تعيين كلمة المرور',
      html:emailLayout('إدارة كلمة المرور',`<p>مرحبًا ${escapeHtml(user.display_name_ar)}،</p><p>استخدم الرابط التالي خلال ${RESET_MINUTES} دقيقة:</p><p><a href="${escapeHtml(resetUrl)}">${purpose === 'setup' ? 'تعيين كلمة المرور' : 'إعادة تعيين كلمة المرور'}</a></p><p>الرابط لمرة واحدة، وأي رابط أقدم أصبح غير صالح.</p>`),
      text:`مرحبًا ${user.display_name_ar}\n\nاستخدم الرابط التالي خلال ${RESET_MINUTES} دقيقة:\n${resetUrl}\n\nالرابط لمرة واحدة، وأي رابط أقدم أصبح غير صالح.`,
      idempotencyKey:`password-v10/${purpose}/${user.id}/${requestId}`
    });
    return {expiresAt,resetUrl,providerMessageId:result.id || null};
  } catch (error) {
    await env.DB.prepare(`DELETE FROM password_reset_tokens WHERE id=?`).bind(tokenId).run();
    throw error;
  }
}

async function sendEmail(env, message) {
  if (!env.RESEND_API_KEY || !env.FROM_EMAIL) fail('خدمة البريد غير مهيأة.',503,'email_not_configured');
  let lastError = null;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const response = await fetch('https://api.resend.com/emails', {
        method:'POST',
        headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,'content-type':'application/json','user-agent':'pterminology-specialist-identity/10.0.0','idempotency-key':message.idempotencyKey},
        body:JSON.stringify({from:env.FROM_EMAIL,to:message.to,subject:message.subject,html:message.html,text:message.text || ''})
      });
      const text = await response.text();
      let data = {};
      try { data = JSON.parse(text); } catch (_) {}
      if (response.ok && data.id) return data;
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
  throw error;
}

async function requireIdentityBound(request, env) {
  const raw = bearerToken(request);
  const hash = await sha256(raw);
  const now = new Date().toISOString();
  const row = await env.DB.prepare(`SELECT s.id AS session_id,s.token_hash,s.expires_at,s.ip_hash,s.user_agent_hash,u.*,p.display_name AS provider_display_name,p.status AS provider_status,p.notification_enabled,p.accepts_new_requests FROM identity_sessions s JOIN identity_users u ON u.id=s.user_id LEFT JOIN providers_private p ON p.provider_id=u.provider_id WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND u.status='active' LIMIT 1`).bind(hash,now).first();
  if (!row || !constantTimeEqual(hash,row.token_hash)) fail('انتهت جلسة الدخول أو لم تعد صالحة.',401,'session_expired');
  const uaHash = await sha256(`${request.headers.get('user-agent') || ''}|${env.RATE_LIMIT_SALT}`);
  if (!constantTimeEqual(uaHash,row.user_agent_hash)) {
    await env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL`).bind(now,row.session_id).run();
    fail('تغيرت بيئة الجلسة. سجّل الدخول من جديد.',401,'session_binding_mismatch');
  }
  if (String(env.SESSION_BIND_IP || '').toLowerCase() === 'strict') {
    const ipHash = await sha256(`${requestIp(request)}|${env.RATE_LIMIT_SALT}`);
    if (!constantTimeEqual(ipHash,row.ip_hash)) {
      await env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL`).bind(now,row.session_id).run();
      fail('تغير عنوان الاتصال. سجّل الدخول من جديد.',401,'session_ip_mismatch');
    }
  }
  return row;
}

async function createIdentitySession(request, env, user) {
  const raw = randomToken(32);
  const hash = await sha256(raw);
  const now = new Date().toISOString();
  const hours = boundedInteger(env.IDENTITY_SESSION_HOURS,SESSION_HOURS,1,72);
  const expiresAt = new Date(Date.now() + hours * 3_600_000).toISOString();
  const ipHash = await sha256(`${requestIp(request)}|${env.RATE_LIMIT_SALT}`);
  const uaHash = await sha256(`${request.headers.get('user-agent') || ''}|${env.RATE_LIMIT_SALT}`);
  await env.DB.prepare(`INSERT INTO identity_sessions (id,user_id,token_hash,expires_at,ip_hash,user_agent_hash,created_at,last_used_at) VALUES (?,?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),user.id,hash,expiresAt,ipHash,uaHash,now,now).run();
  return {sessionToken:raw,expiresAt};
}

async function verifyPasswordConstantTime(password, user, env) {
  let salt;
  let iterations = PASSWORD_ITERATIONS;
  let expected = 'A'.repeat(43);
  let hasRecord = false;
  if (user?.password_hash && user?.password_salt && user?.password_iterations) {
    salt = fromBase64Url(user.password_salt);
    iterations = Number(user.password_iterations);
    expected = user.password_hash;
    hasRecord = true;
  } else {
    const seed = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`dummy-login|${env.RATE_LIMIT_SALT || 'fallback'}`));
    salt = new Uint8Array(seed).slice(0,16);
  }
  const hash = await passwordKey(String(password || ''),salt,passwordPepper(env),iterations);
  return hasRecord && constantTimeEqual(hash,expected);
}

async function createPasswordRecord(password, env) {
  const value = validatePassword(password);
  const salt = crypto.getRandomValues(new Uint8Array(16));
  return {hash:await passwordKey(value,salt,passwordPepper(env),PASSWORD_ITERATIONS),salt:toBase64Url(salt),iterations:PASSWORD_ITERATIONS};
}

async function passwordKey(password, salt, pepper, iterations) {
  const material = await crypto.subtle.importKey('raw',new TextEncoder().encode(`${password}\u0000${pepper}`),'PBKDF2',false,['deriveBits']);
  const bits = await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',salt,iterations},material,256);
  return toBase64Url(new Uint8Array(bits));
}

function validatePassword(password) {
  const value = String(password || '');
  if (value.length < 12 || value.length > 128) fail('كلمة المرور يجب أن تكون بين 12 و128 محرفًا.',400,'weak_password');
  const categories = [/\p{L}/u.test(value),/\d/u.test(value),/[^\p{L}\d\s]/u.test(value),/\s/u.test(value)].filter(Boolean).length;
  const latinCaseBonus = /[a-z]/.test(value) && /[A-Z]/.test(value);
  if (categories < 3 && !(categories >= 2 && latinCaseBonus)) fail('استخدم مزيجًا من الحروف والأرقام والرموز، ويمكن استخدام الحروف العربية.',400,'weak_password');
  return value;
}

function passwordPepper(env) { return String(env.PASSWORD_PEPPER || env.RATE_LIMIT_SALT || ''); }
function bearerToken(request) { const match=(request.headers.get('authorization') || '').match(/^Bearer\s+([A-Za-z0-9_-]{32,500})$/i); if (!match) fail('يلزم تسجيل الدخول.',401,'authentication_required'); return match[1]; }
function requireRole(actor,roles) { if (!roles.includes(actor.role)) fail('لا تملك الصلاحية المطلوبة.',403,'forbidden'); }
function requireBootstrapKey(request,env) { const supplied=cleanString(request.headers.get('x-bootstrap-key'),500,true),expected=String(env.ADMIN_API_KEY || ''); if (!expected || !constantTimeEqual(supplied,expected)) fail('غير مصرح.',403,'forbidden'); }

async function rateLimit(request, env, scope, limit, identity='') {
  if (!env.DB || !env.RATE_LIMIT_SALT) fail('خدمة الحماية غير جاهزة.',503,'rate_limit_unavailable');
  const key = `${scope}:${await sha256(`${scope}|${identity || requestIp(request)}|${env.RATE_LIMIT_SALT}`)}`;
  const bucket = new Date().toISOString().slice(0,13);
  await env.DB.prepare(`INSERT INTO rate_limits (key,bucket,count,updated_at) VALUES (?,?,1,?) ON CONFLICT(key,bucket) DO UPDATE SET count=count+1,updated_at=excluded.updated_at`).bind(key,bucket,new Date().toISOString()).run();
  const row = await env.DB.prepare(`SELECT count FROM rate_limits WHERE key=? AND bucket=?`).bind(key,bucket).first();
  if (Number(row?.count || 0) > limit) fail('تم تجاوز عدد المحاولات المسموح مؤقتًا.',429,'rate_limited');
}

async function verifyTurnstile(tokenValue, request, env, allowedActions=[]) {
  if (!env.TURNSTILE_SECRET) fail('خدمة التحقق غير جاهزة.',503,'turnstile_unavailable');
  const token = cleanString(tokenValue,2048,true);
  const form = new FormData();
  form.set('secret',env.TURNSTILE_SECRET);
  form.set('response',token);
  form.set('remoteip',requestIp(request));
  form.set('idempotency_key',crypto.randomUUID());
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',{method:'POST',body:form});
  const result = await response.json().catch(() => ({}));
  const hosts = new Set([
    'khaledaltheeb.github.io',
    'healthrenewal.org',
    'www.healthrenewal.org',
    ...String(env.TURNSTILE_EXPECTED_HOSTNAMES || '').split(',').map(v=>v.trim()).filter(Boolean),
  ]);
  const actionOk = !result.action || !allowedActions.length || allowedActions.includes(result.action);
  if (!response.ok || result.success !== true || !hosts.has(result.hostname) || !actionOk) fail('تعذر التحقق من الاستخدام البشري.',400,'turnstile_failed');
}

async function parseJson(request) {
  if (!(request.headers.get('content-type') || '').includes('application/json')) fail('يجب إرسال البيانات بصيغة JSON.',415,'unsupported_media_type');
  const declared = Number(request.headers.get('content-length') || 0);
  if (declared > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.',413,'payload_too_large');
  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.',413,'payload_too_large');
  try { const parsed=JSON.parse(text); if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') fail('جسم الطلب غير صالح.',400,'invalid_json'); return parsed; }
  catch (error) { if (error?.code) throw error; fail('تعذر قراءة البيانات المرسلة.',400,'invalid_json'); }
}

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://khaledaltheeb.github.io').split(',').map(v=>v.trim()).filter(Boolean);
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

function publicUser(row) { return {id:row.id,email:row.email,phone:row.phone_e164 || null,displayNameAr:row.display_name_ar,displayNameEn:row.display_name_en || null,role:row.role,status:row.status,providerId:row.provider_id || null,verifiedAt:row.verified_at || null,emailVerifiedAt:row.email_verified_at || null,phoneVerifiedAt:row.phone_verified_at || null,emailNotifications:Number(row.email_notifications)===1,newMessageNotifications:Number(row.new_message_notifications)===1,mustChangePassword:Number(row.must_change_password)===1,lastLoginAt:row.last_login_at || null,createdAt:row.created_at,updatedAt:row.updated_at}; }
function passwordResetBaseForRequest(request,env) {
  const origin=String(request?.headers?.get('origin')||'').replace(/\/$/,'');
  if(origin==='https://healthrenewal.org'||origin==='https://www.healthrenewal.org') return `${origin}/specialists-partners/password-reset/`;
  if(origin==='https://khaledaltheeb.github.io') return 'https://healthrenewal.org/specialists-partners/password-reset/';
  return String(env.PASSWORD_RESET_BASE_URL||'');
}
function validHttpsBase(value) { try { const url=new URL(String(value || '')); if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) return ''; return url.href.replace(/\/$/,''); } catch (_) { return ''; } }
function validEmail(value) { const email=cleanString(value,254,true).toLowerCase(); if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) fail('البريد الإلكتروني غير صالح.',400,'invalid_email'); return email; }
function validId(value,label='المعرف') { const id=cleanString(value,90,true); if (!/^[a-z0-9][a-z0-9-]{2,89}$/i.test(id)) fail(`${label} غير صالح.`,400,'invalid_id'); return id; }
function validPhone(value) { const phone=cleanString(value,24,false).replace(/[\s()-]/g,''); if (!phone) return null; if (!/^\+[1-9]\d{7,14}$/.test(phone)) fail('رقم الهاتف يجب أن يكون بصيغة دولية مثل +9627...',400,'invalid_phone'); return phone; }
function boundedInteger(value,fallback,min,max) { const n=Number.parseInt(String(value ?? ''),10); return Number.isFinite(n) ? Math.min(max,Math.max(min,n)) : fallback; }
function cleanString(value,max=200,required=false) { const text=String(value ?? '').trim(); if (required && !text) fail('أحد الحقول المطلوبة فارغ.',400,'missing_field'); if (text.length > max) fail('أحد الحقول تجاوز الحد المسموح.',400,'field_too_long'); return text; }
function json(payload,status=200,extraHeaders={}) { return new Response(JSON.stringify(payload),{status,headers:{...JSON_HEADERS,...extraHeaders}}); }
function fail(message,status=400,code='invalid_request') { const error=new Error(message); error.status=status; error.code=code; throw error; }
function requestIp(request) { return request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for') || 'unknown'; }
function randomToken(bytes=32) { const array=new Uint8Array(bytes); crypto.getRandomValues(array); return toBase64Url(array); }
function toBase64Url(bytes) { let value=''; for (const byte of bytes) value += String.fromCharCode(byte); return btoa(value).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); }
function fromBase64Url(value) { const text=String(value); const padded=text.replace(/-/g,'+').replace(/_/g,'/') + '='.repeat((4 - text.length % 4) % 4); return Uint8Array.from(atob(padded),char=>char.charCodeAt(0)); }
async function sha256(value) { const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(String(value))); return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join(''); }
function constantTimeEqual(a,b) { a=String(a || ''); b=String(b || ''); let diff=a.length ^ b.length; const n=Math.max(a.length,b.length); for (let i=0;i<n;i+=1) diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0); return diff === 0; }
function sleep(ms) { return new Promise(resolve=>setTimeout(resolve,ms)); }
function safeError(error) { return String(error?.message || error || 'unknown').slice(0,240); }
async function identityAudit(env,actorUserId,eventType,targetUserId,entityId,metadata) { if (!env.DB) return; await env.DB.prepare(`INSERT INTO identity_audit_log (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at) VALUES (?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),actorUserId || null,eventType,targetUserId || null,entityId || null,JSON.stringify(metadata || {}),new Date().toISOString()).run(); }
function emailLayout(title,body) { return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${escapeHtml(title)}</title></head><body style="font-family:Arial,sans-serif;background:#f4f8f7;color:#123;padding:24px"><main style="max-width:640px;margin:auto;background:white;border:1px solid #d9e8e5;border-radius:16px;padding:24px"><h1 style="color:#075f5b">${escapeHtml(title)}</h1>${body}<hr><p style="font-size:13px;color:#567">منصة الصحة النفسية وذوي الاحتياجات الخاصة</p></main></body></html>`; }
function escapeHtml(value) { return String(value ?? '').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char])); }
