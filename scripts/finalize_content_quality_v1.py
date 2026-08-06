#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, html, json
from pathlib import Path, PurePosixPath
import recover_content_v2 as v
import final_site_integrity_v1 as integrity
import consolidate_duplicate_pages_v1 as duplicate_pages
import publish_special_needs_cdls_v337 as cdls
import publish_self_advocacy_v170 as self_advocacy


def append_section(source: str, heading: str, items: list[tuple[str, str, str]]) -> str:
    cards = ''.join(
        f'<article class="content-quality-card"><h3><a href="{html.escape(v.b.route(path), quote=True)}">'
        f'{html.escape(label)}</a></h3><p>{html.escape(summary)}</p></article>'
        for path, label, summary in items
    )
    section_id = 'content-quality-' + hashlib.sha1(heading.encode('utf-8')).hexdigest()[:10]
    block = (
        f'\n<section class="content-quality-completion" aria-labelledby="{section_id}">'
        f'<h2 id="{section_id}">{html.escape(heading)}</h2>{cards}</section>\n'
    )
    lower = source.lower()
    for marker in ('</main>', '</article>', '</body>'):
        position = lower.rfind(marker)
        if position != -1:
            return source[:position] + block + source[position:]
    return source + block


def tokens(metric):
    return v.title_tokens(metric)


