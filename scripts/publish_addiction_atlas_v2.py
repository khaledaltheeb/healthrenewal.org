from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILES = [
    ROOT / "data/addiction-atlas/substances-v1.json",
    ROOT / "data/addiction-atlas/substances-v2.json",
]
COMPARISONS = ROOT / "data/addiction-atlas/comparison-intents-v2.json"
METHOD = ROOT / "data/addiction-atlas/methodology-v1.json"

REQUIRED = [
    "slug", "display_name_ar", "display_name_en", "class_ar", "forms_ar",
    "summary_ar", "mechanism_ar", "acute_effects_ar", "long_term_harms_ar",
    "single_exposure_harm_ar", "withdrawal_ar", "emergency_response_ar",
    "treatment_ar", "risk", "evidence_grade", "source_urls",
]
RISK_KEYS = [
    "acute_toxicity", "overdose_risk", "dependence", "withdrawal_medical_risk",
    "neuro_harm", "cardio_harm", "respiratory_harm", "polysubstance_risk",
]

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def merge_substances():
    merged = {}
    for path in DATA_FILES:
        payload = load_json(path)
        for item in payload.get("substances", []):
            merged[item["slug"]] = item
    return merged


def validate_substance(item):
    missing = [key for key in REQUIRED if key not in item or item[key] in (None, "", [])]
    if missing:
        raise ValueError(f"{item.get('slug','?')}: missing {missing}")
    if len(item["source_urls"]) < 1:
        raise ValueError(f"{item['slug']}: at least one source URL is required")
    for url in item["source_urls"]:
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(f"{item['slug']}: invalid source URL {url!r}")
    if set(item["risk"]) != set(RISK_KEYS):
        raise ValueError(f"{item['slug']}: risk dimensions mismatch")
    for key, value in item["risk"].items():
        if value is not None and (not isinstance(value, int) or not 1 <= value <= 5):
            raise ValueError(f"{item['slug']}: invalid risk {key}={value!r}")


def e(value):
    return html.escape(str(value), quote=True)


def risk_badge(value):
    if value is None:
        return '<span class="risk-badge risk-unknown">غير محسوم</span>'
    return f'<span class="risk-badge risk-{value}">{value}/5</span>'


def list_items(values):
    return "".join(f"<li>{e(v)}</li>" for v in values)


def source_items(values):
    return "".join(f'<li><a href="{e(v)}" rel="noopener">{e(v)}</a></li>' for v in values)


