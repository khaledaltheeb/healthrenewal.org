from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLIER = ROOT / "scripts" / "apply_magazine_enrichments_v202.py"
AUDITOR = ROOT / "scripts" / "audit_magazine_sources_v202.py"
REGISTRY = ROOT / "data" / "magazine-enrichments-v202-batch1.json"
DEPTH_REGISTRY = ROOT / "data" / "magazine-enrichments-v202-batch1-depth.json"
BATCH2_REGISTRY = ROOT / "data" / "magazine-enrichments-v202-batch2.json"
SOURCE = ROOT / "magazine"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


apply_mod = load_module("magazine_enrichment_apply", APPLIER)
audit_mod = load_module("magazine_enrichment_audit", AUDITOR)


class MagazineEnrichmentsV202Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.magazine = self.root / "magazine"
        self.magazine.mkdir(parents=True)
        self.registry = apply_mod.load_registry(REGISTRY)
        self.depth_registry = apply_mod.load_registry(DEPTH_REGISTRY)
        self.batch2_registry = apply_mod.load_registry(BATCH2_REGISTRY)
        self.registries = (self.registry, self.depth_registry, self.batch2_registry)

        all_records: dict[str, dict] = {}
        for registry in self.registries:
            for record in registry["records"]:
                all_records.setdefault(record["path"], record)

        self.originals: dict[str, str] = {}
        for record in all_records.values():
            rel_repo = Path(record["path"])
            rel = Path(*rel_repo.parts[1:])
            src = SOURCE / rel
            dst = self.magazine / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            self.originals[record["path"]] = src.read_text(encoding="utf-8")

        self.old_root = audit_mod.ROOT
        self.old_magazine = audit_mod.MAGAZINE
        audit_mod.ROOT = self.root
        audit_mod.MAGAZINE = self.magazine

    def tearDown(self) -> None:
        audit_mod.ROOT = self.old_root
        audit_mod.MAGAZINE = self.old_magazine
        self.tmp.cleanup()

    def _assert_registry_contract(self, registry: dict, expected_count: int) -> None:
        self.assertEqual(len(registry["records"]), expected_count)
        self.assertTrue(registry["policy"]["non_destructive"])
        self.assertTrue(registry["policy"].get("page_specific", True))
        for record in registry["records"]:
            self.assertTrue(record["source"]["url"].startswith("https://"))
            self.assertTrue(record["source"]["title"])
            self.assertTrue(record["sections"])
            keys = [section["key"] for section in record["sections"]]
            self.assertEqual(len(keys), len(set(keys)))

    def test_registries_are_source_first_and_non_destructive(self) -> None:
        self.assertEqual(self.registry["batch"], "v202-batch1")
        self.assertEqual(self.depth_registry["batch"], "v202-batch1-depth")
        self.assertEqual(self.batch2_registry["batch"], "v202-batch2")
        self._assert_registry_contract(self.registry, 10)
        self._assert_registry_contract(self.depth_registry, 2)
        self._assert_registry_contract(self.batch2_registry, 10)
        self.assertTrue(self.registry["policy"]["source_first"])
        self.assertTrue(self.depth_registry["policy"]["do_not_lower_quality_threshold"])
        self.assertTrue(self.batch2_registry["policy"]["source_first"])
        self.assertTrue(self.batch2_registry["policy"]["do_not_convert_association_to_causation"])

        batch1_paths = {record["path"] for record in self.registry["records"]}
        for record in self.depth_registry["records"]:
            self.assertIn(record["path"], batch1_paths)
        batch2_paths = {record["path"] for record in self.batch2_registry["records"]}
        self.assertTrue(batch1_paths.isdisjoint(batch2_paths))

        for registry in (self.registry, self.batch2_registry):
            for record in registry["records"]:
                keys = [section["key"] for section in record["sections"]]
                self.assertIn("rawafid_reading", keys)
                self.assertIn("not_proven", keys)

    def test_enrichment_is_additive_idempotent_and_preserves_original_prose(self) -> None:
        for registry in (self.registry, self.batch2_registry):
            report = apply_mod.apply_registry(self.magazine, registry)
            self.assertEqual(report["changed_pages"], len(registry["records"]))
            self.assertTrue(report["non_destructive"])
            marker = f'data-rawafid-enrichment="{registry["batch"]}"'

            for record in registry["records"]:
                rel_repo = Path(record["path"])
                rel = Path(*rel_repo.parts[1:])
                updated = (self.magazine / rel).read_text(encoding="utf-8")
                original = self.originals[record["path"]]
                block = apply_mod.render_record(record, registry["batch"])
                self.assertEqual(updated.count(marker), 1, record["path"])
                self.assertEqual(updated.replace(block, "", 1), original, record["path"])

            second = apply_mod.apply_registry(self.magazine, registry)
            self.assertEqual(second["changed_pages"], 0)
            self.assertTrue(all(item["status"] == "already_applied" for item in second["results"]))

    def test_batch1_pages_reach_gold_contract_after_enrichment(self) -> None:
        apply_mod.apply_registry(self.magazine, self.registry)
        apply_mod.apply_registry(self.magazine, self.depth_registry)
        failures: list[dict] = []
        for record in self.registry["records"]:
            page = audit_mod.audit_page(self.root / record["path"])
            if page.gold_contract != "complete":
                failures.append(
                    {
                        "path": record["path"],
                        "word_count": page.word_count,
                        "missing_gold_sections": page.missing_gold_sections,
                        "issues": page.issues,
                    }
                )
        self.assertEqual(failures, [], json.dumps(failures, ensure_ascii=False, indent=2))

    def test_batch2_pages_reach_gold_contract_after_enrichment(self) -> None:
        before = {
            record["path"]: audit_mod.audit_page(self.root / record["path"])
            for record in self.batch2_registry["records"]
        }
        self.assertTrue(all(item.gold_contract == "incomplete" for item in before.values()))

        apply_mod.apply_registry(self.magazine, self.batch2_registry)
        failures: list[dict] = []
        for record in self.batch2_registry["records"]:
            page = audit_mod.audit_page(self.root / record["path"])
            if page.gold_contract != "complete":
                failures.append(
                    {
                        "path": record["path"],
                        "word_count": page.word_count,
                        "missing_gold_sections": page.missing_gold_sections,
                        "issues": page.issues,
                    }
                )
        self.assertEqual(failures, [], json.dumps(failures, ensure_ascii=False, indent=2))

    def test_sources_are_rendered_as_external_verifiable_links(self) -> None:
        for registry in self.registries:
            for record in registry["records"]:
                rendered = apply_mod.render_record(record, registry["batch"])
                self.assertIn("المصدر الذي بُني عليه هذا الاستكمال", rendered)
                self.assertIn('rel="noopener noreferrer external"', rendered)
                if record["source"].get("doi"):
                    self.assertIn("https://doi.org/", rendered)
                if record["source"].get("pmid"):
                    self.assertIn("https://pubmed.ncbi.nlm.nih.gov/", rendered)


if __name__ == "__main__":
    unittest.main()
