#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import ensure_special_needs_publication_v1 as special_needs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', default='_site')
    args = parser.parse_args()
    site = Path(args.site).resolve()

    recovery_path = site / 'api/content-recovery-report.json'
    if not recovery_path.is_file():
        raise SystemExit({'missingContentRecoveryReport': str(recovery_path)})
    recovery = json.loads(recovery_path.read_text(encoding='utf-8'))

    repair = {
        'actions': recovery.get('specialNeedsPublicationRepairActions', []),
        'before': recovery.get('specialNeedsPublicationBeforeCounts', {}),
        'after': recovery.get('specialNeedsPublicationAfterCounts', {}),
    }
    publication = special_needs.validate_publication_inventory(site, repair=repair)
    counts = publication.get('counts', {})

    recovery.update({
        'specialNeedsPublicationStatus': publication.get('status'),
        'specialNeedsPublicationCounts': counts,
        'specialNeedsPublicationTargetRouteCount': publication.get('targetRouteCount', 0),
        'specialNeedsPublicationSitemapUrlCount': publication.get('sitemapUrlCount', 0),
        'specialNeedsPublicationMissingRoots': publication.get('missingRoots', []),
        'specialNeedsPublicationPageIssues': publication.get('pageIssues', {}),
        'specialNeedsPublicationSitemapMissingRoutes': publication.get('sitemapMissingRoutes', []),
    })
    recovery_path.write_text(
        json.dumps(recovery, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )

    print(json.dumps({
        'status': publication.get('status'),
        'counts': counts,
        'targetRouteCount': publication.get('targetRouteCount', 0),
        'sitemapUrlCount': publication.get('sitemapUrlCount', 0),
        'repairActions': repair['actions'],
    }, ensure_ascii=False))

    if publication.get('status') != 'passed':
        raise SystemExit({'specialNeedsPublication': publication})


if __name__ == '__main__':
    main()
