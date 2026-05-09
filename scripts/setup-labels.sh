#!/usr/bin/env bash
# Creates the standard label set. Run once after `gh auth login`.
# Idempotent: existing labels are updated.

set -euo pipefail

declare -A LABELS=(
  ["bug"]="d73a4a:Something isn't working"
  ["enhancement"]="a2eeef:New feature or request"
  ["documentation"]="0075ca:Improvements to docs"
  ["good first issue"]="7057ff:Good for newcomers"
  ["help wanted"]="008672:Extra attention needed"
  ["needs-triage"]="fbca04:Awaiting maintainer review"
  ["needs-info"]="d4c5f9:Awaiting reporter response"
  ["duplicate"]="cccccc:Already reported elsewhere"
  ["wontfix"]="ffffff:Not planned"
  ["design"]="c2e0c6:UI/UX work"
  ["a11y"]="bfd4f2:Accessibility"
  ["performance"]="fef2c0:Speed or resource use"
  ["ci"]="bfdadc:Continuous integration"
  ["dependencies"]="0366d6:Dependency updates"
  ["i18n"]="5319e7:Internationalization"
)

for label in "${!LABELS[@]}"; do
  IFS=':' read -r color desc <<< "${LABELS[$label]}"
  gh label create "$label" --color "$color" --description "$desc" --force
done

echo "✅ Labels configured."
