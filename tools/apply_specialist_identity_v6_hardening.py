from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Required hardening marker not found in {path}: {old[:180]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    worker = ROOT / "specialists-partners" / "account-backend" / "src" / "index.js"
    tests = ROOT / "tests" / "test_specialist_identity_v6.py"

    replace_required(
        worker,
        "  const token=await env.DB.prepare(`SELECT t.*,u.* FROM password_reset_tokens t JOIN identity_users u ON u.id=t.user_id WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>? LIMIT 1`).bind(hash,now).first();\n"
        "  if(!token || !constantTimeEqual(hash,token.token_hash)) fail('رابط إعادة التعيين غير صالح أو انتهت صلاحيته.',401,'invalid_reset_token');\n"
        "  const rec=await createPasswordRecord(body.password,env);\n"
        "  const consumed=await env.DB.prepare(`UPDATE password_reset_tokens SET used_at=? WHERE id=? AND used_at IS NULL`).bind(now,token.id).run();\n",
        "  const token=await env.DB.prepare(`SELECT t.id AS reset_token_id,t.user_id,t.token_hash,t.purpose,t.expires_at,u.provider_id FROM password_reset_tokens t JOIN identity_users u ON u.id=t.user_id WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>? LIMIT 1`).bind(hash,now).first();\n"
        "  if(!token || !constantTimeEqual(hash,token.token_hash)) fail('رابط إعادة التعيين غير صالح أو انتهت صلاحيته.',401,'invalid_reset_token');\n"
        "  const rec=await createPasswordRecord(body.password,env);\n"
        "  const consumed=await env.DB.prepare(`UPDATE password_reset_tokens SET used_at=? WHERE id=? AND used_at IS NULL`).bind(now,token.reset_token_id).run();\n",
    )

    replace_required(
        worker,
        "async function createCoreSession(env,cors,actor){requireRole(actor,['owner','admin','reviewer','moderator']);if(!env.CORE_API_BASE||!env.ADMIN_API_KEY)fail('خدمة الإدارة الأساسية غير مربوطة.',503,'core_admin_unavailable');const response=await fetch(`${String(env.CORE_API_BASE).replace(/\\/$/,'')}/v1/admin/session`,{method:'POST',headers:{'content-type':'application/json','x-admin-key':env.ADMIN_API_KEY,'x-requested-with':'pterminology-identity-bridge'},body:JSON.stringify({actorLabel:actor.display_name_ar})});const data=await response.json().catch(()=>({}));if(!response.ok)fail(data.message||'تعذر فتح جلسة الإدارة الأساسية.',response.status||502,'core_session_failed');return json(data,200,cors);}\n",
        "async function createCoreSession(env,cors,actor){requireRole(actor,['owner','admin','reviewer','moderator']);const credential=(actor.role==='owner'||actor.role==='admin')?env.ADMIN_API_KEY:actor.role==='reviewer'?env.REVIEWER_API_KEY:env.MODERATOR_API_KEY;if(!env.CORE_API_BASE||!credential)fail('خدمة الإدارة الأساسية غير مربوطة لهذا الدور.',503,'core_admin_unavailable');const response=await fetch(`${String(env.CORE_API_BASE).replace(/\\/$/,'')}/v1/admin/session`,{method:'POST',headers:{'content-type':'application/json','x-admin-key':credential,'x-requested-with':'pterminology-identity-bridge'},body:JSON.stringify({actorLabel:actor.display_name_ar})});const data=await response.json().catch(()=>({}));if(!response.ok)fail(data.message||'تعذر فتح جلسة الإدارة الأساسية.',response.status||502,'core_session_failed');return json(data,200,cors);}\n",
    )

    replace_required(
        worker,
        "await env.DB.prepare(`UPDATE specialist_login_tokens SET used_at=? WHERE id=?`).bind(now,row.id).run();let user=",
        "const consumed=await env.DB.prepare(`UPDATE specialist_login_tokens SET used_at=? WHERE id=? AND used_at IS NULL AND expires_at>?`).bind(now,row.id,now).run();if(Number(consumed?.meta?.changes||0)!==1)fail('استُخدم رابط الدخول مسبقًا.',409,'login_token_used');let user=",
    )

    replace_required(
        tests,
        '        self.assertIn("display_name_en", worker)\n',
        '        self.assertIn("display_name_en", worker)\n'
        '        self.assertIn("reset_token_id", worker)\n'
        '        self.assertIn("actor.role===\'reviewer\'?env.REVIEWER_API_KEY", worker)\n'
        '        self.assertIn("env.MODERATOR_API_KEY", worker)\n'
        '        self.assertIn("login_token_used", worker)\n',
    )

    Path(__file__).unlink()
    print("Specialist identity v6 security hardening applied.")


if __name__ == "__main__":
    main()
