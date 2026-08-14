from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "content/strategy/content-10000-wave002-high-value-gaps-v1.json"
SOURCES = ROOT / "content/strategy/source-registry-wave002-v1.json"


def norm(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    value = re.sub(r"[^\w\u0600-\u06ff]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def tokens(value: str) -> set[str]:
    return {t for t in norm(value).split() if len(t) > 2}


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def visible_title(path: Path) -> str | None:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, re.I | re.S)
    if not m:
        m = re.search(r"<title>(.*?)</title>", source, re.I | re.S)
    if not m:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(1))).strip()


def existing_routes_and_titles() -> tuple[set[str], list[tuple[str, str]]]:
    routes: set[str] = set()
    titles: list[tuple[str, str]] = []
    ignored = {".git", "node_modules", ".venv", "venv", "_site"}
    for path in ROOT.rglob("index.html"):
        if any(part in ignored or part.startswith(".child-") or part.startswith(".home-") for part in path.parts):
            continue
        try:
            rel = path.parent.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        routes.add(rel.strip("/"))
        title = visible_title(path)
        if title:
            titles.append((rel, title))
    return routes, titles


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    registry = json.loads(SOURCES.read_text(encoding="utf-8"))
    source_ids = set(registry["sources"])
    pages = [page for cluster in plan["clusters"] for page in cluster["pages"]]

    errors: list[str] = []
    warnings: list[str] = []

    if len(pages) != plan["plannedPages"]:
        errors.append(f"plannedPages={plan['plannedPages']} but actual={len(pages)}")

    slugs = [page["slug"] for page in pages]
    titles = [norm(page["title"]) for page in pages]
    queries = [norm(page["primaryQuery"]) for page in pages]
    for label, values in (("slug", slugs), ("title", titles), ("primaryQuery", queries)):
        if len(values) != len(set(values)):
            errors.append(f"duplicate {label} detected")

    for page in pages:
        missing_sources = [source for source in page.get("sources", []) if source not in source_ids]
        if missing_sources:
            errors.append(f"{page['slug']}: unknown sources {missing_sources}")
        if len(page.get("sources", [])) < plan["publicationRules"]["minimumTopicSpecificSources"]:
            errors.append(f"{page['slug']}: fewer than required topic-specific sources")
        if not page.get("decision"):
            errors.append(f"{page['slug']}: missing decision question")
        if len(tokens(page.get("primaryQuery", ""))) < 2:
            errors.append(f"{page['slug']}: primaryQuery too broad")

    for i, left in enumerate(pages):
        for right in pages[i + 1:]:
            qscore = jaccard(left["primaryQuery"], right["primaryQuery"])
            tscore = jaccard(left["title"], right["title"])
            if qscore >= 0.80:
                errors.append(f"query collision {left['slug']} vs {right['slug']} score={qscore:.2f}")
            elif tscore >= 0.78:
                warnings.append(f"title similarity {left['slug']} vs {right['slug']} score={tscore:.2f}")

    existing_routes, existing_titles = existing_routes_and_titles()
    for page in pages:
        candidate_routes = {
            page["slug"],
            f"care-guides/{page['slug']}",
            f"sections/research-evidence-learning/{page['slug']}",
            f"special-needs/knowledge/{page['slug']}",
        }
        hit_routes = sorted(candidate_routes & existing_routes)
        if hit_routes and not page.get("migration"):
            errors.append(f"{page['slug']}: route already exists {hit_routes}; add migration decision")

        best = (0.0, "", "")
        for route, title in existing_titles:
            score = jaccard(page["title"], title)
            if score > best[0]:
                best = (score, route, title)
        if best[0] >= 0.72 and not page.get("migration"):
            errors.append(
                f"{page['slug']}: likely existing-title collision score={best[0]:.2f} route={best[1]} title={best[2]!r}; add merge/redirect decision"
            )
        elif best[0] >= 0.58:
            warnings.append(
                f"{page['slug']}: inspect similar existing page score={best[0]:.2f} route={best[1]} title={best[2]!r}"
            )

    print(json.dumps({
        "wave": plan["wave"],
        "pages": len(pages),
        "sources": len(source_ids),
        "errors": errors,
        "warnings": warnings,
        "status": "passed" if not errors else "failed",
    }, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
