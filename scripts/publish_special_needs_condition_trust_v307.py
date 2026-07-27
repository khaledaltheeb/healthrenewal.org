#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "content" / "v307" / "special-needs-condition-trust-ar.json"
VERSION = 307
SLUGS = ("autism", "down-syndrome")
STYLE_MARKER = "condition-trust-v307-style"
SCHEMA_MARKER = "condition-trust-v307-schema"
CONTENT_MARKER = "condition-trust-v307-content"
ID_RE = re.compile(r'\bid="([^"]+)"')
SOURCE_ID_RE = re.compile(r'\bid="([AD]\d+)"')


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON object required: {path}")
    return payload


def load_config() -> dict[str, Any]:
    data = read_json(CONFIG)
    if data.get("version") != VERSION or data.get("language") != "ar":
        raise SystemExit("Condition trust configuration contract failed")
    try:
        reviewed = date.fromisoformat(str(data["reviewed_at"]))
        due = date.fromisoformat(str(data["next_review_due"]))
    except (KeyError, ValueError) as exc:
        raise SystemExit("Valid review dates are required") from exc
    if due <= reviewed:
        raise SystemExit("The next review date must follow the completed review date")
    if data.get("external_clinical_review_completed") is not False:
        raise SystemExit("External clinical review state must remain explicit and honest")
    conditions = data.get("conditions")
    if not isinstance(conditions, dict) or set(conditions) != set(SLUGS):
        raise SystemExit("Condition trust routes are incomplete")
    all_ids: set[str] = set()
    for slug in SLUGS:
        item = conditions[slug]
        faqs = item.get("faqs") if isinstance(item, dict) else None
        if not isinstance(faqs, list) or len(faqs) < 4:
            raise SystemExit(f"At least four FAQs are required: {slug}")
        prefix = str(item.get("source_prefix", ""))
        for faq in faqs:
            required = ("id", "question", "answer", "source_ids")
            if any(not faq.get(key) for key in required):
                raise SystemExit(f"Incomplete FAQ in {slug}: {faq}")
            faq_id = str(faq["id"])
            if faq_id in all_ids:
                raise SystemExit(f"Duplicate FAQ id: {faq_id}")
            all_ids.add(faq_id)
            refs = faq["source_ids"]
            if not isinstance(refs, list) or not refs or any(not str(ref).startswith(prefix) for ref in refs):
                raise SystemExit(f"FAQ source contract failed: {slug}/{faq_id}")
    return data


def marked(kind: str, body: str) -> str:
    return f"<!-- {kind}:start -->{body}<!-- {kind}:end -->"


def replace_marked(source: str, kind: str, block: str) -> tuple[str, bool]:
    start = f"<!-- {kind}:start -->"
    end = f"<!-- {kind}:end -->"
    if source.count(start) != source.count(end):
        raise SystemExit(f"Unbalanced marker: {kind}")
    if start not in source:
        return source, False
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    source, count = pattern.subn(block, source, count=1)
    if count != 1:
        raise SystemExit(f"Could not replace marker: {kind}")
    return source, True


def insert_before(source: str, kind: str, block: str, anchor: str) -> str:
    source, replaced = replace_marked(source, kind, block)
    if replaced:
        return source
    if source.count(anchor) != 1:
        raise SystemExit(f"Insertion anchor must occur once for {kind}: {anchor}")
    return source.replace(anchor, block + anchor, 1)


def insert_before_regex(source: str, kind: str, block: str, pattern: str) -> str:
    source, replaced = replace_marked(source, kind, block)
    if replaced:
        return source
    match = re.search(pattern, source, re.I | re.S)
    if not match:
        raise SystemExit(f"Regex insertion anchor missing for {kind}: {pattern}")
    return source[: match.start()] + block + source[match.start() :]


def render_style() -> str:
    css = """
.trust-review{padding:1rem 0 2.25rem}.trust-review-grid{display:grid;grid-template-columns:.8fr 1.2fr;gap:1rem;align-items:start}
.trust-card,.faq-card{background:#fff;border:1px solid #c6e2df;border-radius:18px;padding:1.1rem;box-shadow:0 12px 28px #104c4c14}
.trust-card dl{display:grid;grid-template-columns:max-content 1fr;gap:.35rem .75rem;margin:.6rem 0}.trust-card dt{font-weight:900}.trust-card dd{margin:0}
.trust-warning{border-inline-start:5px solid #8b2f5b;padding-inline-start:.8rem}.faq-list{display:grid;gap:.65rem}
.faq-list details{border:1px solid #c6e2df;border-radius:13px;background:#f9fdfc;padding:.7rem .85rem}.faq-list summary{cursor:pointer;font-weight:900}
.faq-list details[open] summary{margin-bottom:.45rem}.faq-answer{margin:.25rem 0}.faq-refs{display:flex;gap:.35rem;flex-wrap:wrap}
.faq-refs a{font-weight:900;background:#e9f8f5;border-radius:7px;padding:.1rem .4rem;text-decoration:none}
@media(max-width:820px){.trust-review-grid{grid-template-columns:1fr}}@media print{.trust-review-grid{display:block}.trust-card,.faq-card{box-shadow:none;margin-bottom:.8rem}.faq-list details{break-inside:avoid}}
""".strip()
    return marked(STYLE_MARKER, f"<style>{css}</style>")


def render_schema(faqs: list[dict[str, Any]]) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq["question"],
                "acceptedAnswer": {"@type": "Answer", "text": faq["answer"]},
            }
            for faq in faqs
        ],
    }
    body = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return marked(SCHEMA_MARKER, f'<script type="application/ld+json">{body}</script>')


