from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_sitemap_index_v304_core as sitemap_core
import materialize_addiction_condition_guides_v2 as guides


def _hashes(root: Path) -> dict[str, str]:
    return {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in guides.AUTHORITATIVE_EXISTING_ROUTES
    }


def _copy_fixture(destination: Path) -> None:
    shutil.copytree(ROOT / "addiction", destination / "addiction")
    for relative in ("sitemap-addiction.xml", "sitemap-index.xml"):
        shutil.copy2(ROOT / relative, destination / relative)


def test_detailed_addiction_guides_materialize_without_replacing_existing_center():
    with tempfile.TemporaryDirectory() as directory:
        site = Path(directory)
        _copy_fixture(site)
        before = _hashes(site)

        report = guides.materialize(site)

        assert report["status"] == "passed"
        assert report["centerPages"] >= 18
        assert report["conditionPages"] == 10
        assert report["detailedProtocols"] == 100
        assert report["sourceRegistryEntries"] >= 50
        assert report["payloadSha256"] == guides.EXPECTED_XZ_SHA256
        assert _hashes(site) == before

        manifest = json.loads(
            (site / "addiction" / "editorial-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert manifest["version"] == "2.0.0"
        assert manifest["integration"]["extends_existing_center"] is True
        assert len(manifest["condition_pages"]) == 10

        for slug in guides.CONDITION_SLUGS:
            page = site / "addiction" / slug / "index.html"
            text = page.read_text(encoding="utf-8")
            assert text.count('class="protocol"') == 10
            assert "/addiction/sources/" in text
            assert "/addiction/evidence-library/" not in text
            assert "/addiction/recovery-plan/" not in text

        api = json.loads(
            (site / "api" / "addiction-condition-guides-v2.json").read_text(
                encoding="utf-8"
            )
        )
        assert api["status"] == "passed"
        assert api["safety"]["noIndividualDosing"] is True
        assert api["safety"]["noHomeDetoxPlan"] is True


def test_detailed_guides_survive_canonical_sitemap_rebuild():
    namespace = {"s": guides.SITEMAP_NAMESPACE}
    with tempfile.TemporaryDirectory() as directory:
        site = Path(directory)
        _copy_fixture(site)
        guides.materialize(site)

        sitemap_core.generate(site)
        guides.merge_discovery(site)

        primary = ET.parse(site / "sitemap.xml").getroot()
        primary_urls = {
            node.text for node in primary.findall("s:url/s:loc", namespace)
        }
        for slug in guides.CONDITION_SLUGS:
            assert f"https://healthrenewal.org/addiction/{slug}/" in primary_urls
        assert "https://healthrenewal.org/addiction/conditions/" in primary_urls
        assert "https://healthrenewal.org/addiction/methodology/" in primary_urls

        addiction = ET.parse(site / "sitemap-addiction.xml").getroot()
        addiction_urls = [
            node.text for node in addiction.findall("s:url/s:loc", namespace)
        ]
        assert len(addiction_urls) == len(set(addiction_urls))
        assert len(addiction_urls) >= 18

        index = ET.parse(site / "sitemap-index.xml").getroot()
        sitemap_urls = {
            node.text for node in index.findall("s:sitemap/s:loc", namespace)
        }
        assert guides.SITEMAP_URL in sitemap_urls
