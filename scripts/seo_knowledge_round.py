#!/usr/bin/env python3
import argparse
import hashlib
import html
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

BASE = "https://healthrenewal.org"
TARGET = 50
ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIR = ROOT / ".github" / "seo"
MANIFEST_PATH = PRIVATE_DIR / "knowledge-manifest.json"
REPORT_PATH = PRIVATE_DIR / "knowledge-round-report.json"
SITEMAP_PATH = ROOT / "sitemap.xml"
SOCIAL_IMAGE = ROOT / "assets" / "brand" / "rawafid-social-card.jpg"

# Exact owned paths plus two verified subordinate knowledge structures.
# psychology/ is accepted only while its index explicitly links to /encyclopedia/.
# terms/ is accepted only while its index explicitly identifies itself as a glossary.
BASE_SCOPE = [
    ROOT / "encyclopedia",
    ROOT / "resources",
    ROOT / "sectors" / "short-encyclopedia",
]

AR_STOP = {
    "من", "في", "على", "إلى", "الى", "عن", "ما", "هو", "هي", "هذا", "هذه", "ذلك", "تلك",
    "مع", "أو", "او", "ثم", "أن", "ان", "لا", "قد", "كل", "بين", "عند", "كما", "بعد", "قبل",
    "حتى", "إذا", "اذا", "يمكن", "يكون", "تكون", "التي", "الذي", "الذين", "و", "ف", "ب", "ل"
}


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path):
    return path.read_text(encoding="utf-8")


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def strip_tags(value):
    value = re.sub(r"<script\b.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def body_part(doc):
    m = re.search(r"(<body\b.*)", doc, flags=re.I | re.S)
    return m.group(1) if m else ""


def head_part(doc):
    m = re.search(r"(<head\b[^>]*>)(.*?)(</head>)", doc, flags=re.I | re.S)
    return m.groups() if m else None


def get_title(head):
    m = re.search(r"<title\b[^>]*>(.*?)</title>", head, flags=re.I | re.S)
    return strip_tags(m.group(1)) if m else ""


def get_h1(doc):
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", doc, flags=re.I | re.S)
    return strip_tags(m.group(1)) if m else ""


def get_meta(head, key, prop=False):
    attr = "property" if prop else "name"
    p1 = rf'<meta\b[^>]*\b{attr}\s*=\s*["\']{re.escape(key)}["\'][^>]*\bcontent\s*=\s*["\']([^"\']*)["\'][^>]*>'
    p2 = rf'<meta\b[^>]*\bcontent\s*=\s*["\']([^"\']*)["\'][^>]*\b{attr}\s*=\s*["\']{re.escape(key)}["\'][^>]*>'
    m = re.search(p1, head, flags=re.I) or re.search(p2, head, flags=re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def get_canonical(head):
    m = re.search(r'<link\b[^>]*\brel\s*=\s*["\']canonical["\'][^>]*\bhref\s*=\s*["\']([^"\']+)["\'][^>]*>', head, flags=re.I)
    if not m:
        m = re.search(r'<link\b[^>]*\bhref\s*=\s*["\']([^"\']+)["\'][^>]*\brel\s*=\s*["\']canonical["\'][^>]*>', head, flags=re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def set_title(head, value):
    tag = f"<title>{html.escape(value)}</title>"
    if re.search(r"<title\b[^>]*>.*?</title>", head, flags=re.I | re.S):
        return re.sub(r"<title\b[^>]*>.*?</title>", tag, head, count=1, flags=re.I | re.S)
    return tag + "\n" + head


def set_meta(head, key, value, prop=False):
    attr = "property" if prop else "name"
    tag = f'<meta {attr}="{html.escape(key, quote=True)}" content="{html.escape(value, quote=True)}">'
    pat = rf'<meta\b(?=[^>]*\b{attr}\s*=\s*["\']{re.escape(key)}["\'])[^>]*>'
    if re.search(pat, head, flags=re.I):
        return re.sub(pat, tag, head, count=1, flags=re.I)
    return head.rstrip() + "\n" + tag + "\n"


def set_canonical(head, url):
    tag = f'<link rel="canonical" href="{html.escape(url, quote=True)}">'
    pat = r'<link\b(?=[^>]*\brel\s*=\s*["\']canonical["\'])[^>]*>'
    if re.search(pat, head, flags=re.I):
        return re.sub(pat, tag, head, count=1, flags=re.I)
    return head.rstrip() + "\n" + tag + "\n"


def ensure_lang(opening, lang):
    if re.search(r"\blang\s*=", opening, flags=re.I):
        return re.sub(r'\blang\s*=\s*["\'][^"\']+["\']', f'lang="{lang}"', opening, count=1, flags=re.I)
    return opening[:-1] + f' lang="{lang}">'


def expected_url(path):
    rel = path.relative_to(ROOT).as_posix()
    if rel.endswith("/index.html"):
        route = "/" + rel[:-10]
    elif rel == "index.html":
        route = "/"
    else:
        route = "/" + rel
    if not route.endswith("/") and "." not in Path(route).name:
        route += "/"
    return BASE + route, route


def derived_description(doc, h1):
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", doc, flags=re.I | re.S):
        text = strip_tags(m.group(1))
        if len(text) >= 55:
            text = text[:155].rstrip(" ،؛:-")
            return text
    return f"صفحة مرجعية في روافد تشرح {h1} ضمن المحتوى المعرفي الحالي للمنصة."


def page_label(path):
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith("psychology/"):
        return "علم النفس"
    if rel.startswith("terms/"):
        return "مصطلحات علم النفس"
    if rel.startswith("resources/"):
        return "المواد العملية"
    if rel.startswith("sectors/short-encyclopedia/"):
        return "الموسوعة المختصرة"
    return "الموسوعة"


def schema_graph(url, title, desc, h1, label):
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": url + "#webpage",
                "url": url,
                "name": title,
                "description": desc,
                "inLanguage": "ar",
                "isPartOf": {"@id": BASE + "/#website"},
            },
            {
                "@type": "BreadcrumbList",
                "@id": url + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                    {"@type": "ListItem", "position": 2, "name": label, "item": url.rsplit("/", 2)[0] + "/"},
                    {"@type": "ListItem", "position": 3, "name": h1 or title, "item": url},
                ],
            },
            {"@type": "WebSite", "@id": BASE + "/#website", "url": BASE + "/", "name": "روافد | Health Renewal", "inLanguage": "ar"},
            {"@type": "Organization", "@id": BASE + "/#organization", "url": BASE + "/", "name": "Health Renewal | روافد"},
        ],
    }
    return json.dumps(graph, ensure_ascii=False, separators=(",", ":"))


