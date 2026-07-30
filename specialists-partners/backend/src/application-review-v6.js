import {audit, cleanString, constantTimeEqual, emailLayout, escapeHtml, fail, json, sha256} from './messaging-v5-utils.js';

const REVIEW_PATH = '/v1/reviews/applications';
const SESSION_COOKIE = 'pterm_review_session';
const CSRF_COOKIE = 'pterm_review_csrf';
const DEFAULT_TTL_MINUTES = 30;
const COOKIE_PATH = REVIEW_PATH;

export async function issueApplicationReviewInvitation(request, env, ctx, applicationId, referenceId, applicationBody) {
  assertReviewConfiguration(env);
  const ttlMinutes = boundedInteger(env.REVIEW_LINK_TTL_MINUTES, DEFAULT_TTL_MINUTES, 10, 120);
  const expiresAt = new Date(Date.now() + ttlMinutes * 60_000).toISOString();
  const invitationId = crypto.randomUUID();
  const payload = {v:1, invitationId, applicationId, exp:Math.floor(new Date(expiresAt).getTime() / 1000)};
  const signedToken = await signPayload(payload, env.REVIEW_LINK_SECRET);
  const tokenHash = await sha256(signedToken);

  await env.DB.batch([
    env.DB.prepare(`
      UPDATE application_review_invitations
      SET revoked_at = CURRENT_TIMESTAMP
      WHERE application_id = ? AND used_at IS NULL AND revoked_at IS NULL
    `).bind(applicationId),
    env.DB.prepare(`
      INSERT INTO application_review_invitations (
        id, application_id, reference_id, token_hash, expires_at, created_at
      ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    `).bind(invitationId, applicationId, referenceId, tokenHash, expiresAt)
  ]);

  await audit(env, 'application_review_invitation_created', applicationId, {
    invitationId,
    referenceId,
    expiresAt,
    actor:'system-after-application'
  });

  const reviewBase = reviewBaseUrl(request, env);
  const reviewUrl = `${reviewBase}?token=${encodeURIComponent(signedToken)}`;
  const summary = safeApplicationSummary(applicationBody);
  ctx.waitUntil(sendOwnerReviewEmail(env, {
    applicationId,
    referenceId,
    reviewUrl,
    expiresAt,
    summary
  }));
}

export async function handleApplicationReview(request, env) {
  assertReviewConfiguration(env);
  if (request.method === 'GET') return handleReviewGet(request, env);
  if (request.method === 'POST') return handleReviewPost(request, env);
  return new Response('Method Not Allowed', {status:405, headers:securityHeaders({'allow':'GET, POST'})});
}

export async function signedReviewHealth(env) {
  let schema = false;
  try {
    const result = await env.DB.prepare(`
      SELECT COUNT(*) AS count FROM pragma_table_info('application_review_invitations')
      WHERE name IN ('token_hash','review_session_hash','csrf_hash','used_at','revoked_at','decision','decided_by')
    `).first();
    schema = Number(result?.count || 0) === 7;
  } catch (error) {
    console.error('signed_review_health_error', error);
  }
  return {
    signedReviews:Boolean(env.REVIEW_LINK_SECRET && String(env.REVIEW_LINK_SECRET).length >= 32),
    signedReviewSchema:schema,
    signedReviewEmail:Boolean(env.RESEND_API_KEY && env.FROM_EMAIL && env.OWNER_EMAIL)
  };
}

