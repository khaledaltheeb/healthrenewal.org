from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


spec = importlib.util.spec_from_file_location(
    "recover_content_full_history_v3_under_test",
    SCRIPTS / "recover_content_full_history_v3.py",
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _page(words: int, title: str) -> str:
    body = " ".join(f"كلمة{i}" for i in range(words))
    return f"<!doctype html><html lang='ar' dir='rtl'><head><title>{title}</title></head><body><main><h1>{title}</h1><p>{body}</p></main></body></html>"


def test_existing_richer_page_is_restored_after_shorter_historical_replacement(tmp_path, monkeypatch):
    site = tmp_path / "site"
    target = site / "guided-assessment" / "index.html"
    target.parent.mkdir(parents=True)

    richer = _page(1308, "الدليل الحالي الأغنى")
    shorter = _page(714, "فهرس تاريخي أقصر")
    target.write_text(richer, encoding="utf-8")

    def destructive_restore(site_path: Path, since: str, baseline: Path | None):
        destination = site_path / "guided-assessment" / "index.html"
        destination.write_text(shorter, encoding="utf-8")
        return [
            {
                "path": "guided-assessment/index.html",
                "from": "validated-baseline",
                "previousWords": 1308,
                "restoredWords": 714,
                "previousScore": 2277.8,
                "restoredScore": 3104.0,
            }
        ]

    monkeypatch.setattr(module, "_original_restore", destructive_restore)

    accepted = module.restore_without_shortening(site, "2026-07-01", None)

    assert accepted == []
    assert target.read_text(encoding="utf-8") == richer


def test_equal_or_longer_replacement_remains_eligible(tmp_path, monkeypatch):
    site = tmp_path / "site"
    target = site / "example" / "index.html"
    target.parent.mkdir(parents=True)

    current = _page(500, "النسخة الحالية")
    richer = _page(700, "نسخة تاريخية أغنى")
    target.write_text(current, encoding="utf-8")

    item = {
        "path": "example/index.html",
        "from": "historical-commit",
        "previousWords": 500,
        "restoredWords": 700,
        "previousScore": 1000,
        "restoredScore": 1400,
    }

    def richer_restore(site_path: Path, since: str, baseline: Path | None):
        (site_path / "example" / "index.html").write_text(richer, encoding="utf-8")
        return [item]

    monkeypatch.setattr(module, "_original_restore", richer_restore)

    accepted = module.restore_without_shortening(site, "2026-07-01", None)

    assert accepted == [item]
    assert target.read_text(encoding="utf-8") == richer


def test_missing_route_can_still_be_restored(tmp_path, monkeypatch):
    site = tmp_path / "site"
    site.mkdir()
    target = site / "lost-page" / "index.html"
    restored_page = _page(650, "صفحة مفقودة مستعادة")

    item = {
        "path": "lost-page/index.html",
        "from": "historical-commit",
        "previousWords": 0,
        "restoredWords": 650,
        "previousScore": 0,
        "restoredScore": 1200,
    }

    def missing_restore(site_path: Path, since: str, baseline: Path | None):
        destination = site_path / "lost-page" / "index.html"
        destination.parent.mkdir(parents=True)
        destination.write_text(restored_page, encoding="utf-8")
        return [item]

    monkeypatch.setattr(module, "_original_restore", missing_restore)

    accepted = module.restore_without_shortening(site, "2026-07-01", None)

    assert accepted == [item]
    assert target.read_text(encoding="utf-8") == restored_page
