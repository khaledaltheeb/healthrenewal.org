from pathlib import Path


def patch(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}: {old[:90]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


production = "specialists-partners/account-backend/src/index-v10-production.js"
patch(
    production,
    "  const from = String(env.FROM_EMAIL || '').trim().toLowerCase();\n  const match = from.match(/^[^\\s@]+@([^\\s@]+)$/);\n  const domain = match ? match[1].replace(/\\.$/, '') : null;",
    "  const from = String(env.FROM_EMAIL || '').trim().toLowerCase();\n  const bracketed = from.match(/<\\s*([^<>\\s]+@[^<>\\s]+)\\s*>$/);\n  const address = bracketed ? bracketed[1] : from;\n  const match = address.match(/^[^\\s@]+@([^\\s@]+)$/);\n  const domain = match ? match[1].replace(/\\.$/, '') : null;",
)
patch(
    production,
    "  const allowed = String(env.ALLOWED_ORIGINS || 'https://khaledaltheeb.github.io')\n    .split(',')\n    .map((value) => value.trim())\n    .filter(Boolean);",
    "  const allowed = new Set([\n    'https://khaledaltheeb.github.io',\n    'https://healthrenewal.org',\n    'https://www.healthrenewal.org',\n    ...String(env.ALLOWED_ORIGINS || '')\n      .split(',')\n      .map((value) => value.trim())\n      .filter(Boolean),\n  ]);",
)
patch(production, "if (origin && allowed.includes(origin))", "if (origin && allowed.has(origin))")

worker = "specialists-partners/account-backend/src/index-v10.js"
patch(worker, "return await adminManualPasswordReset(env, cors, actor, manualResetMatch[1]);", "return await adminManualPasswordReset(request, env, cors, actor, manualResetMatch[1]);")
patch(worker, "return await adminPasswordReset(env, cors, actor, resetMatch[1]);", "return await adminPasswordReset(request, env, cors, actor, resetMatch[1]);")
patch(worker, "async function adminPasswordReset(env, cors, actor, userId) {", "async function adminPasswordReset(request, env, cors, actor, userId) {")
patch(worker, "async function adminManualPasswordReset(env, cors, actor, userId) {", "async function adminManualPasswordReset(request, env, cors, actor, userId) {")
patch(worker, "const delivery = await issuePasswordReset(env,user,purpose,null,requestId,true);", "const delivery = await issuePasswordReset(env,user,purpose,null,requestId,true,passwordResetBaseForRequest(request,env));")
patch(worker, "const delivery = await issuePasswordReset(env,user,'admin_reset',actor.id,crypto.randomUUID(),true);", "const delivery = await issuePasswordReset(env,user,'admin_reset',actor.id,crypto.randomUUID(),true,passwordResetBaseForRequest(request,env));")
patch(worker, "const delivery = await issuePasswordReset(env,user,'admin_reset',actor.id,crypto.randomUUID(),false);", "const delivery = await issuePasswordReset(env,user,'admin_reset',actor.id,crypto.randomUUID(),false,passwordResetBaseForRequest(request,env));")
patch(worker, "const delivery = await issuePasswordReset(env,user,'setup',actor.id,crypto.randomUUID(),true);", "const delivery = await issuePasswordReset(env,user,'setup',actor.id,crypto.randomUUID(),true,passwordResetBaseForRequest(request,env));")
patch(worker, "const delivery = await issuePasswordReset(env,user,'setup',user.id,crypto.randomUUID(),true);", "const delivery = await issuePasswordReset(env,user,'setup',user.id,crypto.randomUUID(),true,passwordResetBaseForRequest(request,env));")
patch(worker, "async function issuePasswordReset(env, user, purpose='reset', requestedBy=null, requestId=crypto.randomUUID(), deliver=true) {", "async function issuePasswordReset(env, user, purpose='reset', requestedBy=null, requestId=crypto.randomUUID(), deliver=true, resetBaseOverride='') {")
patch(worker, "  const base = validHttpsBase(env.PASSWORD_RESET_BASE_URL);", "  const base = validHttpsBase(resetBaseOverride || env.PASSWORD_RESET_BASE_URL);")
patch(
    worker,
    "  const hosts = String(env.TURNSTILE_EXPECTED_HOSTNAMES || 'khaledaltheeb.github.io').split(',').map(v=>v.trim()).filter(Boolean);\n  const actionOk = !result.action || !allowedActions.length || allowedActions.includes(result.action);\n  if (!response.ok || result.success !== true || !hosts.includes(result.hostname) || !actionOk)",
    "  const hosts = new Set([\n    'khaledaltheeb.github.io',\n    'healthrenewal.org',\n    'www.healthrenewal.org',\n    ...String(env.TURNSTILE_EXPECTED_HOSTNAMES || '').split(',').map(v=>v.trim()).filter(Boolean),\n  ]);\n  const actionOk = !result.action || !allowedActions.length || allowedActions.includes(result.action);\n  if (!response.ok || result.success !== true || !hosts.has(result.hostname) || !actionOk)",
)
patch(
    worker,
    "function validHttpsBase(value) { try { const url=new URL(String(value || '')); if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) return ''; return url.href.replace(/\\/$/,''); } catch (_) { return ''; } }",
    "function passwordResetBaseForRequest(request,env) {\n  const origin=String(request?.headers?.get('origin')||'').replace(/\\/$/,'');\n  if(origin==='https://healthrenewal.org'||origin==='https://www.healthrenewal.org') return `${origin}/specialists-partners/password-reset/`;\n  if(origin==='https://khaledaltheeb.github.io') return 'https://khaledaltheeb.github.io/pterminology-site/specialists-partners/password-reset/';\n  return String(env.PASSWORD_RESET_BASE_URL||'');\n}\nfunction validHttpsBase(value) { try { const url=new URL(String(value || '')); if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) return ''; return url.href.replace(/\\/$/,''); } catch (_) { return ''; } }",
)

workflow = ".github/workflows/deploy-specialist-identity-v10-production.yml"
patch(workflow, 'ALLOWED_ORIGINS = "https://khaledaltheeb.github.io"', 'ALLOWED_ORIGINS = "https://khaledaltheeb.github.io,https://healthrenewal.org,https://www.healthrenewal.org"')
patch(workflow, 'TURNSTILE_EXPECTED_HOSTNAMES = "khaledaltheeb.github.io"', 'TURNSTILE_EXPECTED_HOSTNAMES = "khaledaltheeb.github.io,healthrenewal.org,www.healthrenewal.org"')
patch(
    workflow,
    "          provider=deep.get('emailProvider') or {}\n          report={",
    "          provider=deep.get('emailProvider') or {}\n          capabilities=deep.get('capabilities') or normal.get('capabilities') or {}\n          sender_ready=provider.get('senderReady') is True\n          recovery_email_ready=capabilities.get('passwordRecoveryEmail') is True\n          fully_operational=(\n              normal.get('ok') is True\n              and provider.get('authValid') is True\n              and sender_ready\n              and recovery_email_ready\n          )\n          report={",
)
patch(
    workflow,
    "            'email_provider':{'http_status':int(os.environ.get('DEEP_STATUS') or 0),'configured':provider.get('configured'),'auth_valid':provider.get('authValid'),'access':provider.get('access'),'code':provider.get('code')},",
    "            'email_provider':{'http_status':int(os.environ.get('DEEP_STATUS') or 0),'configured':provider.get('configured'),'auth_valid':provider.get('authValid'),'access':provider.get('access'),'code':provider.get('code'),'sender_ready':sender_ready,'sender_code':provider.get('senderCode'),'sender_domain':provider.get('senderDomain')},",
)
patch(
    workflow,
    "            'fully_operational':normal.get('ok') is True and provider.get('authValid') is True,",
    "            'password_recovery_email_ready':recovery_email_ready,\n            'operational_mode':'full' if fully_operational else 'manual_recovery',\n            'fully_operational':fully_operational,",
)

sender_test = "tests/specialist_sender_policy_v104_runtime.mjs"
patch(sender_test, "assert.equal(consumer.code, 'sender_not_configured');", "assert.equal(consumer.code, 'sender_domain_not_verified');\nassert.equal(consumer.domain, 'gmail.com');")

identity_test = "tests/test_specialist_identity_v10.py"
patch(identity_test, '        self.assertIn("invalid_api_key", self.worker)', '        self.assertIn("invalid_api_key", self.worker)\n        self.assertIn("healthrenewal.org", self.worker)\n        self.assertIn("passwordResetBaseForRequest", self.worker)')
patch(identity_test, '        self.assertIn("corsPreflight:true", self.production_worker)', '        self.assertIn("corsPreflight:true", self.production_worker)\n        self.assertIn("https://healthrenewal.org", self.production_worker)\n        self.assertIn("allowed.has(origin)", self.production_worker)')
patch(identity_test, '        self.assertIn("specialist-identity-v10-production.json", production)', '        self.assertIn("specialist-identity-v10-production.json", production)\n        self.assertIn("healthrenewal.org", production)\n        self.assertIn("sender_ready", production)\n        self.assertIn("operational_mode", production)')

turnstile_test = "tests/test_specialist_turnstile_persistence.py"
patch(turnstile_test, '        self.assertNotIn("secret put TURNSTILE_SECRET", self.workflow)', '        self.assertNotIn("secret put TURNSTILE_SECRET", self.workflow)\n        self.assertIn("healthrenewal.org", self.workflow)\n        self.assertIn("TURNSTILE_EXPECTED_HOSTNAMES", self.workflow)\n        self.assertIn("sender_ready", self.workflow)\n        self.assertIn("fully_operational", self.workflow)')
