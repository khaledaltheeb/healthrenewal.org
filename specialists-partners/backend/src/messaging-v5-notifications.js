import {
  audit, cleanString, emailLayout, escapeHtml,
  issueConversationToken, portalLink, sha256
} from './messaging-v5-utils.js';

export async function messageNotifications(env, conversation, conversationId, messageId, role, now) {
  const portalBase = String(env.PORTAL_BASE_URL ||
    'https://healthrenewal.org/specialists-partners/portal/');
  const notifications = [];

  if (role === 'visitor') {
    if (Number(conversation.provider_notification_enabled) !== 1) {
      await audit(env, 'provider_notification_policy_violation', conversation.provider_id, {
        conversationId,
        messageId
      });
    } else {
      const specialistToken = await issueConversationToken(env, conversationId, 'specialist', now);
      notifications.push({
        to:[conversation.provider_email],
        subject:`رسالة جديدة — ${conversation.reference_id}`,
        html:emailLayout('رسالة جديدة في المحادثة',
          `<p>وصلت رسالة جديدة في المحادثة <strong>${escapeHtml(conversation.reference_id)}</strong>.</p>
           <p><a href="${escapeHtml(portalLink(portalBase, conversationId, specialistToken, 'specialist'))}">فتح المحادثة والرد داخل المنصة</a></p>
           <p>لم نضع نص الرسالة في البريد حمايةً للخصوصية.</p>`),
        entityType:'message',
        entityId:messageId,
        template:'message_specialist_v5',
        idempotencyKey:`message-specialist-v5/${messageId}`
      });
    }
  } else {
    const visitorToken = await issueConversationToken(env, conversationId, 'visitor', now);
    notifications.push({
      to:[conversation.visitor_email],
      subject:`رد من المختص — ${conversation.reference_id}`,
      html:emailLayout('وصل رد جديد',
        `<p>وصل رد جديد في المحادثة <strong>${escapeHtml(conversation.reference_id)}</strong>.</p>
         <p><a href="${escapeHtml(portalLink(portalBase, conversationId, visitorToken, 'visitor'))}">فتح المحادثة الخاصة</a></p>
         <p>لم نضع نص الرد في البريد حمايةً للخصوصية.</p>`),
      entityType:'message',
      entityId:messageId,
      template:'message_visitor_v5',
      idempotencyKey:`message-visitor-v5/${messageId}`
    });
  }

  if (env.OWNER_EMAIL) {
    const ownerName = String(env.OWNER_DISPLAY_NAME || 'خالد الذيب').trim();
    const adminUrl = safeAdminUrl(env.ADMIN_CONSOLE_URL ||
      'https://healthrenewal.org/specialists-partners/admin/#conversations');
    const senderLabel = role === 'visitor' ? 'صاحب الطلب' : 'المختص';
    notifications.push({
      to:[env.OWNER_EMAIL],
      subject:`إشعار إدارة: رسالة جديدة — ${conversation.reference_id}`,
      html:emailLayout(`تنبيه إلى ${ownerName}`,
        `<p>وصلت رسالة جديدة من <strong>${escapeHtml(senderLabel)}</strong> في محادثة الملف <strong>${escapeHtml(conversation.provider_display_name)}</strong>.</p>
         <p><strong>المرجع:</strong> ${escapeHtml(conversation.reference_id)}</p>
         <p><a href="${escapeHtml(adminUrl)}">فتح لوحة إدارة المحادثات</a></p>
         <p>لا يتضمن هذا البريد نص الرسالة أو أي رمز دخول خاص.</p>`),
      entityType:'message',
      entityId:messageId,
      template:'message_owner_v5',
      idempotencyKey:`message-owner-v5/${messageId}`
    });
  }
  return notifications;
}

export function queueNotifications(ctx, env, notifications) {
  const jobs = notifications.filter(item => Array.isArray(item.to) && item.to.filter(Boolean).length)
    .map(item => deliverEmail(env, item));
  if (!jobs.length) return;
  ctx.waitUntil(Promise.allSettled(jobs).then(async results => {
    const failures = results.filter(result => result.status === 'rejected');
    if (failures.length) {
      await audit(env, 'notification_batch_failed_v5', crypto.randomUUID(), {failures:failures.length});
    }
  }));
}

async function deliverEmail(env, item) {
  const recipients = item.to.filter(Boolean);
  const recipientHash = await sha256(recipients.join(',').toLowerCase());
  const eventId = crypto.randomUUID();
  if (!env.RESEND_API_KEY || !env.FROM_EMAIL) {
    await recordEmailEvent(env, item, eventId, recipientHash, 'skipped', null, 'email_not_configured');
    return {skipped:true};
  }

  let failureRecorded = false;
  try {
    const response = await fetch('https://api.resend.com/emails', {
      method:'POST',
      headers:{
        authorization:`Bearer ${env.RESEND_API_KEY}`,
        'content-type':'application/json',
        'user-agent':'pterminology-specialists/5.0',
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
      await recordEmailEvent(env, item, eventId, recipientHash, 'failed', null, code);
      failureRecorded = true;
      throw new Error(`email_send_failed:${code}`);
    }
    await recordEmailEvent(env, item, eventId, recipientHash, 'sent', detail.id || null, null);
    return detail;
  } catch (error) {
    const code = String(error?.message || 'email_transport_error').slice(0,180);
    if (!failureRecorded) {
      await recordEmailEvent(env, item, eventId, recipientHash, 'failed', null, code);
    }
    throw error;
  }
}

async function recordEmailEvent(env, item, id, recipientHash, status, providerMessageId, errorCode) {
  try {
    await env.DB.prepare(`
      INSERT INTO email_events (
        id, entity_type, entity_id, recipient_hash, template,
        status, provider_message_id, error_code, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    `).bind(id, item.entityType, item.entityId, recipientHash, item.template,
      status, providerMessageId, errorCode).run();
  } catch (error) {
    console.error('email_event_v5_error', error);
  }
}

function safeAdminUrl(value) {
  try {
    const parsed = new URL(String(value));
    if (parsed.protocol !== 'https:' || parsed.username || parsed.password) throw new Error('invalid');
    return parsed.href;
  } catch {
    return 'https://healthrenewal.org/specialists-partners/admin/#conversations';
  }
}
