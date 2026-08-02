from __future__ import annotations

import base64
import hashlib
import json
import re
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTOR = ROOT / "specialists-partners"
CORE = SECTOR / "assets" / "directory-core.js"
STATIC_AUDITOR = ROOT / "scripts" / "audit_specialists_partners_v354.py"
LIVE_AUDITOR = ROOT / "scripts" / "audit_specialist_sector_e2e_v10.py"
LIVE_WORKFLOW = ROOT / ".github" / "workflows" / "audit-specialist-sector-e2e-v9.yml"


class SpecialistsPartnersQualityV354Tests(unittest.TestCase):
    def test_directory_core_normalizes_filters_and_sorts_deterministically(self) -> None:
        program = r"""
        const core = require(process.argv[1]);
        const provider = (id, name, accepting, verifiedAt, age, specialties) => ({
          id,
          displayName: name,
          entityType: 'professional',
          publicationStatus: 'published',
          verification: {status: 'verified', lastVerifiedAt: verifiedAt},
          consent: {publicProfileApproved: true},
          communication: {enabled: true, acceptsNewRequests: accepting},
          availability: {status: accepting ? 'available' : 'unavailable'},
          ageGroups: age,
          specialties,
          serviceModes: ['عن بعد'],
          languages: ['العربية'],
          location: {country: 'الأردن', city: 'عمّان'}
        });
        const records = [
          provider('a', 'زيد', true, '2026-01-01', ['الأطفال'], ['speech_language']),
          provider('b', 'أحمد', false, '2026-07-01', ['الأطفال'], ['psychology']),
          provider('c', 'بشار', true, '2026-02-01', ['جميع الأعمار'], ['psychology']),
          {...provider('d', 'غير منشور', true, '2026-07-30', ['الأطفال'], ['psychology']), publicationStatus: 'draft'}
        ];
        const prepared = core.prepareProviders(records);
        const filtered = core.filterProviders(prepared, {
          specialtyAny: ['psychology', 'speech_language'],
          age: 'الأطفال',
          country: 'الاردن',
          verifiedOnly: true
        });
        process.stdout.write(JSON.stringify({
          normalized: core.normalizeArabic('إِعَاقَة'),
          sameCountry: core.same('الأُرْدُن', 'الاردن'),
          allAges: core.ageMatches(['جميع الأعمار'], 'الأطفال'),
          order: prepared.map(item => item.id),
          filtered: filtered.map(item => item.id)
        }));
        """
        completed = subprocess.run(
            ["node", "-e", program, str(CORE)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["normalized"], "اعاقة")
        self.assertTrue(result["sameCountry"])
        self.assertTrue(result["allAges"])
        self.assertEqual(result["order"], ["c", "a", "b"])
        self.assertEqual(result["filtered"], ["c", "a", "b"])

    def test_directory_exposes_truthful_state_and_decision_quality_content(self) -> None:
        page = (SECTOR / "index.html").read_text(encoding="utf-8")
        for marker in (
            'data-specialists-quality-v354="1"',
            'id="directory-health"',
            'id="directory-source"',
            'id="directory-updated"',
            'id="directory-filter-context"',
            'id="provider-empty-detail"',
            "لا توجد ملفات مهنية منشورة حاليًا",
            "لا نعرض أسماء تجريبية",
            "ستة أسئلة قبل حجز الخدمة",
            "مرجعيات المنهج",
            "https://www.who.int/publications/i/item/9789240025707",
            "https://www.hcpc-uk.org/standards/standards-of-conduct-performance-and-ethics/",
            "https://www.asha.org/policy/code-of-ethics/",
        ):
            self.assertIn(marker, page)
        self.assertEqual(page.count('class="quality-question"'), 6)
        self.assertLess(
            page.index("assets/directory-core.js?v=4.1.0"),
            page.index("assets/sector.js?v=4.1.0"),
        )

    def test_all_interfaces_use_allowlisted_csp_and_block_embedding(self) -> None:
        pages = (
            SECTOR / "index.html",
            SECTOR / "join.html",
            SECTOR / "contact.html",
            SECTOR / "verification.html",
            SECTOR / "portal" / "index.html",
            SECTOR / "account" / "index.html",
            SECTOR / "admin" / "index.html",
            SECTOR / "recover" / "index.html",
            SECTOR / "password-reset" / "index.html",
        )
        for path in pages:
            text = path.read_text(encoding="utf-8")
            match = re.search(
                r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"',
                text,
            )
            self.assertIsNotNone(match, path)
            policy = match.group(1)
            connect = next(
                (
                    item.strip().split()[1:]
                    for item in policy.split(";")
                    if item.strip().startswith("connect-src ")
                ),
                [],
            )
            self.assertNotIn("https:", connect, path)
            self.assertIn("frame-ancestors 'none'", policy, path)
            self.assertIn("base-uri 'none'", policy, path)
            self.assertIn("upgrade-insecure-requests", policy, path)
            self.assertIn(
                "'sha256-BvSDsrK+y6wytL+FTl8l8mf29w+riVmJMj7HpNbYEH0='",
                policy,
                path,
            )

    def test_csp_hash_matches_production_service_worker_registration(self) -> None:
        scripts_path = str(ROOT / "scripts")
        sys.path.insert(0, scripts_path)
        try:
            namespace = runpy.run_path(
                str(ROOT / "scripts" / "finalize_pwa_v14.py"),
                run_name="specialists_pwa_hash_contract",
            )
        finally:
            sys.path.remove(scripts_path)
        registration = namespace["REGISTRATION"]
        match = re.search(r"<script[^>]*>([\s\S]*)</script>", registration)
        self.assertIsNotNone(match)
        digest = base64.b64encode(
            hashlib.sha256(match.group(1).encode("utf-8")).digest()
        ).decode("ascii")
        self.assertEqual(
            digest,
            "BvSDsrK+y6wytL+FTl8l8mf29w+riVmJMj7HpNbYEH0=",
        )

    def test_live_audit_is_read_only_and_checks_current_contracts(self) -> None:
        script = LIVE_AUDITOR.read_text(encoding="utf-8")
        workflow = LIVE_WORKFLOW.read_text(encoding="utf-8")
        combined = script + "\n" + workflow
        for forbidden in (
            "owner-password-reset",
            "providerMessageId",
            "contents: write",
            "git push",
            'method="POST"',
            "-X POST",
        ):
            self.assertNotIn(forbidden, combined)
        for required in (
            'EXPECTED_IDENTITY_VERSION = "10.2.0"',
            "/health?deep=1",
            'method="OPTIONS"',
            'id="onboarding-form"',
            'id="contact-form"',
            "audit_specialist_sector_e2e_v10.py",
            "SPECIALISTS_ADMIN_API_KEY",
            "upload-artifact@v4",
        ):
            self.assertIn(required, combined)

    def test_static_audit_passes_complete_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "quality.json"
            completed = subprocess.run(
                [
                    "python",
                    str(STATIC_AUDITOR),
                    str(ROOT),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["version"], 354)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["interfaceCount"], 9)
        self.assertEqual(report["indexableInterfaceCount"], 3)
        self.assertEqual(report["privateInterfaceCount"], 6)
        self.assertEqual(report["qualityQuestions"], 6)
        self.assertEqual(report["unsafePublishedProviderIds"], [])


if __name__ == "__main__":
    unittest.main()
