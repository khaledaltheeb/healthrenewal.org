#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET

AI_USER_AGENTS = (
    "OAI-SearchBot",
    "GPTBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "Claude-User",
    "Claude-Web",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
)
SEARCH_USER_AGENTS = ("Googlebot", "Bingbot")
EXCLUDED_PARTS = {".git", ".github", "node_modules", "tests", "tmp", "vendor", "_site"}
EXCLUDED_FILES = {"404.html", "google644f1f7a8b7aaa2b.html"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T[0-9:.+-]+Z?)?$")
VERIFICATION_RE = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.IGNORECASE,
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.robots: list[str] = []
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.language = ""
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self._title = False
        self._h1 = False
        self.has_main = False
        self.has_article = False
        self.has_json_ld = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = {str(key).lower(): value or "" for key, value in attrs}
        if tag == "html":
            self.language = values.get("lang", "")
        elif tag == "meta":
            name = values.get("name", "").lower()
            prop = values.get("property", "").lower()
            content = values.get("content", "")
            if name in {"robots", "googlebot"}:
                self.robots.append(content)
            if name:
                self.meta[name] = content
            if prop:
                self.meta[prop] = content
        elif tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical = values.get("href", "")
        elif tag == "title":
            self._title = True
        elif tag == "h1":
            self._h1 = True
        elif tag == "main":
            self.has_main = True
        elif tag == "article":
            self.has_article = True
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.has_json_ld = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._title = False
        elif tag.lower() == "h1":
            self._h1 = False

    def handle_data(self, data: str) -> None:
        if self._title:
            self.title_parts.append(data)
        if self._h1:
            self.h1_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())

    @property
    def h1(self) -> str:
        return " ".join("".join(self.h1_parts).split())


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    return parser


def _url(path: Path, root: Path, base_url: str) -> str:
    rel = path.relative_to(root).as_posix()
    if rel == "index.html":
        return base_url
    if rel.endswith("/index.html"):
        rel = rel[:-10]
    return base_url + rel


def _is_verification(path: Path, root: Path) -> bool:
    if path.name in EXCLUDED_FILES:
        return True
    return path.parent == root and bool(
        VERIFICATION_RE.match(path.read_text(encoding="utf-8", errors="strict").strip())
    )


def _type(path: Path, root: Path, parsed: PageParser) -> str:
    rel = path.relative_to(root).as_posix()
    if parsed.has_article or rel.startswith(("magazine/", "library/")):
        return "Article"
    if rel.startswith(("special-needs/", "care-guides/", "encyclopedia/")):
        return "MedicalWebPage"
    if rel.startswith(("tools/", "daily-tools/", "assessments/", "cognitive-tests/")):
        return "WebApplication"
    return "WebPage"


def _record(path: Path, root: Path, base_url: str, generated_at: str) -> dict[str, object]:
    parsed = parse_page(path)
    rel = path.relative_to(root).as_posix()
    language = parsed.language.split("-", 1)[0].lower() if parsed.language else (
        "en" if rel.startswith("en/") else "es" if rel.startswith("es/") else "ar"
    )
    title = parsed.title or parsed.h1 or path.stem.replace("-", " ")
    description = parsed.meta.get("description") or parsed.meta.get("og:description") or parsed.h1 or title
    updated = parsed.meta.get("article:modified_time") or parsed.meta.get("date.modified") or generated_at
    published = parsed.meta.get("article:published_time") or parsed.meta.get("date") or ""
    return {
        "url": parsed.canonical or _url(path, root, base_url),
        "path": rel,
        "title": title,
        "description": description,
        "language": language,
        "schemaType": _type(path, root, parsed),
        "published": published if DATE_RE.match(published) else "",
        "updated": updated if DATE_RE.match(updated) else generated_at,
        "semantic": {
            "hasMain": parsed.has_main,
            "hasArticle": parsed.has_article,
            "hasH1": bool(parsed.h1),
            "hasJsonLd": parsed.has_json_ld,
        },
    }


