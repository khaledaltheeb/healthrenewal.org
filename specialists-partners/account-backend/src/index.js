const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
const MAX_BODY_BYTES = 32_000;
const MAX_MESSAGE_LENGTH = 3_000;
const LOGIN_TOKEN_MINUTES = 15;
const DEFAULT_SESSION_HOURS = 12;
const BUILD_VERSION = '5.0.0';
const CONVERSATION_STATUSES = ['open','closed','blocked','archived'];

export default {
  async scheduled(_event, env, ctx) {
    if (!env.DB) return;
    const now = new Date().toISOString();
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
    const ninetyDaysAgo = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString();
    const thirtyDaysAgoBucket = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 13);
    ctx.waitUntil(env.DB.batch([
      env.DB.prepare(`DELETE FROM specialist_login_tokens WHERE expires_at <= ? OR (used_at IS NOT NULL AND used_at < ?)` ).bind(now, oneDayAgo),
      env.DB.prepare(`DELETE FROM specialist_sessions WHERE expires_at <= ? OR (revoked_at IS NOT NULL AND revoked_at < ?)` ).bind(now, sevenDaysAgo),
      env.DB.prepare(`DELETE FROM specialist_message_requests WHERE created_at < ?`).bind(ninetyDaysAgo),
      env.DB.prepare(`DELETE FROM rate_limits WHERE bucket < ?`).bind(thirtyDaysAgoBucket)
    ]));
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('origin') || '';
    const cors = corsHeaders(origin, env);

    if (request.method === 'OPTIONS') return new Response(null, {status:204, headers:cors});

    try {
      if (request.method === 'GET' && url.pathname === '/health') {
        return await health(env, cors);
      }

      if (request.method === 'POST' && url.pathname === '/v1/specialist/session/request') {
        return await requestSession(request, env, ctx, cors);
      }

      if (request.method === 'POST' && url.pathname === '/v1/specialist/session/verify') {
        return await verifySession(request, env, cors);
      }

      if (!url.pathname.startsWith('/v1/specialist/')) {
        return json({error:'not_found', message:'المسار غير موجود.'}, 404, cors);
      }

      const actor = await requireSpecialist(request, env);

      if (request.method === 'POST' && url.pathname === '/v1/specialist/session/revoke') {
        return await revokeSession(env, cors, actor);
      }

      if (request.method === 'GET' && url.pathname === '/v1/specialist/me') {
        return await specialistMe(env, cors, actor);
      }

      if (request.method === 'GET' && url.pathname === '/v1/specialist/conversations') {
        return await listConversations(url, env, cors, actor);
      }

      const conversationMatch = url.pathname.match(/^\/v1\/specialist\/conversations\/([a-z0-9-]+)$/i);
      if (conversationMatch && request.method === 'GET') {
        return await getConversation(env, cors, actor, conversationMatch[1]);
      }
      if (conversationMatch && request.method === 'PATCH') {
        return await updateConversation(request, env, cors, actor, conversationMatch[1]);
      }

      const messagesMatch = url.pathname.match(/^\/v1\/specialist\/conversations\/([a-z0-9-]+)\/messages$/i);
      if (messagesMatch && request.method === 'POST') {
        return await createMessage(request, env, ctx, cors, actor, messagesMatch[1]);
      }

      return json({error:'not_found', message:'المسار غير موجود.'}, 404, cors);
    } catch (error) {
      console.error('specialist_account_worker_error', error);
      const status = Number(error.status) || 500;
      const message = status === 500 ? 'حدث خطأ داخلي.' : error.message;
      return json({error:error.code || 'internal_error', message}, status, cors);
    }
  }
};

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://khaledaltheeb.github.io')
    .split(',').map(value => value.trim()).filter(Boolean);
  const selected = origin && allowed.includes(origin) ? origin : '';
  const headers = {
    'access-control-allow-methods':'GET,POST,PATCH,OPTIONS',
    'access-control-allow-headers':'authorization,content-type,idempotency-key,x-requested-with',
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
  if (selected) headers['access-control-allow-origin'] = selected;
  return headers;
}

function json(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers:{...JSON_HEADERS, ...extraHeaders}
  });
}

function fail(message, status = 400, code = 'invalid_request') {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  throw error;
}

