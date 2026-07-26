from __future__ import annotations

import html
import json
import re
from pathlib import Path

import enhance_care_guides_v234 as base

RELEASE_DATE = "2026-07-26"
ENHANCEMENT_VERSION = 246
MAX_META_DESCRIPTION_LENGTH = 180

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
_CONTENT_RE = re.compile(r'\bcontent=(["\'])(.*?)\1', flags=re.I | re.S)
_DESCRIPTION_KEYS = {
    ("name", "description"),
    ("property", "og:description"),
    ("name", "twitter:description"),
}


def _meta_key(tag: str) -> tuple[str, str] | None:
    attribute = _ATTRIBUTE_RE.search(tag)
    if not attribute:
        return None
    return attribute.group(1).lower(), attribute.group(2).strip().lower()


def _meta_content(tag: str) -> str | None:
    match = _CONTENT_RE.search(tag)
    return match.group(2) if match else None


def _short_description(value: str, max_length: int = MAX_META_DESCRIPTION_LENGTH) -> str:
    plain = re.sub(r"\s+", " ", html.unescape(value)).strip()
    if len(plain) <= max_length:
        return plain
    candidate = plain[: max_length - 1].rsplit(" ", 1)[0].rstrip("،؛:,.!؟-–—")
    if len(candidate) < 90:
        candidate = plain[: max_length - 1].rstrip("،؛:,.!؟-–—")
    return candidate + "…"


def normalize_meta_descriptions(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    source_description: str | None = None
    for tag in _META_RE.findall(text):
        if _meta_key(tag) == ("name", "description"):
            source_description = _meta_content(tag)
            break
    if source_description is None:
        return 0

    normalized_description = _short_description(source_description)
    escaped_description = html.escape(normalized_description, quote=True)
    changed = 0

    def replace_tag(match: re.Match[str]) -> str:
        nonlocal changed
        tag = match.group(0)
        if _meta_key(tag) not in _DESCRIPTION_KEYS:
            return tag
        content_match = _CONTENT_RE.search(tag)
        if not content_match:
            return tag
        current = html.unescape(content_match.group(2))
        if current == normalized_description:
            return tag
        changed += 1
        quote = content_match.group(1)
        replacement = f"content={quote}{escaped_description}{quote}"
        return tag[: content_match.start()] + replacement + tag[content_match.end() :]

    normalized = _META_RE.sub(replace_tag, text)
    if normalized != text:
        path.write_text(normalized, encoding="utf-8")
    return changed


def meta_description_length(path: Path) -> int | None:
    text = path.read_text(encoding="utf-8")
    for tag in _META_RE.findall(text):
        if _meta_key(tag) == ("name", "description"):
            content = _meta_content(tag)
            return len(html.unescape(content)) if content is not None else None
    return None


def deduplicate_meta_tags(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    seen: set[tuple[str, str]] = set()
    removed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal removed
        tag = match.group(0)
        key = _meta_key(tag)
        if not key:
            return tag
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
    keys = [key for tag in _META_RE.findall(text) if (key := _meta_key(tag))]
    return sorted({f"{kind}:{value}" for kind, value in keys if keys.count((kind, value)) > 1})


def enhance(site: Path) -> dict[str, object]:
    base.RELEASE_DATE = RELEASE_DATE
    base.ENHANCEMENT_VERSION = ENHANCEMENT_VERSION
    base.CATEGORY_RULES = CATEGORY_RULES
    report = base.enhance(site)

    site = Path(site).resolve()
    pages = sorted((site / "care-guides").rglob("index.html"))
    removed = sum(deduplicate_meta_tags(path) for path in pages)
    normalized_meta_tags = sum(normalize_meta_descriptions(path) for path in pages)
    remaining = {
        str(path.relative_to(site)): duplicate_meta_keys(path)
        for path in pages
        if duplicate_meta_keys(path)
    }
    if remaining:
        raise SystemExit(f"Duplicate care-guide metadata remains after normalization: {remaining}")

    description_lengths = {
        str(path.relative_to(site)): length
        for path in pages
        if (length := meta_description_length(path)) is not None
    }
    overlong = {
        relative: length
        for relative, length in description_lengths.items()
        if length > MAX_META_DESCRIPTION_LENGTH
    }
    if overlong:
        raise SystemExit(f"Overlong care-guide meta descriptions remain: {overlong}")

    report["version"] = ENHANCEMENT_VERSION
    report["duplicate_meta_tags_removed"] = removed
    report["duplicate_meta_keys"] = remaining
    report["meta_description_tags_normalized"] = normalized_meta_tags
    report["max_meta_description_length"] = max(description_lengths.values(), default=0)
    report_path = site / "api/care-guides-v234.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
