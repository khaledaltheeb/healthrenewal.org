#!/usr/bin/env python3
"""Run the 250-page generator with reviewed compatibility corrections."""

import shutil

import extend_quick_info_250 as edition

OLD_SLUG = "prepare-first-therapy-session"
NEW_SLUG = "review-therapy-plan-after-first-sessions"
NEW_TITLE = "كيف تراجع خطة العلاج النفسي بعد الجلسات الأولى؟"
STALE_SLUGS = {"prepare-therapy-intake-session"}
DOMAIN_ALIASES = {
    "teen": "child",
}


def main() -> None:
    matched = [topic for topic in edition.NEW_TOPICS if topic["slug"] == OLD_SLUG]
    if len(matched) != 1:
        raise SystemExit(f"Expected one topic to replace, found {len(matched)}")

    topic = matched[0]
    topic["slug"] = NEW_SLUG
    topic["title"] = NEW_TITLE
    edition.DETAILS.pop(OLD_SLUG)
    edition.DETAILS[NEW_SLUG] = {
        "summary": "مراجعة الخطة بعد الجلسات الأولى تساعدك على فهم الأهداف وطريقة العمل ومؤشرات التقدم، وتتيح تعديل ما لا يناسبك بدل الاستمرار بصمت.",
        "key": "اسأل: ما الهدف الحالي، كيف سنعرف أن هناك تقدمًا، ومتى نعيد تقييم الطريقة أو الإحالة؟",
        "items": [
            "هل أصبحت أهداف العلاج أوضح؟",
            "هل تفهم ما يحدث داخل الجلسات ولماذا؟",
            "هل توجد طريقة لمتابعة التقدم أو التعطل؟",
            "هل تستطيع مناقشة عدم الارتياح أو الخلاف؟",
            "هل تحتاج الخطة إلى تعديل أو تقييم إضافي؟",
        ],
    }

    remapped = 0
    for candidate in edition.NEW_TOPICS:
        replacement = DOMAIN_ALIASES.get(candidate["domain"])
        if replacement:
            candidate["domain"] = replacement
            remapped += 1
    if remapped != 2:
        raise SystemExit(f"Expected two teen-domain topics, remapped {remapped}")

    for stale_slug in STALE_SLUGS:
        stale_page = edition.base.ROOT / "quick-info" / stale_slug
        stale_image = edition.base.ROOT / "assets/quick-info/cards" / f"{stale_slug}.png"
        if stale_page.exists():
            shutil.rmtree(stale_page)
        if stale_image.exists():
            stale_image.unlink()

    edition.main()


if __name__ == "__main__":
    main()