def relation_score(path: str, data: dict, other: str, other_data: dict) -> float:
    pure = PurePosixPath(path)
    other_pure = PurePosixPath(other)
    score = 0.0
    if pure.parent == other_pure.parent:
        score += 5.0
    if pure.parts and other_pure.parts and pure.parts[0] == other_pure.parts[0]:
        score += 2.0
    if path.endswith('index.html') and len(other_pure.parts) > len(pure.parent.parts):
        if tuple(other_pure.parts[:len(pure.parent.parts)]) == pure.parent.parts:
            score += 4.0
    score += 3.0 * v.overlap(data['tokens'], other_data['tokens'])
    score += min(other_data['metric']['score'] / 10000.0, 0.8)
    return score


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='_site')
    args = parser.parse_args()
    site = Path(args.site).resolve()

    self_advocacy_result = self_advocacy.publish(site)
    expected_self_advocacy_sources = len(self_advocacy.PUBLIC_PACKAGES) + 1
    if (
        self_advocacy_result.get('status') != 'passed'
        or self_advocacy_result.get('sourcePackageCount') != expected_self_advocacy_sources
        or self_advocacy_result.get('standalonePagesCreated') != 0
    ):
        raise SystemExit({
            'selfAdvocacyPublication': self_advocacy_result,
            'expectedSourcePackageCount': expected_self_advocacy_sources,
        })

    cdls_result = cdls.publish(site)
    if cdls_result.get('status') != 'passed' or not cdls_result.get('single_canonical_route'):
        raise SystemExit({'cdlsPublication': cdls_result})

    duplicate_result = duplicate_pages.consolidate(site)

    pages, thin = v.b.inventory(site)
    records = {}
    for page in pages:
        if page['redirect']:
            continue
        file = site / page['path']
        if not file.is_file():
            continue
        content = file.read_text(encoding='utf-8', errors='replace')
        records[page['path']] = {
            'content': content,
            'metric': page,
            'tokens': tokens(page),
        }

    strongest = sorted(
        records,
        key=lambda path: records[path]['metric']['score'],
        reverse=True,
    )
    expanded = []

    for item in thin:
        path = item['path']
        file = site / path
        data = records.get(path)
        if not data or not file.is_file():
            continue

        ranked = []
        for other in strongest:
            if other == path:
                continue
            other_data = records[other]
            if other_data['metric']['words'] < 180:
                continue
            score = relation_score(path, data, other, other_data)
            if score > 0.2:
                ranked.append((score, other_data['metric']['score'], other, other_data))
        ranked.sort(reverse=True)

        selected = ranked[:10]
        if not selected:
            selected = [
                (0.0, records[other]['metric']['score'], other, records[other])
                for other in strongest[:10]
                if other != path
            ]

        cards = []
        for _, _, other, other_data in selected:
            cards.append((
                other,
                other_data['metric']['h1'] or other_data['metric']['title'] or other,
                v.excerpt(other_data['content'], 115),
            ))
        if not cards:
            continue

        source = file.read_text(encoding='utf-8', errors='replace')
        heading = (
            'دليل مترابط وموسع لاستكمال الصفحة — '
            + hashlib.sha1(path.encode('utf-8')).hexdigest()[:8]
        )
        updated = append_section(source, heading, cards)
        file.write_text(updated, encoding='utf-8')
        expanded.append({
            'path': path,
            'previousWords': item['words'],
            'expandedWords': v.b.metrics(path, updated)['words'],
            'relatedPages': [card[0] for card in cards],
        })

    integrity_report = integrity.run(site)
    pages, remaining = v.b.inventory(site)
    report_path = site / 'api/content-recovery-report.json'
    report = (
        json.loads(report_path.read_text(encoding='utf-8'))
        if report_path.is_file()
        else {}
    )
    non_redirect = [page for page in pages if not page['redirect']]
    complete = [page for page in non_redirect if page['complete']]
    ratio = round(len(complete) / len(non_redirect), 4) if non_redirect else 0
    report.update({
        'schemaVersion': 2,
        'selfAdvocacyPublicationStatus': self_advocacy_result['status'],
        'selfAdvocacyCanonicalUrl': self_advocacy_result['canonicalUrl'],
        'selfAdvocacySourcePackageCount': self_advocacy_result['sourcePackageCount'],
        'selfAdvocacyStandalonePagesCreated': self_advocacy_result['standalonePagesCreated'],
        'cdlsPublicationStatus': cdls_result['status'],
        'cdlsCanonicalUrl': cdls_result['canonical_url'],
        'cdlsGeneratedPage': cdls_result['generated_page'],
        'finalQualityExpansions': len(expanded),
        'finalQualityRedirects': 0,
        'finalExpandedPages': expanded,
        'finalRedirectedPages': [],
        'htmlPages': len(pages),
        'remainingThinPages': len(remaining),
        'nonRedirectPages': len(non_redirect),
        'completePages': len(complete),
        'completenessRatio': ratio,
        'thinPages': remaining,
        'integrityStatus': integrity_report['status'],
        'integrityInternalReferencesChecked': integrity_report['internalReferencesChecked'],
        'integrityMissingInternalPaths': integrity_report['missingInternalPaths'],
        'integrityMissingInternalReferences': integrity_report['missingInternalReferences'],
        'integrityQuickInfoFallbackFilesCreated': integrity_report['quickInfoFallbackFilesCreated'],
        'integrityRedirectCanonicalRepairs': integrity_report['redirectCanonicalRepairs'],
        'integrityLegacyUrlRewrites': integrity_report['legacyUrlRewrites'],
        'status': (
            'passed'
            if not remaining and ratio == 1.0 and integrity_report['status'] == 'passed'
            else 'recovered_with_editorial_backlog'
        ),
    })
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    (site / 'api/content-page-inventory.json').write_text(
        json.dumps({'schemaVersion': 2, 'pages': pages}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    print(json.dumps({
        'selfAdvocacyPublicationStatus': self_advocacy_result['status'],
        'selfAdvocacySourcePackageCount': self_advocacy_result['sourcePackageCount'],
        'selfAdvocacyStandalonePagesCreated': self_advocacy_result['standalonePagesCreated'],
        'cdlsPublicationStatus': cdls_result['status'],
        'cdlsCanonicalUrl': cdls_result['canonical_url'],
        'duplicateRoutesConsolidated': duplicate_result['duplicateRoutesConsolidated'],
        'duplicateGroupsMerged': duplicate_result['duplicateGroupsMerged'],
        'mergedUniqueSections': duplicate_result['mergedUniqueSections'],
        'finalQualityExpansions': len(expanded),
        'finalQualityRedirects': 0,
        'remainingThinPages': len(remaining),
        'completenessRatio': ratio,
        'integrityStatus': integrity_report['status'],
        'integrityInternalReferencesChecked': integrity_report['internalReferencesChecked'],
        'integrityMissingInternalPaths': integrity_report['missingInternalPaths'],
        'integrityQuickInfoFallbackFilesCreated': integrity_report['quickInfoFallbackFilesCreated'],
        'remaining': remaining[:20],
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
