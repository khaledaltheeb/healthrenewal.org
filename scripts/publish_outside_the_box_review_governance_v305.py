#!/usr/bin/env python3
"""Publish the scientific review governance layer for outside-the-box.

The publisher creates a transparent register for 100 conditions, 600 claim-domain
reviews and 1000 plan reviews. It deliberately records zero independent approvals
until real reviewer evidence is supplied. It does not diagnose or grant accreditation.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS_PATH = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
FRAMEWORK_PATH = ROOT / "content" / "v302" / "outside-the-box-ten-plan-framework-ar.json"
GOVERNANCE_PATH = ROOT / "content" / "v305" / "outside-the-box-review-governance-ar.json"
CSS_PATH = ROOT / "assets" / "css" / "outside-the-box-review-governance-v305.css"

BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
SECTION = "outside-the-box"
ROUTE = "review-governance"
VERSION = 305
UPDATED = "2026-07-27"
HUB_START = "<!-- outside-the-box-review-governance-v305-hub:start -->"
HUB_END = "<!-- outside-the-box-review-governance-v305-hub:end -->"
CONDITION_START = "<!-- outside-the-box-review-governance-v305-condition:start -->"
CONDITION_END = "<!-- outside-the-box-review-governance-v305-condition:end -->"
STYLE_MARKER = "<!-- outside-the-box-review-governance-v305:style -->"
SITEMAP_NAME = "sitemap-outside-the-box.xml"


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def load_sources() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    data = json.loads(CONDITIONS_PATH.read_text(encoding="utf-8"))
    framework = json.loads(FRAMEWORK_PATH.read_text(encoding="utf-8"))
    governance = json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8"))
    if data.get("version") != 254 or framework.get("version") != 302 or governance.get("version") != VERSION:
        raise ValueError("Unexpected outside-the-box source versions")
    if len(data.get("conditions", [])) != 100:
        raise ValueError("Review governance requires exactly 100 conditions")
    if len(framework.get("plan_families", [])) != 10:
        raise ValueError("Review governance requires exactly ten plan families")
    if len(governance.get("claim_domains", [])) != 6:
        raise ValueError("Review governance requires six claim domains")
    role_ids = [item["id"] for item in governance.get("reviewer_roles", [])]
    if len(role_ids) < 9 or len(role_ids) != len(set(role_ids)):
        raise ValueError("Reviewer-role registry is incomplete or duplicated")
    if governance["scope"]["external_review_completed"] is not False:
        raise ValueError("External review must remain false until evidence is recorded")
    return data, framework, governance


def condition_source_keys(data: dict[str, Any], condition: dict[str, Any]) -> list[str]:
    cluster = data["clusters"][condition["cluster"]]
    keys = [*condition["source_keys"], *cluster["source_keys"]]
    for protocol_key in condition["protocol_keys"]:
        keys.extend(data["protocols"][protocol_key]["source_keys"])
    valid = [key for key in dedupe(keys) if key in data["sources"]]
    if len(valid) < 2:
        raise ValueError(f"Condition {condition['slug']} has insufficient source linkage")
    return valid


def domain_sources(data: dict[str, Any], condition: dict[str, Any], domain_id: str) -> list[str]:
    cluster = data["clusters"][condition["cluster"]]
    protocol_sources: list[str] = []
    for protocol_key in condition["protocol_keys"]:
        protocol_sources.extend(data["protocols"][protocol_key]["source_keys"])
    mapping = {
        "definition-classification": [*condition["source_keys"], *cluster["source_keys"]],
        "prevalence-burden": [*condition["source_keys"], *cluster["source_keys"]],
        "assessment-measurement": [*condition["source_keys"], *cluster["source_keys"], "who-icf"],
        "intervention-support": [*protocol_sources, *condition["source_keys"]],
        "outcomes-strengths": [*protocol_sources, *cluster["source_keys"], "who-icf"],
        "safety-rights": [*cluster["source_keys"], *condition["source_keys"], "who-icf", "nice-complex"],
    }
    keys = [key for key in dedupe(mapping[domain_id]) if key in data["sources"]]
    if len(keys) < 2:
        keys = condition_source_keys(data, condition)
    return keys[:10]


def plan_roles(kind: str) -> list[str]:
    mapping = {
        "assessment_and_safety": ["condition-specialist", "safeguarding-reviewer", "psychometric-reviewer"],
        "person_centered_outcome": ["condition-specialist", "lived-experience-reviewer", "implementation-reviewer"],
        "access_and_accommodation": ["implementation-reviewer", "lived-experience-reviewer", "disability-rights-reviewer"],
        "communication_and_consent": ["condition-specialist", "lived-experience-reviewer", "disability-rights-reviewer"],
        "evidence_linked_protocol": ["condition-specialist", "evidence-methodologist", "implementation-reviewer", "lived-experience-reviewer"],
        "implementation_support": ["implementation-reviewer", "lived-experience-reviewer", "condition-specialist"],
        "participation_and_strengths": ["evidence-methodologist", "lived-experience-reviewer", "disability-rights-reviewer", "condition-specialist"],
        "maintenance_and_transition": ["condition-specialist", "implementation-reviewer", "lived-experience-reviewer"],
    }
    return mapping[kind]


def plan_risk(kind: str) -> str:
    if kind == "assessment_and_safety":
        return "critical"
    if kind in {"communication_and_consent", "evidence_linked_protocol", "participation_and_strengths"}:
        return "high"
    return "moderate"


def plan_source_keys(
    data: dict[str, Any], condition: dict[str, Any], family: dict[str, Any]
) -> list[str]:
    order = family["order"]
    if 5 <= order <= 7:
        protocol_key = condition["protocol_keys"][order - 5]
        preferred = [*data["protocols"][protocol_key]["source_keys"], *condition["source_keys"]]
    else:
        generic = {
            1: ["who-icf", "nice-complex"],
            2: ["who-icf", "gas", "wwc-scd"],
            3: ["who-icf", "udl", "unicef-inclusive"],
            4: ["who-icf", "asha", "aaidd"],
            8: ["who-cst", "dec", "wwc-scd"],
            9: ["who-icf", "unicef-inclusive", "aaidd"],
            10: ["who-icf", "dec", "nice-complex"],
        }
        preferred = [*generic[order], *condition["source_keys"]]
    keys = [key for key in dedupe(preferred) if key in data["sources"]]
    if len(keys) < 2:
        keys = condition_source_keys(data, condition)
    return keys[:8]


def build_register(
    data: dict[str, Any], framework: dict[str, Any], governance: dict[str, Any]
) -> dict[str, Any]:
    role_ids = {item["id"] for item in governance["reviewer_roles"]}
    conditions = []
    claim_count = 0
    plan_count = 0
    for condition in data["conditions"]:
        claims = []
        required_roles: list[str] = []
        for domain in governance["claim_domains"]:
            keys = domain_sources(data, condition, domain["id"])
            if len(keys) < domain["minimum_sources"]:
                raise ValueError((condition["slug"], domain["id"], keys))
            if not set(domain["required_roles"]).issubset(role_ids):
                raise ValueError(f"Unknown reviewer role in {domain['id']}")
            required_roles.extend(domain["required_roles"])
            claims.append(
                {
                    "id": domain["id"],
                    "title": domain["title"],
                    "risk": domain["risk"],
                    "status": "awaiting-independent-review",
                    "minimum_sources": domain["minimum_sources"],
                    "source_keys": keys,
                    "required_roles": domain["required_roles"],
                    "open_checks": [
                        "تحقق من حداثة المصدر وإصداره وحالته الحالية.",
                        "تحقق من مباشرة المصدر للسكان واللغة والسياق والادعاء.",
                        "سجل صياغة الادعاء المقبولة وحدودها والمخاطر المتبقية."
                    ],
                    "reviews": [],
                    "decision": "awaiting-independent-review"
                }
            )
            claim_count += 1
        plans = []
        for family in framework["plan_families"]:
            roles = plan_roles(family["kind"])
            if not set(roles).issubset(role_ids):
                raise ValueError(f"Unknown plan reviewer role: {family['id']}")
            required_roles.extend(roles)
            plans.append(
                {
                    "id": family["id"],
                    "order": family["order"],
                    "title": family["title"],
                    "kind": family["kind"],
                    "risk": plan_risk(family["kind"]),
                    "status": "awaiting-independent-review",
                    "required_roles": roles,
                    "source_keys": plan_source_keys(data, condition, family),
                    "required_checks": [
                        "مطابقة الهدف والاستخدام وعدم الاستخدام مع احتياجات الفرد.",
                        "صلاحية خط الأساس والجرعة ومؤشرات النتيجة وجودة التنفيذ.",
                        "سلامة التكييفات وقاعدة التوقف والتصعيد.",
                        "عدم تحويل الخطة إلى تشخيص أو وصفة أو امتثال قسري.",
                        "ربط النتيجة بالنشاط والمشاركة والاختيار والاستقلال."
                    ],
                    "reviews": [],
                    "decision": "awaiting-independent-review"
                }
            )
            plan_count += 1
        conditions.append(
            {
                "review_id": f"otb-review-{condition['rank']:03d}-{condition['slug']}",
                "rank": condition["rank"],
                "slug": condition["slug"],
                "title_ar": condition["title_ar"],
                "title_en": condition["title_en"],
                "cluster": condition["cluster"],
                "cluster_title": data["clusters"][condition["cluster"]]["title"],
                "url": BASE + SECTION + "/" + condition["slug"] + "/",
                "status": "awaiting-independent-review",
                "external_review_completed": False,
                "required_roles": dedupe(required_roles),
                "claim_reviews": claims,
                "plan_reviews": plans,
                "external_reviews": [],
                "change_log": [],
                "residual_risks": [
                    "المصادر الحالية مرتبطة بالمحتوى، لكن ترحيل جميع سجلاتها إلى عقد بيانات ببليوغرافي كامل ما يزال قيد العمل.",
                    "لا يجوز تفسير نشر الصفحة بوصفه اعتمادًا سريريًا أو تقنينًا عربيًا للأدوات."
                ]
            }
        )
    source_inventory = []
    missing_contract_metadata = 0
    for key, source in data["sources"].items():
        complete = all(field in source for field in ("year", "verified_at", "source_type", "status", "claims_supported"))
        if not complete:
            missing_contract_metadata += 1
        source_inventory.append(
            {
                "key": key,
                "organization": source["organization"],
                "title": source["title"],
                "url": source["url"],
                "use": source["use"],
                "contract_metadata_status": "complete" if complete else "legacy-basic-record-needs-migration"
            }
        )
    return {
        "version": VERSION,
        "updated_at": UPDATED,
        "status": "passed",
        "review_state": "awaiting-independent-review",
        "condition_count": len(conditions),
        "claim_domain_count": len(governance["claim_domains"]),
        "claim_review_count": claim_count,
        "plans_per_condition": 10,
        "plan_review_count": plan_count,
        "independent_reviews_recorded": 0,
        "conditions_approved": 0,
        "plans_approved": 0,
        "external_review_completed": False,
        "global_accreditation_claim": False,
        "diagnostic_automation": False,
        "proprietary_test_items_published": False,
        "review_contract": governance,
        "source_contract_migration": {
            "source_count": len(source_inventory),
            "records_missing_full_contract_metadata": missing_contract_metadata,
            "status": "in-progress" if missing_contract_metadata else "complete"
        },
        "source_inventory": source_inventory,
        "conditions": conditions
    }


def replace_marker(text: str, start: str, end: str, block: str) -> str:
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError("Malformed review-governance marker block")
        left, rest = text.split(start, 1)
        _, right = rest.split(end, 1)
        return left + block + right
    marker = "</main>"
    if marker not in text:
        raise ValueError("Page main element was not found")
    return text.replace(marker, block + "\n" + marker, 1)


def ensure_stylesheet(text: str) -> str:
    href = BASE_PATH + "assets/css/" + CSS_PATH.name
    if href in text:
        return text
    marker = f'{STYLE_MARKER}<link rel="stylesheet" href="{href}">'
    if "</head>" not in text:
        raise ValueError("Page head was not found")
    return text.replace("</head>", marker + "</head>", 1)


def hub_block() -> str:
    return f"""{HUB_START}
