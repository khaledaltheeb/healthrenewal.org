const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
const MAX_BODY_BYTES = 96_000;
const MAX_MESSAGE_LENGTH = 3_000;
const BUILD_VERSION = '4.0.0';
const APPLICATION_STATUSES = ['pending','reviewing','approved','rejected','withdrawn'];
const CONVERSATION_STATUSES = ['open','closed','blocked','archived'];
const PROVIDER_STATUSES = ['active','suspended','archived'];
const PUBLICATION_STATUSES = ['draft','review','published','suspended','archived'];
const VERIFICATION_STATUSES = ['pending','provisional','verified','rejected','expired'];
const CONSENT_STATUSES = ['pending','approved','revoked'];
const SPECIALTIES = [
  'psychology','psychiatry','speech_language','audiology','special_education',
  'early_intervention','occupational_therapy','physiotherapy','behavior_support',
  'learning_support','autism_support','aac','family_training','social_work',
  'nutrition','center'
];
const AGE_GROUPS = ['الرضع','الطفولة المبكرة','الأطفال','المراهقون','البالغون','جميع الأعمار'];
const SERVICE_MODES = ['حضوري','عن بعد','زيارة منزلية','مدرسي','هجين'];
const ADMIN_SESSION_MINUTES = 20;

export default {
  async scheduled(_event, env, ctx) {
    if (!env.DB) return;
    ctx.waitUntil(env.DB.batch([
      env.DB.prepare(`DELETE FROM conversation_tokens WHERE expires_at <= ?`).bind(new Date().toISOString()),
      env.DB.prepare(`DELETE FROM admin_sessions WHERE expires_at <= ? OR revoked_at IS NOT NULL`).bind(new Date().toISOString()),
      env.DB.prepare(`DELETE FROM rate_limits WHERE bucket < strftime('%Y-%m-%dT%H','now','-30 day')`),
      env.DB.prepare(`DELETE FROM email_events WHERE created_at < datetime('now','-365 day')`)
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

      if (request.method === 'GET' && url.pathname === '/v1/providers') {
        return await listPublicProviders(url, env, cors);
      }

      const publicProviderMatch = url.pathname.match(/^\/v1\/providers\/([a-z0-9-]+)$/i);
      if (publicProviderMatch && request.method === 'GET') {
        return await getPublicProvider(env, cors, publicProviderMatch[1]);
      }

      if (request.method === 'POST' && url.pathname === '/v1/applications') {
        return await createApplication(request, env, ctx, cors);
      }

      if (request.method === 'POST' && url.pathname === '/v1/conversations') {
        return await createConversation(request, env, ctx, cors);
      }

      const conversationMatch = url.pathname.match(/^\/v1\/conversations\/([a-z0-9-]+)$/i);
      if (conversationMatch && request.method === 'GET') {
        return await getConversation(request, env, cors, conversationMatch[1]);
      }
      if (conversationMatch && request.method === 'PATCH') {
        return await updateConversationByParticipant(request, env, cors, conversationMatch[1]);
      }

      const messageMatch = url.pathname.match(/^\/v1\/conversations\/([a-z0-9-]+)\/messages$/i);
      if (messageMatch && request.method === 'POST') {
        return await createMessage(request, env, ctx, cors, messageMatch[1]);
      }

      if (url.pathname === '/v1/admin/session' && request.method === 'POST') {
        return await createAdminSession(request, env, cors);
      }

      if (url.pathname.startsWith('/v1/admin/')) {
        const actor = await requireAdmin(request, env);

        if (url.pathname === '/v1/admin/session/revoke' && request.method === 'POST') {
          return await revokeAdminSession(request, env, cors, actor);
        }

        if (url.pathname === '/v1/admin/overview' && request.method === 'GET') {
          return await adminOverview(env, cors, actor);
        }
        if (url.pathname === '/v1/admin/applications' && request.method === 'GET') {
          requireRole(actor, ['owner','reviewer']);
          return await listApplications(url, env, cors);
        }
        const applicationMatch = url.pathname.match(/^\/v1\/admin\/applications\/([a-z0-9-]+)$/i);
        if (applicationMatch && request.method === 'PATCH') {
          requireRole(actor, ['owner','reviewer']);
          return await updateApplication(request, env, ctx, cors, applicationMatch[1], actor);
        }
        if (url.pathname === '/v1/admin/conversations' && request.method === 'GET') {
          requireRole(actor, ['owner','moderator']);
          return await listConversations(url, env, cors);
        }
        const adminConversationMatch = url.pathname.match(/^\/v1\/admin\/conversations\/([a-z0-9-]+)$/i);
        if (adminConversationMatch && request.method === 'PATCH') {
          requireRole(actor, ['owner','moderator']);
          return await updateConversationByAdmin(request, env, cors, adminConversationMatch[1], actor);
        }
        if (url.pathname === '/v1/admin/providers' && request.method === 'GET') {
          requireRole(actor, ['owner','reviewer']);
          return await listProviders(url, env, cors);
        }
        if (url.pathname === '/v1/admin/providers' && request.method === 'POST') {
          requireRole(actor, ['owner']);
          return await upsertProvider(request, env, cors, actor);
        }
        const providerMatch = url.pathname.match(/^\/v1\/admin\/providers\/([a-z0-9-]+)$/i);
        if (providerMatch && request.method === 'PATCH') {
          requireRole(actor, ['owner']);
          return await updateProvider(request, env, cors, actor, providerMatch[1]);
        }
        const providerActionMatch = url.pathname.match(/^\/v1\/admin\/providers\/([a-z0-9-]+)\/actions$/i);
        if (providerActionMatch && request.method === 'POST') {
          requireRole(actor, ['owner']);
          return await applyProviderAction(request, env, cors, actor, providerActionMatch[1]);
        }
        if (url.pathname === '/v1/admin/audit' && request.method === 'GET') {
          requireRole(actor, ['owner']);
          return await listAudit(url, env, cors);
        }
      }

      return json({error:'not_found', message:'المسار غير موجود.'}, 404, cors);
    } catch (error) {
      console.error('worker_error', error);
      const status = Number(error.status) || 500;
      const message = status === 500 ? 'حدث خطأ داخلي.' : error.message;
      return json({error:error.code || 'internal_error', message}, status, cors);
    }
  }
};

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://healthrenewal.org')
    .split(',').map(value => value.trim()).filter(Boolean);
  const selected = origin ? (allowed.includes(origin) ? origin : '') : (allowed[0] || '');
  const headers = {
    'access-control-allow-methods':'GET,POST,PATCH,OPTIONS',
    'access-control-allow-headers':'content-type,x-admin-key,authorization,x-conversation-role,idempotency-key,x-requested-with',
    'access-control-max-age':'86400',
    'vary':'Origin',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY',
    'referrer-policy':'no-referrer',
    'cache-control':'no-store'
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
  let registrySchema = false;
  try {
    if (env.DB) {
      await env.DB.prepare('SELECT 1 AS ok').first();
      database = true;
      const schema = await env.DB.prepare(`
        SELECT COUNT(*) AS count FROM sqlite_master
        WHERE type='table' AND name IN (
          'admin_sessions','provider_profiles','provider_review_records',
          'provider_profile_versions'
        )
      `).first();
      registrySchema = Number(schema?.count || 0) === 4;
    }
  } catch (error) {
    console.error('health_db_error', error);
  }

  const checks = {
    database,
    registrySchema,
    email:Boolean(env.RESEND_API_KEY && env.FROM_EMAIL),
    turnstile:Boolean(env.TURNSTILE_SECRET),
    adminAuth:Boolean(env.ADMIN_API_KEY),
    rateLimitSalt:Boolean(env.RATE_LIMIT_SALT),
    ownerEmail:Boolean(env.OWNER_EMAIL)
  };
  const ready = Object.values(checks).every(Boolean);
  return json({
    ok:ready,
    service:'pterminology-specialists',
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
  } catch (_error) {
    if (_error?.code) throw _error;
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

function normalizeOptionalStatus(value, allowed) {
  const status = String(value || '').trim();
  if (!status) return '';
  if (!allowed.includes(status)) fail('حالة التصفية غير صالحة.', 400, 'invalid_status');
  return status;
}

function stringArray(value, options = {}) {
  const {
    allowed = null,
    maxItems = 30,
    maxLength = 180,
    required = false
  } = options;
  if (!Array.isArray(value)) {
    if (required) fail('قائمة مطلوبة غير مكتملة.', 400, 'missing_list');
    return [];
  }
  const items = [...new Set(value.map(item => cleanString(item, maxLength, false)).filter(Boolean))];
  if (items.length > maxItems) fail('عدد عناصر القائمة أكبر من الحد المسموح.', 400, 'too_many_items');
  if (required && !items.length) fail('قائمة مطلوبة غير مكتملة.', 400, 'missing_list');
  if (allowed && items.some(item => !allowed.includes(item))) {
    fail('تحتوي القائمة قيمة غير معتمدة.', 400, 'invalid_list_value');
  }
  return items;
}

function validDate(value, required = false) {
  const text = cleanString(value, 10, required);
  if (!text) return null;
  const parsed = new Date(`${text}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text) ||
      Number.isNaN(parsed.getTime()) ||
      parsed.toISOString().slice(0, 10) !== text) {
    fail('صيغة التاريخ غير صالحة.', 400, 'invalid_date');
  }
  return text;
}

function safeHttpUrl(value) {
  const text = cleanString(value, 500, false);
  if (!text) return null;
  try {
    const parsed = new URL(text);
    if (parsed.protocol !== 'https:' || parsed.username || parsed.password) {
      fail('الرابط العام غير صالح.', 400, 'invalid_public_url');
    }
    return parsed.href;
  } catch (error) {
    if (error?.code) throw error;
    fail('الرابط العام غير صالح.', 400, 'invalid_public_url');
  }
}

function nonNegativeInteger(value, max = 1_000) {
  const number = Number.parseInt(String(value ?? '0'), 10);
  if (!Number.isFinite(number) || number < 0 || number > max) {
    fail('قيمة عددية غير صالحة.', 400, 'invalid_number');
  }
  return number;
}

function rootCredential(request, env) {
  const supplied = request.headers.get('x-admin-key') || '';
  const candidates = [
    {secret:env.ADMIN_API_KEY, role:'owner', actorLabel:'site-owner'},
    {secret:env.REVIEWER_API_KEY, role:'reviewer', actorLabel:'professional-reviewer'},
    {secret:env.MODERATOR_API_KEY, role:'moderator', actorLabel:'conversation-moderator'}
  ];
  const match = candidates.find(item => item.secret && constantTimeEqual(supplied, item.secret));
  if (!match) fail('بيانات الوصول غير صحيحة.', 401, 'unauthorized');
  return {role:match.role, actorLabel:match.actorLabel};
}

async function createAdminSession(request, env, cors) {
  await rateLimit(request, env, 'admin_session', 12);
  const credential = rootCredential(request, env);
  const accessToken = token();
  const tokenHash = await sha256(accessToken);
  const minutes = boundedInteger(env.ADMIN_SESSION_MINUTES, ADMIN_SESSION_MINUTES, 5, 60);
  const expiresAt = new Date(Date.now() + minutes * 60 * 1000).toISOString();
  const id = crypto.randomUUID();

  await env.DB.prepare(`
    INSERT INTO admin_sessions (
      id, token_hash, role, actor_label, expires_at, created_at, last_used_at
    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
  `).bind(id, tokenHash, credential.role, credential.actorLabel, expiresAt).run();
  await audit(env, 'admin_session_created', id, {
    role:credential.role,
    expiresAt
  });

  return json({
    ok:true,
    accessToken,
    role:credential.role,
    actorLabel:credential.actorLabel,
    expiresAt
  }, 201, cors);
}

async function requireAdmin(request, env) {
  const header = request.headers.get('authorization') || '';
  const match = header.match(/^Bearer\s+([A-Za-z0-9_-]{32,200})$/i);
  if (!match) fail('انتهت جلسة الإدارة أو لم تُفتح بعد.', 401, 'admin_session_required');
  const tokenHash = await sha256(match[1]);
  const row = await env.DB.prepare(`
    SELECT id, role, actor_label, expires_at
    FROM admin_sessions
    WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?
    LIMIT 1
  `).bind(tokenHash, new Date().toISOString()).first();
  if (!row) {
    fail('جلسة الإدارة غير صالحة أو منتهية.', 401, 'invalid_admin_session');
  }
  await env.DB.prepare(`
    UPDATE admin_sessions SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?
  `).bind(row.id).run();
  return {
    sessionId:row.id,
    role:row.role,
    actorLabel:row.actor_label,
    expiresAt:row.expires_at
  };
}

function requireRole(actor, roles) {
  if (!actor || !roles.includes(actor.role)) {
    fail('لا تملك هذه الصلاحية.', 403, 'insufficient_role');
  }
}

async function revokeAdminSession(request, env, cors, actor) {
  await env.DB.prepare(`
    UPDATE admin_sessions
    SET revoked_at = CURRENT_TIMESTAMP, last_used_at = CURRENT_TIMESTAMP
    WHERE id = ?
  `).bind(actor.sessionId).run();
  await audit(env, 'admin_session_revoked', actor.sessionId, {role:actor.role});
  return json({ok:true}, 200, cors);
}

async function verifyTurnstile(tokenValue, request, env) {
  if (!env.TURNSTILE_SECRET) {
    if (String(env.TURNSTILE_BYPASS_FOR_TESTING || '') === 'true') return true;
    fail('خدمة التحقق الآمن غير مهيأة.', 503, 'turnstile_not_configured');
  }
  const tokenText = cleanString(tokenValue, 2048, true);
  const payload = {
    secret:env.TURNSTILE_SECRET,
    response:tokenText,
    idempotency_key:crypto.randomUUID()
  };
  const ip = request.headers.get('CF-Connecting-IP');
  if (ip) payload.remoteip = ip;

  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method:'POST',
    headers:{'content-type':'application/json','user-agent':'pterminology-specialists/3.0'},
    body:JSON.stringify(payload),
    signal:AbortSignal.timeout(10_000)
  });
  if (!response.ok) fail('تعذر التحقق من الاستخدام البشري.', 503, 'turnstile_unavailable');

  const result = await response.json();
  if (!result.success) fail('فشل التحقق من الاستخدام البشري.', 400, 'turnstile_failed');

  const hostnames = String(env.TURNSTILE_EXPECTED_HOSTNAMES || '')
    .split(',').map(value => value.trim()).filter(Boolean);
  if (hostnames.length && !hostnames.includes(result.hostname)) {
    fail('مصدر التحقق غير معتمد.', 400, 'turnstile_hostname_mismatch');
  }

  const actions = String(env.TURNSTILE_EXPECTED_ACTIONS || '')
    .split(',').map(value => value.trim()).filter(Boolean);
  if (actions.length && result.action && !actions.includes(result.action)) {
    fail('إجراء التحقق غير معتمد.', 400, 'turnstile_action_mismatch');
  }
  return true;
}

async function sha256(value) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(value)));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}

function token() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

function base64Url(bytes) {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function reference(prefix) {
  const date = new Date().toISOString().slice(0,10).replace(/-/g, '');
  const bytes = new Uint8Array(5);
  crypto.getRandomValues(bytes);
  return `${prefix}-${date}-${Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('').toUpperCase()}`;
}

async function rateLimit(request, env, action, limit) {
  if (!env.DB) fail('قاعدة البيانات غير متاحة.', 503, 'database_unavailable');
  const ip = request.headers.get('CF-Connecting-IP') || request.headers.get('x-forwarded-for') || 'unknown';
  const key = await sha256(`${env.RATE_LIMIT_SALT || 'missing-salt'}:${ip}:${action}`);
  const bucket = new Date().toISOString().slice(0,13);
  await env.DB.prepare(`
    INSERT INTO rate_limits (key, bucket, count, updated_at)
    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
    ON CONFLICT(key, bucket)
    DO UPDATE SET count = count + 1, updated_at = CURRENT_TIMESTAMP
  `).bind(key, bucket).run();
  const row = await env.DB.prepare(
    'SELECT count FROM rate_limits WHERE key = ? AND bucket = ?'
  ).bind(key, bucket).first();
  if (Number(row?.count || 0) > limit) {
    fail('تم تجاوز عدد المحاولات المسموح خلال هذه الساعة.', 429, 'rate_limited');
  }
}

function requireIdempotencyKey(request, expected) {
  const supplied = cleanString(request.headers.get('idempotency-key'), 120, true);
  if (!constantTimeEqual(supplied, expected)) {
    fail('معرف منع التكرار غير مطابق للطلب.', 400, 'idempotency_key_mismatch');
  }
}

async function createApplication(request, env, ctx, cors) {
  await rateLimit(request, env, 'application', 5);
  const body = await parseJson(request);
  await verifyTurnstile(body.turnstileToken, request, env);

  const id = validId(body.submissionId || crypto.randomUUID(), 'معرف الطلب');
  requireIdempotencyKey(request, id);
  const referenceId = reference('APP');
  const email = validEmail(body.privateEmail);
  const displayName = cleanString(body.displayName, 140, true);
  const entityType = ['professional','center'].includes(body.entityType)
    ? body.entityType
    : fail('نوع الملف غير صالح.', 400, 'invalid_entity_type');

  if (!body.consent?.dataReview || !body.consent?.publication || !body.consent?.internalMessaging) {
    fail('الموافقات المطلوبة غير مكتملة.', 400, 'consent_required');
  }
  if (!Array.isArray(body.specialties) || body.specialties.length === 0) {
    fail('يلزم اختيار تخصص واحد على الأقل.', 400, 'specialty_required');
  }

  const existing = await env.DB.prepare(`
    SELECT reference_id, email, status FROM applications WHERE id = ?
  `).bind(id).first();
  if (existing) {
    if (!constantTimeEqual(existing.email, email)) {
      fail('معرف الطلب مستخدم لطلب مختلف.', 409, 'idempotency_conflict');
    }
    return json({
      ok:true,
      referenceId:existing.reference_id,
      status:existing.status,
      duplicate:true
    }, 200, cors);
  }

  const stored = {...body};
  delete stored.turnstileToken;

  await env.DB.prepare(`
    INSERT INTO applications (
      id, reference_id, email, display_name, entity_type, payload_json,
      status, admin_notes, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, 'pending', '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
  `).bind(id, referenceId, email, displayName, entityType, JSON.stringify(stored)).run();

  await audit(env, 'application_created', id, {referenceId, entityType});

  queueNotifications(ctx, env, [
    {
      to:[env.OWNER_EMAIL],
      subject:`طلب انضمام جديد — ${referenceId}`,
      html:emailLayout('طلب انضمام جديد', applicationSummary(referenceId, stored)),
      entityType:'application',
      entityId:id,
      template:'application_owner',
      idempotencyKey:`application-owner/${id}`
    },
    {
      to:[email],
      subject:`تم استلام طلب الانضمام ${referenceId}`,
      html:emailLayout('تم استلام طلب الانضمام',
        `<p>تم استلام طلبك وإحالته إلى إدارة المنصة للمراجعة.</p>
         <p><strong>رقم المتابعة:</strong> ${escapeHtml(referenceId)}</p>
         <p>لا يبدأ نشر الملف أو تفعيل المحادثات قبل المراجعة والموافقة النهائية.</p>`),
      entityType:'application',
      entityId:id,
      template:'application_receipt',
      idempotencyKey:`application-receipt/${id}`
    }
  ]);

  return json({ok:true, referenceId}, 201, cors);
}

async function createConversation(request, env, ctx, cors) {
  await rateLimit(request, env, 'conversation', 12);
  const body = await parseJson(request);
  await verifyTurnstile(body.turnstileToken, request, env);

  const id = validId(body.requestId || `conversation-${crypto.randomUUID()}`, 'معرف المحادثة');
  requireIdempotencyKey(request, id);
  const providerId = validId(body.providerId, 'معرف المختص');
  const provider = await env.DB.prepare(`
    SELECT provider_id, display_name, email, status, notification_enabled, accepts_new_requests
    FROM providers_private WHERE provider_id = ?
  `).bind(providerId).first();

  if (!provider || provider.status !== 'active' || Number(provider.accepts_new_requests) !== 1) {
    fail('التواصل الداخلي غير متاح لهذا المختص.', 404, 'provider_unavailable');
  }

  const visitorName = cleanString(body.sender?.displayName, 100, true);
  const visitorEmail = validEmail(body.sender?.email);
  const message = cleanString(body.message, 2000, true);
  if (message.length < 20) fail('الرسالة قصيرة جدًا.', 400, 'message_too_short');
  if (!body.consent?.privacy || !body.consent?.contact) {
    fail('الموافقات المطلوبة غير مكتملة.', 400, 'consent_required');
  }

  const duplicate = await env.DB.prepare(`
    SELECT id, reference_id, provider_id, visitor_email
    FROM conversations WHERE id = ?
  `).bind(id).first();
  if (duplicate) {
    if (!constantTimeEqual(duplicate.provider_id, providerId) ||
        !constantTimeEqual(duplicate.visitor_email, visitorEmail)) {
      fail('معرف الطلب مستخدم لمحادثة مختلفة.', 409, 'idempotency_conflict');
    }
    const renewedAccess = await issueConversationToken(env, id, 'visitor');
    return json({
      ok:true,
      conversationId:id,
      referenceId:duplicate.reference_id,
      accessToken:renewedAccess,
      duplicate:true
    }, 200, cors);
  }
  const referenceId = reference('CONV');
  const visitorAccess = token();
  const specialistAccess = token();
  const visitorHash = await sha256(visitorAccess);
  const specialistHash = await sha256(specialistAccess);
  const tokenExpiry = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();
  const topic = cleanString(body.context?.topic, 120, true);
  const urgency = cleanString(body.context?.urgency, 80, true);
  const now = new Date().toISOString();

  await env.DB.batch([
    env.DB.prepare(`
      INSERT INTO conversations (
        id, reference_id, provider_id, visitor_name, visitor_email,
        status, topic, urgency, context_json, admin_notes,
        created_at, updated_at, last_message_at
      ) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, '', ?, ?, ?)
    `).bind(id, referenceId, providerId, visitorName, visitorEmail, topic, urgency,
      JSON.stringify(body.context || {}), now, now, now),
    env.DB.prepare(`
      INSERT INTO conversation_tokens
      (id, conversation_id, role, token_hash, expires_at, created_at)
      VALUES (?, ?, 'visitor', ?, ?, ?)
    `).bind(crypto.randomUUID(), id, visitorHash, tokenExpiry, now),
    env.DB.prepare(`
      INSERT INTO conversation_tokens
      (id, conversation_id, role, token_hash, expires_at, created_at)
      VALUES (?, ?, 'specialist', ?, ?, ?)
    `).bind(crypto.randomUUID(), id, specialistHash, tokenExpiry, now),
    env.DB.prepare(`
      INSERT INTO messages (id, conversation_id, sender_role, body, created_at)
      VALUES (?, ?, 'visitor', ?, ?)
    `).bind(crypto.randomUUID(), id, message, now)
  ]);

  await audit(env, 'conversation_created', id, {referenceId, providerId, topic, urgency});

  const portalBase = String(env.PORTAL_BASE_URL ||
    'https://healthrenewal.org/specialists-partners/portal/');
  const specialistLink = portalLink(portalBase, id, specialistAccess, 'specialist');
  const visitorLink = portalLink(portalBase, id, visitorAccess, 'visitor');

  const notifications = [];
  if (Number(provider.notification_enabled) === 1) {
    notifications.push({
      to:[provider.email],
      subject:`رسالة جديدة في منصة المختصين — ${referenceId}`,
      html:emailLayout('وصلتك رسالة جديدة',
        `<p>وصل طلب تواصل جديد عبر المنصة.</p>
         <p><strong>الموضوع:</strong> ${escapeHtml(topic)}</p>
         <p><strong>الأولوية:</strong> ${escapeHtml(urgency)}</p>
         <p><a href="${escapeHtml(specialistLink)}">فتح المحادثة والرد داخل المنصة</a></p>
         <p>لا ترد على هذا البريد بمعلومات حساسة.</p>`),
      entityType:'conversation',
      entityId:id,
      template:'conversation_specialist',
      idempotencyKey:`conversation-specialist/${id}`
    });
  }

  notifications.push({
    to:[visitorEmail],
    subject:`تم إنشاء المحادثة — ${referenceId}`,
    html:emailLayout('تم إنشاء محادثتك',
      `<p>تم تسجيل الطلب الموجه إلى ${escapeHtml(provider.display_name)}.</p>
       <p><strong>رقم المتابعة:</strong> ${escapeHtml(referenceId)}</p>
       <p><a href="${escapeHtml(visitorLink)}">فتح المحادثة الخاصة</a></p>
       <p>احتفظ بالرابط ولا تشاركه مع الآخرين.</p>`),
    entityType:'conversation',
    entityId:id,
    template:'conversation_visitor',
    idempotencyKey:`conversation-visitor/${id}`
  });

  if (env.OWNER_EMAIL) {
    notifications.push({
      to:[env.OWNER_EMAIL],
      subject:`محادثة جديدة ${referenceId}`,
      html:emailLayout('محادثة جديدة في القطاع',
        `<p>تم فتح محادثة مع الملف: <strong>${escapeHtml(provider.display_name)}</strong>.</p>
         <p>المرجع: ${escapeHtml(referenceId)}</p>
         <p>الموضوع: ${escapeHtml(topic)}</p>`),
      entityType:'conversation',
      entityId:id,
      template:'conversation_owner',
      idempotencyKey:`conversation-owner/${id}`
    });
  }
  queueNotifications(ctx, env, notifications);

  return json({ok:true, conversationId:id, referenceId, accessToken:visitorAccess}, 201, cors);
}

async function getConversation(request, env, cors, conversationId) {
  const url = new URL(request.url);
  const {accessToken, role} = conversationAccess(request, url);
  const conversation = await authorizedConversation(env, conversationId, accessToken, role);
  const messages = await env.DB.prepare(`
    SELECT id, sender_role, body, created_at
    FROM messages WHERE conversation_id = ? ORDER BY created_at ASC
  `).bind(conversationId).all();

  return json({
    conversation:{
      id:conversation.id,
      referenceId:conversation.reference_id,
      status:conversation.status,
      topic:conversation.topic,
      urgency:conversation.urgency,
      createdAt:conversation.created_at,
      updatedAt:conversation.updated_at,
      closedAt:conversation.closed_at || null,
      role
    },
    provider:{id:conversation.provider_id, displayName:conversation.provider_display_name},
    messages:(messages.results || []).map(row => ({
      id:row.id,
      senderRole:row.sender_role,
      body:row.body,
      createdAt:row.created_at
    }))
  }, 200, cors);
}

async function createMessage(request, env, ctx, cors, conversationId) {
  await rateLimit(request, env, 'message', 80);
  const body = await parseJson(request);
  const {accessToken, role} = conversationAccess(request, new URL(request.url), body);
  const message = cleanString(body.body, MAX_MESSAGE_LENGTH, true);
  const conversation = await authorizedConversation(env, conversationId, accessToken, role);
  if (conversation.status !== 'open') fail('المحادثة مغلقة.', 409, 'conversation_closed');

  const now = new Date().toISOString();
  const messageId = crypto.randomUUID();
  await env.DB.batch([
    env.DB.prepare(`
      INSERT INTO messages (id, conversation_id, sender_role, body, created_at)
      VALUES (?, ?, ?, ?, ?)
    `).bind(messageId, conversationId, role, message, now),
    env.DB.prepare(`
      UPDATE conversations SET updated_at = ?, last_message_at = ? WHERE id = ?
    `).bind(now, now, conversationId)
  ]);
  await audit(env, 'message_created', conversationId, {senderRole:role, messageId});

  const portalBase = String(env.PORTAL_BASE_URL ||
    'https://healthrenewal.org/specialists-partners/portal/');
  if (role === 'visitor' && Number(conversation.provider_notification_enabled) === 1) {
    const specialistToken = await issueConversationToken(env, conversationId, 'specialist', now);
    const link = portalLink(portalBase, conversationId, specialistToken, 'specialist');
    queueNotifications(ctx, env, [{
      to:[conversation.provider_email],
      subject:`رد جديد — ${conversation.reference_id}`,
      html:emailLayout('رسالة جديدة في المحادثة',
        `<p>وصلت رسالة جديدة في المحادثة ${escapeHtml(conversation.reference_id)}.</p>
         <p><a href="${escapeHtml(link)}">فتح المحادثة</a></p>`),
      entityType:'message',
      entityId:messageId,
      template:'message_specialist',
      idempotencyKey:`message-specialist/${messageId}`
    }]);
  } else if (role === 'specialist') {
    const visitorToken = await issueConversationToken(env, conversationId, 'visitor', now);
    const link = portalLink(portalBase, conversationId, visitorToken, 'visitor');
    queueNotifications(ctx, env, [{
      to:[conversation.visitor_email],
      subject:`رد من المختص — ${conversation.reference_id}`,
      html:emailLayout('وصل رد جديد',
        `<p>وصل رد جديد في المحادثة ${escapeHtml(conversation.reference_id)}.</p>
         <p><a href="${escapeHtml(link)}">فتح المحادثة</a></p>`),
      entityType:'message',
      entityId:messageId,
      template:'message_visitor',
      idempotencyKey:`message-visitor/${messageId}`
    }]);
  }

  return json({ok:true, messageId, createdAt:now}, 201, cors);
}

async function updateConversationByParticipant(request, env, cors, conversationId) {
  const body = await parseJson(request);
  const {accessToken, role} = conversationAccess(request, new URL(request.url), body);
  const status = cleanString(body.status, 20, true);
  const conversation = await authorizedConversation(env, conversationId, accessToken, role);

  if (role === 'visitor' && status !== 'closed') {
    fail('يمكن للزائر إغلاق المحادثة فقط.', 403, 'status_not_allowed');
  }
  if (role === 'specialist' && !['open','closed'].includes(status)) {
    fail('الحالة المطلوبة غير مسموحة.', 400, 'invalid_status');
  }
  if (conversation.status === 'blocked' || conversation.status === 'archived') {
    fail('لا يمكن تعديل هذه المحادثة.', 409, 'conversation_locked');
  }

  const now = new Date().toISOString();
  const closedAt = status === 'closed' ? now : null;
  const systemText = status === 'closed' ? 'تم إغلاق المحادثة.' : 'تمت إعادة فتح المحادثة.';
  await env.DB.batch([
    env.DB.prepare(`
      UPDATE conversations
      SET status = ?, closed_at = ?, closed_by = ?, updated_at = ?
      WHERE id = ?
    `).bind(status, closedAt, role, now, conversationId),
    env.DB.prepare(`
      INSERT INTO messages (id, conversation_id, sender_role, body, created_at)
      VALUES (?, ?, 'system', ?, ?)
    `).bind(crypto.randomUUID(), conversationId, systemText, now)
  ]);
  await audit(env, 'conversation_status_changed', conversationId, {status, changedBy:role});
  return json({ok:true, status, updatedAt:now}, 200, cors);
}

async function authorizedConversation(env, conversationId, accessToken, role) {
  const id = validId(conversationId, 'معرف المحادثة');
  const accessHash = await sha256(accessToken);
  const row = await env.DB.prepare(`
    SELECT c.*,
      p.display_name AS provider_display_name,
      p.email AS provider_email,
      p.notification_enabled AS provider_notification_enabled
    FROM conversations c
    JOIN providers_private p ON p.provider_id = c.provider_id
    WHERE c.id = ?
  `).bind(id).first();
  if (!row) fail('المحادثة غير موجودة.', 404, 'conversation_not_found');

  const tokenRow = await env.DB.prepare(`
    SELECT token_hash, expires_at FROM conversation_tokens
    WHERE conversation_id = ? AND role = ? AND token_hash = ? AND expires_at > ?
    ORDER BY created_at DESC LIMIT 1
  `).bind(id, role, accessHash, new Date().toISOString()).first();

  if (!tokenRow || !constantTimeEqual(accessHash, tokenRow.token_hash)) {
    fail('رابط المحادثة غير صالح أو انتهت صلاحيته.', 403, 'invalid_access_token');
  }
  return row;
}

function conversationAccess(request, url, body = {}) {
  if (url.searchParams.has('token') || url.searchParams.has('role') ||
      Object.prototype.hasOwnProperty.call(body, 'token') ||
      Object.prototype.hasOwnProperty.call(body, 'role')) {
    fail('يجب إرسال بيانات دخول المحادثة في الترويسات الآمنة فقط.', 400, 'conversation_credentials_in_url_or_body');
  }
  const header = request.headers.get('authorization') || '';
  const tokenMatch = header.match(/^Bearer\s+([A-Za-z0-9_-]{32,200})$/i);
  if (!tokenMatch) fail('بيانات دخول المحادثة غير مكتملة.', 401, 'conversation_token_required');
  const role = cleanString(request.headers.get('x-conversation-role'), 20, true);
  if (!['visitor','specialist'].includes(role)) {
    fail('دور المحادثة غير صالح.', 400, 'invalid_conversation_role');
  }
  return {accessToken:tokenMatch[1], role};
}

async function issueConversationToken(env, conversationId, role, now = new Date().toISOString()) {
  const accessToken = token();
  const tokenHash = await sha256(accessToken);
  const expiresAt = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();
  await env.DB.prepare(`
    INSERT INTO conversation_tokens
    (id, conversation_id, role, token_hash, expires_at, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `).bind(crypto.randomUUID(), conversationId, role, tokenHash, expiresAt, now).run();
  return accessToken;
}

function portalLink(base, conversationId, accessToken, role) {
  const portalBase = String(base).replace(/\/?$/, '/');
  return `${portalBase}#conversation=${encodeURIComponent(conversationId)}&token=${encodeURIComponent(accessToken)}&role=${encodeURIComponent(role)}`;
}

async function adminOverview(env, cors, actor) {
  const [applications, conversations, providers, profiles, unread, emailFailures] = await Promise.all([
    env.DB.prepare(`
      SELECT COUNT(*) AS total,
        SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
        SUM(CASE WHEN status='reviewing' THEN 1 ELSE 0 END) AS reviewing
      FROM applications
    `).first(),
    env.DB.prepare(`
      SELECT COUNT(*) AS total,
        SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) AS open,
        SUM(CASE WHEN status='blocked' THEN 1 ELSE 0 END) AS blocked
      FROM conversations
    `).first(),
    env.DB.prepare(`
      SELECT COUNT(*) AS total,
        SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) AS active,
        SUM(CASE WHEN accepts_new_requests=1 AND status='active' THEN 1 ELSE 0 END) AS accepting
      FROM providers_private
    `).first(),
    env.DB.prepare(`
      SELECT COUNT(*) AS total,
        SUM(CASE WHEN pp.publication_status='published'
          AND pp.verification_status='verified'
          AND pp.consent_status='approved'
          AND pp.next_review_at >= date('now')
          AND p.status='active' THEN 1 ELSE 0 END) AS published,
        SUM(CASE WHEN pp.publication_status='review' THEN 1 ELSE 0 END) AS review,
        SUM(CASE WHEN pp.next_review_at BETWEEN date('now') AND date('now','+30 day')
          AND pp.publication_status='published' THEN 1 ELSE 0 END) AS review_due,
        SUM(CASE WHEN pp.next_review_at < date('now')
          AND pp.publication_status='published' THEN 1 ELSE 0 END) AS expired
      FROM provider_profiles pp
      JOIN providers_private p ON p.provider_id = pp.provider_id
    `).first(),
    env.DB.prepare(`SELECT COUNT(*) AS count FROM conversations WHERE status='open' AND last_message_at >= datetime('now','-7 day')`).first(),
    env.DB.prepare(`SELECT COUNT(*) AS count FROM email_events WHERE status='failed' AND created_at >= datetime('now','-7 day')`).first()
  ]);

  return json({
    applications:integerRow(applications, ['total','pending','reviewing']),
    conversations:integerRow(conversations, ['total','open','blocked']),
    providers:integerRow(providers, ['total','active','accepting']),
    profiles:integerRow(profiles, ['total','published','review','review_due','expired']),
    activity:{openLast7Days:Number(unread?.count || 0)},
    notifications:{failedLast7Days:Number(emailFailures?.count || 0)},
    authorization:{
      role:actor.role,
      actorLabel:actor.actorLabel,
      expiresAt:actor.expiresAt,
      permissions:permissionsForRole(actor.role)
    },
    generatedAt:new Date().toISOString()
  }, 200, cors);
}

function integerRow(row, keys) {
  return Object.fromEntries(keys.map(key => [key, Number(row?.[key] || 0)]));
}

function permissionsForRole(role) {
  if (role === 'owner') {
    return ['applications:read','applications:decide','providers:read','providers:write',
      'providers:publish','conversations:moderate','audit:read'];
  }
  if (role === 'reviewer') return ['applications:read','applications:review','providers:read'];
  if (role === 'moderator') return ['conversations:moderate'];
  return [];
}

async function listApplications(url, env, cors) {
  const status = normalizeOptionalStatus(url.searchParams.get('status'), APPLICATION_STATUSES);
  const limit = boundedInteger(url.searchParams.get('limit'), 30, 1, 100);
  const offset = boundedInteger(url.searchParams.get('offset'), 0, 0, 10_000);
  const where = status ? 'WHERE status = ?' : '';
  const statement = env.DB.prepare(`
    SELECT id, reference_id, email, display_name, entity_type, payload_json,
      status, admin_notes, reviewed_at, reviewed_by, created_at, updated_at
    FROM applications ${where}
    ORDER BY created_at DESC LIMIT ? OFFSET ?
  `);
  const result = status ? await statement.bind(status, limit, offset).all() : await statement.bind(limit, offset).all();

  return json({
    items:(result.results || []).map(row => ({
      id:row.id,
      referenceId:row.reference_id,
      email:row.email,
      displayName:row.display_name,
      entityType:row.entity_type,
      status:row.status,
      adminNotes:row.admin_notes || '',
      reviewedAt:row.reviewed_at || null,
      reviewedBy:row.reviewed_by || null,
      createdAt:row.created_at,
      updatedAt:row.updated_at,
      payload:safeJson(row.payload_json, {})
    })),
    limit,
    offset
  }, 200, cors);
}

async function updateApplication(request, env, ctx, cors, applicationId, actor) {
  const id = validId(applicationId, 'معرف الطلب');
  const body = await parseJson(request);
  const status = cleanString(body.status, 20, true);
  if (!APPLICATION_STATUSES.includes(status)) fail('حالة الطلب غير صالحة.', 400, 'invalid_status');
  if (actor.role === 'reviewer' && !['pending','reviewing'].includes(status)) {
    fail('صلاحية المراجع تسمح ببدء المراجعة فقط؛ قرار القبول أو الرفض للمالك.', 403, 'owner_decision_required');
  }
  const notes = cleanString(body.adminNotes, 4000, false);
  const publicMessage = cleanString(body.publicMessage, 1000, false);
  const reviewedBy = cleanString(actor.actorLabel, 120, true);
  const application = await env.DB.prepare(`SELECT * FROM applications WHERE id = ?`).bind(id).first();
  if (!application) fail('طلب الانضمام غير موجود.', 404, 'application_not_found');

  const now = new Date().toISOString();
  await env.DB.prepare(`
    UPDATE applications
    SET status = ?, admin_notes = ?, reviewed_at = ?, reviewed_by = ?, updated_at = ?
    WHERE id = ?
  `).bind(status, notes, now, reviewedBy, now, id).run();

  let providerId = null;
  if (status === 'approved' && body.provider) {
    requireRole(actor, ['owner']);
    const providerPayload = {
      ...body.provider,
      providerId:body.provider.providerId,
      email:body.provider.email || application.email,
      displayName:body.provider.displayName || application.display_name,
      applicationId:id
    };
    if (body.provider.profile) {
      const result = await saveProviderBundleData(env, providerPayload, actor,
        body.provider.action || 'save_draft');
      providerId = result.providerId;
    } else {
      providerId = await upsertProviderData(env, providerPayload, actor);
    }
    await audit(env, 'application_provider_activated', id, {
      providerId,
      actorRole:actor.role
    });
  }

  await audit(env, 'application_status_changed', id, {
    status,
    reviewedBy,
    providerId,
    actorRole:actor.role
  });

  if (body.notify !== false) {
    const subjectMap = {
      pending:'تحديث طلب الانضمام',
      reviewing:'طلبك قيد المراجعة',
      approved:'تمت الموافقة على طلب الانضمام',
      rejected:'نتيجة مراجعة طلب الانضمام',
      withdrawn:'تم سحب طلب الانضمام'
    };
    queueNotifications(ctx, env, [{
      to:[application.email],
      subject:`${subjectMap[status]} — ${application.reference_id}`,
      html:emailLayout(subjectMap[status],
        `<p>تم تحديث حالة طلبك ذي الرقم <strong>${escapeHtml(application.reference_id)}</strong>.</p>
         <p><strong>الحالة:</strong> ${escapeHtml(status)}</p>
         ${publicMessage ? `<p>${escapeHtml(publicMessage)}</p>` : ''}`),
      entityType:'application',
      entityId:id,
      template:`application_status_${status}`,
      idempotencyKey:`application-status/${id}/${status}/${now.slice(0,16)}`
    }]);
  }

  return json({ok:true, id, status, providerId, updatedAt:now}, 200, cors);
}

async function listConversations(url, env, cors) {
  const status = normalizeOptionalStatus(url.searchParams.get('status'), CONVERSATION_STATUSES);
  const providerIdRaw = cleanString(url.searchParams.get('providerId'), 90, false);
  const providerId = providerIdRaw ? validId(providerIdRaw, 'معرف المختص') : '';
  const limit = boundedInteger(url.searchParams.get('limit'), 30, 1, 100);
  const offset = boundedInteger(url.searchParams.get('offset'), 0, 0, 10_000);

  const clauses = [];
  const values = [];
  if (status) { clauses.push('c.status = ?'); values.push(status); }
  if (providerId) { clauses.push('c.provider_id = ?'); values.push(providerId); }
  const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';

  const result = await env.DB.prepare(`
    SELECT c.id, c.reference_id, c.provider_id, c.visitor_name, c.visitor_email,
      c.status, c.topic, c.urgency, c.admin_notes, c.created_at, c.updated_at,
      c.last_message_at, c.closed_at, c.closed_by, p.display_name AS provider_display_name,
      (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
    FROM conversations c
    JOIN providers_private p ON p.provider_id = c.provider_id
    ${where}
    ORDER BY c.last_message_at DESC LIMIT ? OFFSET ?
  `).bind(...values, limit, offset).all();

  return json({
    items:(result.results || []).map(row => ({
      id:row.id,
      referenceId:row.reference_id,
      providerId:row.provider_id,
      providerDisplayName:row.provider_display_name,
      visitorName:row.visitor_name,
      visitorEmail:row.visitor_email,
      status:row.status,
      topic:row.topic,
      urgency:row.urgency,
      adminNotes:row.admin_notes || '',
      messageCount:Number(row.message_count || 0),
      createdAt:row.created_at,
      updatedAt:row.updated_at,
      lastMessageAt:row.last_message_at,
      closedAt:row.closed_at || null,
      closedBy:row.closed_by || null
    })),
    limit,
    offset
  }, 200, cors);
}

async function updateConversationByAdmin(request, env, cors, conversationId, actor) {
  const id = validId(conversationId, 'معرف المحادثة');
  const body = await parseJson(request);
  const status = cleanString(body.status, 20, true);
  if (!CONVERSATION_STATUSES.includes(status)) fail('حالة المحادثة غير صالحة.', 400, 'invalid_status');
  const notes = cleanString(body.adminNotes, 4000, false);
  const exists = await env.DB.prepare('SELECT id FROM conversations WHERE id = ?').bind(id).first();
  if (!exists) fail('المحادثة غير موجودة.', 404, 'conversation_not_found');

  const now = new Date().toISOString();
  const closedAt = status === 'closed' ? now : null;
  await env.DB.prepare(`
    UPDATE conversations
    SET status = ?, admin_notes = ?, closed_at = ?, closed_by = ?, updated_at = ?
    WHERE id = ?
  `).bind(status, notes, closedAt, actor.actorLabel, now, id).run();
  await audit(env, 'conversation_admin_status_changed', id, {
    status,
    actorRole:actor.role
  });
  return json({ok:true, id, status, updatedAt:now}, 200, cors);
}

async function listPublicProviders(url, env, cors) {
  const limit = boundedInteger(url.searchParams.get('limit'), 200, 1, 250);
  const result = await env.DB.prepare(`
    SELECT pp.profile_json, pp.updated_at, p.accepts_new_requests
    FROM provider_profiles pp
    JOIN providers_private p ON p.provider_id = pp.provider_id
    WHERE pp.publication_status = 'published'
      AND pp.verification_status = 'verified'
      AND pp.consent_status = 'approved'
      AND p.status = 'active'
      AND pp.next_review_at >= date('now')
    ORDER BY pp.updated_at DESC
    LIMIT ?
  `).bind(limit).all();
  const rows = result.results || [];
  const providers = rows.map(publicProviderFromRow).filter(Boolean)
    .sort((a, b) => String(a.displayName).localeCompare(String(b.displayName), 'ar'));
  const updatedAt = rows.reduce((latest, row) =>
    !latest || String(row.updated_at) > latest ? String(row.updated_at) : latest, '');
  return json({
    schemaVersion:'2.0.0',
    updatedAt:updatedAt || new Date().toISOString(),
    source:'verified-provider-registry',
    providers
  }, 200, {...cors, 'cache-control':'public, max-age=60, stale-while-revalidate=300'});
}

async function getPublicProvider(env, cors, providerId) {
  const id = validId(providerId, 'معرف المختص');
  const row = await env.DB.prepare(`
    SELECT pp.profile_json, pp.updated_at, p.accepts_new_requests
    FROM provider_profiles pp
    JOIN providers_private p ON p.provider_id = pp.provider_id
    WHERE pp.provider_id = ?
      AND pp.publication_status = 'published'
      AND pp.verification_status = 'verified'
      AND pp.consent_status = 'approved'
      AND p.status = 'active'
      AND pp.next_review_at >= date('now')
    LIMIT 1
  `).bind(id).first();
  const provider = row ? publicProviderFromRow(row) : null;
  if (!provider) fail('الملف غير موجود أو غير منشور.', 404, 'provider_not_found');
  return json({provider, updatedAt:row.updated_at}, 200,
    {...cors, 'cache-control':'public, max-age=60, stale-while-revalidate=300'});
}

function publicProviderFromRow(row) {
  const profile = safeJson(row.profile_json, null);
  if (!profile || typeof profile !== 'object' || Array.isArray(profile)) return null;
  return {
    ...profile,
    communication:{
      ...(profile.communication || {}),
      acceptsNewRequests:Number(row.accepts_new_requests) === 1
    }
  };
}

async function listProviders(url, env, cors) {
  const status = normalizeOptionalStatus(url.searchParams.get('status'), PROVIDER_STATUSES);
  const limit = boundedInteger(url.searchParams.get('limit'), 100, 1, 250);
  const offset = boundedInteger(url.searchParams.get('offset'), 0, 0, 10_000);
  const where = status ? 'WHERE p.status = ?' : '';
  const statement = env.DB.prepare(`
    SELECT
      p.provider_id, p.email, p.display_name, p.status AS private_status,
      p.notification_enabled, p.accepts_new_requests,
      p.created_at AS private_created_at, p.updated_at AS private_updated_at,
      pp.application_id, pp.profile_json, pp.publication_status,
      pp.verification_status, pp.consent_status, pp.reviewer_role,
      pp.last_verified_at, pp.next_review_at, pp.published_at,
      pp.public_revision, pp.created_at AS profile_created_at,
      pp.updated_at AS profile_updated_at,
      pr.checklist_json, pr.evidence_summary_json, pr.private_notes,
      pr.public_note, pr.decision, pr.reviewed_at
    FROM providers_private p
    LEFT JOIN provider_profiles pp ON pp.provider_id = p.provider_id
    LEFT JOIN provider_review_records pr ON pr.provider_id = p.provider_id
    ${where}
    ORDER BY p.display_name ASC LIMIT ? OFFSET ?
  `);
  const result = status ? await statement.bind(status, limit, offset).all() : await statement.bind(limit, offset).all();

  return json({
    items:(result.results || []).map(row => {
      const reviewExpired = row.publication_status === 'published' &&
        row.next_review_at && String(row.next_review_at) < new Date().toISOString().slice(0, 10);
      return {
        providerId:row.provider_id,
        email:row.email,
        displayName:row.display_name,
        status:row.private_status,
        notificationEnabled:Number(row.notification_enabled) === 1,
        acceptsNewRequests:Number(row.accepts_new_requests) === 1,
        applicationId:row.application_id || null,
        publicationStatus:row.publication_status || 'draft',
        verificationStatus:reviewExpired ? 'expired' : (row.verification_status || 'pending'),
        consentStatus:row.consent_status || 'pending',
        reviewerRole:row.reviewer_role || null,
        lastVerifiedAt:row.last_verified_at || null,
        nextReviewAt:row.next_review_at || null,
        publishedAt:row.published_at || null,
        publicRevision:Number(row.public_revision || 0),
        profile:safeJson(row.profile_json, null),
        review:{
          checklist:safeJson(row.checklist_json, {}),
          evidenceSummary:safeJson(row.evidence_summary_json, {}),
          privateNotes:row.private_notes || '',
          publicNote:row.public_note || '',
          decision:row.decision || 'pending',
          reviewedAt:row.reviewed_at || null,
          nextReviewAt:row.next_review_at || null
        },
        createdAt:row.profile_created_at || row.private_created_at,
        updatedAt:row.profile_updated_at || row.private_updated_at
      };
    }),
    limit,
    offset
  }, 200, cors);
}

async function upsertProvider(request, env, cors, actor) {
  const body = await parseJson(request);
  const result = body.profile
    ? await saveProviderBundleData(env, body, actor, body.action || 'save_draft')
    : {providerId:await upsertProviderData(env, body, actor)};
  return json({ok:true, ...result}, 200, cors);
}

async function updateProvider(request, env, cors, actor, providerId) {
  const body = await parseJson(request);
  const id = validId(providerId, 'معرف المختص');
  if (body.providerId && !constantTimeEqual(String(body.providerId), id)) {
    fail('معرف المسار لا يطابق معرف الملف.', 409, 'provider_id_mismatch');
  }
  const result = await saveProviderBundleData(env, {...body, providerId:id}, actor,
    body.action || 'save_draft');
  return json({ok:true, ...result}, 200, cors);
}

async function applyProviderAction(request, env, cors, actor, providerId) {
  const body = await parseJson(request);
  const action = cleanString(body.action, 40, true);
  const result = await saveProviderBundleData(env, {
    ...body,
    providerId:validId(providerId, 'معرف المختص')
  }, actor, action);
  return json({ok:true, ...result}, 200, cors);
}

async function saveProviderBundleData(env, body, actor, requestedAction) {
  const action = cleanString(requestedAction || 'save_draft', 40, true);
  const allowedActions = [
    'save_draft','submit_review','approve_publish','suspend','archive','revoke_consent'
  ];
  if (!allowedActions.includes(action)) fail('إجراء الملف غير صالح.', 400, 'invalid_provider_action');

  const normalizedProviderId = validId(body.providerId, 'معرف المختص');
  const privatePayload = {...body};
  if (action === 'approve_publish') privatePayload.status = 'active';
  if (action === 'suspend' || action === 'revoke_consent') privatePayload.status = 'suspended';
  if (action === 'archive') privatePayload.status = 'archived';
  let profile = null;
  let review = null;
  if (body.profile) {
    profile = sanitizePublicProfile(body.profile, normalizedProviderId);
    review = sanitizeProviderReview(body.review || {});
    if (action === 'approve_publish') assertPublishableProfile(profile, review);
  }
  const providerId = await upsertProviderData(
    env,
    {...privatePayload, providerId:normalizedProviderId},
    actor
  );

  if (!body.profile) {
    return {providerId, action, publicationStatus:null};
  }

  const existing = await env.DB.prepare(`
    SELECT publication_status, verification_status, consent_status,
      published_at, public_revision
    FROM provider_profiles WHERE provider_id = ?
  `).bind(providerId).first();
  const now = new Date().toISOString();
  const today = now.slice(0, 10);
  let publicationStatus = existing?.publication_status || 'draft';
  let verificationStatus = existing?.verification_status || 'pending';
  let consentStatus = existing?.consent_status || 'pending';
  let publishedAt = existing?.published_at || null;
  let decision = review.decision || 'pending';

  if (action === 'save_draft') {
    publicationStatus = 'draft';
    verificationStatus = 'pending';
    consentStatus = review.consentApproved ? 'approved' : 'pending';
    decision = 'pending';
  } else if (action === 'submit_review') {
    publicationStatus = 'review';
    verificationStatus = 'provisional';
    consentStatus = review.consentApproved ? 'approved' : 'pending';
    decision = 'pending';
  } else if (action === 'approve_publish') {
    publicationStatus = 'published';
    verificationStatus = 'verified';
    consentStatus = 'approved';
    decision = 'approved';
    publishedAt = publishedAt || now;
  } else if (action === 'suspend') {
    publicationStatus = 'suspended';
    decision = 'suspended';
  } else if (action === 'archive') {
    publicationStatus = 'archived';
    decision = 'suspended';
  } else if (action === 'revoke_consent') {
    publicationStatus = 'suspended';
    consentStatus = 'revoked';
    decision = 'suspended';
  }

  const revision = Number(existing?.public_revision || 0) + 1;
  const lastVerifiedAt = verificationStatus === 'verified'
    ? today
    : null;
  const nextReviewAt = verificationStatus === 'verified' ? review.nextReviewAt : null;
  const publicProfile = {
    ...profile,
    communication:{
      ...profile.communication,
      acceptsNewRequests:privatePayload.acceptsNewRequests !== false &&
        publicationStatus === 'published'
    },
    verification:{
      status:verificationStatus,
      lastVerifiedAt,
      nextReviewAt,
      reviewerRole:verificationStatus === 'verified' ? actor.role : null,
      verifiedFields:verificationStatus === 'verified'
        ? verifiedFieldsFromChecklist(review.checklist)
        : [],
      publicNote:review.publicNote || null,
      sources:verificationStatus === 'verified'
        ? publicVerificationSources(review.checklist, lastVerifiedAt)
        : []
    },
    publicationStatus,
    consent:{
      publicProfileApproved:consentStatus === 'approved',
      approvedAt:consentStatus === 'approved' ? (review.consentApprovedAt || today) : null,
      approvedFields:consentStatus === 'approved'
        ? ['identity','professional_scope','services','location','contact','verification']
        : []
    },
    publicRevision:revision,
    publishedAt,
    updatedAt:now
  };
  const reason = cleanString(body.reason || action, 500, true);

  await env.DB.batch([
    env.DB.prepare(`
      INSERT INTO provider_profiles (
        provider_id, application_id, entity_type, profile_json,
        publication_status, verification_status, consent_status,
        reviewer_role, last_verified_at, next_review_at, published_at,
        public_revision, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(provider_id) DO UPDATE SET
        application_id=COALESCE(excluded.application_id, provider_profiles.application_id),
        entity_type=excluded.entity_type,
        profile_json=excluded.profile_json,
        publication_status=excluded.publication_status,
        verification_status=excluded.verification_status,
        consent_status=excluded.consent_status,
        reviewer_role=excluded.reviewer_role,
        last_verified_at=excluded.last_verified_at,
        next_review_at=excluded.next_review_at,
        published_at=excluded.published_at,
        public_revision=excluded.public_revision,
        updated_at=excluded.updated_at
    `).bind(
      providerId,
      cleanString(body.applicationId, 90, false) || null,
      publicProfile.entityType,
      JSON.stringify(publicProfile),
      publicationStatus,
      verificationStatus,
      consentStatus,
      actor.role,
      lastVerifiedAt,
      nextReviewAt,
      publishedAt,
      revision,
      now,
      now
    ),
    env.DB.prepare(`
      INSERT INTO provider_review_records (
        provider_id, checklist_json, evidence_summary_json, private_notes,
        public_note, decision, reviewer_role, reviewed_at, next_review_at,
        created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(provider_id) DO UPDATE SET
        checklist_json=excluded.checklist_json,
        evidence_summary_json=excluded.evidence_summary_json,
        private_notes=excluded.private_notes,
        public_note=excluded.public_note,
        decision=excluded.decision,
        reviewer_role=excluded.reviewer_role,
        reviewed_at=excluded.reviewed_at,
        next_review_at=excluded.next_review_at,
        updated_at=excluded.updated_at
    `).bind(
      providerId,
      JSON.stringify(review.checklist),
      JSON.stringify(review.evidenceSummary),
      review.privateNotes,
      review.publicNote,
      decision,
      actor.role,
      verificationStatus === 'verified' ? now : null,
      nextReviewAt,
      now,
      now
    ),
    env.DB.prepare(`
      INSERT INTO provider_profile_versions (
        id, provider_id, revision, profile_json, publication_status,
        actor_role, reason, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      crypto.randomUUID(),
      providerId,
      revision,
      JSON.stringify(publicProfile),
      publicationStatus,
      actor.role,
      reason,
      now
    )
  ]);

  await audit(env, 'provider_profile_changed', providerId, {
    action,
    publicationStatus,
    verificationStatus,
    consentStatus,
    revision,
    actorRole:actor.role
  });
  return {
    providerId,
    action,
    publicationStatus,
    verificationStatus,
    consentStatus,
    publicRevision:revision,
    publishedAt,
    updatedAt:now
  };
}

function sanitizePublicProfile(raw, providerId) {
  const entityType = ['professional','center'].includes(raw.entityType)
    ? raw.entityType
    : 'professional';
  const qualifications = Array.isArray(raw.qualifications)
    ? raw.qualifications.slice(0, 8).map(item => ({
      name:cleanString(item?.name, 220, false),
      institution:cleanString(item?.institution, 220, false),
      level:cleanString(item?.level, 100, false) || null,
      year:item?.year ? boundedInteger(item.year, null, 1950, 2100) : null
    })).filter(item => item.name && item.institution)
    : [];
  const licenses = Array.isArray(raw.licenses)
    ? raw.licenses.slice(0, 5).map(item => ({
      authority:cleanString(item?.authority, 220, false) || null,
      identifierPublic:cleanString(item?.identifierPublic, 120, false) || null,
      status:['active','not_applicable','pending_review'].includes(item?.status)
        ? item.status
        : 'pending_review',
      validUntil:validDate(item?.validUntil, false)
    }))
    : [];
  const contact = raw.contact || {};
  const publicEmail = cleanString(contact.publicEmail, 254, false);
  const availabilityStatus = ['available','limited','unavailable'].includes(raw.availability?.status)
    ? raw.availability.status
    : 'unavailable';

  return {
    id:providerId,
    entityType,
    displayName:cleanString(raw.displayName, 140, false),
    professionalTitle:cleanString(raw.professionalTitle, 180, false) || null,
    centerType:cleanString(raw.centerType, 180, false) || null,
    roleInNetwork:cleanString(raw.roleInNetwork, 140, false) || null,
    shortBio:cleanString(raw.shortBio, 1000, false),
    specialties:stringArray(raw.specialties, {allowed:SPECIALTIES, maxItems:16}),
    services:stringArray(raw.services, {maxItems:30, maxLength:180}),
    ageGroups:stringArray(raw.ageGroups, {allowed:AGE_GROUPS, maxItems:6}),
    serviceModes:stringArray(raw.serviceModes, {allowed:SERVICE_MODES, maxItems:5}),
    languages:stringArray(raw.languages, {maxItems:12, maxLength:60}),
    serviceAreas:stringArray(raw.serviceAreas, {maxItems:30, maxLength:140}),
    location:{
      country:cleanString(raw.location?.country, 80, false),
      governorate:cleanString(raw.location?.governorate, 100, false) || null,
      city:cleanString(raw.location?.city, 100, false),
      area:cleanString(raw.location?.area, 140, false) || null,
      accessibility:stringArray(raw.location?.accessibility, {maxItems:20, maxLength:140})
    },
    qualifications,
    licenses,
    availability:{
      status:availabilityStatus,
      updatedAt:validDate(raw.availability?.updatedAt, false) || new Date().toISOString().slice(0, 10)
    },
    communication:{
      enabled:raw.communication?.enabled === true,
      acceptsNewRequests:raw.communication?.acceptsNewRequests === true,
      typicalResponse:cleanString(raw.communication?.typicalResponse, 100, false) || null
    },
    contact:{
      publicUrl:safeHttpUrl(contact.publicUrl),
      website:safeHttpUrl(contact.website),
      publicPhone:cleanString(contact.publicPhone, 40, false) || null,
      publicEmail:publicEmail ? validEmail(publicEmail) : null
    },
    profileUrl:safeHttpUrl(raw.profileUrl)
  };
}

function sanitizeProviderReview(raw) {
  const checklist = {
    identity:raw.checklist?.identity === true,
    qualification:raw.checklist?.qualification === true,
    professionalScope:raw.checklist?.professionalScope === true,
    contact:raw.checklist?.contact === true,
    consent:raw.checklist?.consent === true,
    legalAuthority:['verified','not_applicable'].includes(raw.checklist?.legalAuthority)
      ? raw.checklist.legalAuthority
      : 'pending'
  };
  return {
    checklist,
    evidenceSummary:{
      publicSources:nonNegativeInteger(raw.evidenceSummary?.publicSources || 0, 100),
      privateDocuments:nonNegativeInteger(raw.evidenceSummary?.privateDocuments || 0, 100),
      independentSources:nonNegativeInteger(raw.evidenceSummary?.independentSources || 0, 100)
    },
    privateNotes:cleanString(raw.privateNotes, 4000, false),
    publicNote:cleanString(raw.publicNote, 700, false),
    decision:['pending','changes_requested','approved','rejected','suspended'].includes(raw.decision)
      ? raw.decision
      : 'pending',
    nextReviewAt:validDate(raw.nextReviewAt, false),
    consentApproved:raw.consentApproved === true,
    consentApprovedAt:validDate(raw.consentApprovedAt, false)
  };
}

function assertPublishableProfile(profile, review) {
  const missing = [];
  if (!profile.displayName) missing.push('الاسم الظاهر');
  if (profile.entityType === 'professional' && !profile.professionalTitle) missing.push('المسمى المهني');
  if (profile.entityType === 'center' && !profile.centerType) missing.push('نوع المركز');
  if (profile.shortBio.length < 40) missing.push('نبذة مهنية لا تقل عن 40 حرفًا');
  if (!profile.specialties.length) missing.push('التخصصات');
  if (!profile.services.length) missing.push('الخدمات');
  if (!profile.ageGroups.length) missing.push('الفئات العمرية');
  if (!profile.serviceModes.length) missing.push('طريقة الخدمة');
  if (!profile.languages.length) missing.push('اللغات');
  if (!profile.location.country || !profile.location.city) missing.push('الدولة والمدينة');
  if (profile.entityType === 'professional' && !profile.qualifications.length) missing.push('المؤهل');
  if (!review.checklist.identity) missing.push('التحقق من الهوية');
  if (profile.entityType === 'professional' && !review.checklist.qualification) missing.push('التحقق من المؤهل');
  if (!review.checklist.professionalScope) missing.push('التحقق من نطاق الممارسة');
  if (!review.checklist.contact) missing.push('التحقق من بيانات التواصل');
  if (!review.checklist.consent || !review.consentApproved) missing.push('الموافقة الكتابية');
  if (!['verified','not_applicable'].includes(review.checklist.legalAuthority)) {
    missing.push('الترخيص أو التسجيل القانوني');
  } else if (review.checklist.legalAuthority === 'verified') {
    const currentLicense = profile.licenses.find(license =>
      license.status === 'active' &&
      license.authority &&
      (!license.validUntil || Date.parse(`${license.validUntil}T23:59:59Z`) >= Date.now())
    );
    if (!currentLicense) missing.push('ترخيص أو تسجيل ساري مع الجهة المنظمة');
  }
  const currentYear = new Date().getUTCFullYear();
  if (profile.qualifications.some(item => item.year && item.year > currentYear)) {
    missing.push('سنة مؤهل غير مستقبلية');
  }
  const evidenceCount = Object.values(review.evidenceSummary).reduce((sum, value) => sum + value, 0);
  if (evidenceCount < 1) missing.push('مرجع تحقق واحد على الأقل');
  if (!review.nextReviewAt) {
    missing.push('موعد المراجعة القادمة');
  } else {
    const next = Date.parse(`${review.nextReviewAt}T00:00:00Z`);
    const today = Date.now();
    const max = today + 730 * 24 * 60 * 60 * 1000;
    if (next <= today || next > max) missing.push('موعد مراجعة قادم خلال سنتين');
  }
  if (missing.length) {
    fail(`لا يمكن النشر قبل استكمال: ${missing.join('، ')}.`, 422, 'profile_not_publishable');
  }
}

function verifiedFieldsFromChecklist(checklist) {
  return [
    checklist.identity ? 'displayName' : '',
    checklist.qualification ? 'qualifications' : '',
    checklist.professionalScope ? 'specialties' : '',
    checklist.professionalScope ? 'services' : '',
    checklist.contact ? 'contact' : '',
    checklist.legalAuthority === 'verified' ? 'licenses' : ''
  ].filter(Boolean);
}

function publicVerificationSources(checklist, checkedAt) {
  const sources = [];
  if (checklist.identity) sources.push({type:'identity', reference:'private-verification-record', checkedAt});
  if (checklist.qualification) sources.push({type:'qualification', reference:'private-verification-record', checkedAt});
  if (checklist.legalAuthority === 'verified') {
    sources.push({type:'license', reference:'private-verification-record', checkedAt});
  }
  if (checklist.consent) sources.push({type:'written_consent', reference:'private-consent-record', checkedAt});
  return sources;
}

async function upsertProviderData(env, body, actor = {role:'system'}) {
  const providerId = validId(body.providerId, 'معرف المختص');
  const email = validEmail(body.email);
  const displayName = cleanString(body.displayName, 140, true);
  const status = PROVIDER_STATUSES.includes(body.status) ? body.status : 'active';
  const notifications = body.notificationEnabled === false ? 0 : 1;
  const accepts = body.acceptsNewRequests === false ? 0 : 1;

  await env.DB.prepare(`
    INSERT INTO providers_private (
      provider_id, email, display_name, status, notification_enabled,
      accepts_new_requests, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT(provider_id) DO UPDATE SET
      email=excluded.email,
      display_name=excluded.display_name,
      status=excluded.status,
      notification_enabled=excluded.notification_enabled,
      accepts_new_requests=excluded.accepts_new_requests,
      updated_at=CURRENT_TIMESTAMP
  `).bind(providerId, email, displayName, status, notifications, accepts).run();

  await audit(env, 'provider_private_upserted', providerId, {
    status,
    notificationEnabled:Boolean(notifications),
    acceptsNewRequests:Boolean(accepts),
    actorRole:actor.role
  });
  return providerId;
}

async function listAudit(url, env, cors) {
  const eventType = cleanString(url.searchParams.get('eventType'), 120, false);
  const limit = boundedInteger(url.searchParams.get('limit'), 50, 1, 200);
  const offset = boundedInteger(url.searchParams.get('offset'), 0, 0, 10_000);
  const where = eventType ? 'WHERE event_type = ?' : '';
  const statement = env.DB.prepare(`
    SELECT id, event_type, entity_id, metadata_json, created_at
    FROM audit_log ${where}
    ORDER BY created_at DESC LIMIT ? OFFSET ?
  `);
  const result = eventType ? await statement.bind(eventType, limit, offset).all() : await statement.bind(limit, offset).all();

  return json({
    items:(result.results || []).map(row => ({
      id:row.id,
      eventType:row.event_type,
      entityId:row.entity_id,
      metadata:safeJson(row.metadata_json, {}),
      createdAt:row.created_at
    })),
    limit,
    offset
  }, 200, cors);
}

async function audit(env, eventType, entityId, metadata) {
  if (!env.DB) return;
  try {
    await env.DB.prepare(`
      INSERT INTO audit_log (id, event_type, entity_id, metadata_json, created_at)
      VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    `).bind(crypto.randomUUID(), eventType, entityId, JSON.stringify(metadata || {})).run();
  } catch (error) {
    console.error('audit_error', error);
  }
}

function queueNotifications(ctx, env, notifications) {
  const jobs = notifications.filter(item => Array.isArray(item.to) && item.to.filter(Boolean).length)
    .map(item => deliverEmail(env, item));
  if (!jobs.length) return;
  ctx.waitUntil(Promise.allSettled(jobs).then(async results => {
    const failures = results.filter(result => result.status === 'rejected');
    if (failures.length) {
      await audit(env, 'notification_batch_failed', crypto.randomUUID(), {failures:failures.length});
    }
  }));
}

async function deliverEmail(env, item) {
  const recipients = item.to.filter(Boolean);
  const recipientHash = await sha256(recipients.join(',').toLowerCase());
  const eventId = crypto.randomUUID();

  if (!env.RESEND_API_KEY || !env.FROM_EMAIL) {
    await recordEmailEvent(env, {
      id:eventId,
      entityType:item.entityType,
      entityId:item.entityId,
      recipientHash,
      template:item.template,
      status:'skipped',
      providerMessageId:null,
      errorCode:'email_not_configured'
    });
    return {skipped:true};
  }

  let failureRecorded = false;
  try {
    const response = await fetch('https://api.resend.com/emails', {
      method:'POST',
      headers:{
        'authorization':`Bearer ${env.RESEND_API_KEY}`,
        'content-type':'application/json',
        'user-agent':'pterminology-specialists/3.0',
        'idempotency-key':cleanString(item.idempotencyKey || eventId, 256, true)
      },
      body:JSON.stringify({
        from:env.FROM_EMAIL,
        to:recipients,
        subject:item.subject,
        html:item.html,
        reply_to:env.OWNER_EMAIL || undefined
      }),
      signal:AbortSignal.timeout(12_000)
    });

    const detail = await response.json().catch(async () => ({message:await response.text()}));
    if (!response.ok) {
      const code = String(detail?.name || detail?.message || `http_${response.status}`).slice(0,180);
      await recordEmailEvent(env, {
        id:eventId,
        entityType:item.entityType,
        entityId:item.entityId,
        recipientHash,
        template:item.template,
        status:'failed',
        providerMessageId:null,
        errorCode:code
      });
      failureRecorded = true;
      throw new Error(`email_send_failed:${code}`);
    }

    await recordEmailEvent(env, {
      id:eventId,
      entityType:item.entityType,
      entityId:item.entityId,
      recipientHash,
      template:item.template,
      status:'sent',
      providerMessageId:detail.id || null,
      errorCode:null
    });
    return detail;
  } catch (error) {
    console.error('email_send_failed', error);
    const message = String(error?.message || 'email_transport_error').slice(0,180);
    if (!failureRecorded) await recordEmailEvent(env, {
      id:eventId,
      entityType:item.entityType,
      entityId:item.entityId,
      recipientHash,
      template:item.template,
      status:'failed',
      providerMessageId:null,
      errorCode:message
    });
    throw error;
  }
}

async function recordEmailEvent(env, event) {
  if (!env.DB) return;
  try {
    await env.DB.prepare(`
      INSERT INTO email_events (
        id, entity_type, entity_id, recipient_hash, template,
        status, provider_message_id, error_code, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    `).bind(
      event.id,
      event.entityType || 'unknown',
      event.entityId || 'unknown',
      event.recipientHash,
      event.template || 'unknown',
      event.status,
      event.providerMessageId,
      event.errorCode
    ).run();
  } catch (error) {
    console.error('email_event_error', error);
  }
}

function applicationSummary(referenceId, payload) {
  return `<p><strong>المرجع:</strong> ${escapeHtml(referenceId)}</p>
    <p><strong>الاسم:</strong> ${escapeHtml(payload.displayName)}</p>
    <p><strong>النوع:</strong> ${escapeHtml(payload.entityType)}</p>
    <p><strong>البريد الخاص:</strong> ${escapeHtml(payload.privateEmail)}</p>
    <p><strong>التخصصات:</strong> ${escapeHtml((payload.specialties || []).join('، '))}</p>
    <p><strong>الموقع:</strong> ${escapeHtml([
      payload.location?.city,
      payload.location?.country
    ].filter(Boolean).join('، '))}</p>
    <p>افتح لوحة الإدارة لمراجعة السجل الكامل بدل تداول الوثائق عبر البريد.</p>`;
}

function emailLayout(title, body) {
  return `<!doctype html><html lang="ar" dir="rtl"><body style="font-family:Arial,Tahoma,sans-serif;background:#f4f8f7;color:#12383d;padding:24px"><div style="max-width:680px;margin:auto;background:#fff;border:1px solid #c8e1de;border-radius:18px;padding:24px"><h1 style="font-size:24px;color:#075f5b">${escapeHtml(title)}</h1>${body}<hr style="border:0;border-top:1px solid #c8e1de"><p style="font-size:13px;color:#567176">منصة الصحة النفسية وذوي الاحتياجات الخاصة — قطاع المختصين والشراكات المهنية</p></div></body></html>`;
}

function safeJson(value, fallback) {
  try {
    return JSON.parse(String(value || ''));
  } catch (_error) {
    return fallback;
  }
}

function constantTimeEqual(a, b) {
  const left = String(a || '');
  const right = String(b || '');
  if (left.length !== right.length) return false;
  let diff = 0;
  for (let index = 0; index < left.length; index += 1) {
    diff |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return diff === 0;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;',
    '<':'&lt;',
    '>':'&gt;',
    '"':'&quot;',
    "'":'&#39;'
  }[char]));
}
