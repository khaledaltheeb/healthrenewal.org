from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "setup-specialists-cloudflare.ps1"
LAUNCHER = ROOT / "scripts" / "setup-specialists-cloudflare.cmd"


class SecureBootstrapHelperV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.launcher = LAUNCHER.read_text(encoding="utf-8")

    def test_expected_secure_prompts_and_secret_names_exist(self):
        for token in (
            "Read-Host -Prompt $Prompt -AsSecureString",
            "CLOUDFLARE_API_TOKEN",
            "RESEND_API_KEY",
            "SPECIALISTS_ADMIN_API_KEY",
            "SPECIALISTS_RATE_LIMIT_SALT",
            "SPECIALISTS_FROM_EMAIL",
        ):
            self.assertIn(token, self.script)

    def test_values_are_piped_to_gh_secret_set(self):
        self.assertIn("$Value | & gh secret set $Name --repo $Repository", self.script)
        self.assertNotIn("gh secret set $Name --body", self.script)

    def test_random_values_and_encrypted_local_admin_credential(self):
        self.assertIn("RandomNumberGenerator", self.script)
        self.assertIn("Export-Clixml", self.script)
        self.assertIn("specialists-admin-key.clixml", self.script)
        self.assertNotIn("Set-Content", self.script)

    def test_workflow_is_dispatched_and_watched(self):
        self.assertIn('gh workflow run "bootstrap-specialists-cloudflare.yml"', self.script)
        self.assertIn("gh run watch", self.script)
        self.assertIn("--exit-status", self.script)

    def test_windows_powershell_51_encoding_compatibility(self):
        self.assertTrue(self.script.isascii())
        for mojibake_marker in ("Ø", "Ù", "Ã", "Â"):
            self.assertNotIn(mojibake_marker, self.script)

    def test_no_literal_credentials(self):
        forbidden = (
            re.compile(r"cfat_[A-Za-z0-9_-]{20,}"),
            re.compile(r"re_[A-Za-z0-9_-]{20,}"),
            re.compile(r"Bearer\s+[A-Za-z0-9_-]{30,}"),
        )
        combined = self.script + "\n" + self.launcher
        for pattern in forbidden:
            self.assertIsNone(pattern.search(combined))

    def test_launcher_uses_powershell_without_embedding_values(self):
        self.assertIn("setup-specialists-cloudflare.ps1", self.launcher)
        self.assertIn("ExecutionPolicy Bypass", self.launcher)


if __name__ == "__main__":
    unittest.main()
