#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

VERSION = 231
START = '<!-- content-depth-v222:start -->'
END = '<!-- content-depth-v222:end -->'
WORD_RE = re.compile(r'[\w\u0600-\u06ff]+', re.UNICODE)
LANG_RE = re.compile(r'<html\b[^>]*\blang=(["\'])(.*?)\1', re.I | re.S)
NOINDEX_RE = re.compile(
    r'<meta\b(?=[^>]*\bname=["\']robots["\'])(?=[^>]*\bcontent=["\'][^"\']*noindex)',
    re.I | re.S,
)

POLICIES = {
    'comparisons': 220, 'library': 230, 'magazine': 230,
    'encyclopedia': 200, 'terms': 200, 'hubs': 190,
    'assessments': 220, 'assessment-lab': 220, 'guided-assessment': 220,
    'cognitive-tests': 220, 'cognitive-lab': 220,
    'care-guides': 225, 'special-needs': 225, 'tips': 225,
    'sectors': 225, 'daily-tools': 225, 'learning-paths': 225,
    'start-here': 190, 'sections': 190, 'trust': 230,
    'partners': 190, 'developers': 190,
    'about': 220, 'methodology': 230, 'citation': 210,
    'privacy': 190, 'sources': 220, 'stats': 190,
    'downloads': 190, 'media-kit': 190,
}
EXCLUDED = {'.git', 'node_modules', 'vendor', '__pycache__', 'assets', 'api'}


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []
        self.heading: list[str] = []
        self.title: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        text = re.sub(r'\s+', ' ', data).strip()
        if not text:
            return
        if self.stack and self.stack[-1] == 'title':
            self.title.append(text)
        if 'h1' in self.stack:
            self.heading.append(text)
        if not any(tag in self.stack for tag in ('script', 'style', 'noscript', 'svg', 'template')):
            self.parts.append(text)


def parse_text(source: str) -> tuple[str, str]:
    parser = TextParser()
    parser.feed(source)
    return ' '.join(parser.parts), ' '.join(parser.heading or parser.title).strip()


def words(source: str) -> int:
    visible, _ = parse_text(source)
    return len(WORD_RE.findall(html.unescape(visible)))


def group_for(relative: Path) -> str | None:
    if not relative.parts or relative.parts[0] == 'index.html':
        return None
    group = relative.parts[0]
    return group if group in POLICIES else None


def route_for(relative: Path) -> str:
    if relative.name == 'index.html':
        parent = relative.parent.as_posix().strip('.')
        return '/' + (parent + '/' if parent else '')
    return '/' + relative.as_posix()


def strip_v222(source: str, route: str) -> tuple[str, int]:
    starts, ends = source.count(START), source.count(END)
    if starts != ends:
        raise ValueError(f'{route}: unbalanced v222 markers ({starts}/{ends})')
    if not starts:
        return source, 0
    pattern = re.compile(re.escape(START) + r'.*?' + re.escape(END), re.S)
    stripped, count = pattern.subn('', source)
    if count != starts:
        raise ValueError(f'{route}: nested or malformed v222 blocks')
    return stripped, count


def producer_candidates(repository: Path | None, group: str) -> list[str]:
    if repository is None or not (repository / 'scripts').is_dir():
        return []
    tokens = {group, group.replace('-', '_'), *[part for part in group.split('-') if len(part) >= 4]}
    scored: list[tuple[int, str]] = []
    for path in (repository / 'scripts').glob('*.py'):
        name = path.name.lower()
        if name.startswith(('audit_', 'verify_', 'test_')):
            continue
        try:
            source = path.read_text(encoding='utf-8').lower()
        except (OSError, UnicodeDecodeError):
            continue
        score = sum(source.count(token.lower()) for token in tokens)
        score += 4 if 'publish' in name else 0
        score += 2 if ('write_text' in source or 'render' in source) else 0
        if score:
            scored.append((score, path.relative_to(repository).as_posix()))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, path in scored[:5]]


