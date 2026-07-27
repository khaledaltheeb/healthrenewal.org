#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import publish_special_needs_condition_hubs_v302_base as base

# Preserve the public v302 contract for every existing importer and test.
ROOT = base.ROOT
BASE = base.BASE
BP = base.BP
MANIFEST = base.MANIFEST
PROVIDERS = base.PROVIDERS
PROVIDERS_FILE = base.PROVIDERS_FILE
SOURCE_OVERRIDE_FILE = base.SOURCE_OVERRIDE_FILE
VERSION = base.VERSION
UPDATED = base.UPDATED
MARK = base.MARK
HUB_MARKER = base.HUB_MARKER
INSERT = base.INSERT
BANNED = base.BANNED
CSS = base.CSS

e = base.e
read = base.read
https = base.https
normalized_host = base.normalized_host
official_domain_family = base.official_domain_family
validate_provider_data = base.validate_provider_data
validate_providers = base.validate_providers
apply_source_url_overrides = base.apply_source_url_overrides
load = base.load
provider_cards = base.provider_cards
schema = base.schema
render = base.render
hub_section = base.hub_section
patch_hub = base.patch_hub
q = base.q
sitemap = base.sitemap

BRIDGE_VERSION = 322
ENCYCLOPEDIA_BRIDGE_MARKER = "data-specialized-condition-portals-v322"
AUTISM_TOPIC_BRIDGE_MARKER = "data-autism-scientific-portal-v322"
CONDITION_NAV_MARKER = "data-condition-encyclopedia-nav-v322"
CONDITION_ACTION_MARKER = "data-condition-knowledge-route-v322"


def knowledge_route(condition: dict) -> tuple[str, str]:
    if condition["slug"] == "autism":
        return BP + "hubs/topic-058/", "المسار الموسوعي للتوحد"
    return BP + "encyclopedia/", "الموسوعة النفسية العربية"


def patch_condition_page(site: Path, condition: dict) -> dict[str, object]:
    path = site / "special-needs" / condition["slug"] / "index.html"
    if not path.is_file():
        raise SystemExit(f"Generated condition page is missing: {path}")
    source = path.read_text(encoding="utf-8")

    nav_link = f'<a {CONDITION_NAV_MARKER} href="{BP}encyclopedia/">الموسوعة</a>'
    if CONDITION_NAV_MARKER in source:
        source, count = re.subn(
            rf'<a {CONDITION_NAV_MARKER} href="[^"]+">.*?</a>',
            nav_link,
            source,
            count=1,
            flags=re.S,
        )
    else:
        anchor = f'<a href="{BP}assessment-lab/">منصة التقييم</a>'
        if source.count(anchor) != 1:
            raise SystemExit(f"Condition navigation anchor is missing or ambiguous: {condition['slug']}")
        source = source.replace(anchor, nav_link + anchor, 1)
        count = 1
    if count != 1 or source.count(CONDITION_NAV_MARKER) != 1:
        raise SystemExit(f"Condition encyclopedia navigation is not idempotent: {condition['slug']}")

    href, label = knowledge_route(condition)
    action = f'<a class="btn" {CONDITION_ACTION_MARKER} href="{href}">{base.e(label)}</a>'
    if CONDITION_ACTION_MARKER in source:
        source, count = re.subn(
            rf'<a class="btn" {CONDITION_ACTION_MARKER} href="[^"]+">.*?</a>',
            action,
            source,
            count=1,
            flags=re.S,
        )
    else:
        anchor = '<a class="btn" href="#directory">الأطباء والمراكز</a>'
        if source.count(anchor) != 1:
            raise SystemExit(f"Condition action anchor is missing or ambiguous: {condition['slug']}")
        source = source.replace(anchor, action + anchor, 1)
        count = 1
    if count != 1 or source.count(CONDITION_ACTION_MARKER) != 1:
        raise SystemExit(f"Condition knowledge route is not idempotent: {condition['slug']}")

    path.write_text(source, encoding="utf-8")
    return {
        "path": path.relative_to(site).as_posix(),
        "encyclopedia_navigation": True,
        "knowledge_route": href,
    }


def encyclopedia_bridge_section(conditions: list[dict]) -> str:
    cards: list[str] = []
    for condition in conditions:
        note = (
            "مرتبط أيضًا بمسار الموضوع 58 داخل الموسوعة."
            if condition["slug"] == "autism"
            else "بوابة متخصصة خارج قائمة الموضوعات المئة، مع بقاء الوصول إليها من الموسوعة."
        )
        cards.append(
            '<article class="ency-topic-v2__card">'
            '<span class="ency-topic-v2__badge">بوابة علمية متخصصة</span>'
            f'<h2><a href="{BP}special-needs/{base.e(condition["slug"])}/">{base.e(condition["short_title"])}</a></h2>'
            f'<p>{base.e(condition["meta_description"])}</p><small>{base.e(note)}</small></article>'
        )
    return (
        f'<section class="ency-topic-v2__section" {ENCYCLOPEDIA_BRIDGE_MARKER} '
        'aria-labelledby="specialized-condition-portals-title">'
        '<h2 id="specialized-condition-portals-title">بوابات علمية متخصصة للتوحد ومتلازمة داون</h2>'
        '<p>هذه البوابات أعمق من المدخل الموسوعي العام، وتجمع الإرشادات الصحية والتقييم والدعم والحالات المصاحبة والأدلة العمرية في مسارات مستقلة.</p>'
        f'<div class="ency-topic-v2__grid">{"".join(cards)}</div></section>'
    )


