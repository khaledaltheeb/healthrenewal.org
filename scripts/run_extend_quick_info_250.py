#!/usr/bin/env python3
"""Run the 250-page generator with reviewed compatibility corrections."""

import extend_quick_info_250 as edition

OLD_SLUG = "prepare-first-therapy-session"
NEW_SLUG = "prepare-therapy-intake-session"
NEW_TITLE = "كيف تستعد لجلسة التعارف والتقييم الأولي مع المعالج النفسي؟"
DOMAIN_ALIASES = {
    "teen": "child",
}


def main() -> None:
    matched = [topic for topic in edition.NEW_TOPICS if topic["slug"] == OLD_SLUG]
    if len(matched) != 1:
        raise SystemExit(f"Expected one topic to rename, found {len(matched)}")
    topic = matched[0]
    topic["slug"] = NEW_SLUG
    topic["title"] = NEW_TITLE
    edition.DETAILS[NEW_SLUG] = edition.DETAILS.pop(OLD_SLUG)

    remapped = 0
    for candidate in edition.NEW_TOPICS:
        replacement = DOMAIN_ALIASES.get(candidate["domain"])
        if replacement:
            candidate["domain"] = replacement
            remapped += 1
    if remapped != 2:
        raise SystemExit(f"Expected two teen-domain topics, remapped {remapped}")

    edition.main()


if __name__ == "__main__":
    main()
