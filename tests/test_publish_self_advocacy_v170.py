from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "learning-paths" / "self-advocacy"
sys.path.insert(0, str(ROOT / "scripts"))
import publish_self_advocacy_v170 as publisher  # noqa: E402


def platform_assets(site: Path) -> None:
    assets = site / "assets/platform"
    assets.mkdir(parents=True)
    (assets / "platform-core.js").write_text(
        "const ensureMainId=()=> 'content';if(!doc.querySelector('.pt-skip-link')){body.prepend(skip);}",
        encoding="utf-8",
    )
    (assets / "platform-core.css").write_text(
        ".pt-skip-link{top:-80px}.pt-skip-link:focus{top:12px}", encoding="utf-8"
    )


def test_all_sources_share_one_canonical_and_honest_review_status() -> None:
    assert len(publisher.PUBLIC_PACKAGES) == 9
    files = [name for name, _ in publisher.PUBLIC_PACKAGES]
    files += [publisher.GOVERNANCE_FILE, publisher.HISTORICAL_GOVERNANCE_FILE]
    assert len(files) == 11
    for filename in files:
        data = json.loads((SOURCE_DIR / filename).read_text(encoding="utf-8"))
        assert data["page"] == publisher.CANONICAL_ROUTE
        assert data["canonical"] == publisher.CANONICAL_URL
        assert data["review_status"] == "internally-reviewed"
        assert data.get("external_review") in {"recommended-not-completed", None}
        assert "معاقين" not in json.dumps(data, ensure_ascii=False)


def test_publisher_is_idempotent_and_creates_no_competing_page(tmp_path: Path) -> None:
    site = tmp_path / "site"
    target = site / publisher.TARGET_RELATIVE
    target.parent.mkdir(parents=True)
    target.write_text(
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        f'<link rel="canonical" href="{publisher.CANONICAL_URL}">'
        '</head><body><main id="content"><h1>المناصرة الذاتية</h1>'
        '<details><summary>سؤال</summary><p>إجابة</p></details></main></body></html>',
        encoding="utf-8",
    )
    platform_assets(site)
    first = publisher.publish(site)
    html_first = target.read_text(encoding="utf-8")
    second = publisher.publish(site)
    html_second = target.read_text(encoding="utf-8")

    assert first == second
    assert html_first == html_second
    assert first["status"] == "passed"
    assert first["sourcePackageCount"] == 10
    assert first["totalEvidenceFiles"] == 11
    assert first["publicContentPackageCount"] == 9
    assert first["sectionsRendered"] == 11
    assert first["standalonePagesCreated"] == 0
    assert first["continuityPackageStatus"] == "merged-into-existing-page"
    assert html_first.count('data-source-package="service-transition-and-continuity-plan.json"') == 1
    assert html_first.count(f'<link rel="canonical" href="{publisher.CANONICAL_URL}">') == 1
    assert [p.relative_to(site).as_posix() for p in site.rglob("*.html")] == [publisher.TARGET_RELATIVE.as_posix()]
    for api_name in ("self-advocacy-v170.json", "self-advocacy-v171.json", "self-advocacy-v172.json"):
        assert json.loads((site / "api" / api_name).read_text(encoding="utf-8")) == second


def test_current_governance_matches_publisher_contract() -> None:
    data = json.loads((SOURCE_DIR / publisher.GOVERNANCE_FILE).read_text(encoding="utf-8"))
    requirements = data["publication_requirements"]
    assert requirements["public_content_packages"] == 9
    assert requirements["total_evidence_files"] == 11
    assert requirements["standalone_pages_allowed"] == 0
    assert requirements["single_page_only"] is True
