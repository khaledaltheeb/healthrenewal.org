#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

VERSION = 225
MARKER = "provider-layout-stability-v225"
CONTRACT = "2026.07.25-v220"
TARGET = Path("provider-assessment-demo/activation.js")
INDEX = Path("provider-assessment-demo/index.html")
FUNCTION_OPENING = "  const patchStaticCopy = () => {\n"
GUARD = f'''    // {MARKER}: do not replace final v220 copy with an older operational draft.
    if (
      document.documentElement.dataset.institutionalContract === "{CONTRACT}" ||
      document.querySelector('script[data-institutional-contract-v220]')
    ) return;
'''


def stabilize(root: Path | str) -> dict[str, object]:
    root = Path(root).resolve()
    target = root / TARGET
    index = root / INDEX
    if not target.is_file():
        raise SystemExit(f"Missing provider activation runtime: {target}")
    if not index.is_file():
        raise SystemExit(f"Missing provider page: {index}")

    page = index.read_text(encoding="utf-8")
    required_page_markers = (
        f'data-institutional-contract="{CONTRACT}"',
        "data-institutional-contract-v220",
        "activation.js",
    )
    missing_page = [item for item in required_page_markers if item not in page]
    if missing_page:
        raise SystemExit(f"Provider page is missing v220 activation markers: {missing_page}")

    source = target.read_text(encoding="utf-8")
    if MARKER in source:
        changed = False
    else:
        if source.count(FUNCTION_OPENING) != 1:
            raise SystemExit("Activation patchStaticCopy contract is missing or ambiguous")
        source = source.replace(FUNCTION_OPENING, FUNCTION_OPENING + GUARD, 1)
        target.write_text(source, encoding="utf-8")
        changed = True

    final = target.read_text(encoding="utf-8")
    required_runtime_markers = (
        MARKER,
        f'dataset.institutionalContract === "{CONTRACT}"',
        "script[data-institutional-contract-v220]",
        "const patchStaticCopy = () =>",
        "patchStaticCopy();",
        "installRecordsView();",
        "renderProfessionalRecords();",
    )
    missing_runtime = [item for item in required_runtime_markers if item not in final]
    if missing_runtime:
        raise SystemExit(f"Stabilized activation runtime is incomplete: {missing_runtime}")
    if final.count(MARKER) != 1:
        raise SystemExit("Provider layout stability marker must occur exactly once")

    report = {
        "version": VERSION,
        "status": "passed",
        "changed": changed,
        "target": TARGET.as_posix(),
        "contract": CONTRACT,
        "older_copy_guarded": True,
        "records_runtime_preserved": True,
    }
    api = root / "api"
    if api.is_dir() or root.name not in {"pterminology-site", "repo"}:
        api.mkdir(parents=True, exist_ok=True)
        (api / "provider-layout-stability-v225.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="_site")
    report = stabilize(parser.parse_args().root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
