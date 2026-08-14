from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "content/strategy/content-10000-wave002a-assessment-gap-audit-v2.json"
SOURCES = ROOT / "content/strategy/source-registry-wave002a-assessment-v2.json"
SCAN_ROOTS = ("care-guides", "special-needs", "sections/research-evidence-learning")


def norm(value: str) -> str:
    value = html.unescape(value).strip().lower()
    value = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    value = re.sub(r"[^\w\u0600-\u06ff]+", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def tok(value: str) -> set[str]:
    return {x for x in norm(value).split() if len(x) > 2}


def jac(a: str, b: str) -> float:
    aa, bb = tok(a), tok(b)
    return len(aa & bb) / len(aa | bb) if aa and bb else 0.0


def page_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S) or re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group(1))).strip() if match else ""


def inventory() -> tuple[dict[str, str], list[tuple[str, str]], int]:
    routes: dict[str, str] = {}
    titles: list[tuple[str, str]] = []
    for root_name in SCAN_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("index.html"):
            rel = path.parent.relative_to(ROOT).as_posix().strip("/")
            routes[rel] = str(path.relative_to(ROOT))
            title = page_title(path)
            if title:
                titles.append((rel, title))

    sitemap_routes = 0
    for sitemap in ROOT.glob("sitemap*.xml"):
        text = sitemap.read_text(encoding="utf-8", errors="ignore")
        for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>", text, flags=re.I | re.S):
            parsed = urlparse(html.unescape(loc))
            if parsed.netloc not in {"healthrenewal.org", "www.healthrenewal.org"}:
                continue
            route = parsed.path.strip("/")
            if not route or not any(route == prefix or route.startswith(prefix + "/") for prefix in SCAN_ROOTS):
                continue
            if route not in routes:
                sitemap_routes += 1
            routes.setdefault(route, f"sitemap:{sitemap.name}")
    return routes, titles, sitemap_routes


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    registry = json.loads(SOURCES.read_text(encoding="utf-8"))
    source_ids = set(registry["sources"])
    candidates = plan["candidates"]
    rules = plan["auditRules"]
    routes, titles, sitemap_only_routes = inventory()
    errors: list[str] = []
    decisions: list[dict[str, object]] = []

    if len(candidates) != plan["candidatePages"]:
        errors.append("candidatePages count mismatch")
    if len({c["slug"] for c in candidates}) != len(candidates):
        errors.append("duplicate candidate slug")
    if len({norm(c["primaryQuery"]) for c in candidates}) != len(candidates):
        errors.append("duplicate candidate primaryQuery")

    for c in candidates:
        missing = [sid for sid in c.get("sources", []) if sid not in source_ids]
        if missing:
            errors.append(f"{c['slug']}: unknown sources {missing}")
        if len(c.get("sources", [])) < rules["minimumSources"]:
            errors.append(f"{c['slug']}: fewer than {rules['minimumSources']} sources")

        exact_routes = []
        for prefix in SCAN_ROOTS:
            for route in (
                f"{prefix}/{c['slug']}",
                f"{prefix}/clinical-literacy/{c['slug']}",
                f"{prefix}/knowledge/{c['slug']}",
                f"{prefix}/reference/{c['slug']}",
                f"{prefix}/guides/{c['slug']}",
            ):
                if route in routes:
                    exact_routes.append(route)

        ranked = sorted(((jac(c["title"], title), route, title) for route, title in titles), reverse=True)
        best_score, best_route, best_title = ranked[0] if ranked else (0.0, "", "")
        if exact_routes or best_score >= rules["titleTokenJaccardBlockThreshold"]:
            disposition = "merge-existing"
        elif best_score >= rules["titleTokenJaccardReviewThreshold"]:
            disposition = "manual-review"
        else:
            disposition = "new-page"
        decisions.append({
            "slug": c["slug"],
            "cluster": c["cluster"],
            "disposition": disposition,
            "exactRoutes": exact_routes,
            "bestTitleSimilarity": round(best_score, 3),
            "bestExistingRoute": best_route,
            "bestExistingTitle": best_title,
        })

    report = {
        "schemaVersion": 3,
        "wave": plan["wave"],
        "candidateCount": len(candidates),
        "inventoryRoutes": len(routes),
        "inventoryTitles": len(titles),
        "sitemapOnlyRoutesAdded": sitemap_only_routes,
        "newPage": sum(d["disposition"] == "new-page" for d in decisions),
        "manualReview": sum(d["disposition"] == "manual-review" for d in decisions),
        "mergeExisting": sum(d["disposition"] == "merge-existing" for d in decisions),
        "errors": errors,
        "decisions": decisions,
        "status": "failed" if errors else "audited",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
