from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing expected marker in {relative}: {old[:120]!r}")
    if text.count(old) != 1:
        raise SystemExit(f"expected one marker in {relative}, found {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing expected marker in {relative}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


# Ensure the new recovery area triggers identity deployment and validation.
workflow = ".github/workflows/deploy-specialists-account-backend.yml"
replace_once(
    workflow,
    '      - "specialists-partners/admin/**"\n      - "specialists-partners/account-backend/**"',
    '      - "specialists-partners/admin/**"\n      - "specialists-partners/recover/**"\n      - "specialists-partners/account-backend/**"',
)
replace_once(
    workflow,
    '      - "specialists-partners/admin/**"\n      - "specialists-partners/account-backend/**"',
    '      - "specialists-partners/admin/**"\n      - "specialists-partners/recover/**"\n      - "specialists-partners/account-backend/**"',
)
replace_once(
    workflow,
    '          ALLOWED_ORIGINS = "https://khaledaltheeb.github.io"\n          OWNER_EMAIL = "pterminology@gmail.com"',
    '          ALLOWED_ORIGINS = "https://khaledaltheeb.github.io"\n          IDENTITY_API_BASE = "{os.environ[\'ACCOUNT_API_BASE\']}"\n          OWNER_EMAIL = "pterminology@gmail.com"',
)
replace_once(
    workflow,
    '          echo "Application route is present (expected validation response HTTP ${route_code})."',
    '''          echo "Application route is present (expected validation response HTTP ${route_code})."
          reset_code="$(curl -sS -o /tmp/reset-compat.json -w '%{http_code}' -X POST -H 'content-type: application/json' --data '{}' "${CORE_API_BASE}/v1/auth/password/request")"
          logout_code="$(curl -sS -o /tmp/logout-compat.json -w '%{http_code}' -X POST -H 'content-type: application/json' --data '{}' "${CORE_API_BASE}/v1/auth/logout")"
          if [[ "$reset_code" == "404" || "$logout_code" == "404" ]]; then
            echo "::error::Identity compatibility routes are missing on the core Worker"
            exit 1
          fi
          echo "Identity compatibility routes are present (reset=${reset_code}, logout=${logout_code})."''',
)

# Add compatibility routes to the core Worker so cached clients cannot receive 404.
core = "specialists-partners/backend/src/index-v2.js"
replace_once(
    core,
    """      if (request.method === 'GET' && url.pathname === '/health') {
        return await health(env, cors);
      }

""",
    """      if (request.method === 'GET' && url.pathname === '/health') {
        return await health(env, cors);
      }

      if (request.method === 'POST' && (url.pathname === '/v1/auth/password/request' || url.pathname === '/v1/auth/logout')) {
        return await proxyIdentityCompatibility(request, env, cors, url.pathname);
      }

""",
)
replace_once(
    core,
    "\nfunction corsHeaders(origin, env) {",
    """
async function proxyIdentityCompatibility(request, env, cors, pathname) {
  const base = String(env.IDENTITY_API_BASE || '').replace(/\/+$/, '');
  if (!base) fail('خدمة الحسابات غير مربوطة.', 503, 'identity_service_unavailable');
  const headers = new Headers();
  for (const name of ['content-type', 'authorization', 'x-requested-with', 'origin']) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  headers.set('accept', 'application/json');
  headers.set('x-requested-with', headers.get('x-requested-with') || 'pterminology-core-identity-compat-v7');
  const body = await request.text();
  const response = await fetch(`${base}${pathname}`, {
    method: 'POST', headers, body, redirect: 'manual'
  });
  const responseHeaders = {
    ...cors,
    'content-type': response.headers.get('content-type') || 'application/json; charset=utf-8',
    'cache-control': 'no-store'
  };
  return new Response(await response.text(), {status: response.status, headers: responseHeaders});
}

function corsHeaders(origin, env) {""",
)

# Make password recovery and logout independent of stale JavaScript state.
account_html = "specialists-partners/account/index.html"
replace_all(account_html, "account.css?v=6.0.0", "account.css?v=7.0.0")
replace_all(account_html, "runtime-config.js?v=6.0.0", "runtime-config.js?v=7.0.0")
replace_all(account_html, "account.js?v=6.0.0", "account.js?v=7.0.0")
replace_once(
    account_html,
    '<button class="button secondary" id="forgot-submit" type="submit">إرسال رابط الاستعادة</button>',
    '<a class="button secondary" id="forgot-submit" href="../recover/?v=7">إرسال رابط الاستعادة</a>',
)
replace_once(
    account_html,
    '<button class="button danger" id="logout" type="button">تسجيل الخروج</button>',
    '<a class="button danger" id="logout" href="../recover/?logout=1&amp;v=7">تسجيل الخروج</a>',
)
replace_once(
    account_html,
    '<button class="button primary" type="submit">تغيير كلمة المرور</button></form>',
    '<div class="actions"><button class="button primary" type="submit">تغيير كلمة المرور</button><a class="button secondary" href="../recover/?v=7">نسيت كلمة المرور</a></div></form>',
)

admin_html = "specialists-partners/admin/index.html"
replace_all(admin_html, "admin.css?v=6.0.1", "admin.css?v=7.0.0")
replace_all(admin_html, "runtime-config.js?v=6.0.1", "runtime-config.js?v=7.0.0")
replace_all(admin_html, "admin.js?v=6.0.1", "admin.js?v=7.0.0")
replace_once(
    admin_html,
    '<button class="button secondary" id="admin-forgot" type="button">إرسال رابط إعادة التعيين</button>',
    '<a class="button secondary" id="admin-forgot" href="../recover/?v=7">إرسال رابط إعادة التعيين</a>',
)
replace_once(
    admin_html,
    '<button class="button danger" id="admin-logout" type="button">تسجيل الخروج</button>',
    '<a class="button danger" id="admin-logout" href="../recover/?logout=1&amp;v=7">تسجيل الخروج</a>',
)

account_js = "specialists-partners/account/account.js"
replace_once(
    account_js,
    "function clearSession(){state.token='';state.expiresAt='';state.me=null;state.conversations=[];state.active=null;sessionStorage.removeItem(SESSION_KEY);}",
    "function clearSession(){state.token='';state.expiresAt='';state.me=null;state.conversations=[];state.active=null;for(const key of [SESSION_KEY,'ptAdminIdentityV6','ptSpecialistAccountSessionV5','ptSpecialistSessionV5','ptSpecialistSession'])sessionStorage.removeItem(key);}",
)
replace_once(
    account_js,
    "async function logout(){try{await api('/v1/auth/logout',{method:'POST',body:'{}'});}catch(_){}clearSession();showAuth();status('تم تسجيل الخروج.','success');}",
    "async function logout(){const revoke=state.token?api('/v1/auth/logout',{method:'POST',body:'{}'}):Promise.resolve();clearSession();showAuth();status('تم تسجيل الخروج محليًا.','success');try{await revoke;}catch(_){} }",
)

admin_js = "specialists-partners/admin/admin.js"
replace_once(
    admin_js,
    "function clear(){state.token='';state.expiresAt='';state.user=null;state.coreToken='';state.coreExpiresAt='';sessionStorage.removeItem(SESSION_KEY);}",
    "function clear(){state.token='';state.expiresAt='';state.user=null;state.coreToken='';state.coreExpiresAt='';for(const key of [SESSION_KEY,'ptIdentitySessionV6','ptSpecialistAccountSessionV5','ptSpecialistSessionV5','ptSpecialistSession'])sessionStorage.removeItem(key);}",
)
replace_once(
    admin_js,
    "async function logout(){try{await account('/v1/auth/logout',{method:'POST',body:'{}'});}catch(_){}clear();showLogin();setStatus('تم تسجيل الخروج.','success');}",
    "async function logout(){const revoke=state.token?account('/v1/auth/logout',{method:'POST',body:'{}'}):Promise.resolve();clear();showLogin();setStatus('تم تسجيل الخروج محليًا.','success');try{await revoke;}catch(_){} }",
)

print("specialist auth recovery v7 materialized")
