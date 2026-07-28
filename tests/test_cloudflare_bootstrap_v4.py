from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "bootstrap-specialists-cloudflare.yml"
DOCS = ROOT / "specialists-partners" / "backend" / "CLOUDFLARE_BOOTSTRAP.md"


class CloudflareBootstrapV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.docs = DOCS.read_text(encoding="utf-8")

    def test_workflow_has_manual_dispatch_and_scoped_account(self) -> None:
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn('default: "826ac34927c1e045c06145a327c2ac52"', self.workflow)
        self.assertIn("secrets.CLOUDFLARE_API_TOKEN", self.workflow)

    def test_workflow_provisions_required_cloudflare_resources(self) -> None:
        required_markers = (
            "/tokens/verify",
            "/d1/database",
            "/challenges/widgets",
            "/rotate_secret",
            "/workers/subdomain",
            "d1 migrations apply",
            "wrangler@4 deploy",
            "/health",
            "runtime-config.js",
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.workflow)

    def test_secret_material_is_not_committed(self) -> None:
        combined = self.workflow + "\n" + self.docs
        credential_patterns = (
            re.compile(r"\bcfat_[A-Za-z0-9_-]{20,}\b"),
            re.compile(r"\bcfut_[A-Za-z0-9_-]{20,}\b"),
            re.compile(r"\bre_[A-Za-z0-9]{16,}\b"),
            re.compile(r"0x4[A-Za-z0-9_-]{20,}"),
        )
        for pattern in credential_patterns:
            with self.subTest(pattern=pattern.pattern):
                self.assertIsNone(pattern.search(combined))
        self.assertNotIn("inputs.cloudflare_api_token", self.workflow.lower())

    def test_temporary_secret_files_are_removed(self) -> None:
        self.assertIn("rm -f worker-secrets.json wrangler.toml", self.workflow)
        self.assertIn("::add-mask::", self.workflow)

    def test_documented_permissions_follow_least_privilege(self) -> None:
        for permission in ("Workers Scripts", "D1", "Turnstile Sites"):
            self.assertIn(permission, self.docs)
        for prohibited in ("Billing", "Account Members", "API Tokens Edit"):
            self.assertIn(prohibited, self.docs)


if __name__ == "__main__":
    unittest.main()
