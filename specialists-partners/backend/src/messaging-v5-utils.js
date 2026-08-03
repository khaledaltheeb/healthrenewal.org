export const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
export const MAX_BODY_BYTES = 96_000;
export const MAX_MESSAGE_LENGTH = 3_000;

export function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://healthrenewal.org')
    .split(',').map(value => value.trim()).filter(Boolean);
  const selected = origin ? (allowed.includes(origin) ? origin : '') : (allowed[0] || '');
  const headers = {
    'access-control-allow-methods':'GET,POST,PATCH,OPTIONS',
    'access-control-allow-headers':'content-type,x-admin-key,authorization,x-conversation-role,idempotency-key,x-requested-with',
    'access-control-max-age':'86400',
    vary:'Origin',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY',
    'referrer-policy':'no-referrer',
    'cache-control':'no-store'
  };
  if (selected) headers['access-control-allow-origin'] = selected;
  return headers;
}

export function json(payload, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {status, headers:{...JSON_HEADERS, ...extraHeaders}});
}

export function fail(message, status = 400, code = 'invalid_request') {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  throw error;
}

export async function parseJson(request) {
  const contentType = request.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) fail('يجب إرسال البيانات بصيغة JSON.', 415, 'unsupported_media_type');
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

export function cleanString(value, max = 200, required = false) {
  const text = String(value ?? '').trim();
  if (required && !text) fail('أحد الحقول المطلوبة فارغ.', 400, 'missing_field');
  if (text.length > max) fail('أحد الحقول تجاوز الحد المسموح.', 400, 'field_too_long');
  return text;
}

export function validId(value, name = 'المعرف') {
  const id = cleanString(value, 90, true);
  if (!/^[a-z0-9][a-z0-9-]{2,89}$/i.test(id)) fail(`${name} غير صالح.`, 400, 'invalid_id');
  return id;
}

export function validIdempotencyKey(value) {
  const key = cleanString(value, 120, true);
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{11,119}$/.test(key)) {
    fail('معرف منع تكرار الرسالة غير صالح.', 400, 'invalid_idempotency_key');
  }
  return key;
}

export function conversationAccess(request, url, body = {}) {
  if (url.searchParams.has('token') || url.searchParams.has('role') ||
      Object.prototype.hasOwnProperty.call(body, 'token') ||
      Object.prototype.hasOwnProperty.call(body, 'role')) {
    fail('يجب إرسال بيانات دخول المحادثة في الترويسات الآمنة فقط.', 400, 'conversation_credentials_in_url_or_body');
  }
  const header = request.headers.get('authorization') || '';
  const tokenMatch = header.match(/^Bearer\s+([A-Za-z0-9_-]{32,200})$/i);
  if (!tokenMatch) fail('بيانات دخول المحادثة غير مكتملة.', 401, 'conversation_token_required');
  const role = cleanString(request.headers.get('x-conversation-role'), 20, true);
  if (!['visitor','specialist'].includes(role)) fail('دور المحادثة غير صالح.', 400, 'invalid_conversation_role');
  return {accessToken:tokenMatch[1], role};
}

export async function rateLimit(request, env, action, limit) {
  if (!env.DB) fail('قاعدة البيانات غير متاحة.', 503, 'database_unavailable');
  const ip = request.headers.get('CF-Connecting-IP') || request.headers.get('x-forwarded-for') || 'unknown';
  const key = await sha256(`${env.RATE_LIMIT_SALT || 'missing-salt'}:${ip}:${action}`);
  const bucket = new Date().toISOString().slice(0,13);
  await env.DB.prepare(`
    INSERT INTO rate_limits (key, bucket, count, updated_at)
    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
    ON CONFLICT(key, bucket) DO UPDATE SET count=count+1, updated_at=CURRENT_TIMESTAMP
  `).bind(key, bucket).run();
  const row = await env.DB.prepare('SELECT count FROM rate_limits WHERE key=? AND bucket=?')
    .bind(key, bucket).first();
  if (Number(row?.count || 0) > limit) fail('تم تجاوز عدد المحاولات المسموح خلال هذه الساعة.', 429, 'rate_limited');
}

export async function issueConversationToken(env, conversationId, role, now = new Date().toISOString()) {
  const accessToken = randomToken();
  const tokenHash = await sha256(accessToken);
  const expiresAt = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString();
  await env.DB.prepare(`
    INSERT INTO conversation_tokens (id, conversation_id, role, token_hash, expires_at, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `).bind(crypto.randomUUID(), conversationId, role, tokenHash, expiresAt, now).run();
  return accessToken;
}

export function portalLink(base, conversationId, accessToken, role) {
  const portalBase = String(base).replace(/\/?$/, '/');
  return `${portalBase}#conversation=${encodeURIComponent(conversationId)}&token=${encodeURIComponent(accessToken)}&role=${encodeURIComponent(role)}`;
}

function randomToken() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

export async function sha256(value) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(value)));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
}

export function constantTimeEqual(a, b) {
  const left = String(a || '');
  const right = String(b || '');
  if (left.length !== right.length) return false;
  let diff = 0;
  for (let index = 0; index < left.length; index += 1) diff |= left.charCodeAt(index) ^ right.charCodeAt(index);
  return diff === 0;
}

export async function audit(env, eventType, entityId, metadata) {
  try {
    await env.DB.prepare(`
      INSERT INTO audit_log (id, event_type, entity_id, metadata_json, created_at)
      VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    `).bind(crypto.randomUUID(), eventType, entityId, JSON.stringify(metadata || {})).run();
  } catch (error) {
    console.error('audit_v5_error', error);
  }
}

export function emailLayout(title, body) {
  return `<!doctype html><html lang="ar" dir="rtl"><body style="font-family:Arial,Tahoma,sans-serif;background:#f4f8f7;color:#12383d;padding:24px"><div style="max-width:680px;margin:auto;background:#fff;border:1px solid #c8e1de;border-radius:18px;padding:24px"><h1 style="font-size:24px;color:#075f5b">${escapeHtml(title)}</h1>${body}<hr style="border:0;border-top:1px solid #c8e1de"><p style="font-size:13px;color:#567176">منصة روافد — قطاع المختصين والشراكات المهنية</p></div></body></html>`;
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[char]));
}
