import {
  MAX_MESSAGE_LENGTH, audit, constantTimeEqual, conversationAccess,
  fail, json, parseJson, rateLimit, sha256, validId, validIdempotencyKey
} from './messaging-v5-utils.js';
import {messageNotifications, queueNotifications} from './messaging-v5-notifications.js';

export async function createMessageV5(request, env, ctx, cors, conversationId) {
  await rateLimit(request, env, 'message_v5', 80);
  const body = await parseJson(request);
  const {accessToken, role} = conversationAccess(request, new URL(request.url), body);
  const message = String(body.body ?? '').trim();
  if (!message) fail('أحد الحقول المطلوبة فارغ.', 400, 'missing_field');
  if (message.length > MAX_MESSAGE_LENGTH) fail('أحد الحقول تجاوز الحد المسموح.', 400, 'field_too_long');
  const idempotencyKey = validIdempotencyKey(request.headers.get('idempotency-key'));
  const id = validId(conversationId, 'معرف المحادثة');
  const accessHash = await sha256(accessToken);

  const conversation = await env.DB.prepare(`
    SELECT c.*,
      p.display_name AS provider_display_name,
      p.email AS provider_email,
      p.notification_enabled AS provider_notification_enabled
    FROM conversations c
    JOIN providers_private p ON p.provider_id = c.provider_id
    WHERE c.id = ?
  `).bind(id).first();
  if (!conversation) fail('المحادثة غير موجودة.', 404, 'conversation_not_found');

  const tokenRow = await env.DB.prepare(`
    SELECT token_hash FROM conversation_tokens
    WHERE conversation_id = ? AND role = ? AND token_hash = ? AND expires_at > ?
    ORDER BY created_at DESC LIMIT 1
  `).bind(id, role, accessHash, new Date().toISOString()).first();
  if (!tokenRow || !constantTimeEqual(accessHash, tokenRow.token_hash)) {
    fail('رابط المحادثة غير صالح أو انتهت صلاحيته.', 403, 'invalid_access_token');
  }
  if (conversation.status !== 'open') fail('المحادثة مغلقة.', 409, 'conversation_closed');

  const requestKeyHash = await sha256(`${id}:${role}:${idempotencyKey}`);
  const existing = await env.DB.prepare(`
    SELECT message_id, created_at FROM message_requests WHERE request_key_hash = ?
  `).bind(requestKeyHash).first();
  if (existing) {
    return json({ok:true, messageId:existing.message_id, createdAt:existing.created_at, duplicate:true}, 200, cors);
  }

  const now = new Date().toISOString();
  const messageId = crypto.randomUUID();
  await env.DB.batch([
    env.DB.prepare(`
      INSERT OR IGNORE INTO message_requests (
        request_key_hash, conversation_id, sender_role, message_id, created_at
      ) VALUES (?, ?, ?, ?, ?)
    `).bind(requestKeyHash, id, role, messageId, now),
    env.DB.prepare(`
      INSERT INTO messages (id, conversation_id, sender_role, body, created_at)
      SELECT ?, ?, ?, ?, ? WHERE EXISTS (
        SELECT 1 FROM message_requests WHERE request_key_hash = ? AND message_id = ?
      )
    `).bind(messageId, id, role, message, now, requestKeyHash, messageId),
    env.DB.prepare(`
      UPDATE conversations SET updated_at = ?, last_message_at = ?
      WHERE id = ? AND EXISTS (
        SELECT 1 FROM message_requests WHERE request_key_hash = ? AND message_id = ?
      )
    `).bind(now, now, id, requestKeyHash, messageId)
  ]);

  const canonical = await env.DB.prepare(`
    SELECT message_id, created_at FROM message_requests WHERE request_key_hash = ?
  `).bind(requestKeyHash).first();
  if (!canonical) fail('تعذر تثبيت الرسالة.', 503, 'message_persistence_failed');
  if (canonical.message_id !== messageId) {
    return json({ok:true, messageId:canonical.message_id, createdAt:canonical.created_at, duplicate:true}, 200, cors);
  }

  await audit(env, 'message_created_v5', id, {senderRole:role, messageId});
  const notifications = await messageNotifications(env, conversation, id, messageId, role, now);
  queueNotifications(ctx, env, notifications);
  return json({ok:true, messageId, createdAt:now, duplicate:false}, 201, cors);
}