<section class="rg-section" data-review-governance-v305><div class="rg-wrap">
<p class="rg-kicker">شفافية المراجعة العلمية</p><h2>سجل مراجعة مفتوح للحالات المئة والخطط الألف</h2>
<p class="rg-muted">المحتوى منشور بعد مراجعة منهجية داخلية، لكن عدد الموافقات التخصصية المستقلة المسجلة حاليًا هو صفر. تعرض لوحة الحوكمة ما يحتاج إلى مراجعة، ومن يراجعه، وما الدليل المطلوب، وكيف يُنشر التصحيح بإصدار قابل للتتبع.</p>
<div class="rg-actions"><a class="rg-button" href="{ROUTE}/">فتح لوحة المراجعة العلمية</a><a class="rg-button secondary" href="evidence-standard/">معيار الأدلة</a><a class="rg-button secondary" href="instruments/">سجل الأدوات</a></div>
</div></section>
{HUB_END}"""


def condition_block(condition: dict[str, Any]) -> str:
    return f"""{CONDITION_START}
<section class="rg-condition-note" data-review-governance-v305 aria-labelledby="review-state-{e(condition['slug'])}">
<h2 id="review-state-{e(condition['slug'])}">حالة المراجعة العلمية لهذا المسار</h2>
<p>هذا المسار جزء من سجل يضم ستة مجالات ادعاء وعشر خطط. لم تُسجل له بعد موافقة تخصصية مستقلة؛ لذلك لا يوصف بأنه معتمد سريريًا، ويجب تخصيصه ومراجعته مهنيًا قبل التطبيق.</p>
<dl><div><dt>مجالات الادعاء</dt><dd>6 بانتظار المراجعة</dd></div><div><dt>الخطط</dt><dd>10 بانتظار المراجعة</dd></div><div><dt>الموافقات المستقلة</dt><dd>0</dd></div></dl>
<div class="rg-actions"><a class="rg-button secondary" href="../{ROUTE}/#condition-{e(condition['slug'])}">فتح سجل هذه الحالة</a></div>
</section>
{CONDITION_END}"""


def render_dashboard(data: dict[str, Any], governance: dict[str, Any], report: dict[str, Any]) -> str:
    role_cards = "".join(
        f'<article class="rg-card"><h3>{e(role["title"])}</h3><p class="rg-muted">{e(role["minimum_basis"])}</p><p><strong>النطاق:</strong> {e(role["scope"])}</p></article>'
        for role in governance["reviewer_roles"]
    )
    domain_cards = "".join(
        f'<article class="rg-card"><span class="rg-risk {e(domain["risk"])}">{e(domain["risk"])}</span><h3>{e(domain["title"])}</h3><p><strong>الحد الأدنى للمصادر:</strong> {e(domain["minimum_sources"])}</p><p class="rg-muted">الأدوار: {e("، ".join(domain["required_roles"]))}</p></article>'
        for domain in governance["claim_domains"]
    )
    workflow = "".join(f"<li>{e(item)}</li>" for item in governance["correction_workflow"])
    gates = "".join(f"<li>{e(item)}</li>" for item in governance["acceptance_gates"])
    rows = "".join(
        f'<tr id="condition-{e(item["slug"])}" data-review-condition="{e(item["slug"])}"><td>{item["rank"]}</td><td><a href="../{e(item["slug"])}/">{e(item["title_ar"])}</a><br><small>{e(item["title_en"])}</small></td><td>{e(item["cluster_title"])}</td><td>6/6 بانتظار المراجعة</td><td>10/10 بانتظار المراجعة</td><td class="rg-status">0 موافقات</td></tr>'
        for item in report["conditions"]
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "headline": governance["title"],
        "inLanguage": "ar",
        "dateModified": UPDATED,
        "url": BASE + SECTION + "/" + ROUTE + "/",
        "about": ["المراجعة العلمية", "جودة الأدلة", "حوكمة المحتوى", "التقييم والتأهيل"],
        "mainEntity": {"@type": "ItemList", "numberOfItems": 100}
    }
    return f"""<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>حوكمة المراجعة العلمية | 100 حالة و1000 خطة</title>
