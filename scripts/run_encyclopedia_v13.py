from __future__ import annotations

import importlib.util
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE = Path(__file__).with_name("rebuild_encyclopedia_v13.py")
spec = importlib.util.spec_from_file_location("encyclopedia_v13", SOURCE)
if spec is None or spec.loader is None:
    raise SystemExit("Unable to load v13 encyclopedia builder")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = module.concept_html


def enriched_concept_html(item, related):
    markup, description = original(item, related)
    domain = module.esc(item["domain_ar"])
    facet = module.esc(item["facet"]["ar"])
    title = module.esc(item["ar"])
    replacements = {
        "<p>يبدأ الفهم بخط زمني: ما الوضع المعتاد؟ ما التغير الجديد؟ ما المواقف التي تزيد أو تخفف الصعوبة؟ ثم تُراجع الوظائف المهمة مثل النوم والتعلم والعمل والعلاقات والرعاية الذاتية. في الأطفال أو المراهقين، تكون معلومات الأسرة والمدرسة والتاريخ النمائي مهمة، بينما يحتاج التغير المفاجئ أو الجسدي إلى مراجعة طبية مناسبة.</p>":
        f"<p>في تقييم {title} يبدأ الفهم بخط زمني: ما الوضع المعتاد؟ ما التغير الجديد؟ ما المواقف التي تزيد أو تخفف الصعوبة؟ ثم تُراجع الوظائف المهمة مثل النوم والتعلم والعمل والعلاقات والرعاية الذاتية. وتختلف أهمية هذه المعلومات في زاوية {facet} بحسب العمر والسياق؛ ففي الأطفال أو المراهقين تكون معلومات الأسرة والمدرسة والتاريخ النمائي مهمة، بينما يحتاج التغير المفاجئ أو الجسدي إلى مراجعة طبية مناسبة.</p>",
        "<p>الدعم المفيد يجمع بين الاستماع والاحترام والحدود. يمكن للأسرة أن تساعد في تنظيم المواعيد، توثيق التغير، تخفيف العوائق اليومية، ودعم الالتزام بالخطة دون تحويل الشخص إلى “حالة” أو مراقبته بصورة مهينة. عند الأطفال وذوي الاحتياجات الخاصة، يُفضّل بناء خطة مشتركة توضح نقاط القوة والاحتياجات وطريقة التواصل وما الذي يهدئ وما الذي يفاقم الضغط.</p>":
        f"<p>في سياق {domain} وخصوصًا عند مناقشة {facet}، يجمع الدعم المفيد بين الاستماع والاحترام والحدود. يمكن للأسرة أن تساعد في تنظيم المواعيد، توثيق التغير، تخفيف العوائق اليومية، ودعم الالتزام بالخطة دون تحويل الشخص إلى “حالة” أو مراقبته بصورة مهينة. عند الأطفال وذوي الاحتياجات الخاصة، يُفضّل بناء خطة مشتركة توضح نقاط القوة والاحتياجات وطريقة التواصل وما الذي يهدئ وما الذي يفاقم الضغط.</p>",
        "<p>لا ينبغي تفسير العنف أو الإكراه أو الإهمال على أنه مجرد عرض نفسي. في وجود خطر مباشر تكون السلامة وطلب المساعدة المحلية العاجلة أولوية.</p>":
        f"<p>مهما كان تفسير {domain} أو زاوية {facet}، لا ينبغي تفسير العنف أو الإكراه أو الإهمال على أنه مجرد عرض نفسي. في وجود خطر مباشر تكون السلامة وطلب المساعدة المحلية العاجلة أولوية.</p>",
        "<p>وقت البداية، التكرار، الشدة، المحفزات، ما الذي يخففها، أثرها اليومي، الأدوية والحالة الصحية، والتغيرات التي لاحظها أشخاص موثوقون.</p>":
        f"<p>قبل موعد يتعلق بـ{title} دوّن وقت البداية، التكرار، الشدة، المحفزات، ما الذي يخففها، أثرها اليومي، الأدوية والحالة الصحية، والتغيرات التي لاحظها أشخاص موثوقون.</p>",
        "<p>حدد مؤشرات عملية مثل تحسن النوم أو الحضور أو القدرة على إكمال مهمة أو انخفاض التجنب، وراجعها دوريًا مع المختص بدل الاعتماد على الشعور العام وحده.</p>":
        f"<p>في متابعة {domain} من زاوية {facet} حدد مؤشرات عملية مثل تحسن النوم أو الحضور أو القدرة على إكمال مهمة أو انخفاض التجنب، وراجعها دوريًا مع المختص بدل الاعتماد على الشعور العام وحده.</p>",
        "<p>المعلومات العامة تساعد في الفهم والاستعداد، لكنها لا تكفي عندما توجد معاناة مستمرة أو تعطيل أو خطر أو حاجة إلى تشخيص وعلاج فردي.</p>":
        f"<p>المعلومات العامة حول {title} تساعد في الفهم والاستعداد، لكنها لا تكفي عندما توجد معاناة مستمرة أو تعطيل أو خطر أو حاجة إلى تشخيص وعلاج فردي.</p>",
        "<p>تم ربط المدخل بمصادر مؤسسية عامة تساعد على التحقق والتوسع. قد تتغير التوصيات بمرور الوقت، لذلك تُراجع المصادر الأصلية عند اتخاذ قرار صحي.</p>":
        f"<p>تم ربط مدخل {title} بمصادر مؤسسية عامة تساعد على التحقق والتوسع. قد تتغير التوصيات بمرور الوقت، لذلك تُراجع المصادر الأصلية عند اتخاذ قرار صحي متعلق بـ{domain}.</p>",
    }
    for old, new in replacements.items():
        if old not in markup:
            raise SystemExit(f"Expected v13 paragraph not found: {old[:70]}")
        markup = markup.replace(old, new, 1)
    return markup, description


