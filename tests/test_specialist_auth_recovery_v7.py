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
        self.assertNotIn('localStorage.setItem', script)

    def test_account_and_admin_use_recovery_route_and_versioned_assets(self) -> None:
        account = read("specialists-partners/account/index.html")
        admin = read("specialists-partners/admin/index.html")
        for text in (account, admin):
            self.assertIn('../recover/', text)
            self.assertIn('v=7', text)
        self.assertIn('account.js?v=7.0.0', account)
        self.assertIn('admin.js?v=7.0.0', admin)
        self.assertIn('runtime-config.js?v=7.0.0', account)
        self.assertIn('runtime-config.js?v=7.0.0', admin)

    def test_core_worker_proxies_cached_identity_routes(self) -> None:
        worker = read("specialists-partners/backend/src/index-v2.js")
        workflow = read(".github/workflows/deploy-specialists-account-backend.yml")
        self.assertIn("/v1/auth/password/request", worker)
        self.assertIn("/v1/auth/logout", worker)
        self.assertIn("proxyIdentityCompatibility", worker)
        self.assertIn("IDENTITY_API_BASE", worker)
        self.assertIn('IDENTITY_API_BASE = "{os.environ[\'ACCOUNT_API_BASE\']}"', workflow)
        self.assertIn('Identity compatibility routes are present', workflow)
        self.assertIn('specialists-partners/recover/**', workflow)

    def test_logout_clears_ui_before_remote_revoke_finishes(self) -> None:
        account = read("specialists-partners/account/account.js")
        admin = read("specialists-partners/admin/admin.js")
        self.assertIn("const revoke=state.token?api('/v1/auth/logout'", account)
        self.assertLess(account.index('clearSession();showAuth()'), account.index('await revoke'))
        self.assertIn("const revoke=state.token?account('/v1/auth/logout'", admin)
        self.assertLess(admin.index('clear();showLogin()'), admin.index('await revoke'))

    def test_recovery_javascript_is_valid(self) -> None:
        for path in (
            "specialists-partners/recover/recover.js",
            "specialists-partners/account/account.js",
            "specialists-partners/admin/admin.js",
            "specialists-partners/backend/src/index-v2.js",
        ):
            result = subprocess.run(
                ["node", "--check", str(ROOT / path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
