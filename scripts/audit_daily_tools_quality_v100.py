from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.daily_tools_v100 import CATALOG_CONTRACT, load_data

REPORT = ROOT / "_audit" / "daily-tools-quality-v100.json"
ARABIC_TOKEN = re.compile(r"[\u0600-\u06ff]{3,}")
STOPWORDS = {
    "هذه", "هذا", "التي", "الذي", "على", "إلى", "الى", "أو", "من", "في", "مع",
    "دون", "ثم", "عند", "عن", "بعد", "قبل", "واحد", "واحدة", "يمكن", "حدد",
    "اختر", "اكتب", "سجل", "عبر", "إذا", "كان", "كانت", "ذلك", "الآن",
}


def norm(value: str) -> str:
    return re.sub(r"[\W_]+", " ", value, flags=re.UNICODE).strip().casefold()


def tokens(values: Iterable[str]) -> Counter[str]:
    result: Counter[str] = Counter()
    for value in values:
        for token in ARABIC_TOKEN.findall(value):
            if token not in STOPWORDS:
                result[token] += 1
    return result


def cosine(left: Counter[str], right: Counter[str]) -> float:
    common = set(left) & set(right)
    numerator = sum(left[key] * right[key] for key in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> None:
    data = load_data()
    tools = data["tools"]
    categories = data["categories"]
    sources = {source["id"]: source for source in data["sources"]}
    errors: list[str] = []

    if len(tools) < CATALOG_CONTRACT:
        fail(errors, f"catalog contains {len(tools)} tools; expected at least {CATALOG_CONTRACT}")
    if len(categories) < 10:
        fail(errors, f"catalog contains {len(categories)} categories; expected at least 10")

    category_counts: dict[str, int] = defaultdict(int)
    title_seen: set[str] = set()
    intent_seen: set[str] = set()
    step_signatures: set[tuple[str, ...]] = set()
    vectors: list[tuple[str, Counter[str]]] = []

    for tool in tools:
        slug = tool["slug"]
        category_counts[tool["category_id"]] += 1
        title_key = norm(tool["title"])
        intent_key = norm(tool["intent"])
        signature = tuple(norm(step) for step in tool["steps"])

        if title_key in title_seen:
            fail(errors, f"duplicate title: {slug}")
        title_seen.add(title_key)
        if intent_key in intent_seen:
            fail(errors, f"duplicate intent: {slug}")
        intent_seen.add(intent_key)
        if signature in step_signatures:
            fail(errors, f"duplicate step sequence: {slug}")
        step_signatures.add(signature)

        if len(tool["title"].strip()) < 8:
            fail(errors, f"short title: {slug}")
        if len(tool["intent"].strip()) < 45:
            fail(errors, f"short intent: {slug}")
        if len(tool["steps"]) < 4 or any(len(step.strip()) < 24 for step in tool["steps"]):
            fail(errors, f"weak or short steps: {slug}")
        if len(tool["save_fields"]) < 3:
            fail(errors, f"insufficient interactive fields: {slug}")
        if not tool.get("duration") or not tool.get("audience") or not tool.get("safety"):
            fail(errors, f"missing duration, audience, or safety: {slug}")
        if len(tool.get("source_ids", [])) < 2:
            fail(errors, f"fewer than two institutional sources: {slug}")
        unknown = set(tool.get("source_ids", [])) - set(sources)
        if unknown:
            fail(errors, f"unknown sources in {slug}: {sorted(unknown)}")

        vectors.append((slug, tokens([tool["intent"], *tool["steps"]])))

    if category_counts and min(category_counts.values()) < 8:
        fail(errors, f"unbalanced categories: {dict(category_counts)}")

    near_duplicates: list[dict[str, object]] = []
    maximum_similarity = 0.0
    for index, (left_slug, left_vector) in enumerate(vectors):
        for right_slug, right_vector in vectors[index + 1 :]:
            similarity = cosine(left_vector, right_vector)
            maximum_similarity = max(maximum_similarity, similarity)
            if similarity >= 0.78:
                near_duplicates.append({"left": left_slug, "right": right_slug, "similarity": round(similarity, 4)})
    if near_duplicates:
        fail(errors, f"near-duplicate tools detected: {near_duplicates[:10]}")

    for source_id, source in sources.items():
        if not source.get("url", "").startswith("https://"):
            fail(errors, f"invalid source URL: {source_id}")
        if source.get("status") != "current" or not source.get("verified_at"):
            fail(errors, f"unverified or stale source metadata: {source_id}")
        if not source.get("claims_supported") or not source.get("source_type"):
            fail(errors, f"incomplete evidence metadata: {source_id}")

    report = {
        "contract": CATALOG_CONTRACT,
        "status": "failed" if errors else "passed",
        "tools": len(tools),
        "categories": len(categories),
        "paths": len(data["paths"]),
        "sources": len(sources),
        "minimum_tools_per_category": min(category_counts.values()) if category_counts else 0,
        "maximum_pairwise_similarity": round(maximum_similarity, 4),
        "near_duplicate_threshold": 0.78,
        "near_duplicate_pairs": near_duplicates,
        "minimum_steps": min(len(tool["steps"]) for tool in tools),
        "minimum_fields": min(len(tool["save_fields"]) for tool in tools),
        "minimum_sources_per_tool": min(len(tool["source_ids"]) for tool in tools),
        "errors": errors,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if errors:
        raise SystemExit("Daily tools quality contract failed")


if __name__ == "__main__":
    main()
