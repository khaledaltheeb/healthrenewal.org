#!/usr/bin/env python3
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
SECTOR = ROOT / "evidence-guides" / "social-work"
BASE = "https://healthrenewal.org/evidence-guides/social-work/"

def match(pattern: str, text: str) -> str:
    m = re.search(pattern, text, re.I | re.S)
    return m.group(1).strip() if m else ""

def esc(value: str) -> str:
    return (value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))

pages = sorted(SECTOR.rglob("index.html"))
if not pages:
    raise SystemExit(f"No social-work pages found under {SECTOR}")

changed = 0
for path in pages:
    text = path.read_text(encoding="utf-8")
    title = match(r"<title>(.*?)</title>", text)
    description = match(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', text)
    canonical = match(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']', text)
    if not canonical:
        canonical = match(r'<link\s+href=["\'](.*?)["\']\s+rel=["\']canonical["\']', text)
    if not (title and description and canonical):
        raise SystemExit(f"Missing title/description/canonical: {path}")

    additions = []
    if "property=\"og:title\"" not in text and "property='og:title'" not in text:
        additions.extend([
            f'<meta property="og:type" content="{"website" if canonical == BASE else "article"}">',
            '<meta property="og:locale" content="ar_AR">',
            f'<meta property="og:title" content="{esc(title)}">',
            f'<meta property="og:description" content="{esc(description)}">',
            f'<meta property="og:url" content="{esc(canonical)}">',
            '<meta name="twitter:card" content="summary">',
        ])
    if "application/ld+json" not in text:
        payload = {
            "@context": "https://schema.org",
            "@type": "CollectionPage" if canonical == BASE else "Article",
            "name" if canonical == BASE else "headline": title,
            "description": description,
            "url" if canonical == BASE else "mainEntityOfPage": canonical,
            "inLanguage": "ar",
            "isPartOf" if canonical == BASE else "publisher": (
                {"@type": "WebSite", "name": "Rawafid | Health Renewal", "url": "https://healthrenewal.org/"}
                if canonical == BASE else
                {"@type": "Organization", "name": "Rawafid | Health Renewal", "url": "https://healthrenewal.org/"}
            ),
        }
        additions.append('<script type="application/ld+json">' + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + '</script>')

    robust_robots = '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">'
    robots_pattern = r'<meta\s+name=["\']robots["\']\s+content=["\'][^"\']*["\']\s*/?>'
    if re.search(robots_pattern, text, flags=re.I):
        text = re.sub(robots_pattern, robust_robots, text, flags=re.I)
    else:
        additions.append(robust_robots)

    if additions:
        if "</head>" not in text.lower():
            raise SystemExit(f"Missing </head>: {path}")
        text = re.sub(r"</head>", "".join(additions) + "</head>", text, count=1, flags=re.I)
        changed += 1
    path.write_text(text, encoding="utf-8")

print(json.dumps({"status":"passed","pages":len(pages),"metadataPagesChanged":changed}, ensure_ascii=False))