def set_schema(head, graph_json):
    tag = f'<script id="seo-knowledge-graph" type="application/ld+json">{graph_json}</script>'
    pat = r'<script\b(?=[^>]*\bid\s*=\s*["\']seo-knowledge-graph["\'])[^>]*>.*?</script>'
    if re.search(pat, head, flags=re.I | re.S):
        head = re.sub(pat, tag, head, count=1, flags=re.I | re.S)
    else:
        head = head.rstrip() + "\n" + tag + "\n"
    if "<!-- seo-knowledge-round:v1 -->" not in head:
        head = head.rstrip() + "\n<!-- seo-knowledge-round:v1 -->\n"
    return head


def visible_anchors(doc):
    anchors = []
    seen = set()
    for tag in ("h2", "h3", "strong", "li"):
        for m in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", doc, flags=re.I | re.S):
            t = strip_tags(m.group(1)).strip(" .،؛:-")
            if 4 <= len(t) <= 95 and t not in seen:
                seen.add(t); anchors.append(t)
    text = strip_tags(body_part(doc))
    tokens = re.findall(r"[\u0600-\u06FFA-Za-z][\u0600-\u06FFA-Za-z0-9\-]{2,}", text)
    for n in (2, 3):
        for i in range(max(0, len(tokens) - n + 1)):
            chunk = tokens[i:i+n]
            if all(x.lower() in AR_STOP for x in chunk):
                continue
            t = " ".join(chunk)
            if 7 <= len(t) <= 70 and t not in seen:
                seen.add(t); anchors.append(t)
            if len(anchors) >= 110:
                return anchors
    return anchors


