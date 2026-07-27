#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

MANIFEST = Path("data/recovery-dispositions-v201.json")
VERIFIED = {
    "content/sectors-v10/aac-home-school-guide.json": "45af8668fc66682173118f30d4df1c209ee100e2",
    "content/sectors-v10/inclusive-school-transition.json": "02a6c9ae827940b6beb7c235b67021da7ff20d4f",
    "content/sectors-v10/mental-health-foundations.json": "e23695d9c03898c271e1dcae44ca6a78b82445f6",
}


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["version"] >= 314, data["version"]
    records = {item["path"]: item for item in data["dispositions"]}
    assert len(records) == len(data["dispositions"]), "duplicate disposition paths"

    for path, commit in VERIFIED.items():
        record = records[path]
        assert record["disposition"] == "source-only", record
        assert record["recommended_action"] == "manual-review", record
        reason = record["reason"]
        assert commit in reason, record
        assert "do not count it as a missing page" in reason, record
        assert "do not publish it automatically" in reason, record
        assert Path(path).is_file(), path

    print(json.dumps({"status": "passed", "verified_source_only": len(VERIFIED)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
