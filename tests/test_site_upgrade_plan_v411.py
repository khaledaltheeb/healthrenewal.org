from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("site_upgrade_plan_v411", ROOT / "scripts/build_site_upgrade_plan_v411.py")
assert SPEC and SPEC.loader
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


class TestSiteUpgradePlanV411(unittest.TestCase):
    def test_clinical_safety_blocks_publication(self):
        report = {
            "version": 415,
            "upgrade_queue": [{
                "path": "care-guides/cancer/index.html", "route": "care-guides/cancer/", "title": "سرطان الأطفال",
                "h1": "سرطان الأطفال", "score": 40, "priority": 90, "risk": "high",
                "findings": ["high_risk_without_authoritative_source", "thin_content"],
            }], "research_dossiers": [],
        }
        item = planner.build(report)["items"][0]
        self.assertEqual(item["wave"], "wave-0-clinical-safety")
        self.assertEqual(item["gate"], "blocked-specialist-review")
        self.assertTrue(item["actions"]["specialist_review"])

    def test_safe_metadata_is_not_misclassified_as_editorial(self):
        actions = planner.classify(["missing_lang", "missing_rtl", "missing_title", "canonical_count_not_one"])
        self.assertEqual(len(actions["safe_autofix"]), 4)
        self.assertFalse(actions["editorial_research"])
        self.assertFalse(actions["specialist_review"])

    def test_research_candidates_unlock_verification_gate(self):
        report = {
            "version": 415,
            "upgrade_queue": [{
                "path": "psychology/example/index.html", "route": "psychology/example/", "title": "مثال", "h1": "مثال",
                "score": 70, "priority": 30, "risk": "standard", "findings": ["thin_content", "no_authoritative_source"],
            }],
            "research_dossiers": [{
                "path": "psychology/example/index.html", "query": "psychology example",
                "providers": {"pubmed": [{"pmid": "1"}], "crossref": [{"doi": "10/x"}]},
                "official_targets": ["site:who.int psychology example"],
            }],
        }
        item = planner.build(report)["items"][0]
        self.assertEqual(item["gate"], "evidence-candidates-ready-for-verification")
        self.assertEqual(item["research"]["candidate_count"], 2)

    def test_no_findings_is_not_counted_as_safe_autofix(self):
        report = {"version": 415, "research_dossiers": [], "upgrade_queue": [{
            "path": "healthy/index.html", "route": "healthy/", "title": "Healthy", "h1": "Healthy",
            "score": 100, "priority": 0, "risk": "standard", "findings": [],
        }]}
        plan = planner.build(report)
        self.assertEqual(plan["items"][0]["gate"], "no-action-required")
        self.assertEqual(plan["summary"]["ready_for_safe_autofix"], 0)
        self.assertEqual(plan["summary"]["no_action_required"], 1)

    def test_safe_findings_are_counted_only_when_present(self):
        report = {"version": 415, "research_dossiers": [], "upgrade_queue": [{
            "path": "page/index.html", "route": "page/", "title": "Page", "h1": "Page",
            "score": 90, "priority": 10, "risk": "standard", "findings": ["canonical_count_not_one"],
        }]}
        plan = planner.build(report)
        self.assertEqual(plan["items"][0]["gate"], "ready-for-safe-autofix")
        self.assertEqual(plan["summary"]["ready_for_safe_autofix"], 1)
        self.assertEqual(plan["summary"]["no_action_required"], 0)


if __name__ == "__main__":
    unittest.main()
