# Selected international changes — 2026-10-08

Worktree: `codex/international-release`. Existing mobile App/PWA components retained. No production deployment or payment activation.

## Implemented scope and explicit limits

- B1: anonymous profile browsing; Google OIDC server code, callback page and conditional login button. Existing email authentication retained. OAuth credentials and Google console setup still required. No Apple login.
- C: catalogue metadata, author display-name/story/tag search and language/cast/rating filters. Only permission-filtered catalogue rows are returned. Link-visible roles remain outside public discovery except the existing loopback-only local review mode. Creator emails are never returned as names.
- E: existing relationship upgrade action opens Shared memories. Displays message count, closeness, a small derived emotion label, and up to 100 active L3 plus 100 active L4 memories. Corrections are user/character scoped, optimistic-conflict checked, audited, and never hard-delete originals. L4 corrections require explicit confirmation. L3 stale vectors/hints are cleared; vector regeneration uses the existing backfill path, while text recall can use corrected content. These are model memories, not factual psychological assessments.
- F: creator reply language in quick creation and workshop. Explicit user AI language wins; otherwise creator language wins, then user interface language. Each turn reloads the preference, so no reconnect is necessary. The legacy `response_follows_interface` field remains for DB compatibility and now represents the default chain. UI wording describes that chain.
- H: world book accepts 10,000 Unicode characters. It is screened during creation/edit and passed as untrusted fictional reference. The composer selects at most 3,000 characters including an introduction and query-relevant passages. It is not L3/L4 memory and cannot redefine policy or output conventions.
- J: analysis only in [PRICING_JP_KR.md](PRICING_JP_KR.md). Default configuration is not a verified live price list.
- K: expanded English/Japanese/Korean policy drafts covering AI disclosure, privacy, transfer, content, copyright, retention/deletion, age and future commerce. Adult threshold remains 18+ with stricter applicable local thresholds required; a birthday declaration is not strong age assurance. Public adult-content access in Korea requires a separate local compliance review. Underage profile edits now revoke any stale age-verification flag. Legal operator particulars, processors, retention schedules and verified contact delivery remain publication prerequisites.

## Launch selection

12 first-party public roles adapted as separate `launch_*` character IDs; 4 Japanese, 4 Korean, 4 English. Names, personas, intros, openings, tags and premise cards are in [launch_catalog.json](launch_catalog.json). Existing covers and palette are reused without inventing a new UI. English is the first shared language for Southeast Asian evaluation, not a claim of full Thai/Vietnamese/Indonesian support.

The full 222-source selection audit is private at `/Users/wanglixun/heart/.local-review/production-20260928/audit/international-selection-20261008.csv`. Remaining 210 candidates are held for source rights, full-content and localization review; they are not all translated or cleared for launch. Market suggestions for held rows are preliminary theme-based triage, not measured market preference.

`backend/scripts/prepare_launch_catalog.py` validates by default and only applies to loopback `heart_review`. It creates independent IDs and saves full before/after provenance plus a SHA-256 source hash in `local_review.international_adaptations`. Original 222 roles, original 714-row audit and historical conversations remain intact. New local preview rows are editorial drafts, even though local presentation uses approved catalogue flags; this is not production moderation approval. Do not copy the review database's visibility flags into production.

## Google configuration

- Origin: `https://yuoyuo.app`
- Backend callback: `https://yuoyuo.app/api/auth/google/callback`
- Frontend completion: `https://yuoyuo.app/auth/google/callback`
- Local callback when testing behind Vite proxy: `http://127.0.0.1:55173/api/auth/google/callback`; frontend completion at the same host/port under `/auth/google/callback`.
- Scope: `openid email profile`. No Gmail permissions.
- Settings: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `GOOGLE_FRONTEND_CALLBACK`.
- Migration: `079_google_identities`; links stable Google subject to user ID. Email-based linking is restricted to Google-authoritative Gmail/Workspace identities. Third-party email accounts with existing users use their previous login method.
- Redis state lasts 10 minutes; PKCE/nonce and HttpOnly same-site browser cookie bind the request. A 90-second single-use completion ticket appears in a URL fragment, is cleared by the client, and requires the same browser cookie. Access/refresh tokens are never put into redirect URLs. Redact authorization callback query strings in proxy/access logs before production.
- Deleted accounts must use the existing account recovery flow; Google login does not silently reactivate or regrant balances.

## Email

Planned privacy address: `privacy@yuoyuo.app`, forwarding to the operator's specified Gmail. DNS currently uses Cloudflare and no MX was returned by the check on 2026-10-08. Resend handles application email APIs and can support receiving workflows; it is not by itself a normal hosted mailbox. Prefer a real forwarding/inbox service for privacy correspondence. Do not publish the address as operational until destination verification and an external inbound test pass. No MX records or forwarding routes have been changed yet.

## Validation (2026-10-08)

Canonical `bash scripts/ci.sh`: 2,001 backend tests passed, 34 skipped; 64 frontend tests passed; lint, typing, schemas and production build passed. Seven international Tier E tests passed in 7.02 seconds against isolated `heart_ui_test` with real HTTP/WebSocket/Postgres/Redis and a fake LLM; no paid model calls. Both local review and test DB report migration 079. Anonymous details no longer request companion data or authenticated view increments; chat opens the existing login dialog with a return destination. Real Google login and inbound mail delivery are not yet verified.
