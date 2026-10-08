# Local production-snapshot character review

`LOCAL_CHARACTER_REVIEW=true` is a local-only catalogue review mode, default off. It requires development/test environment, `HEART_DEV_MODE=true` and a loopback database. The middleware requires a loopback peer and localhost Host, rejecting tunnel/forwarded-host headers. Run uvicorn with `--host 127.0.0.1 --no-proxy-headers` and Vite with `--host 127.0.0.1`. Never expose this mode through a tunnel.

The 2026-09-28 transaction-consistent snapshot contains 4,223 users, 2,047,103 chats, 212,291 credit transactions and 714 characters. Local database `heart_review` uses port 55438; MinIO uses port 59000. All 3,763 media objects (612,121,549 bytes) were imported from the logical export. Redis uses a fresh namespace rather than replaying expired OTP/session/dispatch state. Local JWT credentials differ from production. Background workers and outbound email are disabled. Model configuration is available for deliberate chat; validation makes no paid model calls.

The local review operation has completed and the original state of all 714 rows has been restored. The restored source selection contains exactly 222 eligible rows: 192 `public` and 30 `unlisted`, all `active` and `approved`. Private, disabled and unreviewed rows are excluded. This is a local selection view, not new moderation approval or permission to publish creators' private content. Production and original backups were not changed. The restore and approved-catalog exports retain the before/after states and batch IDs.

Audit is only in the local database's `local_review` schema and private `/Users/wanglixun/heart/.local-review/production-20260928/audit/`, excluded from Git. `character_visibility` preserves each entire original character row, original visibility/status/review state, snapshot name and batch ID. `spec_status` records the reactivated spec. JSON exports have SHA-256 manifests and a local-database-guarded SQL restore script. Do not include these data files in a PR or deployment bundle.

The private audit directory contains `approved-catalog-20261007.json` and `.csv` for the 222-row result, plus the original 714-row audit and guarded restore SQL. Chinese character content stays unchanged for local review, while international UI options remain EN/JA/KO.

Restart after Docker is running:

```bash
docker start yuoyuo-intl-test-postgres yuoyuo-intl-test-redis yuoyuo-local-review-minio
/Users/wanglixun/heart/.local-review/production-20260928/start-backend.sh
# Separate terminal:
/Users/wanglixun/heart/.local-review/production-20260928/start-frontend.sh
```

Open http://127.0.0.1:55173/ . Catalogue browsing needs no login; existing password accounts remain. Never run automated tests against the restored database. A separate disposable `heart_ui_test` database and Redis DB 3 are used for automated tests; the restored database uses Redis DB 2.

Validation: the catalogue contains 222 eligible profiles; 711 of 712 recorded covers valid. One source cover is empty; all 52 zero-byte media objects are also empty in the raw-volume backup. These source defects are recorded in the local audit rather than silently replaced.

## 2026-10-08 international preview update

Migration `079_google_identities` is applied. Twelve independent EN/JA/KO `launch_*` adaptations were added, giving 234 local preview entries (222 original candidates + 12 editorial drafts). Original sources and chats remain intact. The new rows retain before/after provenance in `local_review.international_adaptations`; see [implementation record](IMPLEMENTATION_20261008.md). The 222-row validation above describes the source selection, not the current total.