async function health(env, cors) {
  let database = false;
  let accountSchema = false;
  try {
    if (env.DB) {
      await env.DB.prepare('SELECT 1 AS ok').first();
      database = true;
      const schema = await env.DB.prepare(`
        SELECT COUNT(*) AS count FROM sqlite_master
        WHERE type='table' AND name IN (
          'providers_private','conversations','messages','conversation_tokens',
          'specialist_login_tokens','specialist_sessions','specialist_message_requests'
        )
      `).first();
      accountSchema = Number(schema?.count || 0) === 7;
    }
  } catch (error) {
    console.error('account_health_db_error', error);
  }

  const checks = {
    database,
    accountSchema,
    email:Boolean(env.RESEND_API_KEY && env.FROM_EMAIL),
    turnstile:Boolean(env.TURNSTILE_SECRET),
    rateLimitSalt:Boolean(env.RATE_LIMIT_SALT),
    accountBase:Boolean(env.ACCOUNT_BASE_URL),
    portalBase:Boolean(env.PORTAL_BASE_URL)
  };
  const ready = Object.values(checks).every(Boolean);
  return json({
    ok:ready,
    service:'pterminology-specialist-accounts',
    version:BUILD_VERSION,
    checks,
    time:new Date().toISOString()
  }, ready ? 200 : 503, cors);
}

async function parseJson(request) {
  const contentType = request.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    fail('يجب إرسال البيانات بصيغة JSON.', 415, 'unsupported_media_type');
  }
  const declared = Number(request.headers.get('content-length') || 0);
  if (declared > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.', 413, 'payload_too_large');
  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > MAX_BODY_BYTES) {
    fail('حجم الطلب أكبر من الحد المسموح.', 413, 'payload_too_large');
  }
  try {
    const parsed = JSON.parse(text);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      fail('يجب أن يكون جسم الطلب كائن JSON.', 400, 'invalid_json_object');
    }
    return parsed;
  } catch (error) {
    if (error?.code) throw error;
    fail('تعذر قراءة البيانات المرسلة.', 400, 'invalid_json');
  }
}

function cleanString(value, max = 200, required = false) {
  const text = String(value ?? '').trim();
  if (required && !text) fail('أحد الحقول المطلوبة فارغ.', 400, 'missing_field');
  if (text.length > max) fail('أحد الحقول تجاوز الحد المسموح.', 400, 'field_too_long');
  return text;
}

function validEmail(value) {
  const email = cleanString(value, 254, true).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    fail('البريد الإلكتروني غير صالح.', 400, 'invalid_email');
  }
  return email;
}

function validId(value, name = 'المعرف') {
  const id = cleanString(value, 90, true);
  if (!/^[a-z0-9][a-z0-9-]{2,89}$/i.test(id)) {
    fail(`${name} غير صالح.`, 400, 'invalid_id');
  }
  return id;
}

function boundedInteger(value, fallback, min, max) {
  const number = Number.parseInt(String(value ?? ''), 10);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function bearerToken(request) {
  const header = request.headers.get('authorization') || '';
  const match = header.match(/^Bearer\s+(.+)$/i);
  if (!match) fail('يلزم تسجيل الدخول.', 401, 'authentication_required');
  return cleanString(match[1], 500, true);
}

function randomToken(bytes = 32) {
  const buffer = new Uint8Array(bytes);
  crypto.getRandomValues(buffer);
  let binary = '';
  for (const byte of buffer) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

async function sha256(value) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(value)));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}

function constantTimeEqual(left, right) {
  const a = String(left || '');
  const b = String(right || '');
  let mismatch = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    mismatch |= (a.charCodeAt(index) || 0) ^ (b.charCodeAt(index) || 0);
  }
  return mismatch === 0;
}

function requestIp(request) {
  return request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for') || 'unknown';
}