def patch_encyclopedia(site: Path, conditions: list[dict]) -> dict[str, object]:
    path = site / "encyclopedia" / "index.html"
    if not path.is_file():
        return {"available": False, "compatible": False, "added": False, "path": None, "reason": "missing"}
    source = path.read_text(encoding="utf-8")
    if 'data-encyclopedia-index-v2="true"' not in source:
        return {
            "available": True,
            "compatible": False,
            "added": False,
            "path": "encyclopedia/index.html",
            "reason": "topic-first-contract-missing",
        }

    block = encyclopedia_bridge_section(conditions)
    if ENCYCLOPEDIA_BRIDGE_MARKER in source:
        source, count = re.subn(
            rf'<section class="ency-topic-v2__section" {ENCYCLOPEDIA_BRIDGE_MARKER}.*?</section>',
            block,
            source,
            count=1,
            flags=re.S,
        )
    else:
        anchor = '<section class="ency-topic-v2__grid" aria-label="الموضوعات المرجعية">'
        if source.count(anchor) != 1:
            raise SystemExit("Topic-first encyclopedia insertion point is missing or ambiguous")
        source = source.replace(anchor, block + anchor, 1)
        count = 1
    if count != 1 or source.count(ENCYCLOPEDIA_BRIDGE_MARKER) != 1:
        raise SystemExit("Encyclopedia condition bridge idempotence failed")
    for slug in ("autism", "down-syndrome"):
        if source.count(f'{BP}special-needs/{slug}/') != 1:
            raise SystemExit(f"Specialized condition route missing or duplicated in encyclopedia: {slug}")
    path.write_text(source, encoding="utf-8")
    return {"available": True, "compatible": True, "added": True, "path": "encyclopedia/index.html", "reason": None}


def autism_topic_bridge() -> str:
    return (
        f'<section class="ency-topic-v2__section ency-topic-v2__notice" {AUTISM_TOPIC_BRIDGE_MARKER} '
        'aria-labelledby="autism-scientific-portal-title">'
        '<h2 id="autism-scientific-portal-title">الدليل العلمي المتخصص للتوحد</h2>'
        '<p>يتناول هذا المركز الزوايا الموسوعية العشرين. وللتقييم والدعم والحالات المصاحبة والتغير المفاجئ والمتابعة عبر العمر، انتقل إلى البوابة العلمية المتخصصة.</p>'
        f'<p><a class="ency-topic-v2__button" href="{BP}special-needs/autism/">فتح بوابة التوحد العلمية</a></p></section>'
    )


def patch_autism_topic(site: Path) -> dict[str, object]:
    path = site / "hubs" / "topic-058" / "index.html"
    if not path.is_file():
        return {"available": False, "compatible": False, "added": False, "path": None, "reason": "missing"}
    source = path.read_text(encoding="utf-8")
    if 'data-topic-hub-v2="true"' not in source:
        return {
            "available": True,
            "compatible": False,
            "added": False,
            "path": "hubs/topic-058/index.html",
            "reason": "topic-first-contract-missing",
        }

    block = autism_topic_bridge()
    if AUTISM_TOPIC_BRIDGE_MARKER in source:
        source, count = re.subn(
            rf'<section class="ency-topic-v2__section ency-topic-v2__notice" {AUTISM_TOPIC_BRIDGE_MARKER}.*?</section>',
            block,
            source,
            count=1,
            flags=re.S,
        )
    else:
        anchor = '<section class="ency-topic-v2__section">'
        if anchor not in source:
            raise SystemExit("Autism topic bridge insertion point is missing")
        source = source.replace(anchor, block + anchor, 1)
        count = 1
    if count != 1 or source.count(AUTISM_TOPIC_BRIDGE_MARKER) != 1:
        raise SystemExit("Autism topic bridge idempotence failed")
    if source.count(f'{BP}special-needs/autism/') != 1:
        raise SystemExit("Autism scientific portal link is missing or duplicated")
    path.write_text(source, encoding="utf-8")
    return {"available": True, "compatible": True, "added": True, "path": "hubs/topic-058/index.html", "reason": None}


def publish(site: Path) -> dict:
    report = base.publish(site)
    _, _, conditions = base.load()
    condition_pages = {condition["slug"]: patch_condition_page(site, condition) for condition in conditions}
    encyclopedia_bridge = patch_encyclopedia(site, conditions)
    autism_bridge = patch_autism_topic(site)
    report.update(
        {
            "encyclopedia_bridge_version": BRIDGE_VERSION,
            "condition_page_bridges": condition_pages,
            "encyclopedia_bridge": encyclopedia_bridge,
            "autism_topic_bridge": autism_bridge,
            "down_syndrome_specialized_route_visible": bool(encyclopedia_bridge.get("added")),
        }
    )
    (site / "api" / "special-needs-condition-hubs-v302.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    site = parser.parse_args().site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
