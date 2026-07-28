#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

VERSION = 334
DEFAULT_SITE_BASE = "https://khaledaltheeb.github.io/pterminology-site/"
MARKER = f'data-legacy-learning-path-alias="v{VERSION}"'


@dataclass(frozen=True)
class Alias:
    source_slug: str
    target_slug: str
    title: str
    description: str
    heading: str
    message: str


ALIASES: tuple[Alias, ...] = (
    Alias(
        "caregiver-boundaries-7-days",
        "caregiver-wellbeing-7-days",
        "انتقل مسار حدود مقدم الرعاية إلى مسار الرفاه المحدث",
        "صفحة انتقال للمسار القديم حول حدود مقدم الرعاية، وتوجّه إلى النسخة المحدثة لمسار رفاه مقدم الرعاية خلال سبعة أيام.",
        "تم تحديث مسار حدود مقدم الرعاية",
        "جُمعت خطوات الحدود الصحية والعناية الذاتية في مسار رفاه مقدم الرعاية المحدث.",
    ),
    Alias(
        "family-listening-5-days",
        "family-parenting-7-days",
        "انتقل مسار الاستماع الأسري إلى مسار الأسرة والتربية المحدث",
        "صفحة انتقال للمسار القديم حول الاستماع داخل الأسرة، وتوجّه إلى النسخة المحدثة لمسار الأسرة والتربية خلال سبعة أيام.",
        "تم تحديث مسار الاستماع الأسري",
        "أُدمجت تمارين الاستماع والحوار في مسار الأسرة والتربية المحدث.",
    ),
    Alias(
        "grief-support-7-days",
        "change-resilience-7-days",
        "انتقل مسار دعم الحزن إلى مسار التكيف والمرونة المحدث",
        "صفحة انتقال للمسار القديم حول دعم الحزن، وتوجّه إلى النسخة المحدثة لمسار التكيف مع التغيير وبناء المرونة خلال سبعة أيام.",
        "تم تحديث مسار دعم الحزن",
        "نُقلت خطوات دعم الحزن إلى مسار أوسع للتكيف مع التغيير وبناء المرونة.",
    ),
    Alias(
        "stress-basics-7-days",
        "stress-regulation-7-days",
        "انتقل مسار أساسيات الضغط إلى مسار تنظيم الضغط المحدث",
        "صفحة انتقال للمسار القديم حول أساسيات الضغط النفسي، وتوجّه إلى النسخة المحدثة لمسار تنظيم الضغط خلال سبعة أيام.",
        "تم تحديث مسار أساسيات الضغط",
        "أُعيد تنظيم خطوات فهم الضغط وتهدئته داخل مسار تنظيم الضغط المحدث.",
    ),
)


