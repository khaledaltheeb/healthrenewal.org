import identityWorker from './index-v10.js';

const BUILD_VERSION = '10.1.0';
const JSON_HEADERS = {'content-type':'application/json; charset=utf-8'};

export default {
  async scheduled(event, env, ctx) {
    if (typeof identityWorker.scheduled === 'function') return identityWorker.scheduled(event, env, ctx);
  },

  async fetch(request, env, ctx) {
    const origin = request.headers.get('origin') || '';
    if (request.method === 'OPTIONS') return new Response(null, {status:204, headers:corsHeaders(origin, env)});

    const url = new URL(request.url);
    if (request.method === 'POST' && url.pathname === '/v1/auth/password/reset') {
      const body = await request.clone().json().catch(() => ({}));
      if (!strictPassword(body.password)) {
        return json({error:'weak_password', message:'استخدم 12 محرفًا على الأقل ومزيجًا من الحروف والأرقام والرموز. تدعم السياسة الحروف العربية.'},400,corsHeaders(origin,env));
      }
    }

    const response = await identityWorker.fetch(request, env, ctx);
    if (request.method === 'GET' && url.pathname === '/health') {
      const data = await response.clone().json().catch(() => ({}));
      const checks = {...(data.checks || {}), corsPreflight:true, strictPasswordPolicy:true};
      const ok = data.ok === true && Object.values(checks).every(Boolean);
      return json({...data,ok,version:BUILD_VERSION,checks},ok?200:503,corsHeaders(origin,env));
    }
    return response;
  }
};

function strictPassword(value) {
  const password = String(value || '');
  if (password.length < 12 || password.length > 128) return false;
  const groups = [
    /\p{L}/u.test(password),
    /\d/u.test(password),
    /[^\p{L}\d\s]/u.test(password)
  ].filter(Boolean).length;
  const latinCaseBonus = /[a-z]/.test(password) && /[A-Z]/.test(password);
  return groups >= 3 || (groups >= 2 && latinCaseBonus);
}

function corsHeaders(origin, env) {
  const allowed = String(env.ALLOWED_ORIGINS || 'https://khaledaltheeb.github.io').split(',').map(value=>value.trim()).filter(Boolean);
  const headers = {
    'access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers':'authorization,content-type,idempotency-key,x-requested-with,x-bootstrap-key,x-recovery-export-key',
    'access-control-max-age':'86400',
    'cache-control':'no-store',
    'content-security-policy':"default-src 'none'; frame-ancestors 'none'",
    'cross-origin-resource-policy':'same-site',
    'referrer-policy':'no-referrer',
    'strict-transport-security':'max-age=31536000; includeSubDomains',
    'vary':'Origin',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY'
  };
  if (origin && allowed.includes(origin)) headers['access-control-allow-origin']=origin;
  return headers;
}

function json(payload,status=200,headers={}) {
  return new Response(JSON.stringify(payload),{status,headers:{...JSON_HEADERS,...headers}});
}
