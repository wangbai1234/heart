# International preview release — updated 2026-10-08

## Release state

Implemented on `codex/international-release`, isolated from the original checkout and production backups. **Not deployed:** HostHatch instance 182191 is behind an unauthenticated login; no new-server SSH address, SSH key reference has been supplied; the confirmed future domain is `https://yuoyuo.app`. Existing production was not contacted or changed.

The international build now uses the existing App/PWA entrypoint, page components, styles and navigation. The separate international website and stylesheet were removed. English, Japanese and Korean resources cover authentication, discovery/filtering, chat, settings, quick/workshop creation, masks, voice controls, story controls, wallet, membership and error messages. There is no Chinese UI option. Only the language controls are added to the existing screens. User-authored role content and historical chats remain in their original languages; dormant domestic campaign/admin content is not a complete international translation.

`VITE_INTERNATIONAL=true` enables translated text in the same app. `INTERNATIONAL_MODE=true` selects saved per-user reply language and action format, localized openings/fallbacks, removal of the Afdian-paid-only gate, and omission of domestic webhook/referral/commission/lottery/promotion endpoints. Payment collection remains disabled. Existing safety/content controls, credits and membership records remain. This work is local and has not changed old production.

Migration 077 adds `user_language_preferences`. Migration 078 adds `response_follows_interface`: new accounts follow their interface language by default; explicit reply-language overrides remain available. Existing independent choices are preserved by backfill. Action-format selection has been removed: generation retains the original fullwidth `（）` contract and `【】` fallback, with the original detailed Composer format rules. The legacy API field is accepted for compatibility but normalized to fullwidth. Editing an existing role preserves its original content locale and other name translations even after switching UI language. Language directives affect newly generated content, not history. Changes autosave and apply to the next turn on the existing WebSocket; a reply already streaming finishes in its original language.

First visit uses a saved locale first, then authenticated Cloudflare country (JP → Japanese, KR → Korean, other allowed countries → English), browser language when no trusted country is available, and English as final fallback. `/api/locale` does not trust client-supplied geo headers; only authenticated middleware metadata is consumed, and the response is `private, no-store`. Detection is bounded to 1.5 seconds before browser fallback. Signup initializes both languages, existing accounts without preferences initialize on first preference load, and saved account settings override defaults. No third-party IP lookup is performed. The destination still needs the documented Cloudflare/origin controls before IP defaults operate there.

On desktop, the international app retains the mobile layout inside a centered shell up to 430 × 932 px, adapting to available height. Fixed overlays and body portals use the same containing block, and desktop breakpoints do not expand the shell into desktop grids. Phones keep their full viewport.

Translation resources live in `web/src/i18n/locales/{en,ja,ko}.json`. `legacy.json` retains original strings for the domestic compatibility build and stable stored option labels; it is not a selectable international locale. `uiText` supports interpolation, while `uiLabel` translates only application-owned option labels without changing their stored values. User-authored content must not pass through `uiLabel`.

The restored local catalogue now shows 222 active/approved characters (192 public and 30 unlisted) after restoring all 714 original states. See [LOCAL_REVIEW.md](LOCAL_REVIEW.md). Six `intl_*` characters remain optional isolated-test fixtures, not a replacement for the restored selection. Do not seed these into the selected local catalogue.

The next implementation batch adds Google OIDC (migration 079), creator reply-language defaults, world books, discovery filters, shared-memory correction and policy drafts. Explicit user reply language takes priority over creator default, then interface language. Twelve separate EN/JA/KO adaptations bring the local preview to 234 rows. Google credentials and mail forwarding are still pending. See [2026-10-08 implementation](IMPLEMENTATION_20261008.md) for current scope and limitations.

## Verified locally (2026-10-07 baseline; newer batch recorded separately)

- Canonical CI validates lint/format, mypy, backend tests, schemas, frontend tests and build; 1,993 backend tests passed (34 skipped), 64 frontend tests passed, mypy checked 267 files, and the separate international production build passed.
- International Tier E uses a separate `heart_ui_test` database and real uvicorn/Postgres/Redis with an explicit test-only model double. It covers preference isolation/persistence, rejection of Chinese preference values, Korean private character creation, complete WebSocket chat and persisted Japanese output, logical disable, catalogue and commerce-route restrictions. Signup tests cover Japanese/Korean initialization and persistence across login; a second turn on the same WebSocket switches from Japanese to Korean after saving follow-interface preferences.
- Frontend checks cover complete locale keys/interpolation, immediate language changes in original controls, stable stored theme values, creation in Korean and preservation of Japanese/Chinese authored locales during editing in English.
- Native browser verification of the current UI confirmed Japanese/Korean discovery and immediate language switching while retaining the original role-card grid and bottom navigation. Chromium checks at 390 × 844 and 1440 × 1000 confirmed the mobile layout, two-column cards, bounded fixed overlays, no horizontal overflow and no page errors. A mocked locale endpoint confirmed first-visit detection and persistence of manual overrides on reload; backend tests separately verify trusted country handling. Prior chat screenshots belonged to the removed redesign and are not acceptance evidence for this revision.
- The local review DB is never used for test cleanup. No paid model calls were made. Existing source media defects remain recorded in private audit files.
- Earlier infrastructure checks validated the Caddy configuration and Compose overlay, and fetched Cloudflare network ranges. These have not been deployed.

Tests prove request routing and persistence, not real-model translation quality, SMTP deliverability or geographic enforcement on the destination network. These require deployment acceptance below.

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
   ```

   These run commands require restored Postgres/Redis/MinIO already healthy. `alembic current` must show `079_google_identities` and `heads` must show the same single head. Keep background workers off until acceptance is complete.
6. Refresh Cloudflare ranges with `python3 scripts/update-cloudflare-origins.py`. Configure proxied DNS (orange cloud), IP geolocation headers, mainland CN blocking and TLS **Full (strict)**. Restrict origin 80/443 to Cloudflare's IPv4/IPv6 networks and SSH to administration addresses. Preserve a working SSH session while changing firewall rules. API, database, Redis and MinIO have no public port mappings.
7. Establish valid origin TLS before cutover: for an existing hostname restore its still-valid Caddy certificate state; for a new hostname configure a valid origin certificate or DNS-01 issuance. Do not switch to Flexible TLS or open the origin broadly to work around validation. The supplied Caddyfile uses automatic HTTPS and requires an issuance/bootstrap plan for a new hostname behind strict proxying.
8. Validate Caddy inside the container, then `intl_compose up -d api caddy`. Start the worker after the acceptance tests below and a current backup. Use `--no-access-log` for API to avoid uvicorn logging WebSocket query credentials; Caddy access logs redact `token`.

## Acceptance before public use

- Compare restored counts against snapshot baselines before allowing new writes; no missing users, balances, memberships, memories or files. Optional isolated-test fixtures can be seeded from `backend/` with `PYTHONPATH=. python -m scripts.seed_international --apply`; this is not a required production step.
- Japanese and Korean external networks: HTTPS, signup/OTP delivery, adulthood gate, login/refresh/logout, role creation/edit/private visibility, free grant/charged turn, linked/independent UI and reply languages and the original action format, reconnect/history, export and deletion.
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