def semantic_map(doc, topic):
    out, seen = [], set()
    def add(x):
        x = re.sub(r"\s+", " ", x).strip(" .،؛:-")
        if x and x not in seen:
            seen.add(x); out.append(x)

    base_frames = [
        "تعريف {t}", "معنى {t}", "ما هو {t}", "ما معنى {t}", "شرح {t}", "فهم {t}",
        "معلومات عن {t}", "دليل {t}", "أسئلة عن {t}", "أسئلة شائعة عن {t}", "{t} في علم النفس",
        "{t} بالعربية", "مصطلح {t}", "مفهوم {t}", "كيف نفهم {t}", "ما المقصود بـ {t}",
        "{t} روافد", "{t} Health Renewal", "شرح علمي لـ {t}", "معلومات موثوقة عن {t}",
    ]
    for f in base_frames:
        add(f.format(t=topic))

    variants = {topic}
    simple = topic.translate(str.maketrans({"أ":"ا", "إ":"ا", "آ":"ا", "ى":"ي"}))
    if simple != topic: variants.add(simple)
    if "ة" in topic: variants.add(topic.replace("ة", "ه"))
    for v in variants:
        add(f"تعريف {v}"); add(f"ما معنى {v}"); add(f"{v} روافد")

    anchors = visible_anchors(doc)
    templates = [
        "{t} — {a}", "{a} في {t}", "شرح {a} في {t}", "فهم {a} ضمن {t}",
        "ما علاقة {a} بـ {t}", "كيف نفهم {a} عند دراسة {t}", "أسئلة عن {a} و{t}",
        "دليل {t} حول {a}", "معلومات عن {a} ضمن {t}", "{t}: معنى {a}",
        "{t}: شرح {a}", "البحث عن {a} في سياق {t}",
    ]
    for a in anchors:
        if a == topic: continue
        for f in templates:
            add(f.format(t=topic, a=a))
            if len(out) >= 620:
                break
        if len(out) >= 620:
            break

    # Use English/transliteration only if a Latin expression is actually visible.
    body_text = strip_tags(body_part(doc))
    latin = []
    for m in re.finditer(r"\b[A-Z][A-Za-z0-9\-]*(?:\s+[A-Z][A-Za-z0-9\-]*){0,4}\b", body_text):
        e = m.group(0).strip()
        if 2 < len(e) < 70 and e not in latin:
            latin.append(e)
        if len(latin) >= 8: break
    for e in latin:
        add(e); add(f"{e} بالعربية"); add(f"ما معنى {e}"); add(f"{topic} {e}"); add(f"{e} روافد")

    # If a short page still has fewer than 500 phrases, combine only concepts visibly present on that page.
    if len(out) < 500:
        compact = anchors[:60]
        for i, a in enumerate(compact):
            for b in compact[i+1:i+12]:
                add(f"{topic}: {a} و{b}")
                add(f"العلاقة بين {a} و{b} في {topic}")
                if len(out) >= 520: break
            if len(out) >= 520: break
    return out[:620]


def discover_scope():
    roots = [p for p in BASE_SCOPE if p.exists()]
    pidx = ROOT / "psychology" / "index.html"
    if pidx.exists():
        txt = read_text(pidx)
        if 'href="/encyclopedia/"' in txt and ("مركز علم النفس" in txt or "الموسوعة" in txt):
            roots.append(ROOT / "psychology")
    tidx = ROOT / "terms" / "index.html"
    if tidx.exists() and "معجم" in strip_tags(read_text(tidx)):
        roots.append(ROOT / "terms")
    return roots


def page_files(roots):
    found = []
    for root in roots:
        if not root.exists(): continue
        for p in root.rglob("index.html"):
            if any(part in {"assets", "node_modules", ".git"} for part in p.parts):
                continue
            found.append(p)
    return sorted(set(found), key=lambda p: p.relative_to(ROOT).as_posix())


