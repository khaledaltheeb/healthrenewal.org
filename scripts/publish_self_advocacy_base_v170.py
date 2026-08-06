#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "learning-paths" / "self-advocacy"
TARGET_RELATIVE = Path("learning-paths/self-advocacy/index.html")
CANONICAL_ROUTE = "/learning-paths/self-advocacy/"
CANONICAL_URL = "https://healthrenewal.org/learning-paths/self-advocacy/"
VERSION = 170
START = "<!-- self-advocacy-v170:start -->"
END = "<!-- self-advocacy-v170:end -->"
PROHIBITED = re.compile(r"معاقين", re.IGNORECASE)

PUBLIC_PACKAGES = (
    ("content-extension.json", "تطبيق المناصرة الذاتية في مواقف القرار"),
    ("decision-support-workbook.json", "دفتر عمل دعم اتخاذ القرار"),
    ("conversation-cards.json", "بطاقات المحادثة للمناصرة الذاتية"),
    ("meeting-preparation-checklist.json", "قائمة الاستعداد للاجتماعات"),
    ("supported-decision-record.json", "سجل القرار المدعوم"),
    ("complaint-and-safeguarding-pathway.json", "مسار الشكوى والحماية"),
    ("reasonable-accommodation-request-plan.json", "خطة طلب التيسير المعقول"),
    ("privacy-and-information-sharing-plan.json", "خطة الخصوصية ومشاركة المعلومات"),
)
GOVERNANCE_FILE = "source-verification.json"

SKIP_KEYS = {
    "id", "page", "canonical", "language", "direction", "schema_types",
    "review_status", "external_review", "verified_at", "next_review_at",
    "title", "description", "source_log", "internal_links", "rights",
    "copyright", "license", "slug",
}
LABELS = {
    "professional_limits": "الحدود المهنية والقانونية",
    "professional_boundaries": "الحدود المهنية والقانونية",
    "decision_scenarios": "سيناريوهات اتخاذ القرار",
    "practice_questions": "أسئلة ممارسة",
    "workbook": "خطوات دفتر العمل",
    "rapid_checklist": "قائمة تحقق سريعة",
    "outcome_measures": "مؤشرات قياس النتيجة",
    "cards": "البطاقات التطبيقية",
    "checklist": "قائمة التحقق",
    "steps": "الخطوات",
    "record": "ما يجب توثيقه",
    "questions": "الأسئلة",
    "prompts_for_person": "أسئلة للشخص",
    "prompts_for_supporter": "أسئلة للداعم",
    "safe_action": "الإجراء الآمن",
    "measure": "مؤشر القياس",
    "quality_indicator": "مؤشر الجودة",
    "escalation": "متى يلزم التصعيد",
    "goal": "الهدف",
    "purpose": "الغرض",
    "situation": "الموقف",
    "reasonable_accommodation": "التيسير المعقول",
    "privacy": "الخصوصية",
    "information_sharing": "مشاركة المعلومات",
    "complaint": "الشكوى",
    "safeguarding": "الحماية",
    "sources": "المصادر",
    "claim_governance": "حوكمة الادعاءات",
    "rights_and_attribution": "الحقوق والإسناد",
    "publication_requirements": "متطلبات النشر",
    "status": "حالة المراجعة",
    "professional_boundaries": "الحدود المهنية",
}


def label(key: str) -> str:
    if key in LABELS:
        return LABELS[key]
    return key.replace("_", " ").strip().capitalize()


def scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "نعم" if value else "لا"
    if value is None:
        return ""
    return str(value).strip()


def render_scalar(key: str, value: Any) -> str:
    text = scalar(value)
    if not text:
        return ""
    escaped = html.escape(text)
    if key in {"url", "href"} and text.startswith(("https://", "/")):
        return f'<p><strong>{html.escape(label(key))}:</strong> <a href="{html.escape(text, quote=True)}" rel="noopener noreferrer">{escaped}</a></p>'
    return f'<p><strong>{html.escape(label(key))}:</strong> {escaped}</p>'


