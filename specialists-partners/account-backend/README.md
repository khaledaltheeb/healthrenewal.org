# Specialist account Worker v5

This Cloudflare Worker adds a persistent specialist dashboard without replacing the existing per-conversation portal.

## Authentication

- Passwordless email magic links.
- Login links expire after 15 minutes and are one-time use.
- Browser sessions expire after 12 hours by default and are revocable.
- D1 stores SHA-256 token hashes only; raw login and session tokens are never persisted.
- Session tokens are stored by the frontend in `sessionStorage`, not `localStorage`.
- Login requests require server-side Cloudflare Turnstile verification.

## Data and compatibility

The Worker binds to the existing `pterminology-specialists` D1 database and reuses the current provider, conversation, message, audit, email-event, rate-limit, and conversation-token tables. Migration `0004_specialist_accounts.sql` adds only account-specific columns and tables.

The existing visitor/specialist links under `/specialists-partners/portal/` remain operational as a compatibility and recovery path.

## API

- `POST /v1/specialist/session/request`
- `POST /v1/specialist/session/verify`
- `POST /v1/specialist/session/revoke`
- `GET /v1/specialist/me`
- `GET /v1/specialist/conversations`
- `GET /v1/specialist/conversations/:id`
- `POST /v1/specialist/conversations/:id/messages`
- `PATCH /v1/specialist/conversations/:id`

## Deployment secrets

The deployment workflow consumes existing GitHub Actions secrets:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`
- `SPECIALISTS_D1_DATABASE_ID`
- `RESEND_API_KEY`
- `TURNSTILE_SECRET`
- `SPECIALISTS_RATE_LIMIT_SALT`
- `SPECIALISTS_FROM_EMAIL`

No secret is committed to the repository. The deployment workflow generates and deletes temporary Wrangler and secret files on the runner.
