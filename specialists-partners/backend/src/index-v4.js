import baseWorker from './index-v3.js';
import {corsHeaders, json} from './messaging-v5-utils.js';
import {
  handleApplicationReview,
  issueApplicationReviewInvitation,
  signedReviewHealth
} from './application-review-v6.js';

const BUILD_VERSION = '6.0.0';
const REVIEW_PATH = '/v1/reviews/applications';

export default {
  async scheduled(event, env, ctx) {
    if (typeof baseWorker.scheduled === 'function') await baseWorker.scheduled(event, env, ctx);
    if (!env.DB) return;
    ctx.waitUntil(env.DB.batch([
      env.DB.prepare(`
        DELETE FROM application_review_invitations
        WHERE expires_at < datetime('now','-30 day')
          OR used_at < datetime('now','-365 day')
          OR revoked_at < datetime('now','-30 day')
      `),
      env.DB.prepare(`
        UPDATE application_review_invitations
        SET review_session_hash = NULL, csrf_hash = NULL
        WHERE expires_at <= CURRENT_TIMESTAMP
      `)
    ]));
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const cors = corsHeaders(request.headers.get('origin') || '', env);

    try {
      if (url.pathname === REVIEW_PATH && ['GET','POST'].includes(request.method)) {
        return await handleApplicationReview(request, env);
      }

      if (request.method === 'GET' && url.pathname === '/health') {
        const baseResponse = await baseWorker.fetch(request, env, ctx);
        const payload = await baseResponse.clone().json();
        const reviewChecks = await signedReviewHealth(env);
        const checks = {...(payload.checks || {}), ...reviewChecks};
        const ok = Boolean(payload.ok) && Object.values(reviewChecks).every(Boolean);
        return json({
          ...payload,
          ok,
          version:BUILD_VERSION,
          checks
        }, ok ? 200 : 503, cors);
      }

      if (request.method === 'POST' && url.pathname === '/v1/applications') {
        const applicationRequest = request.clone();
        const baseResponse = await baseWorker.fetch(request, env, ctx);
        if (baseResponse.status !== 201) return baseResponse;

        const applicationBody = await applicationRequest.json().catch(() => ({}));
        const result = await baseResponse.clone().json();
        if (!result.referenceId) {
          console.error('signed_review_missing_reference_id');
          return baseResponse;
        }

        let applicationId = String(applicationBody.submissionId || '').trim();
        if (!applicationId) {
          const storedApplication = await env.DB.prepare(`
            SELECT id FROM applications WHERE reference_id = ? LIMIT 1
          `).bind(result.referenceId).first();
          applicationId = String(storedApplication?.id || '').trim();
        }
        if (!applicationId) {
          console.error('signed_review_missing_application_identity');
          return baseResponse;
        }

        try {
          await issueApplicationReviewInvitation(
            applicationRequest,
            env,
            ctx,
            applicationId,
            result.referenceId,
            applicationBody
          );
        } catch (error) {
          console.error('signed_review_invitation_error', error);
          ctx.waitUntil(env.DB.prepare(`
            INSERT INTO audit_log (id, event_type, entity_id, metadata_json, created_at)
            VALUES (?, 'application_review_invitation_failed', ?, ?, CURRENT_TIMESTAMP)
          `).bind(
            crypto.randomUUID(),
            applicationId,
            JSON.stringify({referenceId:result.referenceId, error:error?.code || error?.message || 'unknown'})
          ).run());
        }
        return baseResponse;
      }

      return await baseWorker.fetch(request, env, ctx);
    } catch (error) {
      console.error('signed_review_v6_error', error);
      const status = Number(error?.status) || 500;
      if (url.pathname === REVIEW_PATH) {
        const safeMessage = status === 500 ? 'حدث خطأ داخلي أثناء معالجة المراجعة.' : error.message;
        return new Response(`<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>تعذر تنفيذ المراجعة</title><body style="font-family:Tahoma,Arial,sans-serif;background:#f3f8f7;color:#17383b;padding:24px"><main style="max-width:680px;margin:auto;background:#fff;border:1px solid #c8dfdc;border-radius:18px;padding:24px"><h1>تعذر تنفيذ المراجعة</h1><p>${escapeText(safeMessage)}</p></main></body></html>`, {
          status,
          headers:{
            'content-type':'text/html; charset=utf-8',
            'cache-control':'no-store',
            'content-security-policy':"default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'",
            'referrer-policy':'no-referrer',
            'x-content-type-options':'nosniff',
            'x-frame-options':'DENY'
          }
        });
      }
      return json({
        error:error?.code || 'internal_error',
        message:status === 500 ? 'حدث خطأ داخلي.' : error.message
      }, status, cors);
    }
  }
};

function escapeText(value) {
  return String(value || '').replace(/[&<>"']/g, character => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[character]));
}
