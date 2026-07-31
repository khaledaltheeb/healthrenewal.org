from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "specialists-partners/password-reset/index.html"
JS = ROOT / "specialists-partners/password-reset/reset-v9.js"
WORKFLOW = ROOT / ".github/workflows/issue-owner-password-reset-v8.yml"


class PasswordResetV9Tests(unittest.TestCase):
    def test_isolated_page_exists_and_is_not_indexed(self):
        html = HTML.read_text(encoding="utf-8")
        self.assertIn('noindex,nofollow,noarchive', html)
        self.assertEqual(html.count('rel="canonical"'), 1)
        self.assertIn(
            'href="https://healthrenewal.org/specialists-partners/password-reset/"',
            html,
        )
        self.assertIn('reset-v9.js?v=9.0.0', html)
        self.assertNotIn('runtime-config.js', html)
        self.assertNotIn('admin.js', html)

    def test_client_calls_identity_worker_directly(self):
        js = JS.read_text(encoding="utf-8")
        self.assertIn('https://pterminology-specialist-accounts.pterminology-826ac349.workers.dev', js)
        self.assertIn("/v1/auth/password/reset", js)
        self.assertIn("pterminology-password-reset-v9", js)
        self.assertNotIn("PT_SPECIALIST_CONFIG", js)

    def test_issuance_targets_isolated_page(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            "RESET_PAGE: https://healthrenewal.org/"
            "specialists-partners/password-reset/",
            workflow,
        )
        self.assertIn("link=os.environ['RESET_PAGE']+'?v=9#resetToken='+raw", workflow)
        self.assertNotIn('/specialists-partners/admin/?v=8#resetToken=', workflow)


if __name__ == "__main__":
    unittest.main()
