#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_auditor() -> None:
    path = ROOT / "scripts" / "audit_full_site_v16.py"
    text = path.read_text(encoding="utf-8")

    helper_anchor = "\ndef content_minimum(rel: str) -> int:\n"
    helper = '''
def legacy_alias_contract(page: Path, parser: AuditParser) -> tuple[bool, str | None, list[str]]:
    """Validate explicit noindex redirect aliases without treating them as indexable content."""
    marker = str(parser.html_attrs.get("data-legacy-path-alias") or "").strip()
    if not marker:
        return False, None, []

    rel = page.relative_to(SITE).as_posix()
    errors: list[str] = []
    robots = meta_value(parser, "robots")
    directives = {
        item.strip().lower()
        for value in robots
        for item in value.split(",")
        if item.strip()
    }
    if len(robots) != 1 or not {"noindex", "follow"}.issubset(directives):
        errors.append(f"Legacy alias robots contract failed in {rel}: {robots}")

    refresh = [
        item for item in parser.meta
        if str(item.get("http-equiv", "")).lower() == "refresh"
    ]
    destination = ""
    if len(refresh) != 1:
        errors.append(f"Legacy alias requires one meta refresh in {rel}, found {len(refresh)}")
    else:
        content = str(refresh[0].get("content", ""))
        match = re.match(r"^\\s*0\\s*;\\s*url\\s*=\\s*(.+?)\\s*$", content, re.I)
        if not match:
            errors.append(f"Legacy alias refresh must be immediate in {rel}: {content}")
        else:
            destination = match.group(1).strip("\\\"' ")

    canonical_values = link_values(parser, "canonical")
    if len(canonical_values) != 1:
        errors.append(f"Legacy alias requires one canonical in {rel}, found {len(canonical_values)}")

    refresh_target = local_target(page, destination) if destination else None
    canonical_target = local_target(page, canonical_values[0]) if len(canonical_values) == 1 else None
    if refresh_target is None:
        errors.append(f"Legacy alias refresh target is not an internal page in {rel}: {destination}")
    if canonical_target is None:
        errors.append(f"Legacy alias canonical target is not an internal page in {rel}: {canonical_values}")
    if refresh_target is not None and canonical_target is not None and refresh_target != canonical_target:
        errors.append(
            f"Legacy alias refresh/canonical mismatch in {rel}: {destination} != {canonical_values[0]}"
        )

    target = refresh_target or canonical_target
    target_rel: str | None = None
    if target is not None:
        try:
            target_rel = target.relative_to(SITE).as_posix()
        except ValueError:
            errors.append(f"Legacy alias target escapes site root in {rel}: {target}")
        else:
            if target == page.resolve():
                errors.append(f"Legacy alias redirects to itself in {rel}")
            if not target.is_file():
                errors.append(f"Legacy alias target is missing in {rel}: {target_rel}")
    return True, target_rel, errors

'''
    if "def legacy_alias_contract(" not in text:
        if text.count(helper_anchor) != 1:
            raise SystemExit("audit helper anchor missing or ambiguous")
        text = text.replace(helper_anchor, "\n" + helper + "def content_minimum(rel: str) -> int:\n", 1)

    anchor = "    section_counts: Counter[str] = Counter()\n"
    if "legacy_aliases: dict[str, str]" not in text:
        if text.count(anchor) != 1:
            raise SystemExit("audit variable anchor missing or ambiguous")
        text = text.replace(anchor, anchor + "    legacy_aliases: dict[str, str] = {}\n", 1)

    old = '''        titles[title].append(rel)
        if descs:
            descriptions[descs[0]].append(rel)
        if canonical:
            canonicals[canonical[0]].append(rel)
'''
    new = '''        is_legacy_alias, alias_target, alias_errors = legacy_alias_contract(page, parser)
        errors.extend(alias_errors)
        if is_legacy_alias:
            legacy_aliases[rel] = alias_target or ""
        else:
            titles[title].append(rel)
            if descs:
                descriptions[descs[0]].append(rel)
            if canonical:
                canonicals[canonical[0]].append(rel)
'''
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise SystemExit("audit registration anchor missing")

    old = '''        if len(descs) != 1 or not (50 <= len(descs[0]) <= 320):
            errors.append(f"Invalid meta description in {rel}: {len(descs[0]) if descs else 0}")
        if len(canonical) != 1:
            errors.append(f"Expected one canonical in {rel}, found {len(canonical)}")
        elif canonical[0] != BASE_URL + ("" if rel == "index.html" else rel.removesuffix("index.html")):
            errors.append(f"Canonical mismatch in {rel}: {canonical[0]}")
'''
    new = '''        if not is_legacy_alias:
            if len(descs) != 1 or not (50 <= len(descs[0]) <= 320):
                errors.append(f"Invalid meta description in {rel}: {len(descs[0]) if descs else 0}")
            if len(canonical) != 1:
                errors.append(f"Expected one canonical in {rel}, found {len(canonical)}")
            elif canonical[0] != BASE_URL + ("" if rel == "index.html" else rel.removesuffix("index.html")):
                errors.append(f"Canonical mismatch in {rel}: {canonical[0]}")
'''
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise SystemExit("audit metadata anchor missing")

    anchor = '''        if duplicate_ids:
            errors.append(f"Duplicate IDs in {rel}: {duplicate_ids[:6]}")
'''
    addition = anchor + '''        if is_legacy_alias:
            continue
'''
    if "        if is_legacy_alias:\n            continue\n" not in text:
        if text.count(anchor) != 1:
            raise SystemExit("audit alias continue anchor missing or ambiguous")
        text = text.replace(anchor, addition, 1)

    anchor = '''    duplicate_urls = [url for url, count in Counter(sitemap_urls).items() if count > 1]
'''
    addition = '''    for alias_rel, target_rel in legacy_aliases.items():
        alias_url = BASE_URL + alias_rel.removesuffix("index.html")
        if alias_url in sitemap_urls:
            errors.append(f"Noindex legacy alias must not be in sitemaps: {alias_url}")
        if target_rel:
            target_url = BASE_URL + target_rel.removesuffix("index.html")
            if target_url not in sitemap_urls:
                errors.append(f"Legacy alias canonical target is missing from sitemaps: {target_url}")

'''
    if "Noindex legacy alias must not be in sitemaps" not in text:
        if text.count(anchor) != 1:
            raise SystemExit("audit sitemap anchor missing or ambiguous")
        text = text.replace(anchor, addition + anchor, 1)

    anchor = '        "content_pages": len(content_files),\n'
    addition = anchor + '        "legacy_alias_count": len(legacy_aliases),\n        "legacy_aliases": legacy_aliases,\n        "legacy_alias_contract": "noindex-follow-immediate-internal-redirect-v333",\n'
    if '"legacy_alias_contract"' not in text:
        if text.count(anchor) != 1:
            raise SystemExit("audit report anchor missing or ambiguous")
        text = text.replace(anchor, addition, 1)

    path.write_text(text, encoding="utf-8")