async function handleReviewGet(request, env) {
  const url = new URL(request.url);
  const tokenValue = url.searchParams.get('token');
  if (tokenValue) {
    const invitation = await verifySignedInvitation(tokenValue, env);
    const sessionToken = randomToken();
    const csrfToken = randomToken();
    const sessionHash = await sha256(sessionToken);
    const csrfHash = await sha256(csrfToken);
    const now = new Date().toISOString();

    const updated = await env.DB.prepare(`
      UPDATE application_review_invitations
      SET review_session_hash = ?, csrf_hash = ?, opened_at = COALESCE(opened_at, ?)
      WHERE id = ? AND token_hash = ? AND used_at IS NULL AND revoked_at IS NULL AND expires_at > ?
    `).bind(sessionHash, csrfHash, now, invitation.id, invitation.tokenHash, now).run();
    if (Number(updated?.meta?.changes || 0) !== 1) {
      return reviewMessage('الرابط غير صالح', 'انتهت صلاحية رابط المراجعة أو استُخدم أو أُلغي.', 410);
    }

    await audit(env, 'application_review_link_opened', invitation.applicationId, {
      invitationId:invitation.id,
      effect:'view_only'
    });

    const cleanUrl = new URL(request.url);
    cleanUrl.search = '';
    const headers = securityHeaders({location:cleanUrl.toString()});
    appendCookie(headers, SESSION_COOKIE, sessionToken, true);
    appendCookie(headers, CSRF_COOKIE, csrfToken, false);
    return new Response(null, {status:303, headers});
  }

  const sessionToken = cookieValue(request, SESSION_COOKIE);
  if (!sessionToken) return reviewMessage('جلسة المراجعة غير موجودة', 'افتح رابط المراجعة الأصلي من رسالة البريد.', 401);
  const sessionHash = await sha256(sessionToken);
  const row = await loadReviewBySession(env, sessionHash);
  if (!row) return reviewMessage('جلسة المراجعة منتهية', 'انتهت الجلسة أو استُخدم الرابط أو أُلغي.', 410);

  const csrfToken = cookieValue(request, CSRF_COOKIE);
  if (!csrfToken || !constantTimeEqual(await sha256(csrfToken), row.csrf_hash)) {
    return reviewMessage('تعذر التحقق من الجلسة', 'أعد فتح رابط المراجعة الأصلي من البريد.', 403);
  }
  return renderReviewPage(row, csrfToken);
}

async function handleReviewPost(request, env) {
  enforceSameOrigin(request);
  const contentType = request.headers.get('content-type') || '';
  if (!contentType.includes('application/x-www-form-urlencoded')) {
    fail('صيغة القرار غير مدعومة.', 415, 'unsupported_review_media_type');
  }
  const form = await request.formData();
  const decision = cleanString(form.get('decision'), 20, true);
  if (!['approved','rejected'].includes(decision)) fail('قرار المراجعة غير صالح.', 400, 'invalid_review_decision');
  if (form.get('confirm') !== '1') fail('يلزم تأكيد القرار صراحةً.', 400, 'review_confirmation_required');
  const reason = cleanString(form.get('reason'), 800, decision === 'rejected');
  const csrfBody = cleanString(form.get('csrf'), 200, true);
  const csrfCookie = cookieValue(request, CSRF_COOKIE);
  if (!csrfCookie || !constantTimeEqual(csrfBody, csrfCookie)) fail('فشل تحقق CSRF.', 403, 'csrf_mismatch');

  const sessionToken = cookieValue(request, SESSION_COOKIE);
  if (!sessionToken) fail('جلسة المراجعة غير موجودة.', 401, 'review_session_required');
  const sessionHash = await sha256(sessionToken);
  const csrfHash = await sha256(csrfBody);
  const row = await loadReviewBySession(env, sessionHash);
  if (!row || !constantTimeEqual(csrfHash, row.csrf_hash)) fail('جلسة المراجعة غير صالحة أو منتهية.', 410, 'review_session_expired');

  const now = new Date().toISOString();
  const actor = 'owner-signed-review-link';
  const results = await env.DB.batch([
    env.DB.prepare(`
      UPDATE application_review_invitations
      SET used_at = ?, decision = ?, decided_by = ?, decision_reason = ?,
          review_session_hash = NULL, csrf_hash = NULL
      WHERE id = ? AND review_session_hash = ? AND csrf_hash = ?
        AND used_at IS NULL AND revoked_at IS NULL AND expires_at > ?
    `).bind(now, decision, actor, reason, row.invitation_id, sessionHash, csrfHash, now),
    env.DB.prepare(`
      UPDATE applications
      SET status = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ? AND EXISTS (
        SELECT 1 FROM application_review_invitations
        WHERE id = ? AND used_at = ? AND decision = ? AND decided_by = ?
      )
    `).bind(decision, row.application_id, row.invitation_id, now, decision, actor),
    env.DB.prepare(`
      INSERT INTO audit_log (id, event_type, entity_id, metadata_json, created_at)
      SELECT ?, 'application_review_decided', ?, ?, CURRENT_TIMESTAMP
      WHERE EXISTS (
        SELECT 1 FROM application_review_invitations
        WHERE id = ? AND used_at = ? AND decision = ? AND decided_by = ?
      )
    `).bind(crypto.randomUUID(), row.application_id, JSON.stringify({
      invitationId:row.invitation_id,
      referenceId:row.reference_id,
      decision,
      actor,
      reasonProvided:Boolean(reason)
    }), row.invitation_id, now, decision, actor)
  ]);

  if (Number(results?.[0]?.meta?.changes || 0) !== 1 || Number(results?.[1]?.meta?.changes || 0) !== 1) {
    fail('استُخدم رابط المراجعة أو أُلغي قبل تنفيذ القرار.', 409, 'review_token_already_used');
  }

  const headers = securityHeaders();
  clearCookie(headers, SESSION_COOKIE, true);
  clearCookie(headers, CSRF_COOKIE, false);
  return new Response(renderResultPage(decision, row.reference_id), {status:200, headers});
}

