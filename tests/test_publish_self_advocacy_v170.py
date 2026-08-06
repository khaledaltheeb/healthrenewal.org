from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "learning-paths" / "self-advocacy"
sys.path.insert(0, str(ROOT / "scripts"))
import publish_self_advocacy_v170 as publisher  # noqa: E402


PUBLIC_FILES = [filename for filename, _ in publisher.PUBLIC_PACKAGES]
CURRENT_GOVERNANCE = publisher.GOVERNANCE_FILE
HISTORICAL_GOVERNANCE = publisher.HISTORICAL_GOVERNANCE_FILE
ALL_FILES = PUBLIC_FILES + [CURRENT_GOVERNANCE, HISTORICAL_GOVERNANCE]


def load(filename: str) -> dict:
    return json.loads((SOURCE_DIR / filename).read_text(encoding="utf-8"))


def test_all_packages_target_one_canonical_page_and_are_governed() -> None:
    assert len(PUBLIC_FILES) == 8
    assert len(ALL_FILES) == 10
    for filename in ALL_FILES:
        path = SOURCE_DIR / filename
        assert path.is_file(), filename
        data = load(filename)
        assert data["page"] == publisher.CANONICAL_ROUTE
        assert data["canonical"] == publisher.CANONICAL_URL
        assert data["review_status"] == "internally-reviewed"
        assert data.get("external_review") in {"recommended-not-completed", None}
        serialized = json.dumps(data, ensure_ascii=False)
        assert "معاقين" not in serialized
        assert len(re.findall(r"[\w\u0600-\u06ff]+", serialized)) >= 80


def make_platform_assets(site: Path) -> None:
    assets = site / "assets" / "platform"
    assets.mkdir(parents=True)
    (assets / "platform-core.js").write_text(
        "const ensureMainId=()=> 'content';"
        "if(!doc.querySelector('.pt-skip-link')){body.prepend(skip);}",
        encoding="utf-8",
    )
    (assets / "platform-core.css").write_text(
        ".pt-skip-link{position:fixed;top:-80px}.pt-skip-link:focus{top:12px}",
        encoding="utf-8",
    )


def test_publisher_merges_all_packages_into_existing_page_only(tmp_path: Path) -> None:
    site = tmp_path / "site"
    target = site / publisher.TARGET_RELATIVE
    target.parent.mkdir(parents=True)
    target.write_text(
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        f'<link rel="canonical" href="{publisher.CANONICAL_URL}">'
        '</head><body><main id="content"><h1>مسار المناصرة الذاتية واتخاذ القرار</h1>'
        '<section><h2>المحتوى القائم</h2><p>محتوى صحيح يجب الحفاظ عليه.</p></section>'
        '<section><h2>أسئلة شائعة</h2><details><summary>سؤال</summary><p>إجابة</p></details></section>'
        '</main></body></html>',
        encoding="utf-8",
    )
    make_platform_assets(site)

    first = publisher.publish(site)
    first_html = target.read_text(encoding="utf-8")
    second = publisher.publish(site)
    second_html = target.read_text(encoding="utf-8")

    assert first["status"] == "passed"
    assert first == second
    assert first_html == second_html
    assert first["sourcePackageCount"] == 9
    assert first["totalEvidenceFiles"] == 10
    assert first["publicContentPackageCount"] == 8
    assert first["governancePackageCount"] == 2
    assert first["historicalGovernancePackageCount"] == 1
    assert first["sectionsRendered"] == 10
    assert first["standalonePagesCreated"] == 0
    assert first["mergedIntoExistingPage"] is True
    assert first["externalReviewCompleted"] is False
    assert first["accessibilityStatus"] == "passed"
    assert first["accessibilityChecks"]["unlabelledSectionDetails"] == 0
    assert first["accessibilityChecks"]["nativeDetailsNamed"] is True
    assert first["accessibilityChecks"]["skipLinkCreatedByPlatformJs"] is True
    assert first["accessibilityChecks"]["skipLinkStyledInPlatformCss"] is True
    assert first["generatedPage"] == "learning-paths/self-advocacy/index.html"

    assert first_html.count(publisher.START) == 1
    assert first_html.count(publisher.END) == 1
    assert first_html.count(f'<link rel="canonical" href="{publisher.CANONICAL_URL}">') == 1
    assert first_html.count('data-source-package=') == 8
    assert first_html.count('data-source-governance="source-verification.json"') == 1
    assert first_html.count('data-source-governance="source-verification-initial-audit.json"') == 1
    for filename in PUBLIC_FILES:
        assert f'data-source-package="{filename}"' in first_html
    assert "محتوى صحيح يجب الحفاظ عليه" in first_html
    assert "معاقين" not in first_html

    generated_html = [path.relative_to(site).as_posix() for path in site.rglob("*.html")]
    assert generated_html == ["learning-paths/self-advocacy/index.html"]
    for api_name in ("self-advocacy-v170.json", "self-advocacy-v171.json"):
        report = json.loads((site / "api" / api_name).read_text(encoding="utf-8"))
        assert report == second


def test_current_governance_resolves_historical_merge_blockers() -> None:
    current = load(CURRENT_GOVERNANCE)
    historical = load(HISTORICAL_GOVERNANCE)
    audit = current["semantic_accessibility_audit"]
    assert audit["status"] == "resolved-and-enforced-in-production-pipeline"
    assert audit["merge_blocking_findings_remaining"] == 0
    assert current["supersedes_for_merge_status"] == HISTORICAL_GOVERNANCE
    assert historical["semantic_accessibility_audit"]["status"] == "remediation-required-before-merge"


def test_publisher_rejects_missing_existing_page(tmp_path: Path) -> None:
    site = tmp_path / "site"
    site.mkdir()
    make_platform_assets(site)
    try:
        publisher.publish(site)
    except SystemExit as error:
        assert "Missing existing self-advocacy page" in str(error)
    else:
        raise AssertionError("Publisher created a new page instead of enriching the existing page")


def test_publisher_source_declares_no_standalone_routes() -> None:
    base_source = (ROOT / "scripts" / "publish_self_advocacy_base_v170.py").read_text(encoding="utf-8")
    wrapper_source = (ROOT / "scripts" / "publish_self_advocacy_v170.py").read_text(encoding="utf-8")
    assert 'TARGET_RELATIVE = Path("learning-paths/self-advocacy/index.html")' in base_source
    assert '"standalonePagesCreated": 0' in base_source
    assert "target.write_text(updated" in base_source
    assert "sitemap" not in base_source.lower()
    assert "validate_accessibility_contract" in wrapper_source
    assert "source-verification-initial-audit.json" in wrapper_source
