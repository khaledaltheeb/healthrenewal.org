from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "special-needs/conditions/cerebral-palsy/evidence.json"
VERIFICATION = ROOT / "special-needs/conditions/cerebral-palsy/source-verification.json"


def test_cerebral_palsy_source_verification_contract() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))

    evidence_ids = {source["id"] for source in evidence["sources"]}
    records = verification["sources"]

    assert verification["schema_version"] == "1.0"
    assert verification["condition"] == "cerebral-palsy"
    assert verification["review_status"] == "internally-verified"
    assert verification["external_review"] == "not-completed"
    assert date.fromisoformat(verification["next_review_due"]) > date.fromisoformat(
        verification["verified_on"]
    )
    assert len(records) >= 3

    allowed_hosts = {"www.nice.org.uk", "www.aacpdm.org"}
    for record in records:
        assert record["source_id"] in evidence_ids
        assert record["status"] == "verified"
        assert record["supports"]
        assert record["jurisdiction_note"]
        parsed = urlparse(record["url"])
        assert parsed.scheme == "https"
        assert parsed.netloc in allowed_hosts

    rights = verification["rights"]
    assert rights == {
        "use_mode": "link and summarize with attribution",
        "copied_content": False,
        "logos_used": False,
        "partnership_claimed": False,
    }
