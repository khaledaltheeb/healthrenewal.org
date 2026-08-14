from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Iterable

SITE_NAME = 'منصة روافد'
OLD_SITE_NAME = 'منصة الصحة النفسية وذوي الاحتياجات الخاصة'
CATALOG = 'daily-tools-v150'
REPORT_PATH = 'api/daily-tools-hardening-v150.json'
MIN_DESC = 90
MAX_DESC = 180

META_DESC_RE = re.compile(r'(<meta\s+name="description"\s+content=")([^"]*)(")', re.I)
OG_DESC_RE = re.compile(r'(<meta\s+property="og:description"\s+content=")([^"]*)(")', re.I)
TW_DESC_RE = re.compile(r'(<meta\s+name="twitter:description"\s+content=")([^"]*)(")', re.I)
HTML_OPEN_RE = re.compile(r'<html\b([^>]*)>', re.I)
ROBOTS_RE = re.compile(r'<meta\s+name="robots"\s+content="([^"]*)"', re.I)
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.I | re.S)
CANON_RE = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)


def clean(value: str) -> str:
    return re.sub(r'\s+', ' ', html.unescape(value or '')).strip()


def _description_suffix(kind: str) -> str:
    if kind == 'tool':
        return ' أداة عربية تفاعلية تحفظ بياناتك محليًا وتوضح حدود الاستخدام غير التشخيصي.'
    if kind == 'path':
        return ' مسار عربي عملي يربط التعلم بالتطبيق اليومي مع حدود واضحة للاستخدام غير التشخيصي.'
    return ' دليل عربي عملي من روافد للتعلم والتطبيق اليومي بحدود واضحة وغير تشخيصية.'


def improve_description(value: str, kind: str) -> str:
    value = clean(value).rstrip()
    if len(value) >= MIN_DESC:
        return value
    candidate = value.rstrip(' .،؛') + '.' + _description_suffix(kind)
    candidate = clean(candidate)
    if len(candidate) <= MAX_DESC:
        return candidate
    suffix = ' أداة عربية عملية من روافد بحدود واضحة وغير تشخيصية.' if kind == 'tool' else ' محتوى عربي عملي من روافد بحدود واضحة وغير تشخيصية.'
    room = max(40, MAX_DESC - len(suffix))
    base = value[:room].rstrip(' ،؛.-') + '.'
    return clean(base + suffix)


def page_kind(path: Path, site: Path) -> str:
    rel = path.relative_to(site).as_posix()
    if re.fullmatch(r'daily-tools/[^/]+/index\.html', rel):
        return 'tool'
    if re.fullmatch(r'learning-paths/[^/]+/index\.html', rel):
        return 'path'
    return 'index'


def is_indexable(text: str) -> bool:
    m = ROBOTS_RE.search(text)
    return not m or 'noindex' not in m.group(1).lower()


def patch_page(path: Path, site: Path) -> tuple[bool, int, int]:
    text = path.read_text(encoding='utf-8')
    original = text
    text = text.replace(OLD_SITE_NAME, SITE_NAME)
    text = text.replace('data-catalog="daily-tools-v100"', f'data-catalog="{CATALOG}"')
    m_html = HTML_OPEN_RE.search(text)
    if m_html and 'data-catalog=' not in m_html.group(0):
        replacement = '<html' + m_html.group(1) + f' data-catalog="{CATALOG}">'
        text = text[:m_html.start()] + replacement + text[m_html.end():]

    dm = META_DESC_RE.search(text)
    before_len = 0
    after_len = 0
    if dm:
        current = clean(dm.group(2))
        before_len = len(current)
        improved = improve_description(current, page_kind(path, site))
        after_len = len(improved)
        if improved != current:
            escaped = html.escape(improved, quote=True)
            text = text[:dm.start(2)] + escaped + text[dm.end(2):]
            for pattern in (OG_DESC_RE, TW_DESC_RE):
                sm = pattern.search(text)
                if sm:
                    text = text[:sm.start(2)] + escaped + text[sm.end(2):]
    if text != original:
        path.write_text(text, encoding='utf-8')
        return True, before_len, after_len
    return False, before_len, after_len


def iter_section_pages(site: Path) -> Iterable[Path]:
    for root in (site / 'daily-tools', site / 'learning-paths'):
        if root.is_dir():
            yield from sorted(root.rglob('index.html'))


def validate(site: Path) -> dict:
    all_pages = list(iter_section_pages(site))
    indexable = []
    errors = []
    titles = []
    canonicals = []
    descs = []
    tool_pages = []
    for path in all_pages:
        text = path.read_text(encoding='utf-8')
        rel = path.relative_to(site).as_posix()
        if not is_indexable(text):
            continue
        indexable.append(path)
        if OLD_SITE_NAME in text:
            errors.append(f'{rel}: old site identity remains')
        hm = HTML_OPEN_RE.search(text)
        if not hm or f'data-catalog="{CATALOG}"' not in hm.group(0):
            errors.append(f'{rel}: missing {CATALOG} marker')
        dm = META_DESC_RE.search(text)
        desc = clean(dm.group(2)) if dm else ''
        if not MIN_DESC <= len(desc) <= MAX_DESC:
            errors.append(f'{rel}: description length {len(desc)}')
        descs.append(desc)
        tm = TITLE_RE.search(text)
        title = clean(tm.group(1)) if tm else ''
        if not title:
            errors.append(f'{rel}: missing title')
        titles.append(title)
        cm = CANON_RE.search(text)
        canonical = clean(cm.group(1)) if cm else ''
        if not canonical:
            errors.append(f'{rel}: missing canonical')
        canonicals.append(canonical)
        if re.fullmatch(r'daily-tools/[^/]+/index\.html', rel):
            tool_pages.append(path)
            for marker in ('data-content-upgrade="daily-tools-content-v150"', 'FAQPage', 'BreadcrumbList'):
                if marker not in text:
                    errors.append(f'{rel}: missing {marker}')
    if len(tool_pages) != 150:
        errors.append(f'expected 150 tool pages, got {len(tool_pages)}')
    if len(indexable) != 162:
        errors.append(f'expected 162 indexable section pages, got {len(indexable)}')
    if len(titles) != len(set(titles)):
        errors.append('duplicate title among indexable section pages')
    if len(canonicals) != len(set(canonicals)):
        errors.append('duplicate canonical among indexable section pages')
    if len(descs) != len(set(descs)):
        errors.append('duplicate description among indexable section pages')
    if errors:
        raise SystemExit('Daily tools post-launch hardening failed:\n' + '\n'.join(errors[:100]))
    return {
        'status':'passed',
        'catalog':CATALOG,
        'toolPages':len(tool_pages),
        'indexableSectionPages':len(indexable),
        'minimumMetaDescriptionLength':min(map(len,descs)),
        'maximumMetaDescriptionLength':max(map(len,descs)),
        'uniqueTitles':len(set(titles)),
        'uniqueDescriptions':len(set(descs)),
        'uniqueCanonicals':len(set(canonicals)),
        'oldBrandReferences':0,
    }


def harden(site: Path | str) -> dict:
    target = Path(site).resolve()
    changed = 0
    expanded = 0
    for path in iter_section_pages(target):
        was_changed, before, after = patch_page(path, target)
        changed += int(was_changed)
        expanded += int(before and before < MIN_DESC and after >= MIN_DESC)
    report = validate(target)
    report['pagesChanged'] = changed
    report['metaDescriptionsExpanded'] = expanded
    out = target / REPORT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    import sys
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '_site')
    print(json.dumps(harden(root), ensure_ascii=False, indent=2))
