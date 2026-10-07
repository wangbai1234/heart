# Local production-snapshot character review

`LOCAL_CHARACTER_REVIEW=true` is a local-only catalogue review mode, default off. It requires development/test environment, `HEART_DEV_MODE=true` and a loopback database. The middleware requires a loopback peer and localhost Host, rejecting tunnel/forwarded-host headers. Run uvicorn with `--host 127.0.0.1 --no-proxy-headers` and Vite with `--host 127.0.0.1`. Never expose this mode through a tunnel.

The 2026-09-28 transaction-consistent snapshot contains 4,223 users, 2,047,103 chats, 212,291 credit transactions and 714 characters. Local database `heart_review` uses port 55438; MinIO uses port 59000. All 3,763 media objects (612,121,549 bytes) were imported from the logical export. Redis uses a fresh namespace rather than replaying expired OTP/session/dispatch state. Local JWT credentials differ from production. Background workers and outbound email are disabled. Model configuration is available for deliberate chat; validation makes no paid model calls.

All 714 local character rows are `public/active/approved` for selection only, including formerly private, unlisted, disabled and unreviewed characters. This is not moderation approval or permission to publish creators' private content on the real service. Production and original backups were not changed. Two built-in characters load file specs; one other disabled-only latest spec was reactivated with its original status recorded.

Audit is only in the local database's `local_review` schema and private `/Users/wanglixun/heart/.local-review/production-20260928/audit/`, excluded from Git. `character_visibility` preserves each entire original character row, original visibility/status/review state, snapshot name and batch ID. `spec_status` records the reactivated spec. JSON exports have SHA-256 manifests and a local-database-guarded SQL restore script. Do not include these data files in a PR or deployment bundle.

Fill `selected` and `selection_note` in `character-selection.csv`, retaining `character_id` as stable identity. Rows include original state and local URLs. Catalogue cards also display original visibility/status/ID; search accepts IDs. Chinese character content stays unchanged for local review, while international UI options remain EN/JA/KO.

Restart after Docker is running:

```bash
docker start yuoyuo-intl-test-postgres yuoyuo-intl-test-redis yuoyuo-local-review-minio
/Users/wanglixun/heart/.local-review/production-20260928/start-backend.sh
# Separate terminal:
/Users/wanglixun/heart/.local-review/production-20260928/start-frontend.sh
```

Open http://127.0.0.1:55173/ . Catalogue browsing needs no login; existing password accounts remain. Never run automated tests against the restored database. The disposable test database is removed after restore validation.

Validation: 714 profiles readable, 711 of 712 recorded covers valid. One source cover is empty; all 52 zero-byte media objects are also empty in the raw-volume backup. These source defects are recorded in the local audit rather than silently replaced. Canonical CI: 1,980 tests passed, 34 skipped, 57 frontend tests, mypy clean.
