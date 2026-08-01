# Verified AI crawler and WAF policy

## Objective

Allow legitimate search and AI retrieval crawlers to read the public static site without CAPTCHA or JavaScript challenges while retaining abuse controls. This policy does not grant access to private, authenticated, administrative, or personal-data routes.

## Non-negotiable rule

Never bypass the WAF by `User-Agent` alone. A client can copy any crawler name. Use the provider's current verification method, official IP manifest when available, reverse/forward DNS verification where officially documented, request logging, and conservative rate limits.

## Rule order

1. Deny private, authenticated, administrative, upload, mutation, and secret-bearing routes.
2. Allow verified public crawlers before generic bot challenges.
3. Skip CAPTCHA and browser JavaScript challenges only for verified crawler requests.
4. Keep request logging, anomaly detection, payload-size limits, and abuse rate limits.
5. Apply the normal WAF policy to unverified requests that merely claim a crawler `User-Agent`.

## OpenAI

Public discovery tokens used by this site:

- `OAI-SearchBot`
- `GPTBot`
- `ChatGPT-User`

For OpenAI search retrieval, verify the request against the current official OpenAI crawler documentation and IP manifest before creating a WAF bypass. The discovery manifest points to `https://openai.com/searchbot.json` for operational verification.

## Anthropic

Public tokens used by this site:

- `ClaudeBot`
- `Claude-SearchBot`
- `Claude-User`
- `Claude-Web` retained only as a legacy compatibility token

Follow Anthropic's current official crawler documentation. Do not invent or freeze an unofficial IP allowlist. When a stable provider verification method is unavailable, use the documented token, strict public-path scope, conservative rate limits, and detailed logs rather than a broad security bypass.

## Perplexity

Public tokens used by this site:

- `PerplexityBot`
- `Perplexity-User`

Verify against Perplexity's current official crawler documentation and published IP manifest before bypassing bot challenges. The discovery manifest points to `https://www.perplexity.ai/perplexitybot.json`.

## Google

`Google-Extended` is declared in `robots.txt` as a Google-controlled robots token. It must not be treated as proof that an incoming HTTP request is a distinct verified crawler. Normal Googlebot verification and the site's standard public-crawl policy remain separate.

## Public paths eligible for verified-crawler access

- Canonical HTML pages
- `/robots.txt`
- `/sitemap.xml`
- `/sitemap-index.xml`
- `/sitemap-family-*.xml`
- `/feed.xml`
- `/atom.xml`
- `/llms.txt`
- `/llms-full.txt`
- `/api/v1/content-index.json`
- `/api/v1/ai-discovery.json`
- `/api/v1/ai-discovery.openapi.json`
- Other explicitly public read-only JSON resources under `/api/`

## Paths that must not receive a crawler bypass

- Authentication, account, session, password-reset, or identity routes
- Administrative consoles
- Write, upload, import, webhook, or mutation endpoints
- Private provider records or personal data
- Temporary build artifacts, logs, secrets, backups, or source maps not intended for publication

## Validation checklist

- The verified crawler receives HTTP 200 on public HTML, robots, sitemap, feed, and discovery endpoints.
- The response contains useful text without client-side JavaScript execution.
- No CAPTCHA, managed challenge, interstitial, or cookie wall is returned to verified crawlers.
- Unverified requests using a copied crawler name do not bypass the normal WAF.
- Logs record verification result, path, status, bytes, and rate-limit action without recording sensitive content.
- The allow policy is reviewed whenever a provider changes its crawler documentation or verification manifest.
