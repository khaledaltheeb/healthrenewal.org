from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_required(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Required setup-hardening marker not found in {path}: {old[:180]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    worker = ROOT / "specialists-partners" / "account-backend" / "src" / "index.js"
    account = ROOT / "specialists-partners" / "account" / "account.js"
    tests = ROOT / "tests" / "test_specialist_identity_v6.py"

    replace_required(
        worker,
        "  const token=await env.DB.prepare(`SELECT t.id AS reset_token_id,t.user_id,t.token_hash,t.purpose,t.expires_at,u.provider_id FROM password_reset_tokens t JOIN identity_users u ON u.id=t.user_id WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>? LIMIT 1`).bind(hash,now).first();",
        "  const token=await env.DB.prepare(`SELECT t.id AS reset_token_id,t.user_id,t.token_hash,t.purpose,t.expires_at,u.provider_id,u.status AS user_status FROM password_reset_tokens t JOIN identity_users u ON u.id=t.user_id WHERE t.token_hash=? AND t.used_at IS NULL AND t.expires_at>? LIMIT 1`).bind(hash,now).first();",
    )
    replace_required(
        worker,
        "    env.DB.prepare(`UPDATE identity_users SET password_hash=?,password_salt=?,password_iterations=?,password_set_at=?,must_change_password=0,status='active',email_verified_at=COALESCE(email_verified_at,?),failed_login_count=0,locked_until=NULL,updated_at=? WHERE id=?`).bind(rec.hash,rec.salt,rec.iterations,now,now,now,token.user_id),",
        "    env.DB.prepare(`UPDATE identity_users SET password_hash=?,password_salt=?,password_iterations=?,password_set_at=?,must_change_password=0,status=CASE WHEN status='invited' THEN 'active' ELSE status END,email_verified_at=COALESCE(email_verified_at,?),failed_login_count=0,locked_until=NULL,updated_at=? WHERE id=?`).bind(rec.hash,rec.salt,rec.iterations,now,now,now,token.user_id),",
    )
    replace_required(
        worker,
        "  const body=await parseJson(request); const current=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(actor.id).first();\n"
        "  if(!(await verifyPassword(body.currentPassword,current,env))) fail('كلمة المرور الحالية غير صحيحة.',401,'invalid_current_password');\n",
        "  const body=await parseJson(request); const current=await env.DB.prepare(`SELECT * FROM identity_users WHERE id=?`).bind(actor.id).first();\n"
        "  const requiresSetup=!current.password_hash||Number(current.must_change_password)===1;\n"
        "  if(!requiresSetup&&!(await verifyPassword(body.currentPassword,current,env))) fail('كلمة المرور الحالية غير صحيحة.',401,'invalid_current_password');\n",
    )
    replace_required(
        worker,
        "  await env.DB.prepare(`UPDATE identity_users SET display_name_ar=?,display_name_en=?,phone_e164=?,email_notifications=?,new_message_notifications=?,updated_at=? WHERE id=?`).bind(nameAr,nameEn,phone,emailNotifications,newMessageNotifications,now,actor.id).run();",
        "  const phoneChanged=(phone||null)!==(actor.phone_e164||null);\n"
        "  await env.DB.prepare(`UPDATE identity_users SET display_name_ar=?,display_name_en=?,phone_e164=?,phone_verified_at=CASE WHEN ?=1 THEN NULL ELSE phone_verified_at END,email_notifications=?,new_message_notifications=?,updated_at=? WHERE id=?`).bind(nameAr,nameEn,phone,phoneChanged?1:0,emailNotifications,newMessageNotifications,now,actor.id).run();",
    )
    replace_required(
        worker,
        "let user=await env.DB.prepare(`SELECT * FROM identity_users WHERE provider_id=? OR lower(email)=lower(?) LIMIT 1`).bind(row.provider_id,row.email).first();if(!user){",
        "let user=await env.DB.prepare(`SELECT * FROM identity_users WHERE provider_id=? OR lower(email)=lower(?) LIMIT 1`).bind(row.provider_id,row.email).first();if(user&&!['active','invited'].includes(user.status))fail('الحساب غير نشط.',403,'account_inactive');if(!user){",
    )

    replace_required(
        account,
        "$('settings-message-notifications').checked=user.newMessageNotifications;$('kpi-verification').textContent=provider?label(provider.verificationStatus):'غير مرتبط';",
        "$('settings-message-notifications').checked=user.newMessageNotifications;const current=$('current-password');current.required=!user.mustChangePassword;current.placeholder=user.mustChangePassword?'غير مطلوبة عند تهيئة الحساب':'';const currentLabel=document.querySelector('label[for=\"current-password\"]');if(currentLabel)currentLabel.textContent=user.mustChangePassword?'كلمة المرور الحالية — غير مطلوبة للتهيئة':'كلمة المرور الحالية';$('kpi-verification').textContent=provider?label(provider.verificationStatus):'غير مرتبط';",
    )

    replace_required(
        tests,
        '        self.assertIn("login_token_used", worker)\n',
        '        self.assertIn("login_token_used", worker)\n'
        '        self.assertIn("requiresSetup", worker)\n'
        '        self.assertIn("status=CASE WHEN status=\'invited\' THEN \'active\' ELSE status END", worker)\n'
        '        self.assertIn("phone_verified_at=CASE WHEN ?=1 THEN NULL", worker)\n',
    )
    replace_required(
        tests,
        '        self.assertIn("سجل المحادثات", account_html)\n',
        '        self.assertIn("سجل المحادثات", account_html)\n'
        '        self.assertIn("current.required=!user.mustChangePassword", account_js)\n',
    )

    Path(__file__).unlink()
    print("Specialist identity v6 setup and account-state hardening applied.")


if __name__ == "__main__":
    main()
