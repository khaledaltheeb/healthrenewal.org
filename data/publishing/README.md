# Rawafid Publishing Core

This directory is the single source of truth for Rawafid book publishing metadata.

## Record classes

- `rawafid-original`: Rawafid is the actual publisher of an original work it has the rights to publish.
- `licensed-translation`: Rawafid publishes an authorised Arabic translation under a licence or written permission that allows it.
- `authorized-co-managed`: Rawafid manages metadata on behalf of another publisher only under explicit authorisation and any platform-side approval required.
- `discovery-only`: third-party work discovered or described by Rawafid; it is never counted as a Rawafid publication.

## Safety boundaries

1. Never infer full-text, cover, translation or redistribution rights from open bibliographic metadata.
2. Do not put confidential contracts, email bodies, private reviewer notes or unpublished manuscripts in this public repository.
3. Every book must have a rights-clearance record before it can pass `rights-cleared`.
4. Literary works are held from Thoth upload until Thoth confirms they are in scope for the Metadata Management account.
5. Only professional/scholarly works that pass all required local gates may reach `ready-for-thoth`.
6. Metadata sent to Thoth must be treated as public and reusable under CC0.
7. `thoth-staging.json` is an internal readiness projection, not a Thoth API payload. The live external schema must be verified before any transformation or transmission.
8. `translation-queue.json` contains only workflow metadata for authorised Arabic translation records. It does not itself grant translation rights.

## Required gates before Thoth

`rights -> editorial -> scientific when applicable -> accessibility -> metadata -> files -> ready-for-thoth`

The validator in `scripts/validate_publishing_core.py` enforces the non-negotiable gates.

## Generated outputs

- `catalog.json`: public publication inventory and counts.
- `../../api/v1/open-books.json`: public JSON projection for approved Rawafid publications.
- `thoth-staging.json`: internal list of records that satisfy local readiness rules for a future Thoth mapping step.
- `translation-queue.json`: internal queue of active authorised Arabic translation workflows and their blockers.

Regenerate or verify these outputs with:

```bash
python scripts/build_publishing_catalog.py --check
python scripts/build_publishing_staging.py --check
python scripts/validate_publishing_core.py
```
