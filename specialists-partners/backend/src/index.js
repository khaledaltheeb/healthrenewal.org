const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
const MAX_BODY_BYTES = 96_000;
const MAX_MESSAGE_LENGTH = 3_000;

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(env.DB.batch([
      env.DB.prepare(`DELETE FROM conversation_tokens WHERE expires_at <= ?`).bind(new Date().toISOString()),
      env.DB.prepare(`DELETE FROM rate_limits WHERE bucket < date('now','-30 day')`)
    ]));
  },
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('origin') || '';
    const cors = corsHeaders(origin, env);

    if (request.method === 'OPTIONS') return new Response(null, {status:204, headers:cors});

    try {
      if (request.method === 'GET' && url.pathname === '/health') {
        return json({ok:true, service:'pterminology-specialists', time:new Date().toISOString()}, 200, cors);
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
      const messageMatch = url.pathname.match(/^\/v1\/conversations\/([a-z0-9-]+)\/messages$/i);
      if (messageMatch && request.method === 'POST') {
        return await createMessage(request, env, ctx, cors, messageMatch[1]);
      }
      if (url.pathname === '/v1/admin/providers' && request.method === 'POST') {
        return await upsertProvider(request, env, cors);
      }
      return json({error:'not_found', message:'المسار غير موجود.'}, 404, cors);
    } catch (error) {
      console.error('worker_error', error);
      const status = Number(error.status) || 500;
      return json({error:error.code || 'internal_error', message:status === 500 ? 'حدث خطأ داخلي.' : error.message}, status, cors);
    }
  }
};

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://healthrenewal.org')
    .split(',').map(value => value.trim()).filter(Boolean);
  const selected = allowed.includes(origin) ? origin : allowed[0] || '';
  return {
    'access-control-allow-origin': selected,
    'access-control-allow-methods': 'GET,POST,OPTIONS',
    'access-control-allow-headers': 'content-type,x-admin-key',
    'access-control-max-age': '86400',
    'vary': 'Origin',
    'x-content-type-options': 'nosniff',
    'referrer-policy': 'no-referrer',
    'cache-control': 'no-store'
  };
}

function json(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {status, headers:{...JSON_HEADERS, ...extraHeaders}});
}

function fail(message, status = 400, code = 'invalid_request') {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  throw error;
}

async function parseJson(request) {
  const contentType = request.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) fail('يجب إرسال البيانات بصيغة JSON.', 415, 'unsupported_media_type');
  const declared = Number(request.headers.get('content-length') || 0);
  if (declared > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.', 413, 'payload_too_large');
  const text = await request.text();
  if (new TextEncoder().encode(text).byteLength > MAX_BODY_BYTES) fail('حجم الطلب أكبر من الحد المسموح.', 413, 'payload_too_large');
  try { return JSON.parse(text); }
  catch (_) { fail('تعذر قراءة البيانات المرسلة.', 400, 'invalid_json'); }
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

function validId(value, name = 'المعرف') {
  const id = cleanString(value, 90, true);
  if (!/^[a-z0-9][a-z0-9-]{2,89}$/i.test(id)) fail(`${name} غير صالح.`, 400, 'invalid_id');
  return id;
}

async function verifyTurnstile(tokenValue, request, env) {
  if (!env.TURNSTILE_SECRET) return true;
  if (!tokenValue) fail('يلزم إكمال التحقق من الاستخدام البشري.', 400, 'turnstile_required');
  const form = new FormData();
  form.set('secret', env.TURNSTILE_SECRET);
  form.set('response', tokenValue);
  const ip = request.headers.get('CF-Connecting-IP');
  if (ip) form.set('remoteip', ip);
  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {method:'POST', body:form});
  const result = await response.json();
  if (!result.success) fail('فشل التحقق من الاستخدام البشري.', 400, 'turnstile_failed');
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
  if (!env.DB) return;
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const key = await sha256(`${env.RATE_LIMIT_SALT || 'change-me'}:${ip}:${action}`);
  const bucket = new Date().toISOString().slice(0,10);
  await env.DB.prepare(`
    INSERT INTO rate_limits (key, bucket, count, updated_at) VALUES (?, ?, 1, CURRENT_TIMESTAMP)
    ON CONFLICT(key, bucket) DO UPDATE SET count = count + 1, updated_at = CURRENT_TIMESTAMP
  `).bind(key, bucket).run();
  const row = await env.DB.prepare('SELECT count FROM rate_limits WHERE key = ? AND bucket = ?').bind(key, bucket).first();
  if (Number(row?.count || 0) > limit) fail('تم تجاوز عدد المحاولات المسموح لهذا اليوم.', 429, 'rate_limited');
}

