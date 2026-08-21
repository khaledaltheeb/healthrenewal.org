#!/usr/bin/env python3
"""Materialize governed pediatric-oncology evidence pages from Supabase.

The source feed is intentionally private. In GitHub Actions this script obtains a
short-lived GitHub OIDC token and exchanges it directly with the Supabase Edge
Function. No Supabase service key is stored in the repository.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

BASE_URL = "https://healthrenewal.org"
EDGE_URL = "https://ghljwfwqsyfnthvlzxjy.supabase.co/functions/v1/pediatric-oncology-materialization"
OIDC_AUDIENCE = "rawafid-pediatric-oncology-materializer-v1"
MARKER = "<!-- rawafid:pediatric-oncology-materializer:v1 -->"
OWNER_META = '<meta name="rawafid-materializer" content="pediatric-oncology-v1">'
REPORT_PATH = Path("api/pediatric-oncology-materialization-v1.json")
MANAGED_ROOT = Path("magazine/pediatric-oncology")
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$", re.I)
ALLOWED_ROUTE_RE = re.compile(r"^/magazine/pediatric-oncology/(studies|theses)/([a-z0-9][a-z0-9-]{2,180})/$")


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def request_json(url: str, *, headers: dict[str, str]) -> Any:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def github_oidc_token() -> str:
    url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
    bearer = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
    if not url or not bearer:
        raise RuntimeError("GitHub Actions OIDC environment is unavailable")
    parsed = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True) if k != "audience"]
    query.append(("audience", OIDC_AUDIENCE))
    oidc_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment))
    payload = request_json(oidc_url, headers={"authorization": f"Bearer {bearer}", "accept": "application/json", "user-agent": "rawafid-pediatric-oncology-materializer/1"})
    token = str(payload.get("value") or "") if isinstance(payload, dict) else ""
    if not token:
        raise RuntimeError("GitHub OIDC response did not include a token")
    return token


def fetch_payload() -> dict[str, Any]:
    token = github_oidc_token()
    payload = request_json(EDGE_URL, headers={"authorization": f"Bearer {token}", "accept": "application/json", "user-agent": "rawafid-pediatric-oncology-materializer/1"})
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise RuntimeError("Unexpected pediatric-oncology materialization payload")
    return payload


def split_markdown_blocks(text: str) -> list[tuple[str, str]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[tuple[str, str]] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_kind = "ul"

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            value = " ".join(part.strip() for part in paragraph if part.strip()).strip()
            if value:
                blocks.append(("p", value))
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append((list_kind, "\n".join(list_items)))
            list_items = []

    for raw in lines:
        line = raw.strip()
        if not line:
            flush_paragraph(); flush_list(); continue
        heading = re.match(r"^(#{2,4})\s+(.+)$", line)
        if heading:
            flush_paragraph(); flush_list(); blocks.append((f"h{len(heading.group(1))}", heading.group(2).strip())); continue
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        numbered = re.match(r"^\d+[.)]\s+(.+)$", line)
        if bullet or numbered:
            flush_paragraph()
            desired = "ol" if numbered else "ul"
            if list_items and desired != list_kind:
                flush_list()
            list_kind = desired
            list_items.append((numbered or bullet).group(1).strip())
            continue
        flush_list(); paragraph.append(line)
    flush_paragraph(); flush_list()
    return blocks


def body_html(text: str) -> str:
    rendered: list[str] = []
    for kind, value in split_markdown_blocks(text):
        if kind in {"h2", "h3", "h4"}:
            rendered.append(f"<{kind}>{esc(value)}</{kind}>")
        elif kind == "p":
            rendered.append(f"<p>{esc(value)}</p>")
        elif kind in {"ul", "ol"}:
            items = "".join(f"<li>{esc(item)}</li>" for item in value.split("\n") if item)
            rendered.append(f"<{kind}>{items}</{kind}>")
    return "\n".join(rendered)


def route_info(row: dict[str, Any]) -> tuple[str, str]:
    canonical = str(row.get("canonical_url") or "")
    match = ALLOWED_ROUTE_RE.fullmatch(canonical)
    if not match:
        raise ValueError(f"Unsupported pediatric-oncology canonical route: {canonical!r}")
    kind, slug = match.groups()
    schema = row.get("schema_json") or {}
    evidence_type = schema.get("evidence_record_type")
    expected_kind = "studies" if evidence_type == "study" else "theses" if evidence_type == "thesis" else None
    if expected_kind != kind:
        raise ValueError(f"Route/evidence mismatch for {slug}: {kind} vs {evidence_type}")
    if slug != str(row.get("slug") or ""):
        raise ValueError(f"Canonical slug mismatch for {slug}")
    if int(schema.get("evidence_public_route_contract_version") or 0) < 2:
        raise ValueError(f"Evidence public-route contract v2 is missing for {slug}")
    return kind, slug


def validate_row(row: dict[str, Any]) -> None:
    kind, slug = route_info(row)
    schema = row.get("schema_json") or {}
    token = str(schema.get("release_token") or "")
    if not TOKEN_RE.fullmatch(token):
        raise ValueError(f"Invalid release token for {slug}")
    if row.get("status") not in {"scheduled", "published"}:
        raise ValueError(f"Unexpected materialization status for {slug}: {row.get('status')}")
    if not row.get("robots_index"):
        raise ValueError(f"Materialized evidence must be indexable: {slug}")
    if not str(row.get("title") or "").strip():
        raise ValueError(f"Missing title: {slug}")
    if len(str(row.get("body_text") or "").split()) < 500:
        raise ValueError(f"Evidence body is unexpectedly short: {slug}")
    refs = row.get("references_json")
    if not isinstance(refs, list) or len(refs) < 3:
        raise ValueError(f"Insufficient references: {slug}")
    if kind == "studies" and schema.get("content_evidence_audit_status") != "passed":
        raise ValueError(f"Study evidence audit is not passed: {slug}")


def schema_graph(row: dict[str, Any]) -> dict[str, Any]:
    canonical = BASE_URL + str(row["canonical_url"])
    refs = row.get("references_json") or []
    citations = [ref.get("url") for ref in refs if isinstance(ref, dict) and ref.get("url")]
    date_value = row.get("published_at") or row.get("scheduled_at") or row.get("updated_at") or ""
    return {"@context": "https://schema.org", "@graph": [{"@type": "ScholarlyArticle", "headline": row.get("title") or "", "description": row.get("seo_description") or row.get("excerpt") or "", "inLanguage": "ar", "url": canonical, "mainEntityOfPage": canonical, "datePublished": str(date_value)[:10], "dateModified": str(row.get("updated_at") or date_value)[:10], "author": {"@type": "Organization", "name": row.get("author_display_name") or "فريق تحرير منصة روافد"}, "publisher": {"@type": "Organization", "name": "منصة روافد", "url": BASE_URL + "/"}, "citation": citations}, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE_URL + "/"}, {"@type": "ListItem", "position": 2, "name": "المجلة والأبحاث", "item": BASE_URL + "/magazine/"}, {"@type": "ListItem", "position": 3, "name": "أبحاث سرطان الأطفال", "item": BASE_URL + "/magazine/pediatric-oncology/"}, {"@type": "ListItem", "position": 4, "name": row.get("title") or "", "item": canonical}]}]}


def references_html(row: dict[str, Any]) -> str:
    items = []
    for ref in row.get("references_json") or []:
        if isinstance(ref, dict) and ref.get("url"):
            items.append(f'<li><a href="{esc(ref["url"])}" rel="noopener noreferrer">{esc(ref.get("title") or ref.get("publisher") or ref.get("url"))}</a></li>')
    return "\n".join(items)


def render_article(row: dict[str, Any]) -> str:
    validate_row(row)
    kind, _slug = route_info(row)
    schema = row.get("schema_json") or {}
    token = str(schema["release_token"])
    canonical = BASE_URL + str(row["canonical_url"])
    title = row.get("seo_title") or row.get("title") or ""
    description = row.get("seo_description") or row.get("excerpt") or "قراءة علمية عربية موثقة."
    graph = json.dumps(schema_graph(row), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    label = "الدراسة الأصلية والمراجع" if kind == "studies" else "السجل الجامعي والمراجع"
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)} | منصة روافد</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="rawafid-release-token" content="{esc(token)}">{OWNER_META}<link rel="canonical" href="{esc(canonical)}"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><script type="application/ld+json">{graph}</script><style>body{{font-family:Tahoma,Arial,sans-serif;line-height:1.95;color:#173f45;background:#f7fbfa;margin:0}}main{{width:min(980px,92%);margin:auto;padding:32px 0 72px}}header,article,section,aside{{background:#fff;border:1px solid #cfe7e3;border-radius:20px;padding:clamp(18px,4vw,30px);margin:16px 0}}h1{{font-size:clamp(2rem,5vw,3rem);line-height:1.35}}h2{{color:#075f5b;margin-top:2rem}}h3,h4{{color:#246c68}}a{{color:#075f5b}}li{{margin:.5rem 0}}.meta{{color:#527174}}.eyebrow{{font-weight:800;color:#075f5b}}.sources{{overflow-wrap:anywhere}}</style></head><body>{MARKER}<main><header><p><a href="/magazine/">المجلة والأبحاث</a> ← <a href="/magazine/pediatric-oncology/">أبحاث سرطان الأطفال</a></p><p class="eyebrow">{'دراسة حديثة' if kind == 'studies' else 'رسالة جامعية'}</p><h1>{esc(row.get('title'))}</h1><p>{esc(row.get('excerpt') or description)}</p><p class="meta">هذه قراءة علمية تثقيفية مرتبطة بالمصدر الأصلي وحدود الدراسة، وليست توصية علاجية فردية.</p></header><article>{body_html(str(row.get('body_text') or ''))}</article><section><h2>{label}</h2><ol class="sources">{references_html(row)}</ol></section><aside><a href="/disclaimer/">إخلاء المسؤولية والتنبيهات</a> · <a href="/magazine/pediatric-oncology/{kind}/">المزيد من هذا النوع</a></aside></main></body></html>'''


def render_hub(title: str, description: str, canonical_path: str, rows: Iterable[dict[str, Any]]) -> str:
    cards = []
    for row in sorted(rows, key=lambda item: (str(item.get("updated_at") or ""), str(item.get("slug") or "")), reverse=True):
        cards.append('<article class="card"><h2><a href="{url}">{title}</a></h2><p>{description}</p></article>'.format(url=esc(row["canonical_url"]), title=esc(row["title"]), description=esc(row.get("excerpt") or row.get("seo_description") or "قراءة علمية موثقة.")))
    canonical = BASE_URL + canonical_path
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)} | منصة روافد</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">{OWNER_META}<link rel="canonical" href="{esc(canonical)}"><style>body{{font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#173f45;background:#f7fbfa;margin:0}}main{{width:min(1040px,92%);margin:auto;padding:32px 0 72px}}header,.card{{background:#fff;border:1px solid #cfe7e3;border-radius:18px;padding:22px;margin:14px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}a{{color:#075f5b}}h1{{font-size:clamp(2rem,5vw,3rem)}}</style></head><body>{MARKER}<main><header><p><a href="/magazine/">المجلة والأبحاث</a></p><h1>{esc(title)}</h1><p>{esc(description)}</p></header><div class="grid">{''.join(cards)}</div></main></body></html>'''


def destination_for(root: Path, row: dict[str, Any]) -> Path:
    route = str(row["canonical_url"])
    if not route.startswith("/") or ".." in route or "\\" in route:
        raise ValueError(f"Unsafe canonical route: {route!r}")
    relative = Path(route.lstrip("/"))
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"Unsafe route components: {route!r}")
    return root / relative / "index.html"


def owned(path: Path) -> bool:
    return path.is_file() and MARKER in path.read_text(encoding="utf-8", errors="replace")


def write_owned(path: Path, content: str) -> None:
    if path.exists() and not owned(path):
        raise RuntimeError(f"Refusing to overwrite non-materializer page: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def clean_stale(root: Path, expected: set[Path]) -> list[str]:
    managed = root / MANAGED_ROOT
    removed = []
    if not managed.exists():
        return removed
    for path in sorted(managed.rglob("index.html")):
        if path in expected or path.parent in {managed, managed / "studies", managed / "theses"}:
            continue
        if owned(path):
            removed.append(path.relative_to(root).as_posix()); path.unlink()
            try: path.parent.rmdir()
            except OSError: pass
    return removed


def materialize(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("Payload items must be a list")
    rows = sorted(items, key=lambda item: str(item.get("canonical_url") or ""))
    for row in rows: validate_row(row)
    expected: set[Path] = set(); written = []; study_rows = []; thesis_rows = []
    for row in rows:
        kind, _slug = route_info(row); destination = destination_for(root, row); expected.add(destination); write_owned(destination, render_article(row)); written.append(destination.relative_to(root).as_posix()); (study_rows if kind == "studies" else thesis_rows).append(row)
    hubs = [(root / MANAGED_ROOT / "index.html", "أبحاث سرطان الأطفال", "مركز روافد للقراءات العلمية الحديثة والرسائل الجامعية المرتبطة بأورام الأطفال، مع المصادر الأصلية وحدود الدليل.", "/magazine/pediatric-oncology/", rows), (root / MANAGED_ROOT / "studies" / "index.html", "أحدث دراسات سرطان الأطفال", "قراءات عربية نقدية للدراسات المحكمة الحديثة في أورام الأطفال، مع التصميم والعينة والنتائج والقيود والمصدر الأصلي.", "/magazine/pediatric-oncology/studies/", study_rows), (root / MANAGED_ROOT / "theses" / "index.html", "الرسائل الجامعية في سرطان الأطفال", "ملخصات عربية موثقة للرسائل والأطروحات الجامعية الحديثة ذات الصلة بأورام الأطفال، مع السجل الجامعي الأصلي وحدود الاستدلال.", "/magazine/pediatric-oncology/theses/", thesis_rows)]
    for path, title, description, canonical_path, hub_rows in hubs:
        expected.add(path); write_owned(path, render_hub(title, description, canonical_path, hub_rows)); written.append(path.relative_to(root).as_posix())
    removed = clean_stale(root, expected)
    report = {"schema_version": 1, "status": "passed", "records": len(rows), "studies": len(study_rows), "theses": len(thesis_rows), "routes": [str(row["canonical_url"]) for row in rows], "release_tokens": {str(row["slug"]): str((row.get("schema_json") or {}).get("release_token") or "") for row in rows}, "written": sorted(written), "removed": sorted(removed), "source_contract": "supabase-edge-oidc-v1", "public_route_contract": 2}
    report_path = root / REPORT_PATH; report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", default="."); parser.add_argument("--payload", help="Use a local JSON payload instead of GitHub OIDC")
    args = parser.parse_args(); root = Path(args.root).resolve()
    if not root.is_dir(): raise SystemExit(f"Repository root does not exist: {root}")
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8")) if args.payload else fetch_payload()
    print(json.dumps(materialize(root, payload), ensure_ascii=False)); return 0

if __name__ == "__main__":
    raise SystemExit(main())
