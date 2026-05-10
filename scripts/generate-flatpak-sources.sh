#!/usr/bin/env bash
# Generates Python module sources for Flatpak. Run when deps change.
# Requires:  python3, pip (venv or user)
# Produces:  data/flatpak/google-libs.json
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GENERATOR="${REPO_ROOT}/.venv/bin/flatpak_pip_generator"

# ── 1. Ensure flatpak_pip_generator is available ──────────────────────────
if [[ ! -x "${GENERATOR}" ]]; then
  echo "Installing flatpak-pip-generator into .venv ..."
  "${REPO_ROOT}/.venv/bin/pip" install --quiet flatpak-pip-generator
fi

if [[ ! -x "${GENERATOR}" ]]; then
  echo "ERROR: flatpak_pip_generator not found after install." >&2
  echo "Try: .venv/bin/pip install flatpak-pip-generator" >&2
  exit 1
fi

# ── 2. Generate sources ────────────────────────────────────────────────────
cd "${REPO_ROOT}/data/flatpak"
"${GENERATOR}" \
  --runtime=org.gnome.Sdk//49 \
  google-api-python-client google-auth-oauthlib google-auth-httplib2 \
  -o google-libs

echo "Generated data/flatpak/google-libs.json"
echo "Next: replace the google-libs sources placeholder in com.weekplan.app.json"
echo "      with: \"sources\": [{\"type\": \"file\", ...}]  from google-libs.json"
