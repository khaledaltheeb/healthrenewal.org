from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
PAGE = SITE / "index.html"
FAMILY_PAGE = SITE / "sectors" / "family" / "index.html"
ENCYCLOPEDIA_PAGE = SITE / "encyclopedia" / "index.html"
ADHD_PAGE = SITE / "care-guides" / "adhd-family-practical-guide" / "index.html"
AUTISM_PAGE = SITE / "care-guides" / "autism-family-practical-guide" / "index.html"

NAV_MARKER = '<a href="tips/">النصائح</a>'
NAV_LINK = '<a href="care-guides/">أدلة التعامل</a>'
ACTION_MARKER = '<a class="btn secondary" href="tips/">افتح الأدلة العملية</a>'
ACTION_LINK = '<a class="btn secondary" href="care-guides/">أدلة التعامل مع الحالات</a>'
CARE_GUIDES_HREF = re.compile(r'href=["\']/?care-guides/["\']')

ADHD_HREF = "/care-guides/adhd-family-practical-guide/"
AUTISM_HREF = "/care-guides/autism-family-practical-guide/"
AUTISM_ROUTE_TOKEN = "care-guides/autism-family-practical-guide/"
BASE = "https://healthrenewal.org/"

FAMILY_ADHD_BLOCK = f'''<!-- adhd-family-journey-v42 -->
<section class="care-v21__section" aria-labelledby="adhd-family-guide-link">
  <h2 id="adhd-family-guide-link">دعم الأسرة مع اضطراب نقص الانتباه وفرط النشاط</h2>
  <p>انتقل من فهم الحالة إلى خطة عملية للمنزل والمدرسة والواجبات والنوم، مع حدود واضحة لطلب المساعدة المهنية.</p>
  <p><a href="{ADHD_HREF}">اقرأ دليل الأسرة العملي لاضطراب نقص الانتباه وفرط النشاط</a></p>
</section>
<!-- /adhd-family-journey-v42 -->'''

FAMILY_AUTISM_BLOCK = f'''<!-- autism-family-journey-v73 -->
<section class="care-v21__section" aria-labelledby="autism-family-guide-link">
  <h2 id="autism-family-guide-link">دعم الأسرة مع اضطراب طيف التوحد</h2>
  <p>خطة عملية للتواصل والتنظيم الحسي والانتقالات والنوم والطعام والأمان، مع احترام الفروق الفردية وكرامة الشخص.</p>
  <p><a href="{AUTISM_HREF}">اقرأ دليل الأسرة العملي لاضطراب طيف التوحد</a></p>
</section>
<!-- /autism-family-journey-v73 -->'''

ENCYCLOPEDIA_ADHD_BLOCK = f'''<!-- adhd-encyclopedia-journey-v42 -->
<section class="ency-v13__section" aria-labelledby="adhd-practical-guide-link">
  <h2 id="adhd-practical-guide-link">بعد قراءة مصطلحات ADHD</h2>
  <p>للتطبيق الأسري والمدرسي المنظم، استخدم الدليل العملي غير التشخيصي المرتبط بالحالة.</p>
  <p><a href="{ADHD_HREF}">افتح دليل الأسرة العملي لـ ADHD</a></p>
</section>
<!-- /adhd-encyclopedia-journey-v42 -->'''

ENCYCLOPEDIA_AUTISM_BLOCK = f'''<!-- autism-encyclopedia-journey-v73 -->
<section class="ency-v13__section" aria-labelledby="autism-practical-guide-link">
  <h2 id="autism-practical-guide-link">بعد قراءة مصطلحات اضطراب طيف التوحد</h2>
  <p>انتقل إلى دليل أسري غير تشخيصي يركز على الدعم الوظيفي والتواصل والحواس والأمان بدل محاولة إزالة الاختلاف.</p>
  <p><a href="{AUTISM_HREF}">افتح دليل الأسرة العملي لاضطراب طيف التوحد</a></p>
</section>
<!-- /autism-encyclopedia-journey-v73 -->'''

ADHD_RELATED_BLOCK = '''<!-- adhd-related-journey-v42 -->
<section class="care-v21__section" aria-labelledby="adhd-related-links">
  <h2 id="adhd-related-links">أكمل رحلة الفهم والدعم</h2>
  <ul>
    <li><a href="/care-guides/">تصفح مكتبة أدلة التعامل والأسرة</a></li>
    <li><a href="/sectors/family/">انتقل إلى مركز الأسرة ومسارات الدعم</a></li>
    <li><a href="/encyclopedia/?q=ADHD">راجع مصطلحات ADHD والفروق المرتبطة في الموسوعة</a></li>
  </ul>
  <p>هذه الروابط للتثقيف والتنظيم ولا تحول الدليل أو نتائج البحث إلى تشخيص.</p>
</section>
<!-- /adhd-related-journey-v42 -->'''

