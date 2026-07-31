import finalWorker from './index-v10-final.js';
import {
  handleSpecialistMessageV10,
  processSpecialistMessageOutbox,
  specialistMessageHealth,
} from './specialist-message-v10.js';

const BUILD_VERSION = '10.3.0';
const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};
const SPECIALIST_MESSAGE_PATH = /^\/v1\/specialist\/conversations\/([a-z0-9-]+)\/messages$/i;
const ADMIN_EMAIL_RESET_PATH = /^\/v1\/admin\/users\/([a-z0-9-]+)\/password-reset$/i;
const CONSUMER_SENDER_DOMAINS = new Set([
  'aol.com',
  'gmail.com',
  'gmx.com',
  'googlemail.com',
  'hotmail.com',
  'icloud.com',
  'live.com',
  'mac.com',
  'mail.com',
  'me.com',
  'outlook.com',
  'proton.me',
  'protonmail.com',
  'yahoo.com',
  'ymail.com',
  'zoho.com',
]);

export default {
  async scheduled(event, env, ctx) {
    if (typeof finalWorker.scheduled === 'function') {
      ctx.waitUntil(Promise.resolve(finalWorker.scheduled(event, env, ctx)));
    }
    ctx.waitUntil(processSpecialistMessageOutbox(env).catch((error) => {
      console.error('specialist_message_outbox_scheduled_error', safeError(error));
    }));
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = request.headers.get('origin') || '';
    const cors = corsHeaders(origin, env);

    if (request.method === 'OPTIONS') {
      return new Response(null, {status:204, headers:cors});
    }

    try {
      const sender = senderReadiness(env);
      if (request.method === 'POST' && url.pathname === '/v1/auth/password/request' && !sender.ready) {
        return senderUnavailableResponse(cors, sender, false);
      }

      const adminResetMatch = url.pathname.match(ADMIN_EMAIL_RESET_PATH);
      if (request.method === 'POST' && adminResetMatch && !sender.ready) {
        const session = await authenticatedSession(request, env, ctx);
        if (!session.ok) return ensureCors(session.response, origin, env);
        if (!['owner','admin'].includes(session.user?.role)) {
          return json({error:'forbidden', message:'لا تملك الصلاحية المطلوبة.'}, 403, cors);
        }
        return senderUnavailableResponse(cors, sender, true);
      }

      const specialistMessageMatch = url.pathname.match(SPECIALIST_MESSAGE_PATH);
      if (request.method === 'POST' && specialistMessageMatch) {
        const session = await authenticatedSession(request, env, ctx);
        if (!session.ok) return ensureCors(session.response, origin, env);
        const actor = {
          ...session.user,
          provider_id:session.user.providerId || session.user.provider_id || null,
        };
        return ensureCors(
          await handleSpecialistMessageV10(
            request,
            env,
            ctx,
            cors,
            actor,
            specialistMessageMatch[1],
          ),
          origin,
          env,
        );
      }

      if (request.method === 'GET' && url.pathname === '/health' && url.searchParams.get('deep') === '1') {
        if (!bootstrapAuthorized(request, env)) {
          return json({error:'forbidden', message:'الفحص العميق مقيد بالتشغيل.'}, 403, cors);
        }
        return withProductionVersion(await finalWorker.fetch(request, env, ctx), origin, env);
      }

      if (request.method === 'GET' && url.pathname === '/v1/admin/email-provider-status') {
        const session = await authenticatedSession(request, env, ctx);
        if (!session.ok) return ensureCors(session.response, origin, env);
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
        const ready = provider.authValid === true && sender.ready;
        return json({
          ok:ready,
          provider:'resend',
          configured:provider.configured === true,
          authValid:provider.authValid === true,
          access:provider.access || 'unknown',
          code:ready ? (provider.code || 'ready') : (sender.ready ? (provider.code || 'provider_unavailable') : sender.code),
          senderReady:sender.ready,
          senderCode:sender.code,
          senderDomain:sender.domain,
          senderPolicyVersion:sender.policyVersion,
          manualRecoveryAvailable:Boolean(deep.capabilities?.manualRecovery),
        }, ready ? 200 : 503, cors);
      }

      const response = await finalWorker.fetch(request, env, ctx);
      if (request.method === 'GET' && url.pathname === '/health') {
        return withProductionVersion(response, origin, env);
      }
      if (request.method === 'POST' && url.pathname === '/v1/admin/users' && !sender.ready) {
        const data = await response.clone().json().catch(() => ({}));
        if (response.status === 503 && data.partialSuccess === true) {
          return json({
            ...data,
            error:'email_sender_not_verified',
            message:'تم إنشاء الحساب، لكن نطاق مرسل البريد غير موثّق. استخدم الرابط اليدوي من حساب المالك حتى توثيق نطاق مخصص.',
            senderReady:false,
            senderCode:sender.code,
            manualRecoveryAvailable:true,
          }, 503, cors);
        }
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

async function authenticatedSession(request, env, ctx) {
  const sessionRequest = new Request(new URL('/v1/auth/session', request.url), {
    method:'GET',
    headers:request.headers,
    redirect:'follow',
  });
  const response = await finalWorker.fetch(sessionRequest, env, ctx);
  const data = await response.clone().json().catch(() => ({}));
  if (!response.ok || !data.user) return {ok:false, response};
  return {ok:true, user:data.user, response};
}

async function withProductionVersion(response, origin, env) {
  const data = await response.clone().json().catch(() => ({}));
  if (!data || typeof data !== 'object' || data.service !== 'pterminology-specialist-identity') {
    return ensureCors(response, origin, env);
  }
  const messageChecks = await specialistMessageHealth(env);
  const sender = senderReadiness(env);
  const checks = {
    ...(data.checks || {}),
    ...messageChecks,
    protectedDeepHealth:true,
    adminProviderStatus:true,
    corsPreflight:true,
    emailSenderPolicy:true,
  };
  const emailProvider = {
    ...(data.emailProvider || {}),
    senderReady:sender.ready,
    senderCode:sender.code,
    senderDomain:sender.domain,
    senderPolicyVersion:sender.policyVersion,
  };
  const capabilities = {
    ...(data.capabilities || {}),
    passwordRecoveryEmail:data.capabilities?.passwordRecoveryEmail === true && sender.ready,
    manualRecovery:true,
  };
  const ok = data.ok === true && Object.values(checks).every(Boolean);
  return json({...data, ok, version:BUILD_VERSION, checks, emailProvider, capabilities}, ok ? 200 : 503, corsHeaders(origin, env));
}

export function senderReadiness(env = {}) {
  const from = String(env.FROM_EMAIL || '').trim().toLowerCase();
  const bracketed = from.match(/<\s*([^<>\s]+@[^<>\s]+)\s*>$/);
  const address = bracketed ? bracketed[1] : from;
  const match = address.match(/^[^\s@]+@([^\s@]+)$/);
  const domain = match ? match[1].replace(/\.$/, '') : null;
  const policyVersion = '1';
  if (!domain) {
    return {ready:false, configured:false, code:'sender_not_configured', domain:null, policyVersion};
  }
  if (domain === 'resend.dev') {
    return {ready:false, configured:true, code:'resend_test_sender', domain, policyVersion};
  }
  if (CONSUMER_SENDER_DOMAINS.has(domain)) {
    return {ready:false, configured:true, code:'sender_domain_not_verified', domain, policyVersion};
  }
  const declared = String(env.RESEND_VERIFIED_SENDER_DOMAINS || '')
    .split(',')
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
  if (declared.length && !declared.includes(domain)) {
    return {ready:false, configured:true, code:'sender_domain_not_declared_verified', domain, policyVersion};
  }
  return {
    ready:true,
    configured:true,
    code:declared.length ? 'sender_domain_declared_verified' : 'sender_domain_candidate',
    domain,
    policyVersion,
  };
}

function senderUnavailableResponse(cors, sender, admin) {
  return json({
    error:'email_sender_not_verified',
    message:admin
      ? 'نطاق مرسل البريد غير موثّق؛ لم يُنشأ أو يُرسل رابط. استخدم إنشاء الرابط اليدوي من حساب المالك.'
      : 'خدمة إرسال روابط الاستعادة غير متاحة حاليًا، ولم يُنشأ أو يُرسل أي رابط.',
    senderReady:false,
    senderCode:sender.code,
    manualRecoveryAvailable:Boolean(admin),
    version:BUILD_VERSION,
  }, 503, cors);
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
  const allowed = new Set([
    'https://khaledaltheeb.github.io',
    'https://healthrenewal.org',
    'https://www.healthrenewal.org',
    ...String(env.ALLOWED_ORIGINS || '')
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean),
  ]);
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
  if (origin && allowed.has(origin)) headers['access-control-allow-origin'] = origin;
  return headers;
}

function safeError(error) {
  return String(error?.message || error || 'unknown').slice(0, 240);
}

function json(payload, status = 200, headers = {}) {
  return new Response(JSON.stringify(payload), {status, headers:{...JSON_HEADERS, ...headers}});
}
