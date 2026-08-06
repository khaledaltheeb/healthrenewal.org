from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import publish_self_advocacy_base_v170 as base  # noqa: E402
import publish_self_advocacy_continuity_v1 as publisher  # noqa: E402


def make_site(tmp_path: Path) -> Path:
    site = tmp_path / "site"
    target = site / publisher.TARGET_RELATIVE
    target.parent.mkdir(parents=True)
    target.write_text(
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        f'<link rel="canonical" href="{publisher.CANONICAL_URL}">'
        '</head><body><main id="content">'
        '<h1>مسار المناصرة الذاتية واتخاذ القرار</h1>'
        f'{base.START}<section class="self-advocacy-integrated-tools">محتوى الأدوات الأساسية</section>{base.END}'
        '</main></body></html>',
        encoding="utf-8",
    )
    for route in (
        "daily-tools/medical-visit-preparation",
        "rights",
        "support",
        "contact-specialist",
    ):
        path = site / route / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<!doctype html><title>test</title>", encoding="utf-8")
    return site


def test_publisher_merges_plan_once_without_new_page(tmp_path: Path) -> None:
    site = make_site(tmp_path)
    target = site / publisher.TARGET_RELATIVE

    first = publisher.publish(site)
    first_html = target.read_text(encoding="utf-8")
    second = publisher.publish(site)
    second_html = target.read_text(encoding="utf-8")

    assert first_html == second_html
    assert first["canonicalRoute"] == publisher.CANONICAL_ROUTE
    assert first["standalonePagesCreated"] == 0
    assert first["mergedIntoExistingPage"] is True
    assert first["workflowStages"] == 7
    assert first["practicalQuestions"] >= 28
    assert first["redFlags"] >= 10
    assert first["externalReviewCompleted"] is False
    assert first_html.count(publisher.START) == 1
    assert first_html.count(publisher.END) == 1
    assert first_html.count(f'data-source-package="{publisher.SOURCE.name}"') == 1
    assert first_html.count(f'<link rel="canonical" href="{publisher.CANONICAL_URL}">') == 1

    generated_html = sorted(path.relative_to(site).as_posix() for path in site.rglob("*.html"))
    assert "learning-paths/self-advocacy/index.html" in generated_html
    assert not any("service-transition" in path for path in generated_html)

    report = json.loads((site / "api" / "self-advocacy-continuity-v1.json").read_text(encoding="utf-8"))
    assert report == second


def test_publisher_requires_core_page_and_core_package_marker(tmp_path: Path) -> None:
    empty_site = tmp_path / "empty"
    empty_site.mkdir()
    try:
        publisher.publish(empty_site)
    except SystemExit as error:
        assert "Missing existing self-advocacy page" in str(error)
    else:
        raise AssertionError("Publisher created a competing page")

    site = tmp_path / "without-core"
    target = site / publisher.TARGET_RELATIVE
    target.parent.mkdir(parents=True)
    target.write_text(
        '<!doctype html><head>'
        f'<link rel="canonical" href="{publisher.CANONICAL_URL}">'
        '</head><body><main id="content"></main></body>',
        encoding="utf-8",
    )
    try:
        publisher.publish(site)
    except SystemExit as error:
        assert "Core self-advocacy packages" in str(error)
    else:
        raise AssertionError("Publisher bypassed the core package contract")


def test_source_is_the_only_new_content_contract() -> None:
    data = json.loads(publisher.SOURCE.read_text(encoding="utf-8"))
    assert data["page"] == publisher.CANONICAL_ROUTE
    assert data["canonical"] == publisher.CANONICAL_URL
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert len(data["workflow"]) == 7
    assert len(data["red_flags"]) >= 10
    assert "معاقين" not in json.dumps(data, ensure_ascii=False)