def substance_page(s, method):
    canonical = f"https://healthrenewal.org/addiction/substances/{s['slug']}/"
    risk_rows = []
    for key, meta in method["risk_dimensions"].items():
        risk_rows.append(f"<tr><th>{e(meta['label_ar'])}</th><td>{risk_badge(s['risk'].get(key))}</td><td>{e(meta['definition_ar'])}</td></tr>")
    medical = s.get("medical_use_ar") or "لا يوجد استخدام طبي مشروع معروف في هذا السياق أو لا ينطبق هذا الحقل على السجل."
    common = s.get("common_name_ar") or s["display_name_ar"]
    title = f"{s['display_name_ar']} {s['display_name_en']} | التأثير والمخاطر والعلاج | روافد"
    description = f"مرجع عربي عن {s['display_name_ar']} ({s['display_name_en']}): التأثير والسمية والجرعة الزائدة والاعتماد والانسحاب والأضرار والعلاج وقوة الدليل."
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{e(title)}</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{canonical}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="stylesheet" href="/assets/brand/rawafid-brand.css"><link rel="stylesheet" href="/assets/addiction/condition-guides-v3.css?v=3"><link rel="stylesheet" href="/assets/addiction/atlas-v1.css?v=2"><script defer src="/assets/brand/rawafid-brand.js"></script><script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","inLanguage":"ar","name":{json.dumps(s['display_name_ar'], ensure_ascii=False)},"url":"{canonical}","dateModified":"2026-08-25","publisher":{{"@type":"Organization","name":"منصة روافد","url":"https://healthrenewal.org/"}}}}</script></head><body><header class="site-head"><div class="wrap"><nav class="nav" aria-label="التنقل الأساسي"><a href="/addiction/">مركز الإدمان</a><a href="/addiction/substances/">أطلس المواد</a><a href="/addiction/compare/?a={e(s['slug'])}">قارن هذه المادة</a><a href="/addiction/methodology/">المنهجية</a><a href="/addiction/sources/">المراجع</a></nav></div></header><main class="atlas-shell"><section class="atlas-hero"><div class="atlas-kicker"><span class="atlas-pill">{e(s['class_ar'])}</span><span class="atlas-pill">قوة الدليل: {e(s['evidence_grade'])}</span></div><h1>{e(s['display_name_ar'])} <span lang="en">{e(s['display_name_en'])}</span></h1><p class="atlas-lead">{e(s['summary_ar'])}</p><div class="name-list"><span class="name-chip">الاسم العربي: {e(s['display_name_ar'])}</span><span class="name-chip" lang="en">English: {e(s['display_name_en'])}</span><span class="name-chip">الاسم المتعارف عليه: {e(common)}</span></div><div class="atlas-actions"><a class="atlas-btn" href="/addiction/compare/?a={e(s['slug'])}">قارن بمادة أخرى</a><button class="atlas-btn secondary" onclick="window.print()">طباعة</button></div></section><section class="atlas-note atlas-danger"><h2>السلامة أولاً</h2><p>{e(s['emergency_response_ar'])}</p></section><section><h2>التعريف والتصنيف</h2><p>{e(s['mechanism_ar'])}</p><p><strong>الاستخدام الطبي المشروع:</strong> {e(medical)}</p><p><strong>الأشكال:</strong> {e('، '.join(s['forms_ar']))}. المظهر وحده لا يثبت هوية المادة أو نقاءها أو تركيزها.</p></section><section><h2>ملف المخاطر متعدد المحاور</h2><div class="atlas-table-wrap"><table class="atlas-table"><thead><tr><th>المحور</th><th>التقدير</th><th>التعريف</th></tr></thead><tbody>{''.join(risk_rows)}</tbody></table></div><p class="atlas-meta">الدرجات ترتيبية داخل كل محور وليست نسباً لاحتمال الوفاة أو الإدمان. «غير محسوم» يعني أن الدليل لا يسمح بتقدير مسؤول.</p></section><section><h2>التأثيرات قصيرة المدى</h2><ul>{list_items(s['acute_effects_ar'])}</ul></section><section><h2>الأضرار طويلة المدى</h2><ul>{list_items(s['long_term_harms_ar'])}</ul></section><section><h2>هل يمكن أن يحدث ضرر جسيم من تعرض واحد؟</h2><p>{e(s['single_exposure_harm_ar'])}</p></section><section><h2>الاعتماد والانسحاب</h2><p>{e(s['withdrawal_ar'])}</p></section><section><h2>العلاج والتعافي</h2><p>{e(s['treatment_ar'])}</p></section><section><h2>ما نعرفه وما لا نعرفه</h2><div class="atlas-grid"><article class="atlas-card"><h3>المعرفة الحالية</h3><p>تستند هذه الصفحة إلى مصادر مؤسسية أو علمية موثوقة مدرجة أدناه، وتُعرض قوة الدليل منفصلة عن شدة الخطر.</p></article><article class="atlas-card"><h3>حدود الدليل</h3><p>لا تُملأ الحقول غير المعروفة بالتخمين، ولا تُعرض نسبة «إدمان من أول مرة» أو «وفاة من أول جرعة» دون دليل مباشر صالح للسياق.</p></article></div></section><section><h2>المصادر</h2><ul class="sources">{source_items(s['source_urls'])}</ul></section></main><footer><div class="wrap"><p>مراجعة تحريرية داخلية: فريق روافد — آخر تحديث 25 أغسطس 2026.</p></div></footer></body></html>'''