<meta name="description" content="لوحة عربية شفافة تربط 100 حالة و1000 خطة بمجالات الادعاء والمصادر وأدوار المراجعين والقرارات والتصحيحات دون ادعاء اعتماد سريري غير مكتمل.">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}{SECTION}/{ROUTE}/">
<link rel="stylesheet" href="{BASE_PATH}assets/css/{CSS_PATH.name}"><script type="application/ld+json">{compact_json(schema)}</script></head>
<body class="rg-page"><a class="rg-skip" href="#main">تجاوز إلى المحتوى</a>
<header class="rg-header"><div class="rg-wrap rg-header-inner"><a class="rg-brand" href="{BASE_PATH}">منصة روافد</a><nav class="rg-nav" aria-label="التنقل"><a href="../">المسارات</a><a href="../ten-plan-methodology/">الخطط العشر</a><a href="../instruments/">الأدوات</a><a href="../evidence-standard/">الأدلة</a><a aria-current="page" href="./">المراجعة</a></nav></div></header>
<main id="main"><section class="rg-hero"><div class="rg-wrap"><p class="rg-kicker">سجل قابل للتدقيق وليس شارة اعتماد</p><h1>{e(governance['title'])}</h1><p class="rg-lead">{e(governance['purpose'])}</p>
<div class="rg-notice"><strong>الحالة الحالية:</strong> {e(governance['scope']['current_state'])}.</div><div class="rg-notice warning"><strong>قاعدة النشر:</strong> لا تتحول الصفحة أو الخطة إلى محتوى معتمد سريريًا إلا بعد اكتمال الأدوار المطلوبة وتوثيق القرار والتغييرات والمخاطر المتبقية.</div>
<div class="rg-metrics"><div><strong>{report['condition_count']}</strong><span>حالة</span></div><div><strong>{report['claim_review_count']}</strong><span>مراجعة مجال ادعاء</span></div><div><strong>{report['plan_review_count']}</strong><span>مراجعة خطة</span></div><div><strong>0</strong><span>موافقات مستقلة</span></div><div><strong>{report['source_contract_migration']['records_missing_full_contract_metadata']}</strong><span>سجل مصدر يحتاج ترحيلًا كاملًا</span></div></div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">ست طبقات لا يجوز خلطها</p><h2>مجالات مراجعة الادعاء</h2><div class="rg-grid">{domain_cards}</div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">من يملك صلاحية مراجعة ماذا؟</p><h2>مصفوفة أدوار المراجعين</h2><div class="rg-grid">{role_cards}</div></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">بوابات القبول</p><h2>متى يمكن اعتماد قرار ضمن نطاق محدد؟</h2><article class="rg-card"><ol>{gates}</ol></article></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">تصحيح غير صامت</p><h2>مسار الملاحظة والتدقيق والتصحيح وإعادة النشر</h2><article class="rg-card"><ol>{workflow}</ol></article></div></section>
<section class="rg-section"><div class="rg-wrap"><p class="rg-kicker">السجل الكامل</p><h2>حالة مراجعة الحالات المئة</h2><p class="rg-muted">تعني عبارة «بانتظار المراجعة» أن المحتوى منشور بشفافية بعد ضبط داخلي، لا أنه بلا مصادر، ولا أنه حصل على اعتماد خارجي.</p><div class="rg-table-wrap"><table class="rg-table"><thead><tr><th>#</th><th>الحالة</th><th>العائلة</th><th>مجالات الادعاء</th><th>الخطط</th><th>الموافقات</th></tr></thead><tbody>{rows}</tbody></table></div></div></section>
</main><footer class="rg-footer"><div class="rg-wrap"><p><strong>حالة المراجعة:</strong> صفر موافقات تخصصية مستقلة مسجلة حتى {UPDATED}. أي مراجعة لاحقة يجب أن تحتوي دليل هوية وصلاحية ونطاقًا وتضارب مصالح وقرارًا وسجل تغييرات.</p><p><a href="../">العودة إلى المسارات المئة</a> · <a href="../evidence-standard/">معيار الأدلة</a> · <a href="../instruments/">سجل الأدوات</a></p></div></footer></body></html>"""


def update_sitemap(site: Path) -> None:
    path = site / SITEMAP_NAME
    if not path.is_file():
        raise ValueError("Outside-the-box sitemap is missing")
    tree = ET.parse(path)
    root = tree.getroot()
    namespace = root.tag.split("}", 1)[0].lstrip("{") if root.tag.startswith("{") else "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    q = lambda name: f"{{{namespace}}}{name}"
    target = BASE + SECTION + "/" + ROUTE + "/"
    urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc") if node.text]
    if target not in urls:
        node = ET.SubElement(root, q("url"))
        ET.SubElement(node, q("loc")).text = target
        ET.SubElement(node, q("lastmod")).text = UPDATED
        ET.SubElement(node, q("changefreq")).text = "weekly"
        ET.SubElement(node, q("priority")).text = "0.85"
    tree.write(path, encoding="utf-8", xml_declaration=True)


def patch_apis(site: Path, report: dict[str, Any]) -> None:
    summary = {
        "version": VERSION,
        "route": BASE + SECTION + "/" + ROUTE + "/",
        "condition_count": report["condition_count"],
        "claim_review_count": report["claim_review_count"],
        "plan_review_count": report["plan_review_count"],
        "independent_reviews_recorded": 0,
        "external_review_completed": False
    }
    for relative in ("api/outside-the-box-v254.json", "api/outside-the-box-ten-plans-v302.json"):
        path = site / relative
        if not path.is_file():
            raise ValueError(f"Required API is missing: {relative}")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["scientific_review_governance"] = summary
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ValueError(f"Missing site directory: {site}")
    data, framework, governance = load_sources()
    report = build_register(data, framework, governance)
    destination = site / "assets" / "css" / CSS_PATH.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CSS_PATH, destination)
    root = site / SECTION
    if not root.is_dir():
        raise ValueError("Outside-the-box pages must be published before review governance")
    dashboard = root / ROUTE
    dashboard.mkdir(parents=True, exist_ok=True)
    (dashboard / "index.html").write_text(render_dashboard(data, governance, report), encoding="utf-8")

    hub_path = root / "index.html"
    hub = ensure_stylesheet(hub_path.read_text(encoding="utf-8"))
    hub = replace_marker(hub, HUB_START, HUB_END, hub_block())
    hub_path.write_text(hub, encoding="utf-8")
    for condition in data["conditions"]:
        path = root / condition["slug"] / "index.html"
        text = ensure_stylesheet(path.read_text(encoding="utf-8"))
        text = replace_marker(text, CONDITION_START, CONDITION_END, condition_block(condition))
        path.write_text(text, encoding="utf-8")

    update_sitemap(site)
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "outside-the-box-review-governance-v305.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    template = {
        "version": VERSION,
        "notice": "قالب تسجيل مراجعة؛ لا يعد قرارًا صالحًا دون بيانات حقيقية قابلة للتحقق.",
        **{field: "" for field in governance["required_review_record_fields"]}
    }
    (api / "outside-the-box-review-submission-template-v305.json").write_text(
        json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    patch_apis(site, report)
    validate_published(site, report)
    return report


def validate_published(site: Path, report: dict[str, Any]) -> None:
    if report["condition_count"] != 100 or report["claim_review_count"] != 600 or report["plan_review_count"] != 1000:
        raise ValueError("Scientific review register counts are incomplete")
    if report["independent_reviews_recorded"] != 0 or report["external_review_completed"] is not False:
        raise ValueError("Unverified independent review must not be claimed")
    if any(item["status"] != "awaiting-independent-review" for item in report["conditions"]):
        raise ValueError("Condition review status is not honest")
    dashboard = (site / SECTION / ROUTE / "index.html").read_text(encoding="utf-8")
    if dashboard.count("data-review-condition=") != 100 or "صفر موافقات تخصصية مستقلة" not in dashboard:
        raise ValueError("Review dashboard condition register is incomplete")
    hub = (site / SECTION / "index.html").read_text(encoding="utf-8")
    if hub.count(HUB_START) != 1 or hub.count(HUB_END) != 1:
        raise ValueError("Review dashboard hub integration failed")
    for item in report["conditions"]:
        path = site / SECTION / item["slug"] / "index.html"
        text = path.read_text(encoding="utf-8")
        if text.count(CONDITION_START) != 1 or text.count(CONDITION_END) != 1:
            raise ValueError(f"Condition review marker failed: {item['slug']}")
        if f"../{ROUTE}/#condition-{item['slug']}" not in text:
            raise ValueError(f"Condition review link failed: {item['slug']}")
    urls = {(node.text or "").strip() for node in ET.parse(site / SITEMAP_NAME).getroot().findall("{*}url/{*}loc") if node.text}
    if BASE + SECTION + "/" + ROUTE + "/" not in urls:
        raise ValueError("Review governance route is missing from sitemap")
    forbidden = ("اعتماد عالمي مكتمل", "مراجعة خارجية مكتملة", "الخطة تصلح للجميع", "كل المصابين متفوقون", "معاقين")
    combined = dashboard + "\n" + json.dumps(report, ensure_ascii=False)
    found = [term for term in forbidden if term in combined]
    if found:
        raise ValueError(f"Unsafe review-governance claims detected: {found}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    report = publish(args.site)
    print(json.dumps({
        "version": report["version"],
        "condition_count": report["condition_count"],
        "claim_review_count": report["claim_review_count"],
        "plan_review_count": report["plan_review_count"],
        "independent_reviews_recorded": report["independent_reviews_recorded"],
        "status": report["status"]
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