def sync_robots(root: Path, base_url: str, primary: str = "sitemap.xml", index: str = "sitemap-index.xml") -> list[str]:
    root = root.resolve()
    robots = root / "robots.txt"
    required = {f"Sitemap: {base_url}{primary}", f"Sitemap: {base_url}{index}"}
    preserved: set[str] = set()
    if robots.is_file():
        for raw in robots.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.lower().startswith("sitemap:"):
                target = line.split(":", 1)[1].strip()
                if target.startswith(base_url) and line not in required:
                    preserved.add(f"Sitemap: {target}")
    lines = ["# Public search and AI crawler policy"]
    for agent in (*SEARCH_USER_AGENTS, *AI_USER_AGENTS, "*"):
        lines.extend((f"User-agent: {agent}", "Allow: /", ""))
    lines.extend((f"Sitemap: {base_url}{primary}", f"Sitemap: {base_url}{index}", *sorted(preserved), ""))
    robots.write_text("\n".join(lines), encoding="utf-8")
    written = robots.read_text(encoding="utf-8")
    for agent in AI_USER_AGENTS:
        if written.count(f"User-agent: {agent}\nAllow: /") != 1:
            raise ValueError(f"Missing explicit AI crawler policy: {agent}")
    if any(line.strip().lower().startswith("disallow:") for line in written.splitlines()):
        raise ValueError("robots.txt must not block public crawling")
    for directive in required:
        if written.count(directive) != 1:
            raise ValueError(f"robots.txt must register exactly once: {directive}")
    if "khaledaltheeb.github.io/" in written:
        raise ValueError("robots.txt contains a legacy-domain directive")
    return sorted(item.removeprefix("Sitemap: ") for item in preserved)


