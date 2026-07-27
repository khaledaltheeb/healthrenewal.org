#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    manifest = json.loads(Path("data/recovery-dispositions-v201.json").read_text(encoding="utf-8"))
    report = json.loads(Path("reports/recovery-source-only-v315.json").read_text(encoding="utf-8"))
    records = {item["path"]: item for item in manifest["dispositions"]}

    assert manifest["version"] >= 315
    assert len(records) == len(manifest["dispositions"]), "duplicate disposition paths"
    assert report["automatic_publication"] is False
    assert report["count_as_missing_page"] is False
    assert len(report["items"]) == 3

    for item in report["items"]:
        path = item["path"]
        record = records[path]
        assert Path(path).is_file(), path
        assert record["disposition"] == "source-only", record
        assert record["recommended_action"] == item["decision"] == "manual-review", record
        assert item["addition_commit"] in record["reason"], record
        assert item["addition_commit_files"] == [path], item
        assert "Do not count it as a missing page" in record["reason"], record
        assert "publish it automatically" in record["reason"], record

    print(json.dumps({"status": "passed", "items": len(report["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