async function verifySignedInvitation(tokenValue, env) {
  const token = cleanString(tokenValue, 1200, true);
  const parts = token.split('.');
  if (parts.length !== 2) fail('رابط المراجعة غير صالح.', 400, 'invalid_signed_review_token');
  const expected = await hmac(parts[0], env.REVIEW_LINK_SECRET);
  if (!constantTimeEqual(expected, parts[1])) fail('توقيع رابط المراجعة غير صالح.', 403, 'invalid_review_signature');
  let payload;
  try {
    payload = JSON.parse(decodeBase64Url(parts[0]));
  } catch (_error) {
    fail('محتوى رابط المراجعة غير صالح.', 400, 'invalid_review_payload');
  }
  if (payload?.v !== 1 || !payload.invitationId || !payload.applicationId || !Number.isInteger(payload.exp)) {
    fail('محتوى رابط المراجعة غير مكتمل.', 400, 'invalid_review_payload');
  }
  if (payload.exp <= Math.floor(Date.now() / 1000)) fail('انتهت صلاحية رابط المراجعة.', 410, 'review_token_expired');
  const tokenHash = await sha256(token);
  const row = await env.DB.prepare(`
    SELECT id, application_id, expires_at FROM application_review_invitations
    WHERE id = ? AND application_id = ? AND token_hash = ?
      AND used_at IS NULL AND revoked_at IS NULL AND expires_at > ?
    LIMIT 1
  `).bind(payload.invitationId, payload.applicationId, tokenHash, new Date().toISOString()).first();
  if (!row) fail('رابط المراجعة غير صالح أو مستخدم.', 410, 'review_token_inactive');
  return {id:row.id, applicationId:row.application_id, tokenHash};
}

async function loadReviewBySession(env, sessionHash) {
  return env.DB.prepare(`
    SELECT r.id AS invitation_id, r.application_id, r.reference_id, r.csrf_hash,
           r.expires_at, a.display_name, a.entity_type, a.status, a.payload_json
    FROM application_review_invitations r
    JOIN applications a ON a.id = r.application_id
    WHERE r.review_session_hash = ? AND r.used_at IS NULL AND r.revoked_at IS NULL
      AND r.expires_at > ?
    LIMIT 1
  `).bind(sessionHash, new Date().toISOString()).first();
}

async function signPayload(payload, secret) {
  const encoded = encodeBase64Url(JSON.stringify(payload));
  return `${encoded}.${await hmac(encoded, secret)}`;
}

async function hmac(value, secret) {
  const key = await crypto.subtle.importKey(
    'raw', new TextEncoder().encode(String(secret)),
    {name:'HMAC', hash:'SHA-256'}, false, ['sign']
  );
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(String(value)));
  return encodeBase64Url(new Uint8Array(signature));
}

