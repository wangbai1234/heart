#!/usr/bin/env bash
# Local international build verification; never deploys or contacts production.
set -euo pipefail
cd "$(dirname "$0")/.."
VITE_INTERNATIONAL=true npm --prefix web run build
npm --prefix web test
cd backend
python3.11 -m pytest tests/unit/test_international.py -q
