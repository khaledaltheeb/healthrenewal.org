from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORTER_PATH = ROOT / "scripts" / "import_authorized_courses_v215.py"
spec = importlib.util.spec_from_file_location("course_network_contract_v218", IMPORTER_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


class CourseSourceNetworkContractTests(unittest.TestCase):
    def test_manifest_and_importer_lock_dns_pinning(self) -> None:
        manifest = json.loads(
            (ROOT / "content" / "integrations" / "course-sources-v215.json").read_text(
                encoding="utf-8"
            )
        )
        security = manifest["network_security"]
        self.assertEqual(manifest["policy"], "deny-by-default")
        self.assertEqual(manifest["security_contract_version"], 218)
        self.assertTrue(security["https_default_port_only"])
        self.assertTrue(security["explicit_host_allowlists"])
        self.assertTrue(security["public_dns_addresses_only"])
        self.assertTrue(security["dns_answers_pinned_during_connection"])
        self.assertTrue(security["redirect_target_checked_before_request"])
        self.assertTrue(security["environment_proxies_disabled"])

        source = IMPORTER_PATH.read_text(encoding="utf-8")
        for marker in (
            "class PinnedDnsResolver",
            "dns_answers_pinned_during_connection",
            "with resolver.active()",
            "ProxyHandler({})",
            "SafeRedirectHandler(source, resolver)",
        ):
            self.assertIn(marker, source)

    def test_security_result_contract_includes_dns_pinning(self) -> None:
        result = module.import_courses()
        self.assertEqual(result["status"], "no-approved-sources")
        self.assertTrue(result["security"]["dns_answers_pinned_during_connection"])
        self.assertTrue(result["security"]["dns_public_addresses_only"])
        self.assertTrue(result["security"]["redirects_checked_before_request"])
        self.assertTrue(result["security"]["proxies_disabled"])


if __name__ == "__main__":
    unittest.main()