def normalize_base(value: str) -> str:
    value = value.strip()
    if not value:
        value = DEFAULT_SITE_BASE
    return value.rstrip("/") + "/"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render(alias: Alias, site_base: str) -> str:
    base = normalize_base(site_base)
    base_path = "/" + base.split("/", 3)[-1].strip("/") + "/"
    source_url = f"{base}learning-paths/{alias.source_slug}/"
    target_url = f"{base}learning-paths/{alias.target_slug}/"
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "@id": source_url + "#webpage",
            "url": source_url,
            "name": alias.title,
            "description": alias.description,
            "inLanguage": "ar",
            "isPartOf": {"@type": "WebSite", "@id": base + "#website", "url": base},
            "mainEntity": {
                "@type": "CreativeWork",
                "name": alias.heading,
                "url": target_url,
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f'''<!doctype html>
<html lang="ar" dir="rtl" {MARKER}>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>{esc(alias.title)} | مصطلحات علم النفس</title>
  <meta name="description" content="{esc(alias.description)}">
  <meta name="robots" content="noindex,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
  <meta name="theme-color" content="#0b6b66">
  <link rel="canonical" href="{esc(source_url)}">
  <link rel="alternate" hreflang="ar" href="{esc(source_url)}">
  <link rel="alternate" hreflang="x-default" href="{esc(source_url)}">
  <link rel="manifest" href="{esc(base_path)}manifest.webmanifest">
  <meta http-equiv="refresh" content="0; url={esc(target_url)}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="ar_AR">
  <meta property="og:site_name" content="مصطلحات علم النفس">
  <meta property="og:title" content="{esc(alias.title)}">
  <meta property="og:description" content="{esc(alias.description)}">
  <meta property="og:url" content="{esc(source_url)}">
  <meta name="twitter:card" content="summary">
  <script type="application/ld+json">{schema}</script>
  <style>
    :root{{color-scheme:light;font-family:"Noto Sans Arabic","Segoe UI",Tahoma,sans-serif}}
    body{{margin:0;background:#f4fbfa;color:#123}}
    main{{width:min(760px,calc(100% - 32px));margin:12vh auto;padding:clamp(24px,5vw,48px);background:#fff;border:1px solid #cce4e1;border-radius:24px;box-shadow:0 18px 48px rgba(14,78,74,.12);text-align:center}}
    h1{{color:#075e59;line-height:1.45}}
    p{{font-size:1.08rem;line-height:1.9}}
    a{{display:inline-block;margin-top:12px;padding:12px 20px;border-radius:999px;background:#0b6b66;color:#fff;font-weight:700;text-decoration:none}}
    a:focus-visible{{outline:3px solid #b7791f;outline-offset:4px}}
  </style>
</head>
<body>
  <main>
    <h1>{esc(alias.heading)}</h1>
    <p>{esc(alias.message)}</p>
    <p>سيتم نقلك تلقائيًا. إن لم يحدث ذلك، استخدم الرابط التالي.</p>
    <a href="{esc(target_url)}">فتح المسار المحدث</a>
  </main>
</body>
</html>
'''


def repair(site: Path, site_base: str, strict: bool = False) -> dict[str, object]:
    site = site.resolve()
    site_base = normalize_base(site_base)
    errors: list[str] = []
    records: list[dict[str, object]] = []
    titles: set[str] = set()
    descriptions: set[str] = set()

    for alias in ALIASES:
        target = site / "learning-paths" / alias.target_slug / "index.html"
        source = site / "learning-paths" / alias.source_slug / "index.html"
        target_exists = target.is_file()
        if not target_exists:
            errors.append(f"Missing target page: {target.relative_to(site).as_posix()}")
        content = render(alias, site_base)
        before = source.read_text(encoding="utf-8") if source.is_file() else None
        source.parent.mkdir(parents=True, exist_ok=True)
        changed = before != content
        if changed:
            source.write_text(content, encoding="utf-8")
        if alias.title in titles:
            errors.append(f"Duplicate alias title: {alias.title}")
        if alias.description in descriptions:
            errors.append(f"Duplicate alias description: {alias.description}")
        titles.add(alias.title)
        descriptions.add(alias.description)
        records.append(
            {
                "source": source.relative_to(site).as_posix(),
                "target": target.relative_to(site).as_posix(),
                "target_exists": target_exists,
                "changed": changed,
                "sha256": sha256_text(content),
            }
        )

    report = {
        "schema_version": VERSION,
        "status": "passed" if not errors else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "site_base": site_base,
        "aliases_expected": len(ALIASES),
        "aliases_written": len(records),
        "aliases_changed": sum(bool(record["changed"]) for record in records),
        "robots_contract": "noindex,follow",
        "canonical_contract": "self-canonical transition page",
        "redirect_contract": "zero-second meta refresh plus visible target link",
        "records": records,
        "errors": errors,
    }
    report_path = site / "api" / f"legacy-learning-path-aliases-v{VERSION}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if strict and errors:
        raise SystemExit(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repair legacy learning-path transition pages.")
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    parser.add_argument("--site-base", default=os.environ.get("SITE_BASE", DEFAULT_SITE_BASE))
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    report = repair(args.site, args.site_base, args.strict)
    print(
        json.dumps(
            {
                "status": report["status"],
                "aliases_written": report["aliases_written"],
                "aliases_changed": report["aliases_changed"],
                "errors": report["errors"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
