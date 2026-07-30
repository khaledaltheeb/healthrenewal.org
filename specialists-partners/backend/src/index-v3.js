import baseWorker from './index-v2.js';
import {corsHeaders, json} from './messaging-v5-utils.js';
import {
  assertAdminNotificationConfiguration,
  assertConversationNotificationReady,
  messagingHealth
} from './messaging-v5-policy.js';
import {createMessageV5} from './messaging-v5-handler.js';

export default {
  async scheduled(event, env, ctx) {
    if (typeof baseWorker.scheduled === 'function') await baseWorker.scheduled(event, env, ctx);
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const cors = corsHeaders(request.headers.get('origin') || '', env);
    if (request.method === 'OPTIONS') return baseWorker.fetch(request, env, ctx);

    try {
      if (request.method === 'GET' && url.pathname === '/health') {
        return await messagingHealth(baseWorker, env, cors);
      }
      if (request.method === 'POST' && url.pathname === '/v1/conversations') {
        await assertConversationNotificationReady(request.clone(), env);
        return await baseWorker.fetch(request, env, ctx);
      }
      if (url.pathname.startsWith('/v1/admin/') && ['POST','PATCH'].includes(request.method)) {
        await assertAdminNotificationConfiguration(request.clone(), url.pathname);
      }
      const messageMatch = url.pathname.match(/^\/v1\/conversations\/([a-z0-9-]+)\/messages$/i);
      if (messageMatch && request.method === 'POST') {
        return await createMessageV5(request, env, ctx, cors, messageMatch[1]);
      }
      return await baseWorker.fetch(request, env, ctx);
    } catch (error) {
      console.error('messaging_v5_error', error);
      const status = Number(error?.status) || 500;
      return json({
        error:error?.code || 'internal_error',
        message:status === 500 ? 'حدث خطأ داخلي.' : error.message
      }, status, cors);
    }
  }
};
