from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "seo" / "editorial-intent-map-v278.json"
BASE = "https://healthrenewal.org/"
BANNED = (
    "الأفضل في العالم",
    "الأول عربيًا",
    "ترتيب مضمون",
    "نتائج مضمونة",
    "صفحة بوابة",
    "معاقين",
    "المعاقين",
)


def norm(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[إأآا]", "ا", value)
    value = value.replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE)


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert data["contract"] == 278
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["reviewed_at"])
    assert data["base_url"] == BASE
    assert len(data["principles"]) >= 5

    clusters = data["clusters"]
    assert len(clusters) == 10, len(clusters)
    ids = [item["id"] for item in clusters]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z0-9-]+", item) for item in ids)

    all_queries: list[str] = []
    pillar_urls: list[str] = []
    route_mentions: Counter[str] = Counter()
    for cluster in clusters:
        required = {
            "id", "title_ar", "pillar_url", "primary_intent", "queries_ar",
            "queries_en", "supporting_routes", "recommended_entities",
            "distribution_assets",
        }
        assert required <= set(cluster), (cluster["id"], required - set(cluster))
        assert len(cluster["title_ar"]) >= 10
        assert len(cluster["primary_intent"]) >= 45
        assert len(cluster["queries_ar"]) >= 6
        assert len(cluster["queries_en"]) >= 2
        assert len(cluster["supporting_routes"]) >= 4
        assert len(cluster["recommended_entities"]) >= 3
        assert len(cluster["distribution_assets"]) >= 3

        parsed = urlparse(cluster["pillar_url"])
        assert cluster["pillar_url"].startswith(BASE)
        assert parsed.scheme == "https" and parsed.netloc == "khaledaltheeb.github.io"
        assert parsed.path.endswith("/")
        pillar_urls.append(cluster["pillar_url"])

        local_queries = cluster["queries_ar"] + cluster["queries_en"]
        normalized = [norm(item) for item in local_queries]
        assert len(normalized) == len(set(normalized)), cluster["id"]
        all_queries.extend(normalized)

        for route in cluster["supporting_routes"]:
            assert route.startswith("/") and route.endswith("/"), (cluster["id"], route)
            assert "//" not in route
            route_mentions[route] += 1

        blob = json.dumps(cluster, ensure_ascii=False).casefold()
        assert not any(term.casefold() in blob for term in BANNED), cluster["id"]

    assert len(pillar_urls) == len(set(pillar_urls))
    duplicates = [query for query, count in Counter(all_queries).items() if count > 1]
    assert not duplicates, duplicates
    assert all(count >= 2 for count in route_mentions.values()), route_mentions

    report = {
        "contract": 278,
        "clusters": len(clusters),
        "arabic_queries": sum(len(item["queries_ar"]) for item in clusters),
        "english_queries": sum(len(item["queries_en"]) for item in clusters),
        "unique_queries": len(set(all_queries)),
        "unique_pillars": len(set(pillar_urls)),
        "supporting_routes": dict(sorted(route_mentions.items())),
        "cannibalization_conflicts": duplicates,
        "doorway_language": False,
        "measured_rank_claims": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
