#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import consolidate_duplicate_pages_v1 as duplicate_pages
import ensure_special_needs_publication_v1 as special_needs
import final_site_integrity_v1 as integrity
import publish_self_advocacy_v170 as self_advocacy
import publish_special_needs_cdls_v337 as cdls
import recover_content_v2 as recovery


V280_CONTRACT = {
    'status': 'passed',
    'condition_count': 100,
    'detailed_guide_count': 100,
    'condition_profile_count': 100,
    'direct_condition_reference_count': 100,
    'generated_page_count': 104,
    'curated_evidence_packet_count': 100,
    'curated_evidence_claim_count': 300,
    'curated_evidence_source_count': 112,
}


def _load_v280_report(site: Path) -> dict[str, object]:
    path = site / 'api/capabilities-v280.json'
    if not path.is_file():
        raise SystemExit({'missingCapabilitiesV280Report': str(path)})
    result = json.loads(path.read_text(encoding='utf-8'))
    mismatches = {
        key: {'expected': expected, 'actual': result.get(key)}
        for key, expected in V280_CONTRACT.items()
        if result.get(key) != expected
    }
    if int(result.get('source_count', 0)) < 20:
        mismatches['source_count'] = {
            'expected': '>=20',
            'actual': result.get('source_count', 0),
        }
    if mismatches:
        raise SystemExit({
            'capabilitiesV280Publication': result,
            'contractMismatches': mismatches,
        })
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='_site')
    args = parser.parse_args()
    site = Path(args.site).resolve()
    repo_root = Path(__file__).resolve().parents[1]

    special_needs_repair = special_needs.repair_missing_generated_families(site, repo_root)
    special_needs_count_failures = special_needs.validate_counts(
        dict(special_needs_repair.get('after', {}))
    )
    if special_needs_count_failures:
        raise SystemExit({
            'specialNeedsPublicationRepair': special_needs_repair,
            'countFailures': special_needs_count_failures,
        })

    capabilities_result = _load_v280_report(site)

    self_result = self_advocacy.publish(site)
    if (
        self_result.get('status') != 'passed'
        or self_result.get('publicContentPackageCount', 0) < 9
        or self_result.get('standalonePagesCreated') != 0
    ):
        raise SystemExit({'selfAdvocacyPublication': self_result})

    cdls_result = cdls.publish(site)
    if cdls_result.get('status') != 'passed' or not cdls_result.get('single_canonical_route'):
        raise SystemExit({'cdlsPublication': cdls_result})

    duplicate_result = duplicate_pages.consolidate(site)
    integrity_report = integrity.run(site)

    pages, remaining = recovery.b.inventory(site)
    non_redirect = [page for page in pages if not page['redirect']]
    complete = [page for page in non_redirect if page['complete']]
    ratio = round(len(complete) / len(non_redirect), 4) if non_redirect else 0

    report_path = site / 'api/content-recovery-report.json'
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.is_file() else {}
    report.update({
        'schemaVersion': 3,
        'capabilitiesV280PublicationStatus': capabilities_result['status'],
        'capabilitiesV280ConditionCount': capabilities_result['condition_count'],
        'capabilitiesV280DetailedGuideCount': capabilities_result['detailed_guide_count'],
        'capabilitiesV280ConditionProfileCount': capabilities_result['condition_profile_count'],
        'capabilitiesV280DirectConditionReferenceCount': capabilities_result['direct_condition_reference_count'],
        'capabilitiesV280GeneratedPageCount': capabilities_result['generated_page_count'],
        'capabilitiesV280SourceCount': capabilities_result['source_count'],
        'capabilitiesV280EvidencePacketCount': capabilities_result['curated_evidence_packet_count'],
        'capabilitiesV280EvidenceClaimCount': capabilities_result['curated_evidence_claim_count'],
        'capabilitiesV280EvidenceSourceCount': capabilities_result['curated_evidence_source_count'],
        'specialNeedsPublicationRepairActions': special_needs_repair.get('actions', []),
        'specialNeedsPublicationBeforeCounts': special_needs_repair.get('before', {}),
        'specialNeedsPublicationAfterCounts': special_needs_repair.get('after', {}),
        'selfAdvocacyPublicationStatus': self_result['status'],
        'selfAdvocacyCanonicalUrl': self_result['canonicalUrl'],
        'selfAdvocacySourcePackageCount': self_result.get('sourcePackageCount', 0),
        'selfAdvocacyPublicContentPackageCount': self_result.get('publicContentPackageCount', 0),
        'selfAdvocacyStandalonePagesCreated': self_result['standalonePagesCreated'],
        'cdlsPublicationStatus': cdls_result['status'],
        'cdlsCanonicalUrl': cdls_result['canonical_url'],
        'cdlsGeneratedPage': cdls_result['generated_page'],
        'duplicateRoutesConsolidated': duplicate_result['duplicateRoutesConsolidated'],
        'duplicateGroupsMerged': duplicate_result['duplicateGroupsMerged'],
        'mergedUniqueSections': duplicate_result['mergedUniqueSections'],
        'finalQualityExpansions': 0,
        'finalQualityRedirects': 0,
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
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (site / 'api/content-page-inventory.json').write_text(
        json.dumps({'schemaVersion': 3, 'pages': pages}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    print(json.dumps({
        'status': report['status'],
        'htmlPages': report['htmlPages'],
        'historicalPagesRestored': report.get('historicalPagesRestored', 0),
        'capabilitiesV280GeneratedPageCount': report['capabilitiesV280GeneratedPageCount'],
        'capabilitiesV280ConditionCount': report['capabilitiesV280ConditionCount'],
        'capabilitiesV280EvidenceClaimCount': report['capabilitiesV280EvidenceClaimCount'],
        'specialNeedsPublicationRepairActions': report['specialNeedsPublicationRepairActions'],
        'specialNeedsPublicationAfterCounts': report['specialNeedsPublicationAfterCounts'],
        'selfAdvocacySourcePackageCount': report['selfAdvocacySourcePackageCount'],
        'selfAdvocacyPublicContentPackageCount': report['selfAdvocacyPublicContentPackageCount'],
        'duplicateRoutesConsolidated': report['duplicateRoutesConsolidated'],
        'duplicateGroupsMerged': report['duplicateGroupsMerged'],
        'remainingThinPages': report['remainingThinPages'],
        'completenessRatio': report['completenessRatio'],
        'integrityStatus': report['integrityStatus'],
        'integrityMissingInternalPaths': report['integrityMissingInternalPaths'],
    }, ensure_ascii=False))

    if report['status'] != 'passed':
        raise SystemExit({
            'status': report['status'],
            'remainingThinPages': remaining[:20],
            'integrityMissingInternalReferences': integrity_report['missingInternalReferences'][:20],
        })


if __name__ == '__main__':
    main()
