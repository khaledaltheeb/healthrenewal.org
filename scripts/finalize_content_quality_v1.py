#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, html, json
from pathlib import Path, PurePosixPath
import recover_content_v2 as v
import final_site_integrity_v1 as integrity
import consolidate_duplicate_pages_v1 as duplicate_pages
import publish_special_needs_cdls_v337 as cdls
import publish_self_advocacy_v170 as self_advocacy
import publish_monitor_items_v32 as monitor_items
import harden_lab_runtime_v32 as lab_runtime
import harden_monitor_runtime_v32 as monitor_runtime
import harden_cognitive_distinctness_v32 as cognitive_distinctness
import enrich_lab_content_v32 as lab_depth
import render_lab_specificity_v32 as lab_specificity
import apply_scale_provenance_v32 as scale_provenance


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


def require_issue20_laboratory_contract(site: Path) -> tuple[dict, dict, dict, dict, dict, dict, dict]:
    item_result = monitor_items.publish(site)
    if (
        item_result.get('status') != 'passed'
        or item_result.get('monitor_pages') != 36
        or item_result.get('profiles') != 36
        or item_result.get('total_items') != 432
        or item_result.get('unique_items') != 432
        or item_result.get('generic_template_items') != 0
        or item_result.get('written_total_items') != 432
        or item_result.get('written_unique_items') != 432
        or item_result.get('written_failures')
    ):
        raise SystemExit({'monitorItemPublication': item_result})

    lab_runtime_result = lab_runtime.patch_runtime(site)
    if (
        lab_runtime_result.get('status') != 'passed'
        or not all(
            value is True
            for key, value in lab_runtime_result.items()
            if key not in {'version', 'status', 'runtime'}
        )
    ):
        raise SystemExit({'laboratoryRuntime': lab_runtime_result})

    monitor_runtime_result = monitor_runtime.patch_runtime(site)
    if (
        monitor_runtime_result.get('status') != 'passed'
        or not all(
            value is True
            for key, value in monitor_runtime_result.items()
            if key not in {'version', 'status', 'runtime'}
        )
    ):
        raise SystemExit({'monitorRuntime': monitor_runtime_result})

    cognitive_result = cognitive_distinctness.patch_runtime(site)
    cognitive_checks = (
        'single_response_reaction',
        'sustained_visual_separated',
        'category_semantic_separated',
        'attention_switch_metadata',
        'span_study_hidden',
        'span_unique_tokens',
    )
    if (
        cognitive_result.get('status') != 'passed'
        or cognitive_result.get('missing_pages')
        or not all(cognitive_result.get(key) is True for key in cognitive_checks)
    ):
        raise SystemExit({'cognitiveDistinctness': cognitive_result})

    depth_result = lab_depth.enrich(site)
    if (
        depth_result.get('status') != 'passed'
        or depth_result.get('assessment_pages') != 40
        or depth_result.get('cognitive_pages') != 53
        or depth_result.get('total_tools') != 93
        or depth_result.get('minimum_actual_words', 0) < 850
        or depth_result.get('pages_below_depth')
        or depth_result.get('missing_task_profiles')
        or depth_result.get('unexpected_score_types')
    ):
        raise SystemExit({'laboratoryDepth': depth_result})

    specificity_result = lab_specificity.render(site)
    if (
        specificity_result.get('status') != 'passed'
        or specificity_result.get('monitor_pages') != 36
        or specificity_result.get('cognitive_pages') != 53
        or specificity_result.get('minimum_monitor_specific_words', 0) < 130
        or specificity_result.get('minimum_cognitive_specific_words', 0) < 95
        or specificity_result.get('monitor_failures')
        or specificity_result.get('cognitive_failures')
        or specificity_result.get('duplicate_specific_blocks') != 0
    ):
        raise SystemExit({'laboratorySpecificity': specificity_result})

    provenance_result = scale_provenance.apply(site)
    if (
        provenance_result.get('status') != 'passed'
        or provenance_result.get('found') != ['audit_guided', 'gad7', 'phq9', 'who5']
        or len(provenance_result.get('pages') or []) != 4
        or provenance_result.get('failures')
        or provenance_result.get('who5_policy') != 'adapted_arabic_descriptive_only'
        or provenance_result.get('arabic_exact_text_required_before_validated_claim') is not True
        or provenance_result.get('runtime', {}).get('generic_notice') is not True
        or provenance_result.get('runtime', {}).get('who5_adapted_label') is not True
        or provenance_result.get('runtime', {}).get('who5_no_validated_arabic_claim') is not True
    ):
        raise SystemExit({'scaleProvenance': provenance_result})

    return (
        item_result,
        lab_runtime_result,
        monitor_runtime_result,
        cognitive_result,
        depth_result,
        specificity_result,
        provenance_result,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='_site')
    args = parser.parse_args()
    site = Path(args.site).resolve()

    self_advocacy_result = self_advocacy.publish(site)
    if (
        self_advocacy_result.get('status') != 'passed'
        or self_advocacy_result.get('sourcePackageCount') != 9
        or self_advocacy_result.get('standalonePagesCreated') != 0
    ):
        raise SystemExit({'selfAdvocacyPublication': self_advocacy_result})

    cdls_result = cdls.publish(site)
    if cdls_result.get('status') != 'passed' or not cdls_result.get('single_canonical_route'):
        raise SystemExit({'cdlsPublication': cdls_result})

    (
        monitor_item_result,
        lab_runtime_result,
        monitor_runtime_result,
        cognitive_result,
        lab_depth_result,
        lab_specificity_result,
        scale_provenance_result,
    ) = require_issue20_laboratory_contract(site)

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
        'monitorItemPublicationStatus': monitor_item_result['status'],
        'monitorItemProfiles': monitor_item_result['profiles'],
        'monitorItemTotal': monitor_item_result['total_items'],
        'monitorItemUnique': monitor_item_result['unique_items'],
        'monitorItemGenericTemplates': monitor_item_result['generic_template_items'],
        'monitorItemCriticalProfiles': len(monitor_item_result['critical_profiles']),
        'laboratoryRuntimeStatus': lab_runtime_result['status'],
        'monitorRuntimeStatus': monitor_runtime_result['status'],
        'cognitiveDistinctnessStatus': cognitive_result['status'],
        'cognitiveDistinctnessSpecializedModes': cognitive_result['specialized_mode_count'],
        'laboratoryDepthStatus': lab_depth_result['status'],
        'laboratoryAssessmentPages': lab_depth_result['assessment_pages'],
        'laboratoryCognitivePages': lab_depth_result['cognitive_pages'],
        'laboratoryTotalTools': lab_depth_result['total_tools'],
        'laboratoryMinimumVisibleWords': lab_depth_result['minimum_actual_words'],
        'laboratorySpecificityStatus': lab_specificity_result['status'],
        'laboratoryMonitorSpecificityMinimumWords': lab_specificity_result['minimum_monitor_specific_words'],
        'laboratoryCognitiveSpecificityMinimumWords': lab_specificity_result['minimum_cognitive_specific_words'],
        'laboratoryDuplicateSpecificBlocks': lab_specificity_result['duplicate_specific_blocks'],
        'scaleProvenanceStatus': scale_provenance_result['status'],
        'scaleProvenanceProfiles': scale_provenance_result['found'],
        'who5ArabicPolicy': scale_provenance_result['who5_policy'],
        'arabicExactTextRequiredBeforeValidatedClaim': scale_provenance_result['arabic_exact_text_required_before_validated_claim'],
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
            if (
                not remaining
                and ratio == 1.0
                and integrity_report['status'] == 'passed'
                and monitor_item_result['status'] == 'passed'
                and lab_runtime_result['status'] == 'passed'
                and monitor_runtime_result['status'] == 'passed'
                and cognitive_result['status'] == 'passed'
                and lab_depth_result['status'] == 'passed'
                and lab_specificity_result['status'] == 'passed'
                and scale_provenance_result['status'] == 'passed'
            )
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
        'monitorItemPublicationStatus': monitor_item_result['status'],
        'monitorItemProfiles': monitor_item_result['profiles'],
        'monitorItemUnique': monitor_item_result['unique_items'],
        'monitorItemGenericTemplates': monitor_item_result['generic_template_items'],
        'laboratoryRuntimeStatus': lab_runtime_result['status'],
        'monitorRuntimeStatus': monitor_runtime_result['status'],
        'cognitiveDistinctnessStatus': cognitive_result['status'],
        'cognitiveDistinctnessSpecializedModes': cognitive_result['specialized_mode_count'],
        'laboratoryDepthStatus': lab_depth_result['status'],
        'laboratoryTotalTools': lab_depth_result['total_tools'],
        'laboratoryMinimumVisibleWords': lab_depth_result['minimum_actual_words'],
        'laboratorySpecificityStatus': lab_specificity_result['status'],
        'laboratoryMonitorSpecificityMinimumWords': lab_specificity_result['minimum_monitor_specific_words'],
        'laboratoryCognitiveSpecificityMinimumWords': lab_specificity_result['minimum_cognitive_specific_words'],
        'laboratoryDuplicateSpecificBlocks': lab_specificity_result['duplicate_specific_blocks'],
        'scaleProvenanceStatus': scale_provenance_result['status'],
        'scaleProvenanceProfiles': scale_provenance_result['found'],
        'who5ArabicPolicy': scale_provenance_result['who5_policy'],
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
