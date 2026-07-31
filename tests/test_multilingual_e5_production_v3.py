from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MultilingualE5ProductionV3Tests(unittest.TestCase):
    def test_custom_domain_is_the_corpus_source(self) -> None:
        local = (ROOT / "scripts/build_semantic_search_index.py").read_text(encoding="utf-8")
        remote = (ROOT / "scripts/build_remote_semantic_search_index.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/semantic-search-index.yml").read_text(encoding="utf-8")
        self.assertIn('BASE_URL = "https://healthrenewal.org/"', local)
        self.assertIn('DEFAULT_BASE_URL = "https://healthrenewal.org/"', remote)
        self.assertIn("normalize_site_url", remote)
        self.assertIn("https://healthrenewal.org/sitemap-index.xml", workflow)
        self.assertNotIn("--base-url https://khaledaltheeb.github.io/pterminology-site/", workflow)

    def test_model_contract_is_pinned_and_consistent(self) -> None:
        manifest = json.loads((ROOT / "ai-search/data/manifest.json").read_text(encoding="utf-8"))
        worker = (ROOT / "ai-search/assets/search-worker.js").read_text(encoding="utf-8")
        builder = (ROOT / "scripts/build_semantic_search_index.py").read_text(encoding="utf-8")
        self.assertEqual(manifest["model"], "intfloat/multilingual-e5-small")
        self.assertEqual(manifest["browserModel"], "Xenova/multilingual-e5-small")
        self.assertEqual(manifest["dimensions"], 384)
        self.assertEqual(manifest["queryPrefix"], "query: ")
        self.assertEqual(manifest["passagePrefix"], "passage: ")
        self.assertIn(manifest["modelRevision"], builder)
        self.assertIn(manifest["browserModelRevision"], worker)
        self.assertIn("normalize_embeddings=True", builder)
        self.assertIn("pooling: 'mean', normalize: true", worker)

    def test_cpu_only_build_is_enforced(self) -> None:
        workflow = (ROOT / ".github/workflows/semantic-search-index.yml").read_text(encoding="utf-8")
        requirements = (ROOT / "scripts/semantic-search-requirements.txt").read_text(encoding="utf-8")
        self.assertIn("https://download.pytorch.org/whl/cpu", workflow)
        self.assertIn("torch==2.13.0+cpu", workflow)
        self.assertIn("torch.version.cuda is None", workflow)
        self.assertIn("torch.cuda.is_available() is False", workflow)
        self.assertIn("--no-cache-dir", workflow)
        self.assertNotIn("cache: pip", workflow)
        self.assertNotIn("torch", "\n".join(
            line for line in requirements.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ).lower())
        self.assertIn("sentence-transformers==5.6.1", requirements)
        self.assertIn("transformers==5.14.1", requirements)

    def test_node_and_browser_models_are_executed_in_smoke_gate(self) -> None:
        workflow = (ROOT / ".github/workflows/semantic-search-index.yml").read_text(encoding="utf-8")
        node = (ROOT / "tests/e5_node_smoke.mjs").read_text(encoding="utf-8")
        browser = (ROOT / "tests/e5_browser_smoke.mjs").read_text(encoding="utf-8")
        self.assertIn("@huggingface/transformers@4.2.0", workflow)
        self.assertIn("playwright-core@1.61.1", workflow)
        self.assertIn("node tests/e5_node_smoke.mjs", workflow)
        self.assertIn("node tests/e5_browser_smoke.mjs", workflow)
        self.assertIn("Xenova/multilingual-e5-small", node)
        self.assertIn("761b726dd34fb83930e26aab4e9ac3899aa1fa78", node)
        self.assertIn("device: 'cpu'", node)
        self.assertIn("dtype: 'q8'", node)
        self.assertIn("@huggingface/transformers@4.2.0", browser)
        self.assertIn("runtime: 'chromium-wasm'", browser)
        self.assertIn("No WASM runtime request was observed in Chromium", browser)
        self.assertIn("report.dimensions !== 384", browser)
        self.assertIn("report.relevant > report.unrelated", browser)

    def test_generated_results_are_unique_per_page(self) -> None:
        worker = (ROOT / "ai-search/assets/search-worker.js").read_text(encoding="utf-8")
        self.assertIn("function dedupeRankedByUrl", worker)
        self.assertIn("const uniqueRanked = dedupeRankedByUrl", worker)

    def test_search_page_uses_active_canonical(self) -> None:
        page = (ROOT / "ai-search/index.html").read_text(encoding="utf-8")
        self.assertIn('rel="canonical" href="https://healthrenewal.org/ai-search/"', page)
        self.assertNotIn("khaledaltheeb.github.io/pterminology-site/ai-search/", page)


if __name__ == "__main__":
    unittest.main()
