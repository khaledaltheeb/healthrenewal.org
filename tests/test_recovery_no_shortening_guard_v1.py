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


def test_all_history_keeps_every_commit_beyond_old_24_limit(monkeypatch):
    lines: list[str] = []
    commits: list[str] = []
    for index in range(31):
        commit = f"{index + 1:040x}"
        commits.append(commit)
        lines.extend([f"@@{commit}", "deep/page/index.html", ""])

    monkeypatch.setattr(module.base, "git", lambda args: "\n".join(lines))
    history = module.all_history("1970-01-01", limit=24)

    assert history["deep/page/index.html"] == commits
    assert len(history["deep/page/index.html"]) == 31


def test_history_excludes_private_historical_surfaces(monkeypatch):
    lines = [
        f"@@{'a' * 40}",
        "professional-assessment-hub/index.html",
        "public-guide/index.html",
    ]
    monkeypatch.setattr(module.base, "git", lambda args: "\n".join(lines))

    history = module.all_history("1970-01-01")

    assert "professional-assessment-hub/index.html" not in history
    assert history["public-guide/index.html"] == ["a" * 40]


def test_missing_route_prefers_longest_candidate_even_if_shorter_has_higher_score():
    longer = {
        "words": 1308,
        "score": 2200.0,
        "sections": 8,
        "bytes": 18000,
        "redirect": False,
    }
    shorter_but_structurally_higher = {
        "words": 714,
        "score": 3104.0,
        "sections": 14,
        "bytes": 12000,
        "redirect": False,
    }

    chosen = module.choose_missing_candidate(
        "guided-assessment/index.html",
        None,
        [
            ("longer-history", "LONGER", longer),
            ("shorter-history", "SHORTER", shorter_but_structurally_higher),
        ],
    )

    assert chosen is not None
    assert chosen[0] == "longer-history"
    assert chosen[1] == "LONGER"
    assert chosen[2]["words"] == 1308


def test_history_injection_is_additive_and_preserves_primary_page():
    primary = (
        "<!doctype html><html lang='ar' dir='rtl'><body><main>"
        "<h1>الصفحة الحالية</h1><p>المحتوى الحالي الكامل يبقى كما هو دون استبدال.</p>"
        "</main></body></html>"
    )
    historical = "<section><h2>إضافة تاريخية</h2><p>معلومة فريدة مستعادة.</p></section>"

    updated = module.inject_history(primary, "example/index.html", [historical])

    assert "<h1>الصفحة الحالية</h1>" in updated
    assert "المحتوى الحالي الكامل يبقى كما هو دون استبدال." in updated
    assert historical in updated
    assert updated.index("المحتوى الحالي الكامل") < updated.index("إضافة تاريخية")


def test_duplicate_historical_fragment_is_not_considered_unique():
    known = ["هذه فقرة علمية مفصلة تحتوي معلومات كافية لاختبار منع تكرار المحتوى التاريخي داخل الصفحة الحالية"]
    assert module.similar_enough(known[0], known)


def test_recovery_safe_blocks_reserved_private_prefixes():
    assert not module.recovery_safe("professional-assessment-hub/index.html")
    assert not module.recovery_safe("provider-assessment-platform/tool/index.html")
    assert not module.recovery_safe("specialists-partners/admin/index.html")
    assert not module.recovery_safe("specialists-partners/portal/index.html")
