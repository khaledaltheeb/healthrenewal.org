#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import re
from pathlib import Path
from types import ModuleType

VERSION = 1
BRAND_NAME = "منصة روافد"
TAGLINE = "للعافية النفسية والدمج والتمكين"
LEGACY_HEALTH_RENEWAL = re.compile(r"(?<![\w.-])health\s+renewal(?![\w.-])", re.IGNORECASE)
TEXT_SUFFIXES = {
    ".html", ".htm", ".xml", ".json", ".webmanifest", ".md", ".txt", ".csv",
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".yml", ".yaml", ".svg", ".css",
}
SKIP_PARTS = {".git", "node_modules", ".venv", "venv", "vendor", "dist", "build", "__pycache__"}


def _eligible(root: Path, path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    relative = path.relative_to(root)
    return not any(part in SKIP_PARTS for part in relative.parts)


def _replace_health_renewal(root: Path) -> tuple[int, int]:
    changed = 0
    replacements = 0
    for path in root.rglob("*"):
        if not _eligible(root, path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated, count = LEGACY_HEALTH_RENEWAL.subn(BRAND_NAME, text)
        if count:
            path.write_text(updated, encoding="utf-8")
            changed += 1
            replacements += count
    return changed, replacements


def _legacy_examples(root: Path) -> list[str]:
    examples: list[str] = []
    old_arabic = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
    for path in root.rglob("*"):
        if not _eligible(root, path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if LEGACY_HEALTH_RENEWAL.search(text) or old_arabic in text or "Psychology Terminology" in text:
            examples.append(path.relative_to(root).as_posix())
            if len(examples) >= 20:
                break
    return examples


def _load_brand_module() -> ModuleType:
    """Load the image-capable brand implementation only for real production builds.

    Sitemap and discovery unit tests import this module to inspect wiring but do
    not normalize HTML or generate visual assets. Keeping Pillow behind this
    execution boundary prevents unrelated lightweight checks from failing while
    preserving the complete production implementation.
    """

    return importlib.import_module("apply_rawafid_brand")


def normalize(root: Path) -> dict[str, object]:
    root = root.resolve()
    if not (root / "index.html").is_file():
        raise SystemExit({"missing_production_homepage": str(root / "index.html")})

    # Reuse the established Rawafid identity implementation against the final
    # production artifact rather than against the source checkout. It is loaded
    # lazily because its visual asset routines depend on Pillow, while callers
    # that only import the sitemap generator do not need those routines.
    brand = _load_brand_module()
    brand.ROOT = root
    brand.BRAND_DIR = root / "assets" / "brand"
    brand.BRAND_DIR.mkdir(parents=True, exist_ok=True)

    changed, replacements = brand.replace_brand_text()
    health_files, health_replacements = _replace_health_renewal(root)
    html_changed = brand.enrich_all_html()
    brand.update_homepage(root / "index.html")
    manifests = brand.update_manifests()
    validation = brand.validate()

    legacy = _legacy_examples(root)
    if legacy:
        raise SystemExit({"legacy_brand_remaining": legacy})

    report: dict[str, object] = {
        "schemaVersion": VERSION,
        "status": "passed",
        "brand": BRAND_NAME,
        "tagline": TAGLINE,
        "textFilesChanged": changed,
        "textReplacements": replacements,
        "healthRenewalFilesChanged": health_files,
        "healthRenewalReplacements": health_replacements,
        "htmlFilesEnriched": html_changed,
        "manifestsUpdated": manifests,
        "htmlFiles": validation["html_files"],
        "legacyBrandFiles": 0,
        "requiredAssetsPresent": True,
    }
    api = root / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "rawafid-production-normalization-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize the final production artifact to the Rawafid identity.")
    parser.add_argument("root", nargs="?", default=".", type=Path)
    args = parser.parse_args()
    print(json.dumps(normalize(args.root), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
