import {fail, json, parseJson, validId} from './messaging-v5-utils.js';

export async function assertConversationNotificationReady(request, env) {
  const body = await parseJson(request);
  const providerId = validId(body.providerId, 'معرف المختص');
  const provider = await env.DB.prepare(`
    SELECT status, accepts_new_requests, notification_enabled
    FROM providers_private WHERE provider_id = ?
  `).bind(providerId).first();
  if (!provider || provider.status !== 'active' || Number(provider.accepts_new_requests) !== 1) return;
  if (Number(provider.notification_enabled) !== 1) {
    fail('تعذر فتح المحادثة لأن إشعارات المختص غير مفعلة. تواصل مع إدارة المنصة.', 409,
      'provider_notifications_required');
  }
}

export async function assertAdminNotificationConfiguration(request, pathname) {
  if (!/\/v1\/admin\/(?:providers|applications)/.test(pathname)) return;
  const contentType = request.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) return;
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== 'object' || Array.isArray(body)) return;
  const candidate = body.provider && typeof body.provider === 'object' ? body.provider : body;
  if (candidate.acceptsNewRequests === true && candidate.notificationEnabled === false) {
    fail('لا يمكن استقبال محادثات جديدة مع تعطيل إشعارات المختص.', 422,
      'provider_notification_policy');
  }
}

export async function messagingHealth(baseWorker, env, cors) {
  const baseResponse = await baseWorker.fetch(new Request('https://service.invalid/health'), env, {
    waitUntil() {}
  });
  const base = await baseResponse.json().catch(() => ({checks:{}}));
  let messagingV5 = false;
  let notificationPolicy = false;
  try {
    const schema = await env.DB.prepare(`
      SELECT COUNT(*) AS count FROM sqlite_master
      WHERE type='table' AND name = 'message_requests'
    `).first();
    messagingV5 = Number(schema?.count || 0) === 1;
    const unsafe = await env.DB.prepare(`
      SELECT COUNT(*) AS count FROM providers_private
      WHERE status='active' AND accepts_new_requests=1 AND notification_enabled<>1
    `).first();
    notificationPolicy = Number(unsafe?.count || 0) === 0;
  } catch (error) {
    console.error('messaging_v5_health_db_error', error);
  }

  const deploymentCommit = String(env.RELEASE_COMMIT || '').trim();
  const checks = {
    ...(base.checks || {}),
    messagingV5,
    notificationPolicy,
    ownerIdentity:String(env.OWNER_DISPLAY_NAME || '').trim() === 'خالد الذيب',
    releaseIdentity:/^[a-f0-9]{40}$/i.test(deploymentCommit)
  };
  const ready = Object.values(checks).every(Boolean);
  return json({
    ...base,
    ok:ready,
    version:'5.0.0',
    ownerDisplayName:String(env.OWNER_DISPLAY_NAME || 'خالد الذيب').trim(),
    deploymentCommit,
    checks,
    time:new Date().toISOString()
  }, ready ? 200 : 503, cors);
}
