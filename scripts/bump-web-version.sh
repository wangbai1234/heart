#!/usr/bin/env bash
#
# Auto-bump the frontend patch version on frontend commits.
#
# Single source of truth: web/public/version.json ({ "version": "x.y.z" }).
# Wired as a pre-commit hook (see .pre-commit-config.yaml, id: bump-web-version)
# that runs whenever files under web/src/ are staged. It:
#   1. reads the current version,
#   2. increments the patch component (x.y.z -> x.y.(z+1)),
#   3. writes it back and `git add`s the file so it rides along in the commit.
#
# Why this matters: every deploy that ships new frontend code gets a fresh
# version string. That drives both the "关于 → 版本" row in Settings and the
# "最新版本 vX.Y.Z" line in the PWA update prompt, and the bumped version.json
# is what a running client fetches to learn a new version is available.
#
# Idempotent within a single commit (pre-commit runs it once). Portable: uses
# node (already required to build the frontend) instead of GNU/BSD sed flags.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$REPO_ROOT/web/public/version.json"

if [[ ! -f "$VERSION_FILE" ]]; then
  echo "bump-web-version: $VERSION_FILE not found; skipping" >&2
  exit 0
fi

# A deliberate release bump takes precedence over the automatic patch bump.
# Stage it here so `git commit web/src/...` cannot silently turn 2.0.1 into
# 2.0.2 or omit the manually selected version from the commit.
if ! git diff --quiet HEAD -- "$VERSION_FILE"; then
  current_version="$(node -p "require('$VERSION_FILE').version")"
  git add "$VERSION_FILE"
  echo "bump-web-version: preserving manual version -> $current_version"
  exit 0
fi

new_version="$(node -e '
  const fs = require("fs");
  const f = process.argv[1];
  const raw = fs.readFileSync(f, "utf8");
  const m = raw.match(/"version"\s*:\s*"(\d+)\.(\d+)\.(\d+)"/);
  if (!m) { console.error("bump-web-version: could not parse version"); process.exit(1); }
  const next = `${m[1]}.${m[2]}.${Number(m[3]) + 1}`;
  const out = raw.replace(/("version"\s*:\s*")\d+\.\d+\.\d+(")/, `$1${next}$2`);
  fs.writeFileSync(f, out);
  process.stdout.write(next);
' "$VERSION_FILE")"

git add "$VERSION_FILE"
echo "bump-web-version: web version -> $new_version"
