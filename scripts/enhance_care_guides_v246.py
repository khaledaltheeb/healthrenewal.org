from __future__ import annotations

import json
import re
from pathlib import Path

import enhance_care_guides_v234 as base

RELEASE_DATE = "2026-07-26"
ENHANCEMENT_VERSION = 246

CATEGORY_RULES = (
    ("crisis", "الأزمات والسلامة", ("انتحار", "أزمة", "طوارئ", "هلع", "هياج", "صدمة", "عنف", "ضياع", "استرجاع", "crisis", "panic", "trauma", "wandering")),
    ("addictions", "استخدام المواد والسلوكيات الإدمانية", ("كحول", "مادة", "أفيون", "جرعة", "إدمان", "مقامرة", "ألعاب", "نيكوتين", "alcohol", "opioid", "gambling", "gaming", "substance")),
    ("older", "كبار السن والقدرات المعرفية", ("خرف", "هذيان", "كبار السن", "إدراكي", "وحدة", "dementia", "delirium", "older", "cognitive")),
    ("services", "العلاج والخدمات والحقوق", ("مختص", "موعد", "علاج نفسي", "دواء", "مستشفى", "خصوصية", "رأي ثان", "حقوق", "service", "therapy", "medication", "hospital")),
    ("children", "الأطفال والمراهقون", ("طفل", "مراهق", "مدرسة", "تنمر", "امتحان", "انفصال", "school", "child", "teen", "adolescent", "bullying")),
    ("neurodevelopment", "النمو العصبي وذوو الاحتياجات الخاصة", ("احتياجات خاصة", "نمائي", "داون", "شلل دماغي", "تعلم", "عسر القراءة", "لغة", "حسي", "توريت", "ريت", "فقدان السمع", "فقدان البصر", "AAC", "decision", "developmental", "sensory", "disability")),
    ("mood", "المزاج والقلق", ("قلق", "اكتئاب", "مزاج", "رهاب", "ما بعد الولادة", "كمالية", "غضب", "ثنائي القطب", "anxiety", "depression", "mood", "bipolar")),
    ("daily", "النوم والعمل والمرض المزمن", ("نوم", "أرق", "كوابيس", "ألم مزمن", "مرض مزمن", "العمل", "sleep", "insomnia", "pain", "workplace")),
)

_META_RE = re.compile(r"<meta\b[^>]*>", flags=re.I)
_ATTRIBUTE_RE = re.compile(r'\b(name|property|http-equiv)=["\']([^"\']+)["\']', flags=re.I)


def deduplicate_meta_tags(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    seen: set[tuple[str, str]] = set()
    removed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal removed
        tag = match.group(0)
        attribute = _ATTRIBUTE_RE.search(tag)
        if not attribute:
            return tag
        key = (attribute.group(1).lower(), attribute.group(2).strip().lower())
        if key in seen:
            removed += 1
            return ""
        seen.add(key)
        return tag

    normalized = _META_RE.sub(replace, text)
    if normalized != text:
        path.write_text(normalized, encoding="utf-8")
    return removed


def duplicate_meta_keys(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    keys: list[tuple[str, str]] = []
    for tag in _META_RE.findall(text):
        attribute = _ATTRIBUTE_RE.search(tag)
        if attribute:
            keys.append((attribute.group(1).lower(), attribute.group(2).strip().lower()))
    return sorted({f"{kind}:{value}" for kind, value in keys if keys.count((kind, value)) > 1})


def enhance(site: Path) -> dict[str, object]:
    base.RELEASE_DATE = RELEASE_DATE
    base.ENHANCEMENT_VERSION = ENHANCEMENT_VERSION
    base.CATEGORY_RULES = CATEGORY_RULES
    report = base.enhance(site)

    site = Path(site).resolve()
    pages = sorted((site / "care-guides").rglob("index.html"))
    removed = sum(deduplicate_meta_tags(path) for path in pages)
    remaining = {
        str(path.relative_to(site)): duplicate_meta_keys(path)
        for path in pages
        if duplicate_meta_keys(path)
    }
    if remaining:
        raise SystemExit(f"Duplicate care-guide metadata remains after normalization: {remaining}")

    report["version"] = ENHANCEMENT_VERSION
    report["duplicate_meta_tags_removed"] = removed
    report["duplicate_meta_keys"] = remaining
    report_path = site / "api/care-guides-v234.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
