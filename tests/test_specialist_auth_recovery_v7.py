from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class SpecialistAuthRecoveryV7Tests(unittest.TestCase):
    def test_isolated_recovery_page_is_private_and_cache_independent(self) -> None:
        html = read("specialists-partners/recover/index.html")
        script = read("specialists-partners/recover/recover.js")
        self.assertIn('noindex,nofollow,noarchive', html)
        self.assertIn('no-store, no-cache', html)
        self.assertIn('recover.js?v=7.0.0', html)
        self.assertIn('pterminology-specialist-accounts.pterminology-826ac349.workers.dev', script)
        self.assertIn('/v1/auth/password/request', script)
        self.assertIn('/v1/auth/logout', script)
        self.assertIn('password_reset', script)
        self.assertIn('sessionStorage.removeItem', script)
        self.assertIn('ptIdentitySessionV6', script)
        self.assertIn('ptAdminIdentityV6', script)
        self.assertNotIn('localStorage.setItem', script)

    def test_account_and_admin_use_recovery_route_and_versioned_assets(self) -> None:
        account = read("specialists-partners/account/index.html")
        admin = read("specialists-partners/admin/index.html")
        for text in (account, admin):
            self.assertIn('../recover/', text)
            self.assertIn('no-store, no-cache', text)
        self.assertIn('account.js?v=7.0.0', account)
        self.assertIn('v=7', account)
        self.assertIn('admin.js?v=8.0.0', admin)
        self.assertIn('runtime-config.js?v=7.0.0', account)
        self.assertIn('runtime-config.js?v=10.2.0', admin)
        self.assertIn('href="../recover/?logout=1&amp;v=7"', account)
        self.assertIn('href="../recover/?logout=1&amp;v=10.2.0"', admin)

    def test_recovery_client_has_direct_and_fallback_api_paths(self) -> None:
        script = read("specialists-partners/recover/recover.js")
        self.assertIn("const IDENTITY_API=", script)
        self.assertIn("const CORE_API=", script)
        self.assertIn("if(result.response.status===404)", script)
        self.assertIn("credentials:'omit'", script)
        self.assertIn("cache:'no-store'", script)
        self.assertIn("redirect:'error'", script)

    def test_recovery_javascript_is_valid(self) -> None:
        result = subprocess.run(
            ["node", "--check", str(ROOT / "specialists-partners/recover/recover.js")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