def fix_homepage_heading_hierarchy(site: Path) -> None:
    homepage = site / "index.html"
    text = homepage.read_text(encoding="utf-8")
    starts = list(re.finditer(r"<h1(?P<attrs>\s[^>]*)?>", text, flags=re.I))
    if len(starts) <= 1:
        return
    second = starts[1]
    open_tag = second.group(0)
    replacement = re.sub(r"^<h1", "<h2", open_tag, flags=re.I)
    text = text[:second.start()] + replacement + text[second.end():]
    close = re.search(r"</h1>", text[second.start() + len(replacement):], flags=re.I)
    if close is None:
        raise SystemExit("Second homepage h1 has no closing tag")
    close_start = second.start() + len(replacement) + close.start()
    close_end = second.start() + len(replacement) + close.end()
    text = text[:close_start] + "</h2>" + text[close_end:]
    homepage.write_text(text, encoding="utf-8")


def normalize_hubs_sitemap_namespace(site: Path) -> dict[str, object]:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    sitemap = site / "sitemap-hubs.xml"
    if not sitemap.is_file():
        raise SystemExit(f"Missing hubs sitemap: {sitemap}")

    ET.register_namespace("", namespace)
    tree = ET.parse(sitemap)
    root = tree.getroot()
    if root.tag != f"{{{namespace}}}urlset":
        raise SystemExit(f"Unexpected hubs sitemap root: {root.tag}")

    url_count = len(root.findall(f"{{{namespace}}}url"))
    tree.write(sitemap, encoding="utf-8", xml_declaration=True)
    serialized = sitemap.read_text(encoding="utf-8")
    if "ns0:" in serialized:
        raise SystemExit("Prefixed sitemap namespace remains after normalization")
    if f'xmlns="{namespace}"' not in serialized:
        raise SystemExit("Default sitemap namespace is missing")
    if serialized.count("<url>") != url_count:
        raise SystemExit(
            {
                "hubs_sitemap_serialization_mismatch": {
                    "semantic_urls": url_count,
                    "serialized_urls": serialized.count("<url>"),
                }
            }
        )
    return {
        "status": "passed",
        "url_count": url_count,
        "default_namespace": True,
        "prefixed_namespace_removed": True,
    }


module.concept_html = enriched_concept_html
build_report = module.build()

TOPIC_SOURCE = Path(__file__).with_name("publish_encyclopedia_topic_hubs_v2.py")
topic_spec = importlib.util.spec_from_file_location("encyclopedia_topic_hubs_v2", TOPIC_SOURCE)
if topic_spec is None or topic_spec.loader is None:
    raise SystemExit("Unable to load encyclopedia topic-hub publisher")
topic_module = importlib.util.module_from_spec(topic_spec)
topic_spec.loader.exec_module(topic_module)
topic_report = topic_module.publish(module)
sitemap_report = normalize_hubs_sitemap_namespace(module.SITE)

fix_homepage_heading_hierarchy(module.SITE)

GUIDE_SOURCE = Path(__file__).with_name("publish_adjustment_disorder_v335.py")
guide_spec = importlib.util.spec_from_file_location("adjustment_disorder_v335", GUIDE_SOURCE)
if guide_spec is None or guide_spec.loader is None:
    raise SystemExit("Unable to load adjustment-disorder publisher")
guide_module = importlib.util.module_from_spec(guide_spec)
guide_spec.loader.exec_module(guide_module)
guide_report = guide_module.publish(module.SITE)

AUDIT_SOURCE = Path(__file__).with_name("audit_site_integrity_v13.py")
audit_spec = importlib.util.spec_from_file_location("site_integrity_v13", AUDIT_SOURCE)
if audit_spec is None or audit_spec.loader is None:
    raise SystemExit("Unable to load v13 site integrity audit")
audit_module = importlib.util.module_from_spec(audit_spec)
audit_spec.loader.exec_module(audit_module)
audit_module.SITE = module.SITE
audit_result = audit_module.main()

print(json.dumps({"encyclopedia": build_report, "topic_hubs": topic_report, "hubs_sitemap": sitemap_report, "adjustment_disorder": guide_report, "integrity_audit_exit": audit_result}, ensure_ascii=False, indent=2))