function encodeBase64Url(value) {
  const bytes = value instanceof Uint8Array ? value : new TextEncoder().encode(String(value));
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

function decodeBase64Url(value) {
  const normalized = String(value).replace(/-/g, '+').replace(/_/g, '/');
  const padded = normalized + '='.repeat((4 - normalized.length % 4) % 4);
  const binary = atob(padded);
  return new TextDecoder().decode(Uint8Array.from(binary, character => character.charCodeAt(0)));
}

function randomToken() {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return encodeBase64Url(bytes);
}

function reviewBaseUrl(request, env) {
  if (env.REVIEW_BASE_URL) {
    const configured = new URL(String(env.REVIEW_BASE_URL));
    if (configured.protocol !== 'https:') fail('رابط المراجعة يجب أن يستخدم HTTPS.', 500, 'invalid_review_base_url');
    configured.search = '';
    configured.hash = '';
    return configured.toString().replace(/\/$/, '');
  }
  const url = new URL(request.url);
  url.pathname = REVIEW_PATH;
  url.search = '';
  url.hash = '';
  return url.toString();
}

function safeApplicationSummary(body) {
  return {
    displayName:cleanString(body?.displayName, 140, false),
    entityType:['professional','center'].includes(body?.entityType) ? body.entityType : 'unknown',
    specialties:Array.isArray(body?.specialties)
      ? body.specialties.slice(0, 12).map(value => cleanString(value, 80, false)).filter(Boolean)
      : [],
    region:cleanString(body?.region || body?.serviceRegion, 120, false)
  };
}

async function sendOwnerReviewEmail(env, data) {
  const summaryItems = [
    `<li><strong>الاسم العام:</strong> ${escapeHtml(data.summary.displayName || 'غير محدد')}</li>`,
    `<li><strong>نوع الملف:</strong> ${escapeHtml(data.summary.entityType)}</li>`,
    `<li><strong>التخصصات:</strong> ${escapeHtml(data.summary.specialties.join('، ') || 'غير محددة')}</li>`,
    `<li><strong>المنطقة:</strong> ${escapeHtml(data.summary.region || 'غير محددة')}</li>`
  ].join('');
  const html = emailLayout('مراجعة طلب انضمام مهني', `
    <p><strong>رقم الطلب:</strong> ${escapeHtml(data.referenceId)}</p>
    <ul>${summaryItems}</ul>
    <p><a href="${escapeHtml(data.reviewUrl)}" style="display:inline-block;padding:12px 18px;background:#075f5b;color:#fff;text-decoration:none;border-radius:10px">فتح صفحة المراجعة الآمنة</a></p>
    <p><strong>فتح الرابط لا يوافق على الطلب.</strong> يلزم اختيار القرار ثم تأكيده بزر POST داخل الصفحة.</p>
    <p>تنتهي صلاحية الرابط في ${escapeHtml(data.expiresAt)}، ويُستخدم لاتخاذ قرار واحد فقط.</p>
  `);
  const response = await fetch('https://api.resend.com/emails', {
    method:'POST',
    headers:{authorization:`Bearer ${env.RESEND_API_KEY}`, 'content-type':'application/json'},
    body:JSON.stringify({
      from:env.FROM_EMAIL,
      to:[env.OWNER_EMAIL],
      subject:`مراجعة آمنة لطلب الانضمام ${data.referenceId}`,
      html
    }),
    signal:AbortSignal.timeout(12_000)
  });
  if (!response.ok) {
    console.error('signed_review_email_failed', response.status, await response.text());
    throw new Error('signed_review_email_failed');
  }
  await audit(env, 'application_review_email_sent', data.applicationId, {
    referenceId:data.referenceId,
    expiresAt:data.expiresAt
  });
}

function renderReviewPage(row, csrfToken) {
  let payload = {};
  try { payload = JSON.parse(row.payload_json || '{}'); } catch (_error) { payload = {}; }
  const specialties = Array.isArray(payload.specialties) ? payload.specialties.slice(0, 12).join('، ') : '';
  const region = payload.region || payload.serviceRegion || '';
  const body = `
    <h1>مراجعة طلب انضمام مهني</h1>
    <div class="notice">فتح هذه الصفحة لم يغيّر حالة الطلب. القرار لا يُنفذ إلا بعد الضغط على زر التأكيد.</div>
    <dl>
      <dt>رقم الطلب</dt><dd>${escapeHtml(row.reference_id)}</dd>
      <dt>الاسم العام</dt><dd>${escapeHtml(row.display_name)}</dd>
      <dt>نوع الملف</dt><dd>${escapeHtml(row.entity_type)}</dd>
      <dt>الحالة الحالية</dt><dd>${escapeHtml(row.status)}</dd>
      <dt>التخصصات</dt><dd>${escapeHtml(specialties || 'غير محددة')}</dd>
      <dt>المنطقة</dt><dd>${escapeHtml(region || 'غير محددة')}</dd>
    </dl>
    <form method="post" action="${REVIEW_PATH}">
      <input type="hidden" name="csrf" value="${escapeHtml(csrfToken)}">
      <label for="reason">سبب الرفض أو ملاحظة القرار</label>
      <textarea id="reason" name="reason" maxlength="800" rows="5"></textarea>
      <label class="confirm"><input type="checkbox" name="confirm" value="1" required> أؤكد أنني راجعت الملخص وأريد تنفيذ القرار الآن.</label>
      <div class="actions">
        <button type="submit" name="decision" value="approved">اعتماد الطلب</button>
        <button class="danger" type="submit" name="decision" value="rejected">رفض الطلب</button>
      </div>
    </form>
    <p class="foot">يمكن تعديل الحالة لاحقًا أو تعليق الملف من لوحة الإدارة، ويُسجل كل تغيير في سجل التدقيق.</p>`;
  return new Response(pageTemplate('مراجعة طلب الانضمام', body), {status:200, headers:securityHeaders()});
}

function renderResultPage(decision, referenceId) {
  const label = decision === 'approved' ? 'تم اعتماد الطلب' : 'تم رفض الطلب';
  return pageTemplate(label, `<h1>${label}</h1><p>تم تسجيل القرار للطلب <strong>${escapeHtml(referenceId)}</strong>.</p><p>أُبطل رابط المراجعة ولا يمكن استخدامه مرة أخرى.</p>`);
}

function reviewMessage(title, message, status) {
  return new Response(pageTemplate(title, `<h1>${escapeHtml(title)}</h1><p>${escapeHtml(message)}</p>`), {
    status,
    headers:securityHeaders()
  });
}

function pageTemplate(title, body) {
  return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(title)}</title><style>body{font-family:Tahoma,Arial,sans-serif;background:#f3f8f7;color:#17383b;margin:0;padding:24px}main{max-width:760px;margin:auto;background:#fff;border:1px solid #c8dfdc;border-radius:18px;padding:24px;box-shadow:0 8px 28px #073b3a18}h1{color:#075f5b}dl{display:grid;grid-template-columns:minmax(120px,180px) 1fr;gap:10px}dt{font-weight:700}dd{margin:0;overflow-wrap:anywhere}.notice{background:#fff7d6;border:1px solid #d7b949;border-radius:10px;padding:12px;margin:16px 0}label{display:block;font-weight:700;margin:16px 0 8px}textarea{box-sizing:border-box;width:100%;font:inherit;border:1px solid #7b9c99;border-radius:10px;padding:10px}.confirm{font-weight:400}.actions{display:flex;flex-wrap:wrap;gap:12px;margin-top:18px}button{font:inherit;font-weight:700;border:0;border-radius:10px;padding:12px 18px;background:#08766f;color:#fff;cursor:pointer}.danger{background:#9b2c2c}.foot{font-size:.92rem;color:#536e70;margin-top:24px}@media(max-width:560px){body{padding:12px}main{padding:18px}dl{grid-template-columns:1fr;gap:4px}dd{margin-bottom:10px}.actions button{width:100%}}button:focus-visible,textarea:focus-visible,input:focus-visible{outline:3px solid #f1b52b;outline-offset:3px}</style></head><body><main>${body}</main></body></html>`;
}

function securityHeaders(extra = {}) {
  return new Headers({
    'content-type':'text/html; charset=utf-8',
    'cache-control':'no-store, max-age=0',
    'content-security-policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
    'referrer-policy':'no-referrer',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY',
    'permissions-policy':'camera=(), microphone=(), geolocation=()',
    ...extra
  });
}

function appendCookie(headers, name, value, httpOnly) {
  const parts = [`${name}=${value}`, `Path=${COOKIE_PATH}`, 'Max-Age=1800', 'Secure', 'SameSite=Strict'];
  if (httpOnly) parts.push('HttpOnly');
  headers.append('set-cookie', parts.join('; '));
}

function clearCookie(headers, name, httpOnly) {
  const parts = [`${name}=`, `Path=${COOKIE_PATH}`, 'Max-Age=0', 'Secure', 'SameSite=Strict'];
  if (httpOnly) parts.push('HttpOnly');
  headers.append('set-cookie', parts.join('; '));
}

function cookieValue(request, name) {
  const cookies = String(request.headers.get('cookie') || '').split(';');
  for (const part of cookies) {
    const [key, ...rest] = part.trim().split('=');
    if (key === name) return rest.join('=');
  }
  return '';
}

function enforceSameOrigin(request) {
  const origin = request.headers.get('origin');
  const expected = new URL(request.url).origin;
  if (!origin || origin !== expected) fail('مصدر طلب القرار غير معتمد.', 403, 'review_origin_mismatch');
}

function assertReviewConfiguration(env) {
  if (!env.DB) fail('قاعدة البيانات غير متاحة.', 503, 'database_unavailable');
  if (!env.REVIEW_LINK_SECRET || String(env.REVIEW_LINK_SECRET).length < 32) {
    fail('سر توقيع روابط المراجعة غير مهيأ.', 503, 'review_secret_not_configured');
  }
  if (!env.RESEND_API_KEY || !env.FROM_EMAIL || !env.OWNER_EMAIL) {
    fail('إشعار المراجعة بالبريد غير مهيأ.', 503, 'review_email_not_configured');
  }
}

function boundedInteger(value, fallback, min, max) {
  const parsed = Number.parseInt(String(value ?? ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}