AUTISM_RELATED_BLOCK = '''<!-- autism-related-journey-v73 -->
<section class="care-v21__section" aria-labelledby="autism-related-links">
  <h2 id="autism-related-links">أكمل رحلة الفهم والدعم</h2>
  <ul>
    <li><a href="/care-guides/">تصفح مكتبة أدلة التعامل والأسرة</a></li>
    <li><a href="/sectors/family/">انتقل إلى مركز الأسرة ومسارات الدعم</a></li>
    <li><a href="/encyclopedia/?q=اضطراب%20طيف%20التوحد">راجع مصطلحات طيف التوحد والفروق المرتبطة في الموسوعة</a></li>
  </ul>
  <p>المحتوى للتثقيف والدعم العام، ولا يقدّم تشخيصًا فرديًا أو خطة علاجية شخصية.</p>
</section>
<!-- /autism-related-journey-v73 -->'''


def inject_once(text: str, marker: str, link: str, label: str) -> str:
    if link in text:
        return text
    if marker not in text:
        raise SystemExit(f"Homepage {label} marker changed; refusing unsafe care-guide injection")
    return text.replace(marker, marker + link, 1)


def ensure_homepage_care_guide_discovery(text: str) -> tuple[str, int, bool]:
    """Require semantic care-guide discovery without coupling CI to old labels.

    Modern homepages may expose care guides through cards/journeys rather than
    the v21 navigation and hero labels. If at least two real links already
    exist, preserve the current source verbatim. Only fall back to the legacy
    injection markers when semantic discovery is genuinely missing.
    """

    initial_count = len(CARE_GUIDES_HREF.findall(text))
    if initial_count >= 2:
        return text, initial_count, False

    updated = inject_once(text, NAV_MARKER, NAV_LINK, "navigation")
    updated = inject_once(updated, ACTION_MARKER, ACTION_LINK, "hero action")
    final_count = len(CARE_GUIDES_HREF.findall(updated))
    if final_count < 2:
        raise SystemExit(
            f"Homepage care-guide discovery requires at least two links; found {final_count}"
        )
    if updated.count(NAV_LINK) > 1 or updated.count(ACTION_LINK) > 1:
        raise SystemExit("Legacy care-guide links must not be duplicated")
    return updated, final_count, updated != text


def inject_before_main(path: Path, block: str, marker: str, label: str) -> bool:
    if not path.exists():
        raise SystemExit(f"Missing {label} page: {path.relative_to(SITE)}")
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False
    if "</main>" not in text:
        raise SystemExit(f"{label} page has no </main>; refusing unsafe injection")
    path.write_text(text.replace("</main>", block + "</main>", 1), encoding="utf-8")
    return True


def remove_marked_block(path: Path, marker: str, label: str) -> bool:
    if not path.exists():
        raise SystemExit(f"Missing {label} page: {path.relative_to(SITE)}")
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"<!--\s*{re.escape(marker)}\s*-->.*?<!--\s*/{re.escape(marker)}\s*-->",
        re.DOTALL,
    )
    cleaned, count = pattern.subn("", text)
    if count:
        path.write_text(cleaned, encoding="utf-8")
    return bool(count)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0] + "}" + name
    return name


def normalize_main_sitemap() -> dict[str, object]:
    main_path = SITE / "sitemap.xml"
    care_path = SITE / "sitemap-care-guides.xml"
    if not main_path.exists() or not care_path.exists():
        raise SystemExit("Main or care-guide sitemap is missing")

    main_tree = ET.parse(main_path)
    main_root = main_tree.getroot()
    root_type = local_name(main_root.tag)
    care_tree = ET.parse(care_path)
    care_urls = [
        node.text.strip()
        for node in care_tree.getroot().findall("{*}url/{*}loc")
        if node.text and node.text.strip()
    ]
    if not care_urls:
        raise SystemExit("Care-guide sitemap contains no URLs")

    changed = False
    if root_type == "urlset":
        invalid_children = [child for child in list(main_root) if local_name(child.tag) == "sitemap"]
        for child in invalid_children:
            main_root.remove(child)
            changed = True

        allowed_care_urls = set(care_urls)
        for child in list(main_root):
            if local_name(child.tag) != "url":
                continue
            loc = child.find("{*}loc")
            value = (loc.text or "").strip() if loc is not None else ""
            if value.startswith(BASE + "care-guides/") and value not in allowed_care_urls:
                main_root.remove(child)
                changed = True

        existing = {
            node.text.strip()
            for node in main_root.findall("{*}url/{*}loc")
            if node.text and node.text.strip()
        }
        url_tag = qualify(main_root, "url")
        loc_tag = qualify(main_root, "loc")
        for url in care_urls:
            if url in existing:
                continue
            item = ET.SubElement(main_root, url_tag)
            ET.SubElement(item, loc_tag).text = url
            existing.add(url)
            changed = True
    elif root_type == "sitemapindex":
        invalid_children = [child for child in list(main_root) if local_name(child.tag) == "url"]
        for child in invalid_children:
            main_root.remove(child)
            changed = True
        target = BASE + "sitemap-care-guides.xml"
        existing = {
            node.text.strip()
            for node in main_root.findall("{*}sitemap/{*}loc")
            if node.text and node.text.strip()
        }
        if target not in existing:
            sitemap = ET.SubElement(main_root, qualify(main_root, "sitemap"))
            ET.SubElement(sitemap, qualify(main_root, "loc")).text = target
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {root_type}")

    if changed:
        main_tree.write(main_path, encoding="utf-8", xml_declaration=True)

    reparsed = ET.parse(main_path).getroot()
    valid = local_name(reparsed.tag) in {"urlset", "sitemapindex"}
    if local_name(reparsed.tag) == "urlset":
        valid = valid and not any(local_name(child.tag) == "sitemap" for child in reparsed)
    else:
        valid = valid and not any(local_name(child.tag) == "url" for child in reparsed)
    if not valid:
        raise SystemExit("Main sitemap mixes urlset and sitemapindex element contracts")
    return {"root_type": local_name(reparsed.tag), "changed": changed, "valid": valid}