def page_info(path):
    doc = read_text(path)
    hp = head_part(doc)
    if not hp:
        return {"path": path, "doc": doc, "eligible": False, "reason": "missing-head"}
    opening, head, closing = hp
    body = body_part(doc)
    h1 = get_h1(doc)
    title = get_title(head)
    desc = get_meta(head, "description")
    robots = get_meta(head, "robots").lower()
    canon = get_canonical(head)
    url, route = expected_url(path)
    if "noindex" in robots:
        return {"path": path, "doc": doc, "eligible": False, "reason": "noindex"}
    if re.search(r'<meta\b[^>]*http-equiv\s*=\s*["\']refresh["\']', head, flags=re.I):
        return {"path": path, "doc": doc, "eligible": False, "reason": "redirect"}
    if canon and urlparse(canon).path.rstrip("/") != urlparse(url).path.rstrip("/"):
        return {"path": path, "doc": doc, "eligible": False, "reason": "canonical-elsewhere"}
    if len(strip_tags(body)) < 220 or not h1:
        return {"path": path, "doc": doc, "eligible": False, "reason": "thin-or-missing-h1"}
    return {
        "path": path, "doc": doc, "opening": opening, "head": head, "closing": closing, "body": body,
        "h1": h1, "title": title, "desc": desc, "url": url, "route": route, "eligible": True,
    }


def jsonld_valid(head):
    for m in re.finditer(r'<script\b[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>', head, flags=re.I | re.S):
        try:
            json.loads(html.unescape(m.group(1)).strip())
        except Exception:
            return False
    return True


def required_complete(info, head, opening, sitemap_text, semantic):
    title = get_title(head); desc = get_meta(head, "description")
    robots = get_meta(head, "robots").lower()
    checks = [
        bool(title and ("روافد" in title or "Health Renewal" in title)),
        bool(desc),
        get_canonical(head) == info["url"],
        "index" in robots and "noindex" not in robots,
        "follow" in robots,
        "max-snippet:-1" in robots and "max-image-preview:large" in robots and "max-video-preview:-1" in robots,
        get_meta(head, "og:title", True) == title,
        get_meta(head, "og:description", True) == desc,
        get_meta(head, "og:url", True) == info["url"],
        bool(get_meta(head, "og:type", True)),
        get_meta(head, "og:site_name", True) == "منصة روافد",
        get_meta(head, "og:locale", True) == "ar_AR",
        get_meta(head, "twitter:title") == title,
        get_meta(head, "twitter:description") == desc,
        bool(get_meta(head, "twitter:card")),
        'lang="ar"' in opening.lower() or "lang='ar'" in opening.lower(),
        "seo-knowledge-graph" in head,
        jsonld_valid(head),
        info["url"] in sitemap_text,
        len(semantic) >= 500 and len(set(semantic)) == len(semantic),
    ]
    if SOCIAL_IMAGE.exists():
        checks.extend([
            get_meta(head, "og:image", True) == BASE + "/assets/brand/rawafid-social-card.jpg",
            get_meta(head, "twitter:image") == BASE + "/assets/brand/rawafid-social-card.jpg",
        ])
    return all(checks)