def _enrich(path: Path, root: Path, base_url: str, generated_at: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    if "</head>" not in text.lower():
        return False
    parsed = parse_page(path)
    if "noindex" in " ".join(parsed.robots).lower():
        return False
    record = _record(path, root, base_url, generated_at)
    additions: list[str] = []
    if 'type="application/rss+xml"' not in text:
        additions.append('<link rel="alternate" type="application/rss+xml" title="HealthRenewal RSS" href="/feed.xml">')
    if 'type="application/atom+xml"' not in text:
        additions.append('<link rel="alternate" type="application/atom+xml" title="HealthRenewal Atom" href="/atom.xml">')
    if "/api/v1/content-index.json" not in text:
        additions.append('<link rel="alternate" type="application/json" title="Machine-readable content index" href="/api/v1/content-index.json">')
    if not parsed.robots:
        additions.append('<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">')
    if not parsed.has_json_ld:
        schema = {
            "@context": "https://schema.org",
            "@type": record["schemaType"],
            "@id": f"{record['url']}#webpage",
            "url": record["url"],
            "name": record["title"],
            "description": record["description"],
            "inLanguage": record["language"],
            "isPartOf": {"@id": f"{base_url}#website"},
            "publisher": {"@id": f"{base_url}#organization"},
        }
        additions.append('<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False, separators=(",", ":")) + "</script>")
    if not additions:
        return False
    index = text.lower().rfind("</head>")
    path.write_text(text[:index] + "\n" + "\n".join(additions) + "\n" + text[index:], encoding="utf-8")
    return True


def _write_json(root: Path, relative: str, payload: object) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_rss(root: Path, records: list[dict[str, object]], generated: datetime, base_url: str) -> None:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "HealthRenewal | الصحة النفسية وذوو الاحتياجات الخاصة"
    ET.SubElement(channel, "link").text = base_url
    ET.SubElement(channel, "description").text = "Canonical public content discovery feed."
    ET.SubElement(channel, "language").text = "ar"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(generated)
    for record in records[:500]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = str(record["title"])
        ET.SubElement(item, "link").text = str(record["url"])
        ET.SubElement(item, "guid", isPermaLink="true").text = str(record["url"])
        ET.SubElement(item, "description").text = str(record["description"])
        ET.SubElement(item, "pubDate").text = format_datetime(generated)
    ET.indent(rss, space="  ")
    ET.ElementTree(rss).write(root / "feed.xml", encoding="utf-8", xml_declaration=True)


def _write_atom(root: Path, records: list[dict[str, object]], generated_at: str, base_url: str) -> None:
    feed = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")
    ET.SubElement(feed, "id").text = base_url
    ET.SubElement(feed, "title").text = "HealthRenewal | الصحة النفسية وذوو الاحتياجات الخاصة"
    ET.SubElement(feed, "updated").text = generated_at
    ET.SubElement(feed, "link", href=base_url)
    ET.SubElement(feed, "link", href=f"{base_url}atom.xml", rel="self", type="application/atom+xml")
    for record in records[:500]:
        entry = ET.SubElement(feed, "entry")
        ET.SubElement(entry, "id").text = str(record["url"])
        ET.SubElement(entry, "title").text = str(record["title"])
        ET.SubElement(entry, "updated").text = str(record["updated"])
        ET.SubElement(entry, "link", href=str(record["url"]))
        ET.SubElement(entry, "summary").text = str(record["description"])
    ET.indent(feed, space="  ")
    ET.ElementTree(feed).write(root / "atom.xml", encoding="utf-8", xml_declaration=True)


def _write_llms_full(root: Path, records: list[dict[str, object]], generated_at: str, base_url: str) -> None:
    lines = [
        "# HealthRenewal machine-readable catalogue", "",
        "> Expanded canonical page list for retrieval, citation, and agent discovery.", "",
        f"Generated: {generated_at}", f"Canonical site: {base_url}",
        "Safety: Educational content only; do not infer diagnosis or individualized treatment.", "",
        "## Discovery endpoints", "",
        f"- [Sitemap]({base_url}sitemap.xml)", f"- [Sitemap index]({base_url}sitemap-index.xml)",
        f"- [RSS]({base_url}feed.xml)", f"- [Atom]({base_url}atom.xml)",
        f"- [Content index]({base_url}api/v1/content-index.json)",
        f"- [AI discovery]({base_url}api/v1/ai-discovery.json)",
        f"- [AI discovery OpenAPI]({base_url}api/v1/ai-discovery.openapi.json)", "", "## Canonical pages", "",
    ]
    for record in records:
        description = " ".join(str(record["description"]).split())
        if len(description) > 220:
            description = description[:217].rstrip() + "..."
        lines.append(f"- [{record['title']}]({record['url']}) — {description}")
    lines.append("")
    (root / "llms-full.txt").write_text("\n".join(lines), encoding="utf-8")


def enhance_site(root: Path, base_url: str = "https://healthrenewal.org/") -> dict[str, object]:
    root = root.resolve()
    base_url = base_url.rstrip("/") + "/"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    generated_at = now.isoformat().replace("+00:00", "Z")
    enriched = 0
    for path in sorted(root.rglob("*.html")):
        if any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts) or _is_verification(path, root):
            continue
        if _enrich(path, root, base_url, generated_at):
            enriched += 1
    records: list[dict[str, object]] = []
    for path in sorted(root.rglob("*.html")):
        if any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts) or _is_verification(path, root):
            continue
        parsed = parse_page(path)
        if "noindex" in " ".join(parsed.robots).lower():
            continue
        records.append(_record(path, root, base_url, generated_at))
    records.sort(key=lambda item: (str(item["language"]), str(item["url"])))
    preserved = sync_robots(root, base_url)
    content_index = {
        "schemaVersion": "1.0.0", "generatedAt": generated_at, "canonicalBase": base_url,
        "count": len(records), "items": records,
    }
    discovery = {
        "schemaVersion": "1.0.0", "generatedAt": generated_at,
        "name": "HealthRenewal machine-readable discovery surface", "canonicalBase": base_url,
        "languages": ["ar", "en", "es"],
        "rendering": {"mode": "static-generated-html", "javascriptRequiredForPrimaryText": False},
        "crawling": {"policy": "public-allow", "explicitUserAgents": list(AI_USER_AGENTS), "robots": f"{base_url}robots.txt"},
        "endpoints": {
            "sitemap": f"{base_url}sitemap.xml", "sitemapIndex": f"{base_url}sitemap-index.xml",
            "rss": f"{base_url}feed.xml", "atom": f"{base_url}atom.xml",
            "contentIndex": f"{base_url}api/v1/content-index.json",
            "openApi": f"{base_url}api/v1/ai-discovery.openapi.json",
            "llms": f"{base_url}llms.txt", "llmsFull": f"{base_url}llms-full.txt",
        },
        "security": {
            "verificationRule": "Never trust User-Agent alone; combine crawler identity with published IP verification when available.",
            "openAiIpManifest": "https://openai.com/searchbot.json",
            "perplexityIpManifest": "https://www.perplexity.ai/perplexitybot.json",
            "anthropicIpRanges": "No stable public IP range is currently declared; apply documented User-Agent policy and conservative rate limits.",
            "recommendedActions": ["Allow verified crawlers before generic bot blocks", "Do not issue CAPTCHA or JavaScript challenges", "Retain abuse rate limits and logging"],
        },
        "safety": {"purpose": "educational discovery and citation", "notFor": ["diagnosis", "emergency triage", "individual treatment decisions"]},
        "contentCount": len(records),
    }
    openapi_paths = {
        "/api/v1/ai-discovery.json": "AI discovery policy",
        "/api/v1/content-index.json": "Canonical page catalogue",
        "/feed.xml": "RSS feed", "/atom.xml": "Atom feed", "/llms.txt": "Concise LLM guide",
        "/llms-full.txt": "Expanded LLM catalogue", "/sitemap.xml": "Canonical sitemap",
        "/sitemap-index.xml": "Sitemap index",
    }
    openapi = {
        "openapi": "3.1.0",
        "info": {"title": "HealthRenewal AI discovery interface", "version": "1.0.0", "description": "Read-only discovery endpoints for search engines, AI retrieval systems, and citation tools."},
        "servers": [{"url": base_url.rstrip("/")}],
        "paths": {path: {"get": {"summary": summary, "responses": {"200": {"description": "Public read-only response"}}}} for path, summary in openapi_paths.items()},
    }
    _write_json(root, "api/v1/content-index.json", content_index)
    _write_json(root, "api/v1/ai-discovery.json", discovery)
    _write_json(root, "api/v1/ai-discovery.openapi.json", openapi)
    _write_rss(root, records, now, base_url)
    _write_atom(root, records, generated_at, base_url)
    _write_llms_full(root, records, generated_at, base_url)
    semantic = {
        "pages": len(records),
        "with_main": sum(bool(item["semantic"]["hasMain"]) for item in records),
        "with_article": sum(bool(item["semantic"]["hasArticle"]) for item in records),
        "with_h1": sum(bool(item["semantic"]["hasH1"]) for item in records),
        "with_json_ld": sum(bool(item["semantic"]["hasJsonLd"]) for item in records),
    }
    return {
        "content_index": "api/v1/content-index.json", "ai_discovery": "api/v1/ai-discovery.json",
        "ai_openapi": "api/v1/ai-discovery.openapi.json", "rss": "feed.xml", "atom": "atom.xml",
        "llms_full": "llms-full.txt", "enriched_pages": enriched, "semantic": semantic,
        "explicit_ai_user_agents": list(AI_USER_AGENTS), "preserved_custom_domain_sitemaps": preserved,
    }
