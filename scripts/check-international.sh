#!/usr/bin/env bash
# Local international build verification; never deploys or contacts production.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/generate_locales.py --check
python3 scripts/check_locale_resources.py
VITE_INTERNATIONAL=true VITE_LOCALIZATION=true npm --prefix web run build
VITE_INTERNATIONAL=true VITE_LOCALIZATION=true npm --prefix web test
cd backend
python3.11 -m pytest tests/unit/test_international.py -q
