#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/content-expansion-v1"
REPORT = ROOT / "reports/content-expansion-v1.json"
START = "<!-- official-evidence-profile-v1:start -->"
END = "<!-- official-evidence-profile-v1:end -->"

BASES = {
    "special-needs": "special-needs/guides",
    "care-guides": "care-guides/evidence-guided",
    "learning-paths": "learning-paths/evidence-guided",
    "comparisons": "comparisons/disability-support",
    "daily-tools": "daily-tools/disability-support",
}


def page_path(page: dict) -> str:
    parts = [BASES[page["sector"]]]
    if page["sector"] == "special-needs":
        parts.append(page["cluster"].replace("_", "-"))
    parts.extend([page["slug"], "index.html"])
    return "/".join(parts)


def inventory() -> dict[str, dict]:
    pages: list[dict] = []
    with (DATA / "special-needs.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            row = {key: (value or "").strip() for key, value in row.items()}
            row["sector"] = "special-needs"
            pages.append(row)
    for filename in ("care-guides.json", "learning-paths.json", "comparisons.json", "daily-tools.json"):
        pages.extend(json.loads((DATA / filename).read_text(encoding="utf-8")))
    return {page_path(page): page for page in pages}


def matches(profile: dict, searchable: str) -> bool:
    patterns = profile.get("match", [])
    if "*" in patterns:
        return True
    return any(pattern.lower() in searchable for pattern in patterns)


def select_profiles(page: dict, profiles: list[dict]) -> list[dict]:
    searchable = " ".join(
        [page_path(page), page.get("slug", ""), page.get("title", ""), page.get("focus", "")]
    ).lower()
    specific = [
        profile for profile in profiles
        if "*" not in profile.get("match", []) and matches(profile, searchable)
    ]
    exclusive = [profile for profile in specific if profile.get("exclusive") is True]
    default = [profile for profile in profiles if "*" in profile.get("match", [])]
    if exclusive:
        return exclusive[:2]
    return specific[:2] if specific else default[:1]


def list_html(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def render(page: dict, selected: list[dict], sources: dict) -> tuple[str, list[str], list[str]]:
    profile_ids = [profile["id"] for profile in selected]
    source_ids: list[str] = []
    for profile in selected:
        source_ids.extend(profile.get("sources", []))
    source_ids = list(dict.fromkeys(source_ids))
    source_links = "".join(
        f'<li><a href="{html.escape(sources[source_id]["url"], quote=True)}" rel="noopener">'
        f'{html.escape(sources[source_id]["title"])}</a></li>'
        for source_id in source_ids if source_id in sources
    )
    blocks = []
    for profile in selected:
        blocks.append(
            f'<article class="box" data-evidence-profile="{html.escape(profile["id"], quote=True)}">'
            f'<h3>{html.escape(profile["id"].replace("-", " "))}</h3>'
            f'<h4>ما الذي تدعمه الإرشادات؟</h4>{list_html(profile.get("principles", []))}'
            f'<h4>خطوات التطبيق</h4>{list_html(profile.get("actions", []))}'
            f'<h4>مؤشرات المتابعة</h4>{list_html(profile.get("measures", []))}'
            f'<h4>حدود الاستدلال والسلامة</h4>{list_html(profile.get("boundaries", []))}'
            '</article>'
        )
    section = (
        f'{START}<section id="official-evidence" class="box" '
        f'data-evidence-profiles="{html.escape(",".join(profile_ids), quote=True)}">'
        f'<h2>طبقة الأدلة الرسمية الخاصة بموضوع الصفحة</h2>'
        f'<p>تربط هذه الطبقة موضوع <strong>{html.escape(page["title"])}</strong> '
        f'بإرشادات رسمية قابلة للتتبع. تعرض ما يمكن تطبيقه عمليًا وما لا يجوز استنتاجه '
        f'من الصفحة دون تقييم فردي أو تحقق من النظام المحلي.</p>'
        f'{"".join(blocks)}<h3>المصادر المباشرة لهذه الطبقة</h3><ol>{source_links}</ol>'
        f'</section>{END}'
    )
    urls = [sources[source_id]["url"] for source_id in source_ids if source_id in sources]
    return section, profile_ids, urls


def update_jsonld(markup: str, urls: list[str]) -> str:
    pattern = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.I | re.S)
    match = pattern.search(markup)
    if not match:
        return markup
    try:
        payload = json.loads(html.unescape(match.group(2)))
    except json.JSONDecodeError:
        return markup
    citations = payload.get("citation", [])
    if isinstance(citations, str):
        citations = [citations]
    payload["citation"] = list(dict.fromkeys([*citations, *urls]))
    replacement = match.group(1) + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + match.group(3)
    return markup[:match.start()] + replacement + markup[match.end():]


def word_count(markup: str) -> int:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", markup, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return len(re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", text))


def main() -> None:
    config = json.loads((DATA / "official-evidence.json").read_text(encoding="utf-8"))
    overrides_path = DATA / "official-evidence-overrides.json"
    overrides = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else {}
    sources = {**config["sources"], **overrides.get("sources", {})}
    profiles = [*overrides.get("profiles", []), *config["profiles"]]
    pages = inventory()
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    distribution: dict[str, int] = {}
    counts = []
    for record in report["pages"]:
        path = ROOT / record["path"]
        page = pages[record["path"]]
        selected = select_profiles(page, profiles)
        section, profile_ids, urls = render(page, selected, sources)
        markup = path.read_text(encoding="utf-8")
        if START in markup and END in markup:
            markup = re.sub(re.escape(START) + r".*?" + re.escape(END), section, markup, flags=re.S)
        elif '<section class="sources" id="sources">' in markup:
            markup = markup.replace('<section class="sources" id="sources">', section + '<section class="sources" id="sources">', 1)
        else:
            raise SystemExit(f"cannot place evidence section in {record['path']}")
        markup = update_jsonld(markup, urls)
        path.write_text(markup, encoding="utf-8")
        record["evidenceProfiles"] = profile_ids
        record["officialEvidenceSources"] = urls
        record["words"] = word_count(markup)
        counts.append(record["words"])
        for profile_id in profile_ids:
            distribution[profile_id] = distribution.get(profile_id, 0) + 1
    report["minimumObservedWords"] = min(counts)
    report["averageWords"] = round(sum(counts) / len(counts), 1)
    report["maximumObservedWords"] = max(counts)
    report["officialEvidenceProfiles"] = distribution
    report["officialEvidenceLayer"] = True
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pages": len(report["pages"]),
        "profiles": distribution,
        "minimumWords": min(counts),
        "averageWords": report["averageWords"],
        "maximumWords": max(counts),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
