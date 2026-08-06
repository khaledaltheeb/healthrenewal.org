from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

VERSION = 32
EXPECTED_ASSESSMENTS = 40
EXPECTED_OFFICIAL = 4
EXPECTED_MONITORS = 36
EXPECTED_COGNITIVE = 53
EXPECTED_TOTAL = EXPECTED_ASSESSMENTS + EXPECTED_COGNITIVE
MARK_START = "<!-- lab-provenance-v32:start -->"
MARK_END = "<!-- lab-provenance-v32:end -->"
DEFINITION_RE = re.compile(
    r'(<script type="application/json" id="lab-definition">)(.*?)(</script>)', re.S
)
ALLOWED_HOSTS = {
    "www.who.int",
    "who.int",
    "tdr.who.int",
    "www.nimh.nih.gov",
    "nimh.nih.gov",
    "www.samhsa.gov",
    "samhsa.gov",
    "www.cdc.gov",
    "cdc.gov",
    "pubmed.ncbi.nlm.nih.gov",
}
OFFICIAL_SCORE_TYPES = {"phq9", "gad7", "who5", "audit_guided"}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_definition(source: str) -> dict:
    match = DEFINITION_RE.search(source)
    if not match:
        raise ValueError("missing lab-definition")
    return json.loads(match.group(2).replace("<\\/", "</"))


