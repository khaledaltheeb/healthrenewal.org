#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import json
import posixpath
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

VERSION = 417
HREF_RE = re.compile(r"<a\b[^>]*\bhref\s*=\s*([\"'])(.*?)\1", re.I | re.S)
SKIP_PARTS = {".git", ".github", "node_modules", "vendor", "dist", "build", "_site", "artifacts", "reports", "tests", "test-results", "coverage", "__pycache__"}
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "javascript:", "data:")


def public_html(root: Path) -> list[Path]:
    out=[]
    for p in sorted(root.rglob("*.html")):
        rel=p.relative_to(root)
        if p.name == "404.html" or any(x in SKIP_PARTS or x.startswith(".") for x in rel.parts):
            continue
        out.append(p)
    return out


def route_for(rel: Path) -> str:
    s=rel.as_posix()
    if s == "index.html": return "/"
    if s.endswith("/index.html"): return "/" + s[:-10]
    return "/" + s


def route_index(root: Path) -> tuple[dict[str, str], list[str]]:
    index={}
    for p in public_html(root):
        rel=p.relative_to(root)
        route=route_for(rel)
        index[route.rstrip("/") or "/"] = rel.as_posix()
        index["/" + rel.as_posix()] = rel.as_posix()
    return index, sorted(index)


def normalize_href(href: str, source_route: str) -> str | None:
    href=href.strip()
    if not href or href.startswith("#") or href.lower().startswith(SKIP_SCHEMES): return None
    parsed=urlparse(href)
    if parsed.scheme or parsed.netloc: return None
    path=unquote(parsed.path or "")
    if not path: return None
    if path.startswith("/"):
        target=posixpath.normpath(path)
    else:
        base=source_route if source_route.endswith("/") else posixpath.dirname(source_route)+"/"
        target=posixpath.normpath(posixpath.join(base, path))
    if not target.startswith("/"): target="/"+target
    if path.endswith("/") and target != "/": target += "/"
    return target


def exists(target: str, index: dict[str,str], root: Path) -> bool:
    key=target.rstrip("/") or "/"
    if key in index or target in index: return True
    fs=(root / target.lstrip("/"))
    if fs.is_file(): return True
    if fs.is_dir() and (fs/"index.html").is_file(): return True
    return False


def suggestions(target: str, routes: list[str], n: int=5) -> list[str]:
    key=target.rstrip("/") or "/"
    # Restrict candidates to similar final slug or parent before fuzzy matching.
    slug=key.split("/")[-1]
    parent="/".join(key.split("/")[:-1])
    pool=[r for r in routes if (slug and slug in r) or (parent and r.startswith(parent))]
    if len(pool) < 5: pool=routes
    return difflib.get_close_matches(key, pool, n=n, cutoff=0.55)


def build(root: Path) -> dict:
    index,routes=route_index(root)
    refs=defaultdict(list)
    for page in public_html(root):
        rel=page.relative_to(root).as_posix()
        route=route_for(page.relative_to(root))
        text=page.read_text(encoding="utf-8", errors="replace")
        for _,href in HREF_RE.findall(text):
            target=normalize_href(href, route)
            if target is None or exists(target,index,root): continue
            refs[target].append({"source":rel,"href":href})
    items=[]
    for target,uses in refs.items():
        unique_sources=sorted({u["source"] for u in uses})
        items.append({
            "target":target,
            "occurrences":len(uses),
            "source_pages":unique_sources,
            "source_page_count":len(unique_sources),
            "suggested_existing_routes":suggestions(target,routes),
        })
    items.sort(key=lambda x:(-x["occurrences"],-x["source_page_count"],x["target"]))
    return {
        "version":VERSION,
        "status":"passed",
        "policy":"Suggestions are candidates only. Never rewrite a link unless destination intent is verified.",
        "summary":{
            "broken_targets":len(items),
            "broken_occurrences":sum(x["occurrences"] for x in items),
            "affected_pages":len({p for x in items for p in x["source_pages"]}),
            "top_targets": [{"target":x["target"],"occurrences":x["occurrences"]} for x in items[:20]],
        },
        "items":items,
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("site",type=Path)
    ap.add_argument("--output",type=Path,default=Path("artifacts/site-quality-agent-v410/broken-links-v417.json"))
    args=ap.parse_args()
    result=build(args.site.resolve())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result["summary"],ensure_ascii=False,indent=2))
    return 0

if __name__ == "__main__": raise SystemExit(main())
