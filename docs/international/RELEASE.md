# International preview release — 2026-10-07

## Release state

Implemented on `codex/international-release`, isolated from the original checkout and production backups. **Not deployed:** HostHatch instance 182191 is behind an unauthenticated login; no new-server SSH address, SSH key reference or deployment domain has been supplied. Existing production was not contacted or changed.

This is a core international preview, not a translation of every legacy screen. It provides discovery, character details, email/password authentication, localized OTP mail, account/age completion, character creation/edit/disable, text chat, history, balances/check-in, data export/deletion and policy/contact pages in English, Japanese and Korean. There is no Chinese UI option. Voice calls, story campaigns, masks and the old promotions UI are not exposed in this preview. Their stored data is retained. Existing Chinese private characters remain accessible to their owners; they are not promoted in the international public catalogue. User-authored content and old chat history are not automatically translated.

`VITE_INTERNATIONAL=true` builds the international entrypoint. `INTERNATIONAL_MODE=true` selects backend behavior: saved per-user reply language and action format, localized openings/fallbacks, removal of the Afdian-paid-only gate, omission of domestic webhook/referral/commission/lottery/promotion endpoints. Existing credits and membership records are preserved; daily grants and usage limits remain. No new payment platform is integrated and no payment collection opens. Existing safety/content controls remain; switching region does not disable them.

Migration 077 adds a separate `user_language_preferences` table. It does not rewrite existing users or messages. Six original adult launch characters are seeded idempotently under new `intl_*` IDs. Interface and reply language are independent. Action styles are parentheses, fullwidth parentheses or asterisks; action bubbles render without marker characters. Language directives apply to newly generated content, not historical messages. Backend operational and some internal persona instructions still contain Chinese; these are not public UI translations.

## Verified locally

- Canonical `bash scripts/ci.sh`: lint/format, mypy, 1,975 unit tests passed (34 skipped), schema checks, frontend build and 57 frontend tests.
- Legacy Tier E: 5 passed, using real uvicorn/Postgres/Redis and the existing no-provider fallback.
- International Tier E: 2 passed with an explicit test-only language-aware model double. Tests cover two-user preference isolation and DB persistence, rejection of Chinese preference values, Korean private character creation/visibility, complete WebSocket turn and persisted messages, selected Japanese output reaching the model double, logical character disable, localized public catalogue and omitted commerce endpoints.
- Unit tests cover Accept-Language negotiation, hostile preference rejection, OTP translation, all three action styles, prompt format conflicts and fail-closed HTTP/WebSocket geo checks.
- Separate `VITE_INTERNATIONAL=true` production build passed; legacy UI chunk is absent.
- Browser: EN/JA/KO catalogue, Japanese character description, local password login, independent Japanese UI/Korean response settings, Korean opening and completed chat with the model double; mobile layout at 390 × 844 with no horizontal overflow.
- Empty isolated PostgreSQL migrated to 077 and six characters seeded. Production backup restoration was verified in the earlier migration work; this release has not restored that backup on the destination server.
- Caddy configuration validated in the official Caddy image. Compose overlay validated with dummy configuration and without resolving secret env files. Cloudflare's official API returned 22 validated network ranges.

Tests prove request routing and persistence, not real-model translation quality, SMTP deliverability or geographic enforcement on the destination network. These require deployment acceptance below. No paid model calls were made in local verification.

## Deployment inputs still needed

1. SSH hostname/IP, login name, port and existing private-key **path** (do not paste private keys), or authenticated HostHatch control panel. Confirm instance 182191's actual location, resources and renewal price before operating it.
2. International hostname and access to its DNS/Cloudflare settings. Use a separate hostname for preview if the existing domestic service is still running.
3. Public operator identity and working support/privacy contact addresses. Current page copy references `support@yuoyuo.app` and `privacy@yuoyuo.app`; these addresses are not yet verified. Policy text is a draft and does not establish legal or payment-provider approval. Before public registration, identify actual processors, transfer locations, retention periods and operator contact details.
4. Cutover data freshness: the supplied snapshot is dated 2026-09-28. If old production accepted writes afterwards, a new transaction-consistent snapshot or explicit reconciliation is needed before retiring it. Never restore the older dump over a live destination.

## Restore and activate on the NEW server only

Detailed existing restore SOP is in the original checkout's `docs/JAPAN_SERVER_MIGRATION.md`; its backup baseline is 4,223 users, 2,047,103 chat messages and 212,291 credit ledger rows. The snapshot is `/Users/wanglixun/heart/.local-backups/production-final-20260928`. Keep its SHA256SUMS and original files unchanged.