def write_definition(source: str, definition: dict) -> str:
    payload = json.dumps(definition, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    updated, count = DEFINITION_RE.subn(
        lambda match: match.group(1) + payload + match.group(3), source, count=1
    )
    if count != 1:
        raise ValueError("definition replacement failed")
    return updated


def replace_marked(source: str, fragment: str) -> str:
    pattern = re.escape(MARK_START) + r".*?" + re.escape(MARK_END)
    if re.search(pattern, source, re.S):
        return re.sub(pattern, fragment, source, count=1, flags=re.S)
    for marker in ("</main>", "</article>", "<footer", "</body>"):
        position = source.lower().rfind(marker.lower())
        if position != -1:
            return source[:position] + fragment + source[position:]
    return source + fragment


def load_contracts(repo_root: Path) -> tuple[dict, dict, dict]:
    contract = json.loads(
        (repo_root / "content/v32/lab-provenance-ar.json").read_text(encoding="utf-8")
    )
    official = json.loads(
        (repo_root / "content/v32/official-scale-provenance-ar.json").read_text(
            encoding="utf-8"
        )
    )
    methods = json.loads(
        (repo_root / "content/v32/lab-methods-ar.json").read_text(encoding="utf-8")
    )
    if contract.get("version") != VERSION or official.get("version") != VERSION:
        raise SystemExit("provenance contract version mismatch")
    return contract, official, methods


def official_sources(official: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    sources: dict[str, dict] = {}
    profiles: dict[str, dict] = {}
    for score_type, profile in official.get("profiles", {}).items():
        source_id = f"official-{profile['source_id']}"
        sources[source_id] = {
            "title_ar": profile["title_ar"],
            "publisher": profile["publisher"],
            "url": profile["url"],
            "supports_ar": profile.get("scoring_note", "يربط الصفحة بالأصل المنشور."),
            "does_not_support_ar": profile.get(
                "use_limit",
                "لا يحول النسخة الرقمية إلى تشخيص أو ترجمة متحققة معياريًا.",
            ),
            "kind": "primary_instrument_source",
            "accessed_at": profile.get("accessed_at"),
        }
        profiles[score_type] = {
            **profile,
            "source_ids": [source_id],
        }
    return sources, profiles


def monitor_groups(contract: dict) -> tuple[dict[str, dict], list[str]]:
    mapping: dict[str, dict] = {}
    duplicates: list[str] = []
    for group_id, group in contract.get("monitor_source_groups", {}).items():
        for slug in group.get("slugs", []):
            if slug in mapping:
                duplicates.append(slug)
            mapping[slug] = {
                "group_id": group_id,
                "source_ids": group.get("source_ids", []),
                "use_ar": group.get("use_ar", ""),
            }
    return mapping, sorted(set(duplicates))


def validate_source(source_id: str, source: dict) -> list[str]:
    errors: list[str] = []
    for field in (
        "title_ar",
        "publisher",
        "url",
        "supports_ar",
        "does_not_support_ar",
        "kind",
    ):
        if not isinstance(source.get(field), str) or not source[field].strip():
            errors.append(f"{source_id}: missing {field}")
    url = str(source.get("url") or "")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        errors.append(f"{source_id}: invalid https URL {url}")
    elif parsed.netloc.lower() not in ALLOWED_HOSTS:
        errors.append(f"{source_id}: host not allowlisted {parsed.netloc}")
    return errors


def source_cards(source_ids: list[str], sources: dict[str, dict]) -> str:
    cards = []
    for source_id in source_ids:
        source = sources[source_id]
        cards.append(
            '<li class="lab-provenance-v32__source">'
            f'<p><strong>{esc(source["title_ar"])}</strong> — {esc(source["publisher"])}</p>'
            f'<p><strong>يسند:</strong> {esc(source["supports_ar"])}</p>'
            f'<p><strong>لا يسند:</strong> {esc(source["does_not_support_ar"])}</p>'
            f'<p><a href="{esc(source["url"])}" rel="noopener noreferrer">فتح المصدر الأصلي</a></p>'
            "</li>"
        )
    return "".join(cards)


def provenance_fragment(
    *,
    title: str,
    classification: str,
    validation_status: str,
    implementation_scope: str,
    use_ar: str,
    source_ids: list[str],
    sources: dict[str, dict],
) -> str:
    cards = source_cards(source_ids, sources)
    return f'''{MARK_START}<section class="lab-provenance-v32" aria-labelledby="lab-provenance-v32-title">
<style>.lab-provenance-v32{{margin-block:2rem;padding:1.35rem;border:2px solid #0f766e;border-radius:1.25rem;background:#f5fffd;line-height:1.95}}.lab-provenance-v32__status{{display:grid;grid-template-columns:minmax(10rem,13rem) 1fr;gap:.55rem 1rem;margin:0}}.lab-provenance-v32__status dt{{font-weight:800}}.lab-provenance-v32__status dd{{margin:0}}.lab-provenance-v32__sources{{display:grid;gap:.8rem;padding:0;list-style:none}}.lab-provenance-v32__source{{background:#fff;border:1px solid #b9ddd8;border-radius:1rem;padding:1rem}}.lab-provenance-v32__source p{{margin:.25rem 0}}@media(max-width:640px){{.lab-provenance-v32__status{{grid-template-columns:1fr}}}}</style>
<h2 id="lab-provenance-v32-title">المصدرية وحالة القياس — {esc(title)}</h2>
<dl class="lab-provenance-v32__status"><dt>تصنيف الأداة</dt><dd>{esc(classification)}</dd><dt>حالة التحقق</dt><dd>{esc(validation_status)}</dd><dt>نطاق التنفيذ الحالي</dt><dd>{esc(implementation_scope)}</dd></dl>
<h3>كيف استُخدمت المصادر؟</h3><p>{esc(use_ar)}</p>
<h3>قاعدة التفسير</h3><p>الاستشهاد بمصدر لتعريف مجال أو مبدأ لا يعني أن الكود أو الترجمة أو البنود أو المعايير الرقمية في هذه الصفحة نُشرت أو تحققت ضمن ذلك المصدر. القرار السريري أو التعليمي أو الوظيفي أو القانوني يحتاج أداة مناسبة للسكان والسياق ومراجعًا مؤهلًا.</p>
<h3>المصادر وحدود كل استشهاد</h3><ul class="lab-provenance-v32__sources">{cards}</ul>
</section>{MARK_END}'''


def classify_page(
    definition: dict,
    contract: dict,
    official_profiles: dict[str, dict],
    monitor_map: dict[str, dict],
    methods: dict,
) -> dict:
    slug = str(definition.get("slug") or "")
    score_type = str(definition.get("score_type") or "")
    if score_type in OFFICIAL_SCORE_TYPES:
        profile = official_profiles.get(score_type)
        if not profile:
            raise ValueError(f"missing official provenance profile for {score_type}")
        status = str(profile.get("provenance_status") or "")
        classification = (
            "عرض إرشادي مرتبط بأداة منشورة؛ لا يطبق الترميز الرسمي"
            if score_type == "audit_guided"
            else "نسخة عربية رقمية تثقيفية مرتبطة بأداة منشورة"
        )
        implementation = (
            "تعرض الصفحة موضوعات AUDIT وتمنع حساب الدرجة الرسمية لأن بدائل الإجابة ليست التطبيق الأصلي بندًا بندًا."
            if score_type == "audit_guided"
            else "تستخدم الصفحة بنودًا وصياغة عربية رقمية داخل الموقع؛ مصدر الأداة والحساب لا يثبت وحده تكافؤ هذه الصياغة مع ترجمة عربية متحققة."
        )
        return {
            "classification_key": "official_instrument",
            "classification": classification,
            "validation_status": f"{status}. {profile.get('validation_note', '')}".strip(),
            "implementation_scope": implementation,
            "use_ar": profile.get("use_limit", ""),
            "source_ids": profile["source_ids"],
            "source_group": score_type,
        }
    if score_type == "monitor":
        group = monitor_map.get(slug)
        if not group:
            raise ValueError(f"missing monitor provenance group for {slug}")
        policy = str(definition.get("monitor_policy") or "burden_tracking")
        return {
            "classification_key": "original_monitor",
            "classification": "أداة متابعة أصلية غير معيارية من إنشاء الموقع",
            "validation_status": "غير متحققة سيكومتريًا: لا توجد بيانات منشورة عن الصدق أو الثبات أو الحساسية أو النوعية أو المعايير أو نقاط القطع.",
            "implementation_scope": f"سياسة النتيجة: {policy}. تُستخدم البنود لمقارنة نمط الشخص نفسه عبر ظروف متقاربة، مع قراءة إشارات السلامة مستقلًا عن المجموع.",
            "use_ar": group["use_ar"],
            "source_ids": group["source_ids"],
            "source_group": group["group_id"],
        }
    category = str(definition.get("category") or definition.get("mode") or "")
    source_ids = contract.get("cognitive_category_sources", {}).get(category)
    if not source_ids:
        raise ValueError(f"missing cognitive provenance category for {slug}: {category}")
    task_method = methods.get("task_methods", {}).get(slug)
    if not task_method:
        raise ValueError(f"missing task method disclosure for {slug}")
    return {
        "classification_key": "site_cognitive_task",
        "classification": "مهمة معرفية تجريبية خاصة بالموقع وغير مقننة",
        "validation_status": "لا توجد معايير عمرية أو تعليمية أو بيانات صدق وثبات منشورة لهذا التنفيذ، ولا يُعد اختبار ذكاء أو فحصًا عصبيًا نفسيًا.",
        "implementation_scope": task_method,
        "use_ar": "تُستخدم مصادر RDoC لتعريف البناء المعرفي ومبادئ اختيار المهمة فقط. مولد المحاولات والتدرج والتغذية الراجعة والمؤشر المركب تنفيذات خاصة بالموقع وليست نسخًا رسمية من مهمة بحثية أو بطارية معيارية.",
        "source_ids": source_ids,
        "source_group": category,
    }


def attach_provenance(site: Path, repo_root: Path | None = None) -> dict:
    site = site.resolve()
    root = (repo_root or Path(__file__).resolve().parents[1]).resolve()
    contract, official, methods = load_contracts(root)
    official_source_map, official_profiles = official_sources(official)
    sources = {**contract.get("sources", {}), **official_source_map}
    monitor_map, duplicate_monitor_slugs = monitor_groups(contract)

    source_errors: list[str] = []
    for source_id, source in sorted(sources.items()):
        source_errors.extend(validate_source(source_id, source))
    referenced_ids = set()
    for group in contract.get("monitor_source_groups", {}).values():
        referenced_ids.update(group.get("source_ids", []))
    for ids in contract.get("cognitive_category_sources", {}).values():
        referenced_ids.update(ids)
    for profile in official_profiles.values():
        referenced_ids.update(profile.get("source_ids", []))
    missing_source_ids = sorted(referenced_ids - set(sources))
    unused_source_ids = sorted(set(sources) - referenced_ids)

    assessment_pages = sorted((site / "assessment-lab").glob("*/index.html"))
    cognitive_pages = sorted((site / "cognitive-lab").glob("*/index.html"))
    if len(assessment_pages) != EXPECTED_ASSESSMENTS or len(cognitive_pages) != EXPECTED_COGNITIVE:
        raise SystemExit(
            {
                "assessment_pages": len(assessment_pages),
                "cognitive_pages": len(cognitive_pages),
                "expected": [EXPECTED_ASSESSMENTS, EXPECTED_COGNITIVE],
            }
        )

    rows: list[dict] = []
    page_errors: list[dict] = []
    changed_pages: list[str] = []
    for page in assessment_pages + cognitive_pages:
        kind = "assessment" if "assessment-lab" in page.parts else "cognitive"
        source = page.read_text(encoding="utf-8")
        try:
            definition = load_definition(source)
            provenance = classify_page(
                definition, contract, official_profiles, monitor_map, methods
            )
            unknown = sorted(set(provenance["source_ids"]) - set(sources))
            if unknown:
                raise ValueError(f"unknown source IDs: {unknown}")
            definition.update(
                {
                    "provenance_version": VERSION,
                    "provenance_classification": provenance["classification_key"],
                    "provenance_validation_status": provenance["validation_status"],
                    "provenance_source_group": provenance["source_group"],
                    "provenance_source_ids": provenance["source_ids"],
                    "provenance_source_urls": [
                        sources[source_id]["url"] for source_id in provenance["source_ids"]
                    ],
                    "provenance_implementation_scope": provenance[
                        "implementation_scope"
                    ],
                }
            )
            updated = write_definition(source, definition)
            fragment = provenance_fragment(
                title=str(definition.get("title") or definition.get("slug") or "الأداة"),
                classification=provenance["classification"],
                validation_status=provenance["validation_status"],
                implementation_scope=provenance["implementation_scope"],
                use_ar=provenance["use_ar"],
                source_ids=provenance["source_ids"],
                sources=sources,
            )
            updated = replace_marked(updated, fragment)
            if updated != source:
                page.write_text(updated, encoding="utf-8")
                changed_pages.append(page.relative_to(site).as_posix())
            rows.append(
                {
                    "path": page.relative_to(site).as_posix(),
                    "slug": definition.get("slug"),
                    "kind": kind,
                    "classification": provenance["classification_key"],
                    "source_group": provenance["source_group"],
                    "source_ids": provenance["source_ids"],
                    "source_urls": [
                        sources[source_id]["url"] for source_id in provenance["source_ids"]
                    ],
                    "validation_status": provenance["validation_status"],
                }
            )
        except Exception as error:
            page_errors.append(
                {"path": page.relative_to(site).as_posix(), "error": str(error)}
            )

    written_failures: list[dict] = []
    for row in rows:
        page = site / row["path"]
        source = page.read_text(encoding="utf-8")
        definition = load_definition(source)
        checks = {
            "marker": source.count(MARK_START) == 1 and source.count(MARK_END) == 1,
            "version": definition.get("provenance_version") == VERSION,
            "classification": definition.get("provenance_classification")
            == row["classification"],
            "source_ids": definition.get("provenance_source_ids") == row["source_ids"],
            "source_urls": definition.get("provenance_source_urls")
            == row["source_urls"],
            "validation_status": bool(definition.get("provenance_validation_status")),
            "implementation_scope": bool(
                definition.get("provenance_implementation_scope")
            ),
            "visible_status": "حالة التحقق" in source,
            "visible_limits": "ما الذي لا يسند" in source or "لا يسند:" in source,
        }
        failed = [name for name, value in checks.items() if not value]
        if failed:
            written_failures.append({"path": row["path"], "failed": failed})

    classification_counts = {
        key: sum(1 for row in rows if row["classification"] == key)
        for key in ("official_instrument", "original_monitor", "site_cognitive_task")
    }
    pages_missing = sorted(
        set(page.relative_to(site).as_posix() for page in assessment_pages + cognitive_pages)
        - set(row["path"] for row in rows)
    )
    broken_source_urls = sorted(
        error for error in source_errors if "URL" in error or "host not allowlisted" in error
    )
    report = {
        "version": VERSION,
        "status": "passed",
        "reviewedAt": contract.get("reviewed_at"),
        "totalPages": len(rows),
        "assessmentPages": sum(1 for row in rows if row["kind"] == "assessment"),
        "cognitivePages": sum(1 for row in rows if row["kind"] == "cognitive"),
        "officialInstrumentPages": classification_counts.get("official_instrument", 0),
        "originalMonitorPages": classification_counts.get("original_monitor", 0),
        "siteSpecificCognitivePages": classification_counts.get(
            "site_cognitive_task", 0
        ),
        "classificationCounts": classification_counts,
        "totalSources": len(sources),
        "referencedSources": len(referenced_ids),
        "unusedSourceIds": unused_source_ids,
        "missingSourceIds": missing_source_ids,
        "duplicateMonitorSlugs": duplicate_monitor_slugs,
        "pagesMissingProvenance": pages_missing,
        "pageErrors": page_errors,
        "sourceErrors": source_errors,
        "brokenSourceUrls": broken_source_urls,
        "writtenFailures": written_failures,
        "changedPages": len(changed_pages),
        "changedPagePaths": changed_pages,
        "pages": rows,
    }
    if (
        len(rows) != EXPECTED_TOTAL
        or classification_counts.get("official_instrument") != EXPECTED_OFFICIAL
        or classification_counts.get("original_monitor") != EXPECTED_MONITORS
        or classification_counts.get("site_cognitive_task") != EXPECTED_COGNITIVE
        or source_errors
        or missing_source_ids
        or duplicate_monitor_slugs
        or pages_missing
        or page_errors
        or written_failures
    ):
        report["status"] = "failed"

    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-provenance-v32.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if report["status"] != "passed":
        raise SystemExit(json.dumps(report, ensure_ascii=False)[:12000])
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path, nargs="?", default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(attach_provenance(args.site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
