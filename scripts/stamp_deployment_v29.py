from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from publish_global_metadata_v27 import main as publish_global_metadata


SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
CRITICAL_FILES = (
    "index.html",
    "sitemap.xml",
    "manifest.webmanifest",
    "sw.js",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Site directory not found: {SITE}")

    publish_global_metadata()
    metadata_path = SITE / "api" / "global-metadata-v27.json"
    if not metadata_path.is_file():
        raise SystemExit(f"Global metadata evidence not found: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("status") != "passed" or int(metadata.get("remaining_missing_count", -1)) != 0:
        raise SystemExit({"invalid_global_metadata_evidence": metadata})

    pwa_path = SITE / "api" / "pwa-v14.json"
    if not pwa_path.is_file():
        raise SystemExit(f"PWA evidence not found: {pwa_path}")

    missing = [name for name in CRITICAL_FILES if not (SITE / name).is_file()]
    if missing:
        raise SystemExit({"missing_critical_files": missing})

    pwa = json.loads(pwa_path.read_text(encoding="utf-8"))
    if not pwa.get("registration_verified") or int(pwa.get("pages_scanned", 0)) <= 0:
        raise SystemExit({"invalid_pwa_evidence": pwa})
    if int(metadata.get("pages_scanned", 0)) != int(pwa.get("pages_scanned", 0)):
        raise SystemExit({
            "metadata_pwa_page_count_mismatch": {
                "metadata": metadata.get("pages_scanned"),
                "pwa": pwa.get("pages_scanned"),
            }
        })

    artifacts = {
        name: {
            "sha256": sha256(SITE / name),
            "bytes": (SITE / name).stat().st_size,
        }
        for name in CRITICAL_FILES
    }

    payload = {
        "schema_version": 29,
        "commit": os.environ["GITHUB_SHA"],
        "workflow_run": os.environ["GITHUB_RUN_ID"],
        "workflow_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "1"),
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "gate": "40 assessments, 53 cognitive tools, 186 browser runs, full PWA registration, complete global metadata, critical artifact SHA-256",
        "pwa_pages": int(pwa["pages_scanned"]),
        "metadata_pages": int(metadata["pages_scanned"]),
        "metadata_version": int(metadata["version"]),
        "metadata_remaining_missing": int(metadata["remaining_missing_count"]),
        "artifacts": artifacts,
    }

    output = SITE / "deployment.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    written = json.loads(output.read_text(encoding="utf-8"))
    for name, evidence in artifacts.items():
        if written["artifacts"][name]["sha256"] != evidence["sha256"]:
            raise SystemExit({"deployment_stamp_mismatch": name})

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