async function rateLimit(request, env, scope, limit, identity = '') {
  if (!env.DB || !env.RATE_LIMIT_SALT) fail('خدمة الحماية غير جاهزة.', 503, 'rate_limit_unavailable');
  const raw = `${scope}|${identity || requestIp(request)}|${env.RATE_LIMIT_SALT}`;
  const key = `${scope}:${await sha256(raw)}`;
  const bucket = new Date().toISOString().slice(0, 13);
  await env.DB.prepare(`
    INSERT INTO rate_limits (key, bucket, count, updated_at)
    VALUES (?, ?, 1, ?)
    ON CONFLICT(key, bucket) DO UPDATE SET
      count = count + 1,
      updated_at = excluded.updated_at
  `).bind(key, bucket, new Date().toISOString()).run();
  const row = await env.DB.prepare(`SELECT count FROM rate_limits WHERE key = ? AND bucket = ?`)
    .bind(key, bucket).first();
  if (Number(row?.count || 0) > limit) {
    fail('تم تجاوز عدد المحاولات المسموح مؤقتًا. حاول لاحقًا.', 429, 'rate_limited');
  }
}

async function verifyTurnstile(tokenValue, request, env) {
  if (!env.TURNSTILE_SECRET) fail('خدمة التحقق غير جاهزة.', 503, 'turnstile_unavailable');
  const token = cleanString(tokenValue, 2048, true);
  const form = new FormData();
  form.set('secret', env.TURNSTILE_SECRET);
  form.set('response', token);
  form.set('remoteip', requestIp(request));
  form.set('idempotency_key', crypto.randomUUID());
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method:'POST', body:form
  });
  const result = await response.json().catch(() => ({}));
  const allowedHosts = String(env.TURNSTILE_EXPECTED_HOSTNAMES || 'khaledaltheeb.github.io')
    .split(',').map(value => value.trim()).filter(Boolean);
  if (!response.ok || result.success !== true || !allowedHosts.includes(result.hostname) ||
      (result.action && result.action !== 'specialist_login')) {
    fail('تعذر التحقق من الاستخدام البشري.', 400, 'turnstile_failed');
  }
}

async function requestSession(request, env, ctx, cors) {
  await rateLimit(request, env, 'specialist-login-ip', 8);
  const body = await parseJson(request);
  await verifyTurnstile(body.turnstileToken, request, env);
  const email = validEmail(body.email);
  await rateLimit(request, env, 'specialist-login-email', 5, email);

  const provider = await env.DB.prepare(`
    SELECT provider_id, display_name, email, status, account_enabled
    FROM providers_private
    WHERE lower(email) = lower(?)
    LIMIT 1
  `).bind(email).first();

  if (provider && provider.status === 'active' && Number(provider.account_enabled) === 1) {
    const loginToken = randomToken(32);
    const tokenHash = await sha256(loginToken);
    const now = new Date().toISOString();
    const expiresAt = new Date(Date.now() + LOGIN_TOKEN_MINUTES * 60 * 1000).toISOString();
    const ipHash = await sha256(`${requestIp(request)}|${env.RATE_LIMIT_SALT}`);

    await env.DB.batch([
      env.DB.prepare(`
        DELETE FROM specialist_login_tokens
        WHERE provider_id = ? AND (expires_at <= ? OR used_at IS NOT NULL)
      `).bind(provider.provider_id, now),
      env.DB.prepare(`
        INSERT INTO specialist_login_tokens
        (id, provider_id, token_hash, expires_at, request_ip_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
      `).bind(crypto.randomUUID(), provider.provider_id, tokenHash, expiresAt, ipHash, now)
    ]);

    await audit(env, 'specialist_login_requested', provider.provider_id, {expiresAt});
    ctx.waitUntil(sendLoginEmail(env, provider, loginToken));
  }

  return json({
    ok:true,
    message:'إذا كان البريد مرتبطًا بحساب نشط، فسيصل رابط الدخول خلال دقائق.'
  }, 202, cors);
}

