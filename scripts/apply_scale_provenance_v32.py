from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import add_lab_data_controls_v32 as lab_data_controls

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "v32" / "official-scale-provenance-ar.json"
START = "<!-- scale-provenance-v32:start -->"
END = "<!-- scale-provenance-v32:end -->"
EXPECTED = {"phq9", "gad7", "who5", "audit_guided"}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def extract_definition(source: str) -> dict:
    match = re.search(r'<script type="application/json" id="lab-definition">(.*?)</script>', source, re.S)
    if not match:
        raise ValueError("missing lab-definition")
    return json.loads(match.group(1).replace("<\\/", "</"))


def write_definition(source: str, definition: dict) -> str:
    payload = json.dumps(definition, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    updated, count = re.subn(
        r'(<script type="application/json" id="lab-definition">).*?(</script>)',
        lambda match: match.group(1) + payload + match.group(2),
        source,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise ValueError("definition replacement failed")
    return updated


def replace_or_insert(source: str, fragment: str) -> str:
    pattern = re.escape(START) + r".*?" + re.escape(END)
    if re.search(pattern, source, re.S):
        return re.sub(pattern, fragment, source, count=1, flags=re.S)
    anchor = "<!-- lab-depth-v32:body:start -->"
    if anchor in source:
        return source.replace(anchor, fragment + anchor, 1)
    if "<footer" in source:
        return source.replace("<footer", fragment + "<footer", 1)
    return source.replace("</main>", fragment + "</main>", 1)


def fragment(profile: dict) -> str:
    return f'''{START}<section class="scale-provenance-v32" aria-labelledby="scale-provenance-v32-title">
<style>.scale-provenance-v32{{display:grid;gap:1rem;margin-block:2rem}}.scale-provenance-v32__card{{background:#fff;border:1px solid #b9ddd8;border-radius:1.25rem;padding:1.25rem;line-height:1.95}}.scale-provenance-v32__warning{{border-inline-start:6px solid #9b2c2c;background:#fff7f7}}</style>
<h2 id="scale-provenance-v32-title">مصدر النسخة العربية وحدود نقل الصلاحية</h2>
<section class="scale-provenance-v32__card scale-provenance-v32__warning"><h3>حالة هذه الصفحة</h3><p>{esc(profile['status'])}</p><p><strong>قاعدة الاستخدام:</strong> {esc(profile['usage_rule'])}</p></section>
<section class="scale-provenance-v32__card"><h3>الدليل الأصلي</h3><p>{esc(profile['original_reference'])}</p><p><a href="{esc(profile['original_url'])}" rel="noopener">فتح المرجع الأصلي</a></p></section>
<section class="scale-provenance-v32__card"><h3>الدليل أو الحالة العربية</h3><p>{esc(profile['arabic_reference'])}</p><p>{esc(profile['arabic_evidence'])}</p><p><a href="{esc(profile['arabic_url'])}" rel="noopener">فتح مرجع النسخة/الدليل العربي</a></p></section>
<section class="scale-provenance-v32__card"><h3>الحقوق والترخيص</h3><p>{esc(profile['rights'])}</p></section>
</section>{END}'''


def patch_runtime(site: Path) -> dict:
    runtime = site / "assets" / "js" / "lab-v12.js"
    if not runtime.is_file():
        raise SystemExit(f"missing runtime: {runtime}")
    source = runtime.read_text(encoding="utf-8")
    old = "interpretation=`هذا وصف لشدة الأعراض المبلغ عنها ضمن فترة الأداة، وليس تشخيصًا. ${partial?'النتيجة مؤقتة لأن بعض البنود لم تُجب بعد؛ لا تستخدم نطاق الشدة قبل الإكمال.':'اربط المجموع بالتعطل اليومي والسياق والتقييم المهني عند الحاجة.'}`;"
    new = "interpretation=`هذا وصف لشدة الأعراض المبلغ عنها ضمن فترة الأداة، وليس تشخيصًا. ${partial?'النتيجة مؤقتة لأن بعض البنود لم تُجب بعد؛ لا تستخدم نطاق الشدة قبل الإكمال.':'اربط المجموع بالتعطل اليومي والسياق والتقييم المهني عند الحاجة.'} ${d.provenance_notice||''}`;"
    if "${d.provenance_notice||''}" not in source:
        if old not in source:
            raise SystemExit("assessment provenance runtime anchor not found")
        source = source.replace(old, new, 1)

    old_who = "heading='WHO-5 — العافية النفسية الحالية';primary=`<div class=\"result-score\">${score.percent} / 100</div>`;\n  interpretation=`الدرجة الخام ${score.raw} من ${score.max}، وحُولت بضربها في أربعة. الدرجة الأعلى تعكس عافية أفضل؛ النتيجة لا تستبعد اضطرابًا أو خطرًا ولا تقدم تشخيصًا.`;"
    new_who = "heading='متابعة العافية بخمسة بنود — عرض عربي متكيف';primary=`<div class=\"result-score\">${score.percent} / 100</div>`;\n  interpretation=`الدرجة الخام ${score.raw} من ${score.max}، وحُولت حسابيًا بضربها في أربعة. الصياغة العربية المعروضة متكيفة وليست مطابقة للنص العربي المنشور مع WHO-5، لذلك تُستخدم النتيجة للتتبع الوصفي فقط ولا تُعامل كدرجة نسخة عربية معيارية أو تشخيص. ${d.provenance_notice||''}`;"
    if "عرض عربي متكيف" not in source:
        if old_who not in source:
            raise SystemExit("WHO-5 runtime anchor not found")
        source = source.replace(old_who, new_who, 1)

    runtime.write_text(source, encoding="utf-8")
    return {
        "runtime": runtime.relative_to(site).as_posix(),
        "generic_notice": "${d.provenance_notice||''}" in source,
        "who5_adapted_label": "متابعة العافية بخمسة بنود — عرض عربي متكيف" in source,
        "who5_no_validated_arabic_claim": "ليست مطابقة للنص العربي المنشور مع WHO-5" in source,
    }


def apply(site: Path) -> dict:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    profiles = data.get("instruments") or {}
    if set(profiles) != EXPECTED:
        raise SystemExit({"expected": sorted(EXPECTED), "actual": sorted(profiles)})

    pages = []
    found = set()
    for path in sorted((site / "assessment-lab").glob("*/index.html")):
        source = path.read_text(encoding="utf-8")
        definition = extract_definition(source)
        score_type = str(definition.get("score_type") or "")
        if score_type not in profiles:
            continue
        profile = profiles[score_type]
        found.add(score_type)
        definition["provenance_reviewed_at"] = data["reviewed_at"]
        definition["provenance_status"] = profile["status"]
        definition["provenance_notice"] = "حدود الدرجات وخصائص الصلاحية تعود إلى إصدار موثق؛ راجع قسم مصدر النسخة العربية قبل تعميمها على الصياغة الرقمية الحالية."
        definition["rights_status"] = profile["rights"]
        if score_type == "who5":
            definition["instrument_type"] = "عرض عربي متكيف مستلهم من WHO-5؛ غير معياري بهذه الصياغة"
            definition["scoring_policy"] = "descriptive_transformation_only"
            definition["title"] = "متابعة العافية بخمسة بنود — عرض عربي متكيف مستلهم من WHO-5"
            source = re.sub(r"<h1>.*?</h1>", f"<h1>{esc(definition['title'])}</h1>", source, count=1, flags=re.S)
        source = write_definition(source, definition)
        provenance = fragment(profile)
        source = replace_or_insert(source, provenance)
        path.write_text(source, encoding="utf-8")
        pages.append({
            "score_type": score_type,
            "path": path.relative_to(site).as_posix(),
            "status_visible": profile["status"] in provenance,
            "rights_visible": profile["rights"] in provenance,
            "arabic_evidence_visible": profile["arabic_evidence"] in provenance,
        })

    runtime = patch_runtime(site)
    controls = lab_data_controls.patch(site)
    failures = [row for row in pages if not all(row[key] for key in ("status_visible", "rights_visible", "arabic_evidence_visible"))]
    report = {
        "version": 32,
        "status": "passed" if found == EXPECTED and len(pages) == 4 and not failures and all(runtime[key] for key in ("generic_notice", "who5_adapted_label", "who5_no_validated_arabic_claim")) and controls.get("status") == "passed" and controls.get("total_tools") == 93 else "failed",
        "reviewed_at": data["reviewed_at"],
        "expected": sorted(EXPECTED),
        "found": sorted(found),
        "pages": pages,
        "failures": failures,
        "runtime": runtime,
        "data_controls": controls,
        "who5_policy": "adapted_arabic_descriptive_only",
        "arabic_exact_text_required_before_validated_claim": True,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "scale-provenance-v32.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        raise SystemExit(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(apply(args.site.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
