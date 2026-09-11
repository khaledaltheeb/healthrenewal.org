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

## Required gates before Thoth

`rights -> editorial -> scientific when applicable -> accessibility -> metadata -> files -> ready-for-thoth`

The validator in `scripts/validate_publishing_core.py` enforces the non-negotiable gates.