async function sendLoginEmail(env, provider, loginToken) {
  const base = String(env.ACCOUNT_BASE_URL || '').replace(/#.*$/, '');
  const link = `${base}#loginToken=${encodeURIComponent(loginToken)}`;
  await sendEmail(env, {
    to:[provider.email],
    subject:'رابط الدخول إلى حساب المختص',
    html:emailLayout('الدخول إلى حساب المختص', `
      <p>مرحبًا ${escapeHtml(provider.display_name)}،</p>
      <p>استخدم الرابط التالي لفتح لوحة محادثاتك. تنتهي صلاحيته خلال ${LOGIN_TOKEN_MINUTES} دقيقة ويُستخدم مرة واحدة فقط.</p>
      <p><a href="${escapeHtml(link)}">فتح حساب المختص</a></p>
      <p>إذا لم تطلب هذا الرابط، تجاهل الرسالة. لا تشارك الرابط مع أي شخص.</p>
    `),
    entityType:'specialist_login',
    entityId:provider.provider_id,
    template:'specialist_magic_link',
    idempotencyKey:`specialist-login/${provider.provider_id}/${Date.now()}`
  });
}

async function verifySession(request, env, cors) {
  await rateLimit(request, env, 'specialist-verify-ip', 20);
  const body = await parseJson(request);
  const rawToken = cleanString(body.token, 500, true);
  const tokenHash = await sha256(rawToken);
  const now = new Date().toISOString();

  const login = await env.DB.prepare(`
    SELECT t.id, t.provider_id, t.token_hash, t.expires_at,
      p.display_name, p.status, p.account_enabled
    FROM specialist_login_tokens t
    JOIN providers_private p ON p.provider_id = t.provider_id
    WHERE t.token_hash = ? AND t.used_at IS NULL AND t.expires_at > ?
    LIMIT 1
  `).bind(tokenHash, now).first();

  if (!login || !constantTimeEqual(tokenHash, login.token_hash) || login.status !== 'active' ||
      Number(login.account_enabled) !== 1) {
    fail('رابط الدخول غير صالح أو انتهت صلاحيته.', 401, 'invalid_login_token');
  }

  const consumed = await env.DB.prepare(`
    UPDATE specialist_login_tokens SET used_at = ?
    WHERE id = ? AND used_at IS NULL AND expires_at > ?
  `).bind(now, login.id, now).run();
  if (Number(consumed?.meta?.changes || 0) !== 1) {
    fail('رابط الدخول استُخدم مسبقًا.', 401, 'login_token_used');
  }

  const sessionToken = randomToken(32);
  const sessionHash = await sha256(sessionToken);
  const sessionHours = boundedInteger(env.SPECIALIST_SESSION_HOURS, DEFAULT_SESSION_HOURS, 1, 72);
  const expiresAt = new Date(Date.now() + sessionHours * 60 * 60 * 1000).toISOString();
  const sessionId = crypto.randomUUID();

  await env.DB.batch([
    env.DB.prepare(`
      INSERT INTO specialist_sessions
      (id, provider_id, token_hash, expires_at, created_at, last_used_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `).bind(sessionId, login.provider_id, sessionHash, expiresAt, now, now),
    env.DB.prepare(`
      UPDATE providers_private SET account_last_login_at = ?, updated_at = ?
      WHERE provider_id = ?
    `).bind(now, now, login.provider_id)
  ]);
  await audit(env, 'specialist_login_completed', login.provider_id, {sessionId, expiresAt});

  return json({
    ok:true,
    sessionToken,
    expiresAt,
    provider:{id:login.provider_id, displayName:login.display_name}
  }, 200, cors);
}

async function requireSpecialist(request, env) {
  const rawToken = bearerToken(request);
  const tokenHash = await sha256(rawToken);
  const now = new Date().toISOString();
  const row = await env.DB.prepare(`
    SELECT s.id AS session_id, s.token_hash, s.expires_at,
      p.provider_id, p.display_name, p.email, p.status,
      p.notification_enabled, p.accepts_new_requests, p.account_enabled
    FROM specialist_sessions s
    JOIN providers_private p ON p.provider_id = s.provider_id
    WHERE s.token_hash = ? AND s.revoked_at IS NULL AND s.expires_at > ?
      AND p.status = 'active' AND p.account_enabled = 1
    LIMIT 1
  `).bind(tokenHash, now).first();

  if (!row || !constantTimeEqual(tokenHash, row.token_hash)) {
    fail('انتهت جلسة الدخول أو لم تعد صالحة.', 401, 'session_expired');
  }

  await env.DB.prepare(`UPDATE specialist_sessions SET last_used_at = ? WHERE id = ?`)
    .bind(now, row.session_id).run();
  return row;
}

async function revokeSession(env, cors, actor) {
  const now = new Date().toISOString();
  await env.DB.prepare(`UPDATE specialist_sessions SET revoked_at = ? WHERE id = ?`)
    .bind(now, actor.session_id).run();
  await audit(env, 'specialist_session_revoked', actor.provider_id, {sessionId:actor.session_id});
  return json({ok:true}, 200, cors);
}

async function specialistMe(env, cors, actor) {
  const profile = await env.DB.prepare(`
    SELECT profile_json, publication_status, verification_status, consent_status,
      last_verified_at, next_review_at, updated_at
    FROM provider_profiles WHERE provider_id = ?
  `).bind(actor.provider_id).first();

  return json({
    provider:{
      id:actor.provider_id,
      displayName:actor.display_name,
      status:actor.status,
      notificationEnabled:Number(actor.notification_enabled) === 1,
      acceptsNewRequests:Number(actor.accepts_new_requests) === 1,
      accountEnabled:Number(actor.account_enabled) === 1,
      profile:profile ? safeJson(profile.profile_json, {}) : null,
      publicationStatus:profile?.publication_status || 'draft',
      verificationStatus:profile?.verification_status || 'pending',
      consentStatus:profile?.consent_status || 'pending',
      lastVerifiedAt:profile?.last_verified_at || null,
      nextReviewAt:profile?.next_review_at || null,
      updatedAt:profile?.updated_at || null
    },
    session:{expiresAt:actor.expires_at}
  }, 200, cors);
}

async function listConversations(url, env, cors, actor) {
  const status = String(url.searchParams.get('status') || '').trim();
  if (status && !CONVERSATION_STATUSES.includes(status)) {
    fail('حالة التصفية غير صالحة.', 400, 'invalid_status');
  }
  const limit = boundedInteger(url.searchParams.get('limit'), 50, 1, 100);
  const offset = boundedInteger(url.searchParams.get('offset'), 0, 0, 10_000);
  const where = status ? 'AND c.status = ?' : '';
  const bindings = status ? [actor.provider_id, status, limit, offset] : [actor.provider_id, limit, offset];
  const rows = await env.DB.prepare(`
    SELECT c.id, c.reference_id, c.visitor_name, c.status, c.topic, c.urgency,
      c.created_at, c.updated_at, c.last_message_at, c.closed_at,
      (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count,
      (SELECT substr(m2.body, 1, 180) FROM messages m2
        WHERE m2.conversation_id = c.id ORDER BY m2.created_at DESC LIMIT 1) AS last_message
    FROM conversations c
    WHERE c.provider_id = ? ${where}
    ORDER BY c.last_message_at DESC
    LIMIT ? OFFSET ?
  `).bind(...bindings).all();

  const countBindings = status ? [actor.provider_id, status] : [actor.provider_id];
  const count = await env.DB.prepare(`
    SELECT COUNT(*) AS count FROM conversations c
    WHERE c.provider_id = ? ${where}
  `).bind(...countBindings).first();

  return json({
    conversations:(rows.results || []).map(row => ({
      id:row.id,
      referenceId:row.reference_id,
      visitorName:row.visitor_name,
      status:row.status,
      topic:row.topic,
      urgency:row.urgency,
      messageCount:Number(row.message_count || 0),
      lastMessage:row.last_message || '',
      createdAt:row.created_at,
      updatedAt:row.updated_at,
      lastMessageAt:row.last_message_at,
      closedAt:row.closed_at || null
    })),
    pagination:{limit, offset, total:Number(count?.count || 0)}
  }, 200, cors);
}

async function providerConversation(env, actor, conversationId) {
  const id = validId(conversationId, 'معرف المحادثة');
  const row = await env.DB.prepare(`
    SELECT * FROM conversations WHERE id = ? AND provider_id = ?
  `).bind(id, actor.provider_id).first();
  if (!row) fail('المحادثة غير موجودة.', 404, 'conversation_not_found');
  return row;
}

async function getConversation(env, cors, actor, conversationId) {
  const conversation = await providerConversation(env, actor, conversationId);
  const messages = await env.DB.prepare(`
    SELECT id, sender_role, body, created_at
    FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
  `).bind(conversation.id).all();

  return json({
    conversation:{
      id:conversation.id,
      referenceId:conversation.reference_id,
      visitorName:conversation.visitor_name,
      status:conversation.status,
      topic:conversation.topic,
      urgency:conversation.urgency,
      context:safeJson(conversation.context_json, {}),
      createdAt:conversation.created_at,
      updatedAt:conversation.updated_at,
      lastMessageAt:conversation.last_message_at,
      closedAt:conversation.closed_at || null
    },
    messages:(messages.results || []).map(row => ({
      id:row.id,
      senderRole:row.sender_role,
      body:row.body,
      createdAt:row.created_at
    }))
  }, 200, cors);
}

async function createMessage(request, env, ctx, cors, actor, conversationId) {
  await rateLimit(request, env, 'specialist-message', 120, actor.provider_id);
  const body = await parseJson(request);
  const message = cleanString(body.body, MAX_MESSAGE_LENGTH, true);
  const conversation = await providerConversation(env, actor, conversationId);
  if (conversation.status !== 'open') fail('المحادثة مغلقة.', 409, 'conversation_closed');

  const idempotencyKey = cleanString(request.headers.get('idempotency-key'), 120, true);
  if (!/^[a-z0-9][a-z0-9._:-]{11,119}$/i.test(idempotencyKey)) {
    fail('معرف الإرسال غير صالح.', 400, 'invalid_idempotency_key');
  }
  const existing = await env.DB.prepare(`
    SELECT message_id, provider_id, conversation_id
    FROM specialist_message_requests WHERE idempotency_key = ?
  `).bind(idempotencyKey).first();
  if (existing) {
    if (existing.provider_id !== actor.provider_id || existing.conversation_id !== conversation.id) {
      fail('معرف الإرسال مستخدم لطلب مختلف.', 409, 'idempotency_conflict');
    }
    return json({ok:true, messageId:existing.message_id, duplicate:true}, 200, cors);
  }

  const now = new Date().toISOString();
  const messageId = crypto.randomUUID();
  await env.DB.batch([
    env.DB.prepare(`
      INSERT INTO messages (id, conversation_id, sender_role, body, created_at)
      VALUES (?, ?, 'specialist', ?, ?)
    `).bind(messageId, conversation.id, message, now),
    env.DB.prepare(`
      INSERT INTO specialist_message_requests
      (idempotency_key, provider_id, conversation_id, message_id, created_at)
      VALUES (?, ?, ?, ?, ?)
    `).bind(idempotencyKey, actor.provider_id, conversation.id, messageId, now),
    env.DB.prepare(`
      UPDATE conversations SET updated_at = ?, last_message_at = ? WHERE id = ?
    `).bind(now, now, conversation.id)
  ]);
  await audit(env, 'message_created_from_specialist_account', conversation.id, {
    providerId:actor.provider_id, messageId
  });

  const visitorToken = randomToken(32);
  const visitorHash = await sha256(visitorToken);
  const tokenExpiry = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();
  await env.DB.prepare(`
    INSERT INTO conversation_tokens
    (id, conversation_id, role, token_hash, expires_at, created_at)
    VALUES (?, ?, 'visitor', ?, ?, ?)
  `).bind(crypto.randomUUID(), conversation.id, visitorHash, tokenExpiry, now).run();

  const link = portalLink(env.PORTAL_BASE_URL, conversation.id, visitorToken, 'visitor');
  ctx.waitUntil(sendEmail(env, {
    to:[conversation.visitor_email],
    subject:`رد من المختص — ${conversation.reference_id}`,
    html:emailLayout('وصل رد جديد', `
      <p>وصل رد جديد في المحادثة ${escapeHtml(conversation.reference_id)}.</p>
      <p><a href="${escapeHtml(link)}">فتح المحادثة الخاصة</a></p>
      <p>لا تشارك رابط المحادثة مع الآخرين.</p>
    `),
    entityType:'message',
    entityId:messageId,
    template:'message_visitor_from_account',
    idempotencyKey:`message-visitor-account/${messageId}`
  }));

  return json({ok:true, messageId, createdAt:now}, 201, cors);
}

async function updateConversation(request, env, cors, actor, conversationId) {
  const body = await parseJson(request);
  const status = cleanString(body.status, 20, true);
  if (!['open','closed'].includes(status)) {
    fail('الحالة المطلوبة غير مسموحة.', 400, 'invalid_status');
  }
  const conversation = await providerConversation(env, actor, conversationId);
  if (['blocked','archived'].includes(conversation.status)) {
    fail('لا يمكن تعديل هذه المحادثة.', 409, 'conversation_locked');
  }
  const now = new Date().toISOString();
  const closedAt = status === 'closed' ? now : null;
  const systemText = status === 'closed' ? 'أغلق المختص المحادثة.' : 'أعاد المختص فتح المحادثة.';
  await env.DB.batch([
    env.DB.prepare(`
      UPDATE conversations SET status = ?, closed_at = ?, closed_by = 'specialist', updated_at = ?
      WHERE id = ? AND provider_id = ?
    `).bind(status, closedAt, now, conversation.id, actor.provider_id),
    env.DB.prepare(`
      INSERT INTO messages (id, conversation_id, sender_role, body, created_at)
      VALUES (?, ?, 'system', ?, ?)
    `).bind(crypto.randomUUID(), conversation.id, systemText, now)
  ]);
  await audit(env, 'conversation_status_changed_from_specialist_account', conversation.id, {
    providerId:actor.provider_id, status
  });
  return json({ok:true, status, updatedAt:now}, 200, cors);
}

function portalLink(baseValue, conversationId, accessToken, role) {
  const base = String(baseValue ||
    'https://khaledaltheeb.github.io/pterminology-site/specialists-partners/portal/');
  const url = new URL(base);
  url.hash = new URLSearchParams({conversation:conversationId, token:accessToken, role}).toString();
  return url.href;
}

function safeJson(value, fallback) {
  try {
    const parsed = JSON.parse(String(value || ''));
    return parsed && typeof parsed === 'object' ? parsed : fallback;
  } catch (_) {
    return fallback;
  }
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[char]));
}