def patch_release_gate() -> None:
    path = ROOT / ".github" / "workflows" / "validate-all-labs-v22.yml"
    text = path.read_text(encoding="utf-8")
    old = '''          test "$(find _site/daily-tools -name index.html | wc -l)" -eq 9
          test "$(find _site/learning-paths -name index.html | wc -l)" -eq 5
          test "$(grep -o '<url>' _site/sitemap-tools-paths.xml | wc -l)" -eq 14
          test "$(grep -o 'sitemap-tools-paths.xml' _site/sitemap.xml | wc -l)" -eq 1
          test -f _site/api/daily-tools-v24.json
'''
    new = '''          test -f _site/api/daily-tools-v24.json
          python - <<'PY'
          import json
          from pathlib import Path
          root = Path('_site')
          report = json.loads((root / 'api/daily-tools-v24.json').read_text(encoding='utf-8'))
          assert report['version'] == 100, report
          assert report['catalog_contract'] == 100, report
          assert report['tools'] == 100, report
          assert report['paths'] == 10, report
          assert report['pages'] == 112, report
          daily_pages = list((root / 'daily-tools').rglob('index.html'))
          learning_pages = list((root / 'learning-paths').rglob('index.html'))
          assert len(daily_pages) == 101, len(daily_pages)
          assert len(learning_pages) == 15, len(learning_pages)
          aliases = []
          for page in learning_pages:
              page_text = page.read_text(encoding='utf-8')
              if 'data-legacy-path-alias=' in page_text:
                  aliases.append(page)
                  assert 'noindex,follow' in page_text, page
                  assert 'http-equiv="refresh"' in page_text, page
          assert len(aliases) == 4, aliases
          sitemap = (root / 'sitemap-tools-paths.xml').read_text(encoding='utf-8')
          assert sitemap.count('<url>') == 112, sitemap.count('<url>')
          main_sitemap = (root / 'sitemap.xml').read_text(encoding='utf-8')
          assert main_sitemap.count('sitemap-tools-paths.xml') == 1
          print({'daily_pages': len(daily_pages), 'learning_pages': len(learning_pages), 'aliases': len(aliases), 'sitemap_urls': 112})
          PY
'''
    if old in text:
        text = text.replace(old, new, 1)
    elif new not in text:
        raise SystemExit("daily-tools workflow count anchor missing")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_auditor()
    patch_release_gate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