def render_content(config: dict[str, Any], slug: str, source_count: int) -> str:
    item = config["conditions"][slug]
    faq_cards: list[str] = []
    for faq in item["faqs"]:
        refs = "".join(f'<a href="#{esc(ref)}">[{esc(ref)}]</a>' for ref in faq["source_ids"])
        faq_cards.append(
            f'<details id="{esc(faq["id"])}"><summary>{esc(faq["question"])}</summary>'
            f'<p class="faq-answer">{esc(faq["answer"])}</p><div class="faq-refs" aria-label="مراجع الإجابة">{refs}</div></details>'
        )
    external_state = "لم تكتمل بعد" if not config["external_clinical_review_completed"] else "مكتملة"
    body = f'''
<section class="trust-review" id="quality-and-faq" aria-labelledby="quality-and-faq-title">
  <div class="wrap trust-review-grid">
    <aside class="trust-card" aria-labelledby="quality-and-faq-title">
      <p class="kicker">حوكمة ومراجعة</p>
      <h2 id="quality-and-faq-title">بطاقة الثقة ودورة تحديث المحتوى</h2>
      <dl>
        <dt>آخر مراجعة</dt><dd><time datetime="{esc(config["reviewed_at"])}">{esc(config["reviewed_at"])}</time></dd>
        <dt>المراجعة التالية</dt><dd><time datetime="{esc(config["next_review_due"])}">{esc(config["next_review_due"])}</time></dd>
        <dt>المراجع الظاهرة</dt><dd>{source_count} مراجع مرتبطة بالمحاور</dd>
        <dt>المراجعة السريرية الخارجية</dt><dd>{external_state}</dd>
      </dl>
      <p>{esc(config["review_note"])}</p>
      <p class="trust-warning"><b>حدود الصفحة:</b> محتوى تثقيفي لا يثبت تشخيصًا ولا يحدد علاجًا فرديًا ولا يغني عن التقييم المهني.</p>
    </aside>
    <section class="faq-card" aria-labelledby="condition-faq-title">
      <p class="kicker">إجابات موثقة</p>
      <h2 id="condition-faq-title">أسئلة شائعة عن {esc(item["label"])}</h2>
      <div class="faq-list">{"".join(faq_cards)}</div>
    </section>
  </div>
</section>
'''.strip()
    return marked(CONTENT_MARKER, body)


def validate_page(source: str, slug: str, config: dict[str, Any], source_ids: set[str]) -> dict[str, Any]:
    item = config["conditions"][slug]
    required = (
        f"<!-- {STYLE_MARKER}:start -->",
        f"<!-- {SCHEMA_MARKER}:start -->",
        f"<!-- {CONTENT_MARKER}:start -->",
        '"@type": "FAQPage"',
        'id="quality-and-faq"',
        'id="condition-faq-title"',
        'class="trust-warning"',
        config["next_review_due"],
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise SystemExit(f"Trust and FAQ markers missing for {slug}: {missing}")
    ids = ID_RE.findall(source)
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    if duplicates:
        raise SystemExit(f"Duplicate HTML ids after trust injection in {slug}: {duplicates}")
    faqs = item["faqs"]
    for faq in faqs:
        if source.count(f'id="{faq["id"]}"') != 1 or source.count(esc(faq["question"])) != 2:
            raise SystemExit(f"Visible and structured FAQ mismatch: {slug}/{faq['id']}")
        missing_refs = [ref for ref in faq["source_ids"] if ref not in source_ids]
        if missing_refs:
            raise SystemExit(f"FAQ references are absent from the page: {slug}/{faq['id']}/{missing_refs}")
        for ref in faq["source_ids"]:
            if source.count(f'href="#{ref}"') < 1:
                raise SystemExit(f"FAQ reference link missing: {slug}/{faq['id']}/{ref}")
    return {
        "slug": slug,
        "faq_count": len(faqs),
        "source_count": len(source_ids),
        "next_review_due": config["next_review_due"],
        "faq_schema_visible_match": True,
        "external_clinical_review_completed": config["external_clinical_review_completed"],
    }


def enhance_page(site: Path, config: dict[str, Any], slug: str) -> dict[str, Any]:
    path = site / "special-needs" / slug / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing condition page for trust enhancement: {path}")
    source = path.read_text(encoding="utf-8")
    source_ids = set(SOURCE_ID_RE.findall(source))
    expected_prefix = config["conditions"][slug]["source_prefix"]
    if not source_ids or any(not ref.startswith(expected_prefix) for ref in source_ids):
        raise SystemExit(f"Unexpected source anchors in {slug}: {sorted(source_ids)}")
    source = insert_before(source, STYLE_MARKER, render_style(), "</head>")
    source = insert_before(source, SCHEMA_MARKER, render_schema(config["conditions"][slug]["faqs"]), "</head>")
    source = insert_before_regex(
        source,
        CONTENT_MARKER,
        render_content(config, slug, len(source_ids)),
        r'<section\b[^>]*\bid="directory"[^>]*>',
    )
    report = validate_page(source, slug, config, source_ids)
    path.write_text(source, encoding="utf-8")
    return report


def publish(site: Path) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    config = load_config()
    pages = [enhance_page(site, config, slug) for slug in SLUGS]
    report = {
        "version": VERSION,
        "status": "passed",
        "reviewed_at": config["reviewed_at"],
        "next_review_due": config["next_review_due"],
        "condition_slugs": list(SLUGS),
        "condition_count": len(pages),
        "faq_count": sum(item["faq_count"] for item in pages),
        "minimum_source_count": min(item["source_count"] for item in pages),
        "faq_schema_visible_match": all(item["faq_schema_visible_match"] for item in pages),
        "external_clinical_review_completed": config["external_clinical_review_completed"],
        "config_source": CONFIG.relative_to(ROOT).as_posix(),
        "pages": pages,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-condition-trust-v307.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