async function createApplication(request, env, ctx, cors) {
  await rateLimit(request, env, 'application', 8);
  const body = await parseJson(request);
  await verifyTurnstile(body.turnstileToken, request, env);

  const id = validId(body.submissionId || crypto.randomUUID(), 'معرف الطلب');
  const referenceId = reference('APP');
  const email = validEmail(body.privateEmail);
  const displayName = cleanString(body.displayName, 140, true);
  const entityType = ['professional','center'].includes(body.entityType) ? body.entityType : fail('نوع الملف غير صالح.', 400, 'invalid_entity_type');
  if (!body.consent?.dataReview || !body.consent?.publication || !body.consent?.internalMessaging) fail('الموافقات المطلوبة غير مكتملة.', 400, 'consent_required');
  if (!Array.isArray(body.specialties) || body.specialties.length === 0) fail('يلزم اختيار تخصص واحد على الأقل.', 400, 'specialty_required');

  const stored = {...body};
  delete stored.turnstileToken;
  await env.DB.prepare(`
    INSERT INTO applications (id, reference_id, email, display_name, entity_type, payload_json, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
  `).bind(id, referenceId, email, displayName, entityType, JSON.stringify(stored)).run();
  await audit(env, 'application_created', id, {referenceId, entityType});

  ctx.waitUntil(Promise.allSettled([
    sendOwnerApplicationEmail(env, referenceId, stored),
    sendEmail(env, {
      to:[email], subject:`تم استلام طلب الانضمام ${referenceId}`,
      html:emailLayout('تم استلام طلب الانضمام', `<p>تم استلام طلبك وإحالته إلى إدارة المنصة للمراجعة.</p><p><strong>رقم المتابعة:</strong> ${escapeHtml(referenceId)}</p><p>لا يبدأ نشر الملف أو تفعيل المحادثات قبل المراجعة والموافقة النهائية.</p>`)
    })
  ]));

  return json({ok:true, referenceId}, 201, cors);
}