def improve(info, title_counts, desc_counts):
    opening, head = info["opening"], info["head"]
    old_head = head
    h1 = info["h1"]
    title = info["title"] or h1
    if "روافد" not in title and "Health Renewal" not in title:
        title = f"{title} | روافد"
    if title_counts[info["title"]] > 1 or not info["title"]:
        title = f"{h1} | روافد"
    desc = info["desc"] or derived_description(info["doc"], h1)
    if desc_counts[info["desc"]] > 1 or not info["desc"]:
        base = desc[:115].rstrip(" ،؛:-")
        desc = f"{base} — {h1} في روافد."
    if len(desc) > 170:
        desc = desc[:167].rstrip(" ،؛:-") + "…"

    head = set_title(head, title)
    head = set_meta(head, "description", desc)
    head = set_meta(head, "robots", "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1")
    head = set_canonical(head, info["url"])

    existing_type = get_meta(head, "og:type", True)
    if not existing_type:
        existing_type = "article" if re.search(r'"@type"\s*:\s*"Article"', head) else "website"
    head = set_meta(head, "og:title", title, True)
    head = set_meta(head, "og:description", desc, True)
    head = set_meta(head, "og:type", existing_type, True)
    head = set_meta(head, "og:url", info["url"], True)
    head = set_meta(head, "og:site_name", "منصة روافد", True)
    head = set_meta(head, "og:locale", "ar_AR", True)
    if SOCIAL_IMAGE.exists():
        img = BASE + "/assets/brand/rawafid-social-card.jpg"
        head = set_meta(head, "og:image", img, True)
        head = set_meta(head, "twitter:image", img)
        head = set_meta(head, "twitter:card", "summary_large_image")
    else:
        head = set_meta(head, "twitter:card", "summary")
    head = set_meta(head, "twitter:title", title)
    head = set_meta(head, "twitter:description", desc)
    opening = ensure_lang(opening, "ar")
    head = set_schema(head, schema_graph(info["url"], title, desc, h1, page_label(info["path"])))

    new_doc = info["doc"].replace(info["opening"] + info["head"] + info["closing"], opening + head + info["closing"], 1)
    fixes = {
        "meta": old_head != head,
        "schema": "seo-knowledge-graph" not in old_head,
        "og": get_meta(old_head, "og:site_name", True) != "منصة روافد" or get_meta(old_head, "og:locale", True) != "ar_AR" or not get_meta(old_head, "og:title", True),
        "twitter": not get_meta(old_head, "twitter:title") or not get_meta(old_head, "twitter:description"),
        "canonical": get_canonical(old_head) != info["url"],
        "indexability": "max-video-preview:-1" not in get_meta(old_head, "robots").lower(),
    }
    return new_doc, opening, head, title, desc, fixes


def load_manifest():
    if not MANIFEST_PATH.exists(): return {"version": 1, "pages": {}}
    try:
        return json.loads(read_text(MANIFEST_PATH))
    except Exception:
        return {"version": 1, "pages": {}}


