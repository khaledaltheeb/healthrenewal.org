import finalWorker from './index-v10-final.js';

const BUILD_VERSION = '10.3.0';
const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};

export default {
  async scheduled(event, env, ctx) {
    if (typeof finalWorker.scheduled === 'function') return finalWorker.scheduled(event, env, ctx);
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('origin') || '';
    const cors = corsHeaders(origin, env);

    if (request.method === 'OPTIONS') {
      return new Response(null, {status:204, headers:cors});
    }

    try {
      if (request.method === 'GET' && url.pathname === '/health' && url.searchParams.get('deep') === '1') {
        if (!bootstrapAuthorized(request, env)) {
          return json({error:'forbidden', message:'الفحص العميق مقيد بالتشغيل.'}, 403, cors);
        }
        return withProductionVersion(await finalWorker.fetch(request, env, ctx), origin, env);
      }

      if (request.method === 'GET' && url.pathname === '/v1/admin/email-provider-status') {
        const sessionRequest = new Request(new URL('/v1/auth/session', request.url), {
          method:'GET',
          headers:request.headers,
          redirect:'follow',
        });
        const sessionResponse = await finalWorker.fetch(sessionRequest, env, ctx);
        const session = await sessionResponse.clone().json().catch(() => ({}));
        if (!sessionResponse.ok) return ensureCors(sessionResponse, origin, env);
        if (!['owner','admin'].includes(session.user?.role)) {
          return json({error:'forbidden', message:'لا تملك الصلاحية المطلوبة.'}, 403, cors);
        }

        const headers = new Headers(request.headers);
        headers.set('x-bootstrap-key', String(env.ADMIN_API_KEY || ''));
        const deepRequest = new Request(new URL('/health?deep=1', request.url), {
          method:'GET',
          headers,
          redirect:'follow',
        });
        const deepResponse = await finalWorker.fetch(deepRequest, env, ctx);
        const deep = await deepResponse.json().catch(() => ({}));
        const provider = deep.emailProvider || {};
        return json({
          ok:provider.authValid === true,
          provider:'resend',
          configured:provider.configured === true,
          authValid:provider.authValid === true,
          access:provider.access || 'unknown',
          code:provider.code || 'unknown',
          manualRecoveryAvailable:Boolean(deep.capabilities?.manualRecovery),
        }, provider.authValid === true ? 200 : 503, cors);
      }

      const response = await finalWorker.fetch(request, env, ctx);
      if (request.method === 'GET' && url.pathname === '/health') {
        return withProductionVersion(response, origin, env);
      }
      return ensureCors(response, origin, env);
    } catch (error) {
      console.error('specialist_identity_v103_production_error', safeError(error));
      return json({
        error:'internal_error',
        message:'حدث خطأ داخلي في خدمة الحسابات. أعد المحاولة بعد لحظات.',
        version:BUILD_VERSION,
      }, 500, cors);
    }
  },
};

async function withProductionVersion(response, origin, env) {
  const data = await response.clone().json().catch(() => ({}));
  if (!data || typeof data !== 'object' || data.service !== 'pterminology-specialist-identity') {
    return ensureCors(response, origin, env);
  }
  const checks = {...(data.checks || {}), protectedDeepHealth:true, adminProviderStatus:true, corsPreflight:true};
  const ok = data.ok === true && Object.values(checks).every(Boolean);
  return json({...data, ok, version:BUILD_VERSION, checks}, ok ? 200 : 503, corsHeaders(origin, env));
}

function ensureCors(response, origin, env) {
  const headers = new Headers(response.headers);
  for (const [name, value] of Object.entries(corsHeaders(origin, env))) {
    if (!headers.has(name)) headers.set(name, value);
  }
  return new Response(response.body, {
    status:response.status,
    statusText:response.statusText,
    headers,
  });
}

function bootstrapAuthorized(request, env) {
  const supplied = String(request.headers.get('x-bootstrap-key') || '');
  const expected = String(env.ADMIN_API_KEY || '');
  return Boolean(expected) && constantTimeEqual(supplied, expected);
}

function constantTimeEqual(a, b) {
  a = String(a || '');
  b = String(b || '');
  let diff = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    diff |= (a.charCodeAt(index) || 0) ^ (b.charCodeAt(index) || 0);
  }
  return diff === 0;
}

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://khaledaltheeb.github.io')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
  const headers = {
    'access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers':'authorization,content-type,idempotency-key,x-requested-with,x-bootstrap-key,x-recovery-export-key',
    'access-control-max-age':'86400',
    'cache-control':'no-store',
    'content-security-policy':"default-src 'none'; frame-ancestors 'none'",
    'cross-origin-resource-policy':'cross-origin',
    'referrer-policy':'no-referrer',
    'strict-transport-security':'max-age=31536000; includeSubDomains',
    'vary':'Origin',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY',
  };
  if (origin && allowed.includes(origin)) headers['access-control-allow-origin'] = origin;
  return headers;
}

function json(payload, status = 200, headers = {}) {
  return new Response(JSON.stringify(payload), {status, headers:{...JSON_HEADERS, ...headers}});
}

function safeError(error) {
  return String(error?.message || error || 'unknown').slice(0, 240);
}