def audit(site: Path, repository: Path | None = None) -> dict:
    if not site.is_dir():
        raise FileNotFoundError(f'Site directory not found: {site}')
    gaps, unhandled, malformed = [], [], []
    scanned = eligible = skipped_noindex = skipped_non_arabic = marker_blocks = 0
    cache: dict[str, list[str]] = {}

    for path in sorted(site.rglob('*.html')):
        relative = path.relative_to(site)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        group = group_for(relative)
        if group is None:
            continue
        scanned += 1
        source = path.read_text(encoding='utf-8', errors='replace')
        if NOINDEX_RE.search(source):
            skipped_noindex += 1
            continue
        lang = LANG_RE.search(source)
        if not lang or not lang.group(2).lower().startswith('ar'):
            skipped_non_arabic += 1
            continue
        eligible += 1
        route, minimum = route_for(relative), POLICIES[group]
        try:
            original, blocks = strip_v222(source, route)
        except ValueError as exc:
            malformed.append(str(exc))
            continue
        production_words, source_words = words(source), words(original)
        _, title = parse_text(original)
        marker_blocks += blocks
        if blocks:
            candidates = cache.setdefault(group, producer_candidates(repository, group))
            gaps.append({
                'route': route, 'route_group': group, 'minimum_words': minimum,
                'source_words': source_words, 'production_words': production_words,
                'injected_words': max(0, production_words - source_words),
                'title': title, 'producer_candidates': candidates,
            })
        elif source_words < minimum:
            unhandled.append({
                'route': route, 'route_group': group, 'minimum_words': minimum,
                'words': source_words, 'title': title,
            })

    gaps.sort(key=lambda item: (item['source_words'], item['route']))
    unhandled.sort(key=lambda item: (item['words'], item['route']))
    return {
        'version': VERSION,
        'status': 'passed' if not malformed and not unhandled else 'failed',
        'pages_scanned': scanned, 'eligible_pages': eligible,
        'skipped_noindex': skipped_noindex, 'skipped_non_arabic': skipped_non_arabic,
        'source_gap_count': len(gaps), 'marker_block_count': marker_blocks,
        'unhandled_thin_count': len(unhandled), 'malformed_marker_count': len(malformed),
        'minimum_source_words': min((item['source_words'] for item in gaps), default=None),
        'maximum_injected_words': max((item['injected_words'] for item in gaps), default=0),
        'route_group_counts': {
            group: sum(item['route_group'] == group for item in gaps)
            for group in sorted({item['route_group'] for item in gaps})
        },
        'gaps': gaps, 'unhandled_thin_pages': unhandled, 'malformed_markers': malformed,
    }


def write_report(report: dict, json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = [
        '# فجوة عمق المصدر v231', '',
        f"- الحالة: **{report['status']}**",
        f"- صفحات تعتمد على إضافة v222: **{report['source_gap_count']}**",
        f"- صفحات قصيرة غير معالجة: **{report['unhandled_thin_count']}**",
        f"- علامات غير سليمة: **{report['malformed_marker_count']}**", '',
        '## الأولويات', '',
    ]
    for item in report['gaps']:
        producers = '، '.join(item['producer_candidates']) or 'غير محدد'
        lines.append(
            f"- `{item['route']}` — المصدر {item['source_words']}، الإنتاج {item['production_words']} كلمة — الناشر المحتمل: {producers}"
        )
    if report['unhandled_thin_pages']:
        lines += ['', '## صفحات قصيرة غير معالجة', '']
        for item in report['unhandled_thin_pages']:
            lines.append(f"- `{item['route']}` — {item['words']} / {item['minimum_words']} كلمة")
    markdown_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('site', type=Path)
    parser.add_argument('--repository', type=Path)
    parser.add_argument('--json-output', type=Path)
    parser.add_argument('--markdown-output', type=Path)
    parser.add_argument('--fail-on-gap', action='store_true')
    args = parser.parse_args()
    site = args.site.resolve()
    report = audit(site, args.repository.resolve() if args.repository else None)
    json_path = args.json_output or site / 'api' / 'source-depth-gap-v231.json'
    markdown_path = args.markdown_output or site / 'api' / 'source-depth-gap-v231.md'
    write_report(report, json_path, markdown_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['status'] != 'passed' or (args.fail_on_gap and report['source_gap_count']):
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