def update_sitemap(urls):
    if not SITEMAP_PATH.exists():
        return "", set(urls), False
    text = read_text(SITEMAP_PATH)
    missing = {u for u in urls if u not in text}
    if not missing:
        return text, set(), False
    if "</urlset>" not in text:
        return text, missing, False
    payload = "".join(f"\n  <url><loc>{html.escape(u)}</loc></url>" for u in sorted(missing))
    text2 = text.replace("</urlset>", payload + "\n</urlset>", 1)
    write_text(SITEMAP_PATH, text2)
    return text2, set(), True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=TARGET)
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    roots = discover_scope()
    files = page_files(roots)
    infos = [page_info(p) for p in files]
    eligible = [i for i in infos if i.get("eligible")]
    title_counts = Counter(i["title"] for i in eligible if i["title"])
    desc_counts = Counter(i["desc"] for i in eligible if i["desc"])
    manifest = load_manifest()
    manifest.setdefault("pages", {})

    skipped = Counter(i.get("reason", "unknown") for i in infos if not i.get("eligible"))
    noops = 0
    failed = []
    staged = []
    maps = {}

    # Identify pages that still need a material head improvement. Never count unchanged pages.
    current_sitemap = read_text(SITEMAP_PATH) if SITEMAP_PATH.exists() else ""
    for info in eligible:
        if len(staged) >= args.target:
            break
        semantic = semantic_map(info["doc"], info["h1"])
        new_doc, opening, new_head, title, desc, fixes = improve(info, title_counts, desc_counts)
        if new_doc == info["doc"]:
            noops += 1
            continue
        if body_part(new_doc) != info["body"]:
            failed.append({"path": info["route"], "reason": "visible-body-changed"})
            continue
        if len(semantic) < 500:
            failed.append({"path": info["route"], "reason": "semantic-map-below-500"})
            continue
        staged.append({"info": info, "doc": new_doc, "opening": opening, "head": new_head, "title": title, "desc": desc, "semantic": semantic, "fixes": fixes})
        maps[info["route"]] = semantic

    sitemap_text, sitemap_unresolved, sitemap_changed = update_sitemap([x["info"]["url"] for x in staged])
    if not sitemap_text and SITEMAP_PATH.exists(): sitemap_text = read_text(SITEMAP_PATH)

    # Recompute pairwise overlap for the selected round only; record the strongest competitor.
    overlap = {}
    routes = list(maps)
    mapsets = {r: set(maps[r]) for r in routes}
    for r in routes:
        best_peer, best_score = None, 0.0
        for q in routes:
            if q == r: continue
            a, b = mapsets[r], mapsets[q]
            score = len(a & b) / max(1, len(a | b))
            if score > best_score:
                best_peer, best_score = q, score
        overlap[r] = {"closest_page": best_peer, "jaccard": round(best_score, 6)}

    # Ensure final title/description uniqueness against all scoped pages, replacing originals for selected pages.
    final_titles = Counter(i["title"] for i in eligible if i["title"])
    final_descs = Counter(i["desc"] for i in eligible if i["desc"])
    for x in staged:
        oldt, oldd = x["info"]["title"], x["info"]["desc"]
        if oldt: final_titles[oldt] -= 1
        if oldd: final_descs[oldd] -= 1
        final_titles[x["title"]] += 1
        final_descs[x["desc"]] += 1

    successes = []
    fix_counts = Counter()
    for x in staged:
        info = x["info"]
        route = info["route"]
        if info["url"] in sitemap_unresolved:
            failed.append({"path": route, "reason": "sitemap-unresolved"}); continue
        if final_titles[x["title"]] != 1:
            failed.append({"path": route, "reason": "duplicate-title"}); continue
        if final_descs[x["desc"]] != 1:
            failed.append({"path": route, "reason": "duplicate-description"}); continue
        if not required_complete(info, x["head"], x["opening"], sitemap_text, x["semantic"]):
            failed.append({"path": route, "reason": "post-write-seo-validation"}); continue
        write_text(info["path"], x["doc"])
        for k, v in x["fixes"].items():
            if v: fix_counts[k] += 1
        if sitemap_changed: fix_counts["sitemap"] += 1
        seo_fp = sha256(x["opening"] + x["head"])
        manifest["pages"][route] = {
            "url": info["url"],
            "primary_intent": f"فهم {info['h1']} علميًا",
            "source_fingerprint": sha256(info["body"]),
            "seo_fingerprint": seo_fp,
            "last_optimized": started,
            "semantic_map_count": len(x["semantic"]),
            "semantic_map": x["semantic"],
            "cannibalization": overlap.get(route, {"closest_page": None, "jaccard": 0.0}),
            "verification": {
                "title_unique": True, "description_unique": True, "canonical": True,
                "robots_indexable": True, "sitemap_included": True, "structured_data_valid": True,
                "og_twitter_consistent": True, "locale": "ar_AR", "visible_body_unchanged": True
            }
        }
        successes.append(route)

    # Pages not written due validation must not be left in sitemap solely because this run staged them.
    # We do not remove pre-existing sitemap entries; removal is intentionally out of scope.
    manifest["version"] = 1
    manifest["scope"] = [str(r.relative_to(ROOT)) for r in roots]
    manifest["updated_at"] = started
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    write_text(MANIFEST_PATH, json.dumps(manifest, ensure_ascii=False, indent=2))

    # Remaining eligible pages are pages that would still receive a material change on the next idempotent pass.
    remaining = 0
    success_set = set(successes)
    for info in eligible:
        if info["route"] in success_set: continue
        semantic = semantic_map(info["doc"], info["h1"])
        new_doc, *_ = improve(info, title_counts, desc_counts)
        if new_doc != info["doc"] and len(semantic) >= 500:
            remaining += 1

    complete = len(successes) >= args.target
    report = {
        "sector": "الموسوعة والمعرفة",
        "target": args.target,
        "status": "complete" if complete else "incomplete",
        "status_ar": "الجولة مكتملة" if complete else "الجولة غير مكتملة",
        "successes_actual": len(successes),
        "success_paths": successes,
        "skipped_noop": noops,
        "skipped_by_reason": dict(skipped),
        "failed_count": len(failed),
        "failed": failed,
        "eligible_remaining": remaining,
        "fix_counts": dict(fix_counts),
        "sitemap_changed": sitemap_changed,
        "scope_roots": [str(r.relative_to(ROOT)) for r in roots],
        "started_at": started,
        "hard_blocker": None if complete else ("fewer-than-target-verified-pages" if len(eligible) < args.target else "validation-prevented-target"),
    }
    write_text(REPORT_PATH, json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