def item_heading(item: dict[str, Any], fallback: str) -> str:
    for key in ("title", "name_ar", "label", "indicator", "step", "id"):
        value = scalar(item.get(key))
        if value:
            return value
    return fallback


def render_value(key: str, value: Any, depth: int = 0) -> str:
    if key in SKIP_KEYS:
        return ""
    heading_level = min(4, 3 + depth)
    heading = html.escape(label(key))
    if isinstance(value, dict):
        body = "".join(
            render_value(child_key, child_value, depth + 1)
            for child_key, child_value in value.items()
            if child_key not in SKIP_KEYS
        )
        if not body:
            return ""
        return f'<div class="card self-advocacy-subsection"><h{heading_level}>{heading}</h{heading_level}>{body}</div>'
    if isinstance(value, list):
        if not value:
            return ""
        if all(not isinstance(item, (dict, list)) for item in value):
            items = "".join(f"<li>{html.escape(scalar(item))}</li>" for item in value if scalar(item))
            return f'<div class="self-advocacy-list"><h{heading_level}>{heading}</h{heading_level}><ul>{items}</ul></div>' if items else ""
        cards: list[str] = []
        for position, item in enumerate(value, 1):
            if isinstance(item, dict):
                card_title = html.escape(item_heading(item, f"البند {position}"))
                body = "".join(
                    render_value(child_key, child_value, depth + 1)
                    for child_key, child_value in item.items()
                    if child_key not in SKIP_KEYS and child_key not in {"title", "name_ar", "label", "id"}
                )
                cards.append(f'<article class="card self-advocacy-tool"><h{heading_level}>{card_title}</h{heading_level}>{body}</article>')
            elif isinstance(item, list):
                body = render_value(f"item_{position}", item, depth + 1)
                if body:
                    cards.append(f'<article class="card self-advocacy-tool">{body}</article>')
        return f'<div class="self-advocacy-group"><h{heading_level}>{heading}</h{heading_level}><div class="grid">{"".join(cards)}</div></div>' if cards else ""
    return render_scalar(key, value)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected an object in {path}")
    return data


def validate_package(path: Path, data: dict[str, Any]) -> None:
    if data.get("page") != CANONICAL_ROUTE:
        raise SystemExit(f"Package {path.name} targets a different page: {data.get('page')}")
    if data.get("canonical") != CANONICAL_URL:
        raise SystemExit(f"Package {path.name} has a different canonical: {data.get('canonical')}")
    if data.get("review_status") != "internally-reviewed":
        raise SystemExit(f"Package {path.name} must retain internally-reviewed status")
    if data.get("external_review") not in {"recommended-not-completed", None}:
        raise SystemExit(f"Package {path.name} overstates external review")
    serialized = json.dumps(data, ensure_ascii=False)
    if PROHIBITED.search(serialized):
        raise SystemExit(f"Prohibited terminology remains in {path.name}")
    if len(re.findall(r"[\w\u0600-\u06ff]+", serialized)) < 80:
        raise SystemExit(f"Package {path.name} is unexpectedly thin")


def render_package(filename: str, fallback_title: str, data: dict[str, Any]) -> str:
    title = scalar(data.get("title")) or fallback_title
    description = scalar(data.get("description") or data.get("purpose") or data.get("editorial_purpose"))
    body = "".join(
        render_value(key, value)
        for key, value in data.items()
        if key not in SKIP_KEYS and key not in {"purpose", "editorial_purpose"}
    )
    intro = f"<p>{html.escape(description)}</p>" if description else ""
    return (
        f'<section class="self-advocacy-package" data-source-package="{html.escape(filename, quote=True)}" '
        f'aria-labelledby="self-advocacy-{html.escape(filename.replace(".json", ""), quote=True)}">'
        f'<h2 id="self-advocacy-{html.escape(filename.replace(".json", ""), quote=True)}">{html.escape(title)}</h2>'
        f'{intro}{body}</section>'
    )