function emailLayout(title, body) {
  return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"></head>
  <body style="font-family:Arial,sans-serif;line-height:1.8;background:#f4f8f7;padding:24px;color:#173734">
    <main style="max-width:640px;margin:auto;background:#fff;border:1px solid #d8e4e1;border-radius:18px;padding:28px">
      <h1 style="font-size:24px;color:#075f5b">${escapeHtml(title)}</h1>${body}
      <hr style="border:0;border-top:1px solid #d8e4e1;margin:24px 0">
      <p style="font-size:13px;color:#5f7773">منصة الصحة النفسية وذوي الاحتياجات الخاصة — قطاع المختصين والشراكات المهنية.</p>
    </main>
  </body></html>`;
}

async function sendEmail(env, item) {
  if (!env.RESEND_API_KEY || !env.FROM_EMAIL) {
    await recordEmailEvent(env, item, 'skipped', null, 'email_not_configured');
    return;
  }
  let response;
  try {
    response = await fetch('https://api.resend.com/emails', {
      method:'POST',
      headers:{
        authorization:`Bearer ${env.RESEND_API_KEY}`,
        'content-type':'application/json',
        'idempotency-key':item.idempotencyKey
      },
      body:JSON.stringify({
        from:env.FROM_EMAIL,
        to:item.to,
        subject:item.subject,
        html:item.html
      })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.message || `email_http_${response.status}`);
    await recordEmailEvent(env, item, 'sent', data.id || null, null);
  } catch (error) {
    console.error('specialist_account_email_failed', item.template, error);
    await recordEmailEvent(env, item, 'failed', null, cleanString(error.message, 160, false));
  }
}

async function recordEmailEvent(env, item, status, providerMessageId, errorCode) {
  if (!env.DB) return;
  try {
    const recipientHash = await sha256((item.to || []).join(',').toLowerCase());
    const now = new Date().toISOString();
    await env.DB.prepare(`
      INSERT INTO email_events
      (id, entity_type, entity_id, recipient_hash, template, status,
       provider_message_id, error_code, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(crypto.randomUUID(), item.entityType, item.entityId, recipientHash,
      item.template, status, providerMessageId, errorCode, now, now).run();
  } catch (error) {
    console.error('specialist_account_email_event_failed', error);
  }
}

async function audit(env, eventType, entityId, metadata = {}) {
  if (!env.DB) return;
  await env.DB.prepare(`
    INSERT INTO audit_log (id, event_type, entity_id, metadata_json, created_at)
    VALUES (?, ?, ?, ?, ?)
  `).bind(crypto.randomUUID(), eventType, entityId, JSON.stringify(metadata), new Date().toISOString()).run();
}
