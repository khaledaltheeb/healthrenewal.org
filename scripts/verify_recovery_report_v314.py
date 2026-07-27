#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    manifest = json.loads(Path("data/recovery-dispositions-v201.json").read_text(encoding="utf-8"))
    report = json.loads(Path("reports/recovery-source-only-v314.json").read_text(encoding="utf-8"))
    dispositions = {item["path"]: item for item in manifest["dispositions"]}

    assert report["automatic_publication"] is False
    assert report["count_as_missing_page"] is False
    assert len(report["items"]) == 3
    for item in report["items"]:
        disposition = dispositions[item["path"]]
        assert disposition["disposition"] == "source-only"
        assert disposition["recommended_action"] == item["decision"] == "manual-review"
        assert item["addition_commit"] in disposition["reason"]
        assert item["addition_commit_files"] == [item["path"]]

    print(json.dumps({"status": "passed", "items": len(report["items"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