def render_governance(data: dict[str, Any]) -> str:
    selected = {
        key: value
        for key, value in data.items()
        if key in {
            "status", "professional_boundaries", "professional_limits", "sources",
            "claim_governance", "rights_and_attribution", "rights",
            "publication_requirements", "source_log",
        }
    }
    body = "".join(render_value(key, value) for key, value in selected.items())
    return (
        '<section class="self-advocacy-package self-advocacy-governance" '
        'data-source-governance="source-verification.json" aria-labelledby="self-advocacy-governance">'
        '<h2 id="self-advocacy-governance">المصادر والحقوق وحدود المراجعة</h2>'
        '<p>هذه الحزمة توثق مصادر الصفحة وحدود استخدامها. المراجعة داخلية، والمراجعة الخارجية المتخصصة موصى بها ولم يُدّع اكتمالها.</p>'
        f'{body}</section>'
    )


def strip_existing(source: str) -> str:
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    return pattern.sub("", source)


def insert_before_main_end(source: str, block: str) -> str:
    clean = strip_existing(source)
    match = list(re.finditer(r"</main\s*>", clean, re.I))
    if not match:
        raise SystemExit("Self-advocacy page has no closing </main>")
    position = match[-1].start()
    return clean[:position] + "\n" + block + "\n" + clean[position:]


def publish(site: Path) -> dict[str, Any]:
    target = site / TARGET_RELATIVE
    if not target.is_file():
        raise SystemExit(f"Missing existing self-advocacy page: {target}")
    source = target.read_text(encoding="utf-8", errors="replace")
    if source.count(f'<link rel="canonical" href="{CANONICAL_URL}">') != 1:
        raise SystemExit("Self-advocacy page must have exactly one expected canonical")

    sections: list[str] = []
    package_ids: list[str] = []
    for filename, fallback_title in PUBLIC_PACKAGES:
        path = SOURCE_DIR / filename
        if not path.is_file():
            raise SystemExit(f"Missing self-advocacy source package: {path}")
        data = load_json(path)
        validate_package(path, data)
        package_ids.append(scalar(data.get("id")) or filename)
        sections.append(render_package(filename, fallback_title, data))

    governance_path = SOURCE_DIR / GOVERNANCE_FILE
    if not governance_path.is_file():
        raise SystemExit(f"Missing source governance: {governance_path}")
    governance = load_json(governance_path)
    validate_package(governance_path, governance)
    sections.append(render_governance(governance))

    wrapper = (
        f'{START}\n'
        '<section class="self-advocacy-integrated-tools" data-content-version="170" '
        'aria-labelledby="self-advocacy-integrated-tools-heading">'
        '<h2 id="self-advocacy-integrated-tools-heading">أدوات المناصرة الذاتية ودعم اتخاذ القرار</h2>'
        '<p class="notice">الأدوات التالية للتثقيف والتنظيم والتوثيق. لا تحسم الأهلية القانونية، ولا تبرر الإكراه، ولا تستبدل المشورة القانونية أو السريرية الفردية. تختلف إجراءات الحماية والتظلم والخصوصية حسب الدولة.</p>'
        + "".join(sections)
        + '</section>\n'
        f'{END}'
    )
    updated = insert_before_main_end(source, wrapper)
    if updated.count(START) != 1 or updated.count(END) != 1:
        raise SystemExit("Self-advocacy integration marker is not idempotent")
    if updated.count(f'<link rel="canonical" href="{CANONICAL_URL}">') != 1:
        raise SystemExit("Canonical changed during self-advocacy publication")
    if PROHIBITED.search(updated):
        raise SystemExit("Prohibited terminology remains in the generated page")
    target.write_text(updated, encoding="utf-8")

    report = {
        "version": VERSION,
        "status": "passed",
        "canonicalRoute": CANONICAL_ROUTE,
        "canonicalUrl": CANONICAL_URL,
        "generatedPage": TARGET_RELATIVE.as_posix(),
        "sourcePackageCount": len(PUBLIC_PACKAGES) + 1,
        "publicContentPackageCount": len(PUBLIC_PACKAGES),
        "governancePackageCount": 1,
        "sectionsRendered": len(sections),
        "standalonePagesCreated": 0,
        "mergedIntoExistingPage": True,
        "externalReviewCompleted": False,
        "packageIds": package_ids,
        "outputBytes": len(updated.encode("utf-8")),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "self-advocacy-v170.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
