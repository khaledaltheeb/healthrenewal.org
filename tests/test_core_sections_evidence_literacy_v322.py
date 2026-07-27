from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "scripts" / "complete_core_sections_v15.py"
CONTENT = ROOT / "content" / "v322" / "evidence-literacy-library-ar.json"


class CoreSectionsEvidenceLiteracyV322Tests(unittest.TestCase):
    def test_core_publisher_imports_and_enforces_v322(self) -> None:
        source = CORE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and node.module == "publish_evidence_literacy_library_v322"
            for alias in node.names
        }
        self.assertIn("publish", imports)
        for marker in (
            "evidence = publish_evidence_literacy(SITE)",
            'evidence.get("version") != 322',
            'evidence.get("guide_count") != 4',
            'evidence.get("minimum_guide_words", 0)) < 900',
            '"evidence_literacy_guides": evidence["guide_count"]',
            '"evidence_literacy_sources": evidence["source_count"]',
        ):
            self.assertIn(marker, source)

    def test_manifest_has_four_unique_nonduplicative_guides(self) -> None:
        payload = json.loads(CONTENT.read_text(encoding="utf-8"))
        guides = payload["guides"]
        slugs = [guide["slug"] for guide in guides]
        titles = [guide["title"] for guide in guides]
        self.assertEqual(len(guides), 4)
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(sum(len(guide["sections"]) for guide in guides), 24)
        self.assertTrue(all(len(guide["red_flags"]) == 5 for guide in guides))
        self.assertTrue(all(len(guide["action_steps"]) == 5 for guide in guides))


if __name__ == "__main__":
    unittest.main()
