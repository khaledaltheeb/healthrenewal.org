# Rawafid Publishing Core

This directory is the single source of truth for Rawafid book publishing metadata.

## Record classes

- `rawafid-original`: Rawafid is the actual publisher of an original work it has the rights to publish.
- `licensed-translation`: Rawafid publishes an authorised Arabic translation under a licence or written permission that allows it.
- `authorized-co-managed`: Rawafid manages metadata on behalf of another publisher only under explicit authorisation and any platform-side approval required.
- `discovery-only`: third-party work discovered or described by Rawafid; it is never counted as a Rawafid publication.

## Safety boundaries

1. Never infer full-text, cover, translation or redistribution rights from open bibliographic metadata.
2. Do not put confidential contracts, email bodies, invitation links, credentials, private reviewer notes or unpublished manuscripts in this public repository.
3. Every book must have a rights-clearance record before it can pass `rights-cleared`.
4. Literary works are held from Thoth upload until Thoth confirms they are in scope for the Metadata Management account.
5. Only professional/scholarly works that pass all required local gates may reach `ready-for-thoth`.
6. Metadata sent to Thoth must be treated as public and reusable under CC0.
7. Thoth has no test-instance label for this account path; a real record must never be created merely as a test because records are public on creation.
8. `thoth-staging.json` is an internal readiness projection, not a Thoth API payload.
9. `thoth-upload-plan.json` is a deterministic offline mapping review artifact. It is deliberately non-executable and always records `transmission_permitted=false`.
10. `translation-queue.json` contains only workflow metadata for authorised Arabic translation records. It does not itself grant translation rights.
11. Contributor family names are never inferred by splitting a display name. For a contributor with multiple roles, `role_details` must explicitly record `main_contribution` per role.
12. The current Thoth bulk-uploader CSV/ONIX 3.0 template or live schema is the final authority immediately before any real upload.

## Required gates before Thoth

`rights -> editorial -> scientific when applicable -> accessibility -> metadata -> files -> ready-for-thoth`

Passing those gates only creates a local candidate. External transmission remains blocked until the current Thoth mapping, activated publisher/imprint identity and generated plan are reviewed.

The validator in `scripts/validate_publishing_core.py` enforces the non-negotiable local gates. `scripts/build_thoth_upload_plan.py` performs the next mapping layer without network access or credentials.

## Generated outputs

- `catalog.json`: public publication inventory and counts.
- `../../api/v1/open-books.json`: public JSON projection for approved Rawafid publications.
- `thoth-staging.json`: internal list of records that satisfy local readiness rules for a future Thoth mapping step.
- `thoth-upload-plan.json`: non-executable field-by-field Thoth mapping plan with explicit blockers and warnings.
- `translation-queue.json`: internal queue of active authorised Arabic translation workflows and their blockers.

Regenerate or verify these outputs with:

```bash
python scripts/build_publishing_catalog.py --check
python scripts/build_publishing_staging.py --check
python scripts/build_thoth_upload_plan.py --check
python scripts/validate_publishing_core.py
python -m unittest tests.test_publishing_core_contract tests.test_publishing_staging_contract tests.test_publishing_metadata_readiness tests.test_thoth_upload_plan
```
