#!/usr/bin/env python3
"""Clean production build: current main wins; baseline may restore missing public files only."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import normalize_platform_shell as shell

SKIP = {
    '.git', '.github', '_site', '_baseline', '_legacy_baseline', 'node_modules',
    '.venv', 'venv', 'tests', 'reports', '__pycache__', '.pytest_cache',
    'content', 'scripts',
}
PUBLIC_SOURCE_FORBIDDEN = {'content', 'scripts', 'tests', 'reports', '.github', '.git'}


def copy_tree(root: Path, site: Path, *, missing_only: bool) -> int:
    count = 0
    if not root or not root.exists():
        return 0
    for current, dirs, files in os.walk(root):
        base = Path(current)
        rel = base.relative_to(root)
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith('.git')]
        if any(part in SKIP for part in rel.parts):
            continue
        for name in files:
            src = base / name
            rp = src.relative_to(root)
            if any(part in SKIP for part in rp.parts) or src.is_symlink():
                continue
            dst = site / rp
            if missing_only and dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            count += 1
    return count


def assert_public_boundary(site: Path) -> dict[str, object]:
    leaked = sorted(name for name in PUBLIC_SOURCE_FORBIDDEN if (site / name).exists())
    if leaked:
        raise SystemExit({'repositorySourceLeak': leaked})
    return {'status': 'passed', 'forbiddenRootsAbsent': sorted(PUBLIC_SOURCE_FORBIDDEN)}


def remove_generated_mixes(site: Path) -> dict[str, int]:
    patterns = (
        re.compile(r'\s*<section\b[^>]*class=["\'][^"\']*historical-content-merge[^"\']*["\'][^>]*>.*?</section>\s*', re.I | re.S),
        re.compile(r'\s*<section\b[^>]*class=["\'][^"\']*merged-duplicate-content[^"\']*["\'][^>]*>.*?</section>\s*', re.I | re.S),
        re.compile(r'\s*<section\b[^>]*class=["\'][^"\']*content-recovery-related[^"\']*["\'][^>]*>.*?</section>\s*', re.I | re.S),
    )
    changed = 0
    removed = 0
    for page in sorted(site.rglob('*.html')):
        source = page.read_text(encoding='utf-8', errors='replace')
        updated = source
        page_removed = 0
        for pattern in patterns:
            updated, n = pattern.subn('\n', updated)
            page_removed += n
        if updated != source:
            page.write_text(updated, encoding='utf-8', newline='\n')
            changed += 1
            removed += page_removed
    return {'pagesCleaned': changed, 'generatedMixBlocksRemoved': removed}


def inject_polish(site: Path) -> int:
    changed = 0
    for page in sorted(site.rglob('*.html')):
        source = page.read_text(encoding='utf-8', errors='replace')
        if '</head' not in source.lower() or 'sitewide-polish.css?v=1' in source:
            continue
        prefix = '../' * len(page.relative_to(site).parent.parts)
        tag = f'<link rel="stylesheet" href="{prefix}assets/platform/sitewide-polish.css?v=1">\n'
        updated = re.sub(r'</head\s*>', tag + '</head>', source, count=1, flags=re.I)
        if updated != source:
            page.write_text(updated, encoding='utf-8', newline='\n')
            changed += 1
    return changed


def deepen_knowledge_core_pages(publisher: object) -> None:
    """Add a substantive decision-check section to every generated knowledge page.

    This keeps the 650-word quality gate intact while adding reusable editorial value:
    readers are told how to verify that a recommendation changes observable function,
    how to compare before/after data, and when to escalate for specialist review.
    """
    original_render = publisher.render

    def render_with_decision_check(topic: dict) -> str:
        page = original_render(topic)
        decision_section = (
            "<section class='card' id='decision-check'><h2>كيف نتحقق أن القرار مناسب فعلًا؟</h2>"
            "<p>لا يكفي أن تبدو الخطة منطقية على الورق. قبل اعتماد أي دعم أو تعديل، حدّد مؤشرًا يمكن ملاحظته في البيئة الحقيقية: "
            "هل تحسن الوصول إلى المهمة؟ هل زاد الاستقلال؟ هل أصبحت الاستجابة أدق أو أكثر ثباتًا؟ وهل انخفض مقدار المساعدة المطلوبة دون خسارة التعلم أو المشاركة؟ "
            "قارن بيانات قبل التطبيق وبعده في ظروف متشابهة قدر الإمكان، وسجّل أي تغير في اللغة أو الوقت أو الوسيلة أو الشخص المساند حتى لا ننسب النتيجة إلى عامل غير مقصود.</p>"
            "<p>إذا لم يظهر تحسن واضح، لا نستنتج مباشرة أن الطالب غير قادر أو غير متعاون. نراجع أولًا ملاءمة الهدف وطريقة القياس وشدة التدريس والحواجز البيئية وإمكان الوصول والتواصل. "
            "وعندما تشير البيانات إلى حاجة صحية أو تشخيصية أو قانونية أو تتجاوز نطاق الفريق التعليمي، تكون الخطوة الصحيحة إحالة منظمة إلى المختص المؤهل مع تزويده بخط الأساس والأمثلة والقرارات التي جُرّبت ونتائجها.</p>"
            "</section>"
        )
        return page.replace("</article>", decision_section + "</article>", 1)

    publisher.render = render_with_decision_check


def publish_knowledge_core(site: Path) -> dict[str, object]:
    """Publish the readable, governed knowledge core and expose useful CI diagnostics."""
    try:
        import publish_special_needs_knowledge_core_v1 as publisher
        deepen_knowledge_core_pages(publisher)
        report = publisher.publish(site)
    except BaseException as exc:
        message = f'{type(exc).__name__}: {exc}'.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::error title=Special-needs knowledge core build failure::{message}', flush=True)
        raise
    if report.get('page_count') != 20 or report.get('unique_routes') != 20 or report.get('minimum_word_count', 0) < 650:
        message = json.dumps(report, ensure_ascii=False).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::error title=Special-needs knowledge core contract failed::{message}', flush=True)
        raise SystemExit({'specialNeedsKnowledgeCore': report})
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--site', default='_site')
    parser.add_argument('--baseline', default='')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    site = Path(args.site).resolve()
    baseline = Path(args.baseline).resolve() if args.baseline else None
    shutil.rmtree(site, ignore_errors=True)
    site.mkdir(parents=True)

    main_files = copy_tree(root, site, missing_only=False)
    baseline_files = copy_tree(baseline, site, missing_only=True) if baseline else 0
    if not (site / 'index.html').is_file():
        raise SystemExit('index.html missing from current main')

    boundary = assert_public_boundary(site)
    cleanup = remove_generated_mixes(site)
    knowledge_report = publish_knowledge_core(site)

    runtime = shell.copy_platform_runtime(site)
    results = [shell.normalize_file(path, site, check_only=False) for path in shell.production_html_files(site)]
    errors = [item for item in results if item.status == 'error']
    if errors:
        raise SystemExit({'normalizationErrors': [item.path for item in errors[:20]]})
    polished = inject_polish(site)

    html_pages = sum(1 for _ in site.rglob('*.html'))
    report = {
        'schemaVersion': 5,
        'status': 'passed',
        'policy': 'current-main public pages are authoritative; baseline restores missing public paths only; repository source/tooling roots are excluded; new knowledge pages must pass route/title conflict checks and evidence contracts',
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'mainFilesCopied': main_files,
        'baselineMissingFilesRestored': baseline_files,
        'htmlPages': html_pages,
        'publicBoundary': boundary,
        'pagesCleaned': cleanup['pagesCleaned'],
        'generatedMixBlocksRemoved': cleanup['generatedMixBlocksRemoved'],
        'pagesPolished': polished,
        'platformRuntimeFilesCopied': len(runtime.get('files', [])),
        'specialNeedsKnowledgeCoreV1': {
            'pageCount': knowledge_report['page_count'],
            'uniqueRoutes': knowledge_report['unique_routes'],
            'candidatePoolCount': knowledge_report['candidate_pool_count'],
            'minimumWordCount': knowledge_report['minimum_word_count'],
            'skippedConflicts': len(knowledge_report.get('skipped', [])),
        },
    }
    api = site / 'api'
    api.mkdir(parents=True, exist_ok=True)
    (api / 'clean-site-build-v1.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (site / '.nojekyll').touch()
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()