async function createConversation(request, env, ctx, cors) {
  await rateLimit(request, env, 'conversation', 12);
  const body = await parseJson(request);
  await verifyTurnstile(body.turnstileToken, request, env);

  const providerId = validId(body.providerId, 'معرف المختص');
  const provider = await env.DB.prepare(`SELECT provider_id, display_name, email, status, notification_enabled FROM providers_private WHERE provider_id = ?`).bind(providerId).first();
  if (!provider || provider.status !== 'active') fail('التواصل الداخلي غير متاح لهذا المختص.', 404, 'provider_unavailable');

  const visitorName = cleanString(body.sender?.displayName, 100, true);
  const visitorEmail = validEmail(body.sender?.email);
  const message = cleanString(body.message, 2000, true);
  if (message.length < 20) fail('الرسالة قصيرة جدًا.', 400, 'message_too_short');
  if (!body.consent?.privacy || !body.consent?.contact) fail('الموافقات المطلوبة غير مكتملة.', 400, 'consent_required');

  const id = validId(body.requestId || `conversation-${crypto.randomUUID()}`, 'معرف المحادثة');
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
        status, topic, urgency, context_json, created_at, updated_at, last_message_at
      ) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?)
    `).bind(id, referenceId, providerId, visitorName, visitorEmail, topic, urgency, JSON.stringify(body.context || {}), now, now, now),
    env.DB.prepare(`INSERT INTO conversation_tokens (id, conversation_id, role, token_hash, expires_at, created_at) VALUES (?, ?, 'visitor', ?, ?, ?)`)
      .bind(crypto.randomUUID(), id, visitorHash, tokenExpiry, now),
    env.DB.prepare(`INSERT INTO conversation_tokens (id, conversation_id, role, token_hash, expires_at, created_at) VALUES (?, ?, 'specialist', ?, ?, ?)`)
      .bind(crypto.randomUUID(), id, specialistHash, tokenExpiry, now),
    env.DB.prepare(`INSERT INTO messages (id, conversation_id, sender_role, body, created_at) VALUES (?, ?, 'visitor', ?, ?)`)
      .bind(crypto.randomUUID(), id, message, now)
  ]);
  await audit(env, 'conversation_created', id, {referenceId, providerId, topic, urgency});

  const portalBase = String(env.PORTAL_BASE_URL || 'https://healthrenewal.org/specialists-partners/portal/');
  const specialistLink = `${portalBase}?conversation=${encodeURIComponent(id)}&token=${encodeURIComponent(specialistAccess)}&role=specialist`;
  const visitorLink = `${portalBase}?conversation=${encodeURIComponent(id)}&token=${encodeURIComponent(visitorAccess)}&role=visitor`;

  const jobs = [
    sendEmail(env, {
      to:[provider.email], subject:`رسالة جديدة في منصة المختصين — ${referenceId}`,
      html:emailLayout('وصلتك رسالة جديدة', `<p>وصل طلب تواصل جديد عبر المنصة.</p><p><strong>الموضوع:</strong> ${escapeHtml(topic)}</p><p><strong>الأولوية:</strong> ${escapeHtml(urgency)}</p><p><a href="${escapeHtml(specialistLink)}">فتح المحادثة والرد داخل المنصة</a></p><p>لا ترد على هذا البريد بمعلومات حساسة.</p>`)
    }),
    sendEmail(env, {
      to:[visitorEmail], subject:`تم إنشاء المحادثة — ${referenceId}`,
      html:emailLayout('تم إنشاء محادثتك', `<p>تم إرسال إشعار إلى ${escapeHtml(provider.display_name)}.</p><p><strong>رقم المتابعة:</strong> ${escapeHtml(referenceId)}</p><p><a href="${escapeHtml(visitorLink)}">فتح المحادثة الخاصة</a></p><p>احتفظ بالرابط ولا تشاركه مع الآخرين.</p>`)
    })
  ];
  if (env.OWNER_EMAIL) jobs.push(sendEmail(env, {
    to:[env.OWNER_EMAIL], subject:`محادثة جديدة ${referenceId}`,
    html:emailLayout('محادثة جديدة في القطاع', `<p>تم فتح محادثة مع الملف: <strong>${escapeHtml(provider.display_name)}</strong>.</p><p>المرجع: ${escapeHtml(referenceId)}</p><p>الموضوع: ${escapeHtml(topic)}</p>`)
  }));
  ctx.waitUntil(Promise.allSettled(jobs));

  return json({ok:true, conversationId:id, referenceId, accessToken:visitorAccess}, 201, cors);
}

async function getConversation(request, env, cors, conversationId) {
  const url = new URL(request.url);
  const accessToken = cleanString(url.searchParams.get('token'), 200, true);
  const role = url.searchParams.get('role') === 'specialist' ? 'specialist' : 'visitor';
  const conversation = await authorizedConversation(env, conversationId, accessToken, role);
  const messages = await env.DB.prepare(`SELECT id, sender_role, body, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC`).bind(conversationId).all();
  return json({
    conversation:{id:conversation.id, referenceId:conversation.reference_id, status:conversation.status, topic:conversation.topic, urgency:conversation.urgency, createdAt:conversation.created_at, updatedAt:conversation.updated_at},
    provider:{id:conversation.provider_id, displayName:conversation.provider_display_name},
    messages:(messages.results || []).map(row => ({id:row.id, senderRole:row.sender_role, body:row.body, createdAt:row.created_at}))
  }, 200, cors);
}

async function createMessage(request, env, ctx, cors, conversationId) {
  await rateLimit(request, env, 'message', 60);
  const body = await parseJson(request);
  const role = body.role === 'specialist' ? 'specialist' : 'visitor';
  const accessToken = cleanString(body.token, 200, true);
  const message = cleanString(body.body, MAX_MESSAGE_LENGTH, true);
  const conversation = await authorizedConversation(env, conversationId, accessToken, role);
  if (conversation.status !== 'open') fail('المحادثة مغلقة.', 409, 'conversation_closed');

  const now = new Date().toISOString();
  await env.DB.batch([
    env.DB.prepare(`INSERT INTO messages (id, conversation_id, sender_role, body, created_at) VALUES (?, ?, ?, ?, ?)`)
      .bind(crypto.randomUUID(), conversationId, role, message, now),
    env.DB.prepare(`UPDATE conversations SET updated_at = ?, last_message_at = ? WHERE id = ?`).bind(now, now, conversationId)
  ]);
  await audit(env, 'message_created', conversationId, {senderRole:role});

  const portalBase = String(env.PORTAL_BASE_URL || 'https://healthrenewal.org/specialists-partners/portal/');
  if (role === 'visitor') {
    const specialistToken = token();
    const specialistHash = await sha256(specialistToken);
    const expiresAt = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();
    await env.DB.prepare(`INSERT INTO conversation_tokens (id, conversation_id, role, token_hash, expires_at, created_at) VALUES (?, ?, 'specialist', ?, ?, ?)`)
      .bind(crypto.randomUUID(), conversationId, specialistHash, expiresAt, now).run();
    const link = `${portalBase}?conversation=${encodeURIComponent(conversationId)}&token=${encodeURIComponent(specialistToken)}&role=specialist`;
    ctx.waitUntil(sendEmail(env, {to:[conversation.provider_email], subject:`رد جديد — ${conversation.reference_id}`, html:emailLayout('رسالة جديدة في المحادثة', `<p>وصلت رسالة جديدة في المحادثة ${escapeHtml(conversation.reference_id)}.</p><p><a href="${escapeHtml(link)}">فتح المحادثة</a></p>`)}));
  } else {
    const visitorToken = token();
    const visitorHash = await sha256(visitorToken);
    const expiresAt = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();
    await env.DB.prepare(`INSERT INTO conversation_tokens (id, conversation_id, role, token_hash, expires_at, created_at) VALUES (?, ?, 'visitor', ?, ?, ?)`)
      .bind(crypto.randomUUID(), conversationId, visitorHash, expiresAt, now).run();
    const link = `${portalBase}?conversation=${encodeURIComponent(conversationId)}&token=${encodeURIComponent(visitorToken)}&role=visitor`;
    ctx.waitUntil(sendEmail(env, {to:[conversation.visitor_email], subject:`رد من المختص — ${conversation.reference_id}`, html:emailLayout('وصل رد جديد', `<p>وصل رد جديد في المحادثة ${escapeHtml(conversation.reference_id)}.</p><p><a href="${escapeHtml(link)}">فتح المحادثة</a></p>`)}));
  }

  return json({ok:true, createdAt:now}, 201, cors);
}

async function authorizedConversation(env, conversationId, accessToken, role) {
  const id = validId(conversationId, 'معرف المحادثة');
  const accessHash = await sha256(accessToken);
  const row = await env.DB.prepare(`
    SELECT c.*, p.display_name AS provider_display_name, p.email AS provider_email
    FROM conversations c JOIN providers_private p ON p.provider_id = c.provider_id
    WHERE c.id = ?
  `).bind(id).first();
  if (!row) fail('المحادثة غير موجودة.', 404, 'conversation_not_found');
  const tokenRow = await env.DB.prepare(`
    SELECT token_hash, expires_at FROM conversation_tokens
    WHERE conversation_id = ? AND role = ? AND token_hash = ? AND expires_at > ?
    ORDER BY created_at DESC LIMIT 1
  `).bind(id, role, accessHash, new Date().toISOString()).first();
  if (!tokenRow || !constantTimeEqual(accessHash, tokenRow.token_hash)) fail('رابط المحادثة غير صالح أو انتهت صلاحيته.', 403, 'invalid_access_token');
  return row;
}

function constantTimeEqual(a, b) {
  const left = String(a || '');
  const right = String(b || '');
  if (left.length !== right.length) return false;
  let diff = 0;
  for (let i = 0; i < left.length; i++) diff |= left.charCodeAt(i) ^ right.charCodeAt(i);
  return diff === 0;
}

async function upsertProvider(request, env, cors) {
  const adminKey = request.headers.get('x-admin-key') || '';
  if (!env.ADMIN_API_KEY || !constantTimeEqual(adminKey, env.ADMIN_API_KEY)) fail('غير مصرح.', 401, 'unauthorized');
  const body = await parseJson(request);
  const providerId = validId(body.providerId, 'معرف المختص');
  const email = validEmail(body.email);
  const displayName = cleanString(body.displayName, 140, true);
  const status = ['active','suspended','archived'].includes(body.status) ? body.status : 'active';
  const notifications = body.notificationEnabled === false ? 0 : 1;
  await env.DB.prepare(`
    INSERT INTO providers_private (provider_id, email, display_name, status, notification_enabled, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    ON CONFLICT(provider_id) DO UPDATE SET email=excluded.email, display_name=excluded.display_name, status=excluded.status, notification_enabled=excluded.notification_enabled, updated_at=CURRENT_TIMESTAMP
  `).bind(providerId, email, displayName, status, notifications).run();
  await audit(env, 'provider_private_upserted', providerId, {status, notificationEnabled:Boolean(notifications)});
  return json({ok:true, providerId}, 200, cors);
}

async function audit(env, eventType, entityId, metadata) {
  if (!env.DB) return;
  try {
    await env.DB.prepare(`INSERT INTO audit_log (id, event_type, entity_id, metadata_json, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`)
      .bind(crypto.randomUUID(), eventType, entityId, JSON.stringify(metadata || {})).run();
  } catch (error) { console.error('audit_error', error); }
}

async function sendOwnerApplicationEmail(env, referenceId, payload) {
  if (!env.OWNER_EMAIL) return;
  const summary = `<p><strong>الاسم:</strong> ${escapeHtml(payload.displayName)}</p>
    <p><strong>النوع:</strong> ${escapeHtml(payload.entityType)}</p>
    <p><strong>البريد الخاص:</strong> ${escapeHtml(payload.privateEmail)}</p>
    <p><strong>التخصصات:</strong> ${escapeHtml((payload.specialties || []).join('، '))}</p>
    <p><strong>الموقع:</strong> ${escapeHtml([payload.location?.city,payload.location?.country].filter(Boolean).join('، '))}</p>
    <details><summary>السجل الكامل</summary><pre style="white-space:pre-wrap">${escapeHtml(JSON.stringify(payload, null, 2))}</pre></details>`;
  return sendEmail(env, {to:[env.OWNER_EMAIL], subject:`طلب انضمام جديد — ${referenceId}`, html:emailLayout('طلب انضمام جديد', summary)});
}

async function sendEmail(env, {to, subject, html}) {
  if (!env.RESEND_API_KEY || !env.FROM_EMAIL || !Array.isArray(to) || to.length === 0) return {skipped:true};
  const response = await fetch('https://api.resend.com/emails', {
    method:'POST',
    headers:{'authorization':`Bearer ${env.RESEND_API_KEY}`,'content-type':'application/json'},
    body:JSON.stringify({from:env.FROM_EMAIL,to,subject,html,reply_to:env.OWNER_EMAIL || undefined})
  });
  if (!response.ok) {
    const detail = await response.text();
    console.error('email_send_failed', response.status, detail);
    throw new Error('email_send_failed');
  }
  return response.json();
}

function emailLayout(title, body) {
  return `<!doctype html><html lang="ar" dir="rtl"><body style="font-family:Arial,Tahoma,sans-serif;background:#f4f8f7;color:#12383d;padding:24px"><div style="max-width:680px;margin:auto;background:#fff;border:1px solid #c8e1de;border-radius:18px;padding:24px"><h1 style="font-size:24px;color:#075f5b">${escapeHtml(title)}</h1>${body}<hr style="border:0;border-top:1px solid #c8e1de"><p style="font-size:13px;color:#567176">منصة الصحة النفسية وذوي الاحتياجات الخاصة — قطاع المختصين والشراكات المهنية</p></div></body></html>`;
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