1. Inspect the destination without making changes: OS/architecture, RAM, CPU allocation, free disk/inodes, Docker, running services and mounted volumes. Confirm it is the new destination, not the old production IP. Reserve enough room for restored DB, media, WAL, images and at least two backup generations. Never purchase an upgrade without a separately approved cost.
2. Stage verified backup and the reviewed release commit in a new directory. Preserve `.env.prod` with mode 600; never print/commit it. Preserve existing JWT and DB/storage credentials as described in the restore SOP. Do **not** overwrite this release's Compose/Caddy files with the old snapshot versions.
3. Restore Postgres into an empty dedicated volume **before** Alembic. Restore MinIO/Redis as the migration SOP specifies. Keep API/workers/Caddy stopped until counts and restored schema 076 are verified. Caddy state may only be reused when it matches the selected hostname.
4. Configure `.env.prod`: `INTERNATIONAL_DOMAIN=<verified hostname>`, `INTERNATIONAL_ORIGIN_SECRET=<new cryptographic random secret>`, correct public/CORS/mail URLs, `HEART_DEV_MODE=false`, real model credentials, and existing infrastructure settings. Never set fake model/test JWT values in production. Build frontend with `VITE_INTERNATIONAL=true npm --prefix web run build` (install with `npm ci` first).
5. All deployment commands must include both Compose files, e.g. define this shell function at the repository root:

   ```bash
   intl_compose() {
     docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.international.yml "$@"
   }
   intl_compose config --quiet
   intl_compose build api encoder-worker
   intl_compose run --rm --no-deps api python -m alembic upgrade heads
   intl_compose run --rm --no-deps api python -m alembic current
   intl_compose run --rm --no-deps api python scripts/seed_international.py --apply
   ```

   These run commands require restored Postgres/Redis/MinIO already healthy. `alembic current` must show `077_language_preferences` and `heads` must show the same single head. Keep background workers off until acceptance is complete.
6. Refresh Cloudflare ranges with `python3 scripts/update-cloudflare-origins.py`. Configure proxied DNS (orange cloud), IP geolocation headers, mainland CN blocking and TLS **Full (strict)**. Restrict origin 80/443 to Cloudflare's IPv4/IPv6 networks and SSH to administration addresses. Preserve a working SSH session while changing firewall rules. API, database, Redis and MinIO have no public port mappings.
7. Establish valid origin TLS before cutover: for an existing hostname restore its still-valid Caddy certificate state; for a new hostname configure a valid origin certificate or DNS-01 issuance. Do not switch to Flexible TLS or open the origin broadly to work around validation. The supplied Caddyfile uses automatic HTTPS and requires an issuance/bootstrap plan for a new hostname behind strict proxying.
8. Validate Caddy inside the container, then `intl_compose up -d api caddy`. Start the worker after the acceptance tests below and a current backup. Use `--no-access-log` for API to avoid uvicorn logging WebSocket query credentials; Caddy access logs redact `token`.

## Acceptance before public use

- Compare restored counts against snapshot baselines before allowing new writes; no missing users, balances, memberships, memories or files. After seeding expect six new characters and specs only.
- Japanese and Korean external networks: HTTPS, signup/OTP delivery, adulthood gate, login/refresh/logout, role creation/edit/private visibility, free grant/charged turn, independent UI/reply languages and three action styles, reconnect/history, export and deletion.
- Mainland CN edge traffic: reject both web and API/WebSocket. Unknown country and missing origin-secret header fail closed. Direct IPv4 **and IPv6**, forged `CF-IPCountry: JP` from a non-Cloudflare peer and all alternate hostnames must fail. Confirm no DNS-only alias exposes the origin.
- No Afdian or alternative checkout, webhooks, domestic campaigns, yuan store credit or merchant-approved claims. Verify actual policy/contact details before requesting payment underwriting.
- Safety/moderation and UGC review must work in target languages, including severe sexual/exploitation/self-harm/violence cases. Existing Chinese-oriented moderation is not evidence of adequate Japanese/Korean coverage; complete this audit before broad registration.
- Exercise the configured real-model route and SMTP on the destination. The successful local model double is not evidence that paid provider credentials or outbound networking work.

IP geoblocking excludes mainland networks; it cannot reliably determine nationality or guarantee exclusion of users tunnelling through overseas VPNs. Do not describe it as an absolute identity-level ban.

## Rollback

Keep source server and backups intact until acceptance and data reconciliation finish. Stop the new API/worker and return DNS to the prior approved origin only after deciding how to preserve writes made on the new server. Do not restore an old dump over new user data. Application rollback may leave the additive preference table in place; migration downgrade deliberately does not delete preferences. Do not point the international frontend at the domestic backend.

## HostHatch price check

Source: https://hosthatch.com/products (public **starting** prices read 2026-10-07, not an account invoice).

| RAM | CPU description | NVMe | Public starting monthly price |
| --- | --- | --- | --- |
| 4 GB | 2 fair-share cores | 20 GB | USD 6 |
| 8 GB | 2 fair-share cores | 35 GB | USD 9 |
| 12 GB | 1 dedicated + 3 fair-share cores | 50 GB | USD 12 |
| 16 GB | 2 dedicated + 2 fair-share cores | 75 GB | USD 15 |
| 24 GB | 2 dedicated + 4 fair-share cores | 100 GB | USD 22 |

These prices are attractive for API-driven inference. RAM is not the only sizing constraint: the 8 GB plan's 35 GB disk is below the existing restore guide's 80 GB recommendation. The 16 GB plan is closer but its 75 GB is also below that recommendation; 24 GB/100 GB has more recovery room. The 2 GB plan explicitly advertises reduced 500 GB traffic in Tokyo/Hong Kong/Singapore/Sydney; other rows' generic bandwidth should not be assumed to apply unchanged in Tokyo. Confirm regional pricing, traffic, tax, term/renewal rate and the existing instance's disk capacity in the portal before choosing. No server purchase, resize or billing change was made.