def main() -> None:
    if not PAGE.exists():
        raise SystemExit("Production homepage is missing")
    if not ADHD_PAGE.exists():
        raise SystemExit("Approved ADHD guide is missing")

    text = PAGE.read_text(encoding="utf-8")
    text, homepage_care_links, homepage_legacy_injected = ensure_homepage_care_guide_discovery(text)
    PAGE.write_text(text, encoding="utf-8")

    autism_published = AUTISM_PAGE.is_file()
    family_adhd_changed = inject_before_main(
        FAMILY_PAGE, FAMILY_ADHD_BLOCK, "adhd-family-journey-v42", "family hub"
    )
    encyclopedia_adhd_changed = inject_before_main(
        ENCYCLOPEDIA_PAGE,
        ENCYCLOPEDIA_ADHD_BLOCK,
        "adhd-encyclopedia-journey-v42",
        "encyclopedia hub",
    )
    adhd_target_changed = inject_before_main(
        ADHD_PAGE, ADHD_RELATED_BLOCK, "adhd-related-journey-v42", "ADHD guide"
    )

    if autism_published:
        family_autism_changed = inject_before_main(
            FAMILY_PAGE, FAMILY_AUTISM_BLOCK, "autism-family-journey-v73", "family hub"
        )
        encyclopedia_autism_changed = inject_before_main(
            ENCYCLOPEDIA_PAGE,
            ENCYCLOPEDIA_AUTISM_BLOCK,
            "autism-encyclopedia-journey-v73",
            "encyclopedia hub",
        )
        autism_target_changed = inject_before_main(
            AUTISM_PAGE, AUTISM_RELATED_BLOCK, "autism-related-journey-v73", "autism guide"
        )
    else:
        family_autism_changed = remove_marked_block(
            FAMILY_PAGE, "autism-family-journey-v73", "family hub"
        )
        encyclopedia_autism_changed = remove_marked_block(
            ENCYCLOPEDIA_PAGE, "autism-encyclopedia-journey-v73", "encyclopedia hub"
        )
        autism_target_changed = False

    sitemap_state = normalize_main_sitemap()
    family_text = FAMILY_PAGE.read_text(encoding="utf-8")
    encyclopedia_text = ENCYCLOPEDIA_PAGE.read_text(encoding="utf-8")
    adhd_text = ADHD_PAGE.read_text(encoding="utf-8")
    autism_text = AUTISM_PAGE.read_text(encoding="utf-8") if autism_published else ""
    care_hub_text = (SITE / "care-guides" / "index.html").read_text(encoding="utf-8")
    care_sitemap_text = (SITE / "sitemap-care-guides.xml").read_text(encoding="utf-8")
    main_sitemap_text = (SITE / "sitemap.xml").read_text(encoding="utf-8")

    autism_inbound_from_care_hub = AUTISM_HREF in care_hub_text
    autism_inbound_from_family_hub = AUTISM_HREF in family_text
    autism_inbound_from_encyclopedia_hub = AUTISM_HREF in encyclopedia_text
    autism_outgoing_to_care_hub = "/care-guides/" in autism_text
    autism_outgoing_to_family_hub = "/sectors/family/" in autism_text
    autism_outgoing_to_encyclopedia_search = (
        "/encyclopedia/?q=اضطراب%20طيف%20التوحد" in autism_text
    )
    blocked_review_links_removed = (
        autism_published
        or (
            AUTISM_HREF not in family_text
            and AUTISM_HREF not in encyclopedia_text
            and AUTISM_HREF not in care_hub_text
        )
    )
    no_blocked_review_routes = (
        autism_published
        or (
            not AUTISM_PAGE.exists()
            and AUTISM_ROUTE_TOKEN not in care_sitemap_text
            and AUTISM_ROUTE_TOKEN not in main_sitemap_text
        )
    )
    autism_contract_valid = (
        (
            autism_inbound_from_care_hub
            and autism_inbound_from_family_hub
            and autism_inbound_from_encyclopedia_hub
            and autism_outgoing_to_care_hub
            and autism_outgoing_to_family_hub
            and autism_outgoing_to_encyclopedia_search
        )
        if autism_published
        else (blocked_review_links_removed and no_blocked_review_routes)
    )
    idempotent_blocks = (
        family_text.count("adhd-family-journey-v42") == 2
        and encyclopedia_text.count("adhd-encyclopedia-journey-v42") == 2
        and adhd_text.count("adhd-related-journey-v42") == 2
        and (
            (
                family_text.count("autism-family-journey-v73") == 2
                and encyclopedia_text.count("autism-encyclopedia-journey-v73") == 2
                and autism_text.count("autism-related-journey-v73") == 2
            )
            if autism_published
            else (
                family_text.count("autism-family-journey-v73") == 0
                and encyclopedia_text.count("autism-encyclopedia-journey-v73") == 0
            )
        )
    )

    legacy_duplicate_free = text.count(NAV_LINK) <= 1 and text.count(ACTION_LINK) <= 1
    report = {
        "version": 194,
        "care_guides_linked": homepage_care_links >= 2,
        "homepage_care_guide_links": homepage_care_links,
        "homepage_semantic_discovery": homepage_care_links >= 2,
        "homepage_legacy_injected": homepage_legacy_injected,
        "navigation_link": homepage_care_links >= 1,
        "hero_link": homepage_care_links >= 2,
        "duplicate_free": legacy_duplicate_free,
        "adhd_inbound_from_care_hub": ADHD_HREF in care_hub_text,
        "adhd_inbound_from_family_hub": ADHD_HREF in family_text,
        "adhd_inbound_from_encyclopedia_hub": ADHD_HREF in encyclopedia_text,
        "adhd_outgoing_to_care_hub": "/care-guides/" in adhd_text,
        "adhd_outgoing_to_family_hub": "/sectors/family/" in adhd_text,
        "adhd_outgoing_to_encyclopedia_search": "/encyclopedia/?q=ADHD" in adhd_text,
        "autism_published": autism_published,
        "autism_inbound_from_care_hub": autism_inbound_from_care_hub,
        "autism_inbound_from_family_hub": autism_inbound_from_family_hub,
        "autism_inbound_from_encyclopedia_hub": autism_inbound_from_encyclopedia_hub,
        "autism_outgoing_to_care_hub": autism_outgoing_to_care_hub,
        "autism_outgoing_to_family_hub": autism_outgoing_to_family_hub,
        "autism_outgoing_to_encyclopedia_search": autism_outgoing_to_encyclopedia_search,
        "blocked_review_links_removed": blocked_review_links_removed,
        "no_blocked_review_routes": no_blocked_review_routes,
        "autism_contract_valid": autism_contract_valid,
        "idempotent_blocks": idempotent_blocks,
        "main_sitemap_valid": bool(sitemap_state["valid"]),
        "main_sitemap_root": sitemap_state["root_type"],
        "changed": {
            "homepage_legacy_injected": homepage_legacy_injected,
            "family_adhd": family_adhd_changed,
            "family_autism": family_autism_changed,
            "encyclopedia_adhd": encyclopedia_adhd_changed,
            "encyclopedia_autism": encyclopedia_autism_changed,
            "adhd_guide": adhd_target_changed,
            "autism_guide": autism_target_changed,
            "sitemap": sitemap_state["changed"],
        },
    }
    required_keys = [
        "care_guides_linked",
        "homepage_semantic_discovery",
        "navigation_link",
        "hero_link",
        "duplicate_free",
        "adhd_inbound_from_care_hub",
        "adhd_inbound_from_family_hub",
        "adhd_inbound_from_encyclopedia_hub",
        "adhd_outgoing_to_care_hub",
        "adhd_outgoing_to_family_hub",
        "adhd_outgoing_to_encyclopedia_search",
        "blocked_review_links_removed",
        "no_blocked_review_routes",
        "autism_contract_valid",
        "idempotent_blocks",
        "main_sitemap_valid",
    ]
    if not all(report[key] for key in required_keys):
        raise SystemExit(f"Care-guide journey integration failed: {report}")

    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "care-guides-homepage-v21.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