def comparison_page(c, a, b, method):
    canonical = f"https://healthrenewal.org/addiction/compare/{c['slug']}/"
    rows = []
    for key, meta in method["risk_dimensions"].items():
        rows.append(f"<tr><th>{e(meta['label_ar'])}</th><td>{risk_badge(a['risk'].get(key))}</td><td>{risk_badge(b['risk'].get(key))}</td></tr>")
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{e(c['title_ar'])} | مقارنة علمية | روافد</title><meta name="description" content="{e(c['title_ar'])}: مقارنة متعددة المحاور في {e(c['intent_ar'])} مع قوة الدليل وروابط المصادر."><link rel="canonical" href="{canonical}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="stylesheet" href="/assets/brand/rawafid-brand.css"><link rel="stylesheet" href="/assets/addiction/condition-guides-v3.css?v=3"><link rel="stylesheet" href="/assets/addiction/atlas-v1.css?v=2"></head><body><header class="site-head"><div class="wrap"><nav class="nav"><a href="/addiction/">مركز الإدمان</a><a href="/addiction/substances/">أطلس المواد</a><a href="/addiction/compare/">قارن</a></nav></div></header><main class="atlas-shell"><section class="atlas-hero"><div class="atlas-kicker"><span class="atlas-pill">مقارنة مستقلة</span><span class="atlas-pill">محاور متعددة</span></div><h1>{e(c['title_ar'])}</h1><p class="atlas-lead">تركز هذه المقارنة على {e(c['intent_ar'])}. لا تعني النتيجة أن إحدى المادتين «آمنة»؛ يختلف الخطر حسب المحور والسياق وقوة الدليل.</p><div class="atlas-actions"><a class="atlas-btn secondary" href="/addiction/substances/{e(a['slug'])}/">صفحة {e(a['display_name_ar'])}</a><a class="atlas-btn secondary" href="/addiction/substances/{e(b['slug'])}/">صفحة {e(b['display_name_ar'])}</a><button class="atlas-btn" onclick="window.print()">طباعة</button></div></section><section><h2>المقارنة السريعة</h2><div class="atlas-table-wrap"><table class="compare-table"><thead><tr><th>المحور</th><th>{e(a['display_name_ar'])}<br><small lang="en">{e(a['display_name_en'])}</small></th><th>{e(b['display_name_ar'])}<br><small lang="en">{e(b['display_name_en'])}</small></th></tr></thead><tbody><tr><th>الفئة</th><td>{e(a['class_ar'])}</td><td>{e(b['class_ar'])}</td></tr>{''.join(rows)}<tr><th>قوة الدليل</th><td>{e(a['evidence_grade'])}</td><td>{e(b['evidence_grade'])}</td></tr></tbody></table></div></section><section><h2>الفرق في التأثير والمخاطر</h2><div class="atlas-grid"><article class="atlas-card"><h3>{e(a['display_name_ar'])}</h3><p>{e(a['summary_ar'])}</p><p><strong>الانسحاب:</strong> {e(a['withdrawal_ar'])}</p><p><strong>الاستجابة للتسمم:</strong> {e(a['emergency_response_ar'])}</p></article><article class="atlas-card"><h3>{e(b['display_name_ar'])}</h3><p>{e(b['summary_ar'])}</p><p><strong>الانسحاب:</strong> {e(b['withdrawal_ar'])}</p><p><strong>الاستجابة للتسمم:</strong> {e(b['emergency_response_ar'])}</p></article></div></section><section><h2>كيف تفسر المقارنة؟</h2><p>لا يجوز جمع الدرجات تلقائياً في رقم خطورة كلي. «غير محسوم» يعني عدم كفاية الأدلة، وليس انخفاض الخطر. المقارنة تهدف إلى فهم الفروق لا إلى اختيار مادة للاستخدام.</p></section><section><h2>المصادر</h2><div class="atlas-grid"><article class="atlas-card"><h3>مصادر {e(a['display_name_ar'])}</h3><ul class="sources">{source_items(a['source_urls'])}</ul></article><article class="atlas-card"><h3>مصادر {e(b['display_name_ar'])}</h3><ul class="sources">{source_items(b['source_urls'])}</ul></article></div></section></main><footer><div class="wrap"><p>منصة روافد — مقارنة تعليمية قائمة على الأدلة، آخر تحديث 25 أغسطس 2026.</p></div></footer></body></html>'''


def publish(site: Path):
    method = load_json(METHOD)
    substances = merge_substances()
    for s in substances.values():
        validate_substance(s)
    comparisons = load_json(COMPARISONS).get("comparisons", [])
    for c in comparisons:
        if not c.get("indexable"):
            continue
        if c["a"] not in substances or c["b"] not in substances:
            raise ValueError(f"comparison references missing substance: {c}")
    substance_root = site / "addiction/substances"
    compare_root = site / "addiction/compare"
    substance_root.mkdir(parents=True, exist_ok=True)
    compare_root.mkdir(parents=True, exist_ok=True)
    generated = 0
    preserved = 0
    for s in substances.values():
        dest = substance_root / s["slug"] / "index.html"
        if dest.exists():
            preserved += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(substance_page(s, method), encoding="utf-8")
        generated += 1
    generated_comparisons = 0
    preserved_comparisons = 0
    for c in comparisons:
        if not c.get("indexable"):
            continue
        dest = compare_root / c["slug"] / "index.html"
        if dest.exists():
            preserved_comparisons += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(comparison_page(c, substances[c["a"]], substances[c["b"]], method), encoding="utf-8")
        generated_comparisons += 1
    report = {
        "schemaVersion": 2,
        "status": "passed",
        "substances": len(substances),
        "generatedSubstancePages": generated,
        "preservedSubstancePages": preserved,
        "indexableComparisons": sum(1 for c in comparisons if c.get("indexable")),
        "generatedComparisonPages": generated_comparisons,
        "preservedComparisonPages": preserved_comparisons,
        "unknownRiskValues": sum(1 for s in substances.values() for v in s["risk"].values() if v is None),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "addiction-atlas-v2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site")
    args = parser.parse_args()
    publish(Path(args.site))
