#!/usr/bin/env bash
# One-time (per clone) installer for the Feature-ID governance git hooks.
# core.hooksPath is a *local* git config, so it is not carried by the repo —
# every fresh clone must run this once. Idempotent.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

chmod +x .githooks/commit-msg .githooks/pre-push
git config core.hooksPath .githooks

conf="$repo_root/.githooks/governance.conf"
# shellcheck disable=SC1090
[ -f "$conf" ] && . "$conf"
PREFIX="${PREFIX:-FT}"; TRAILER="${TRAILER:-Feature-ID}"; DEPLOY_BRANCHES="${DEPLOY_BRANCHES-main}"

echo "✓ core.hooksPath -> .githooks"
echo "✓ commit-msg + pre-push hooks are now active."
echo
echo "  commit-msg : requires a '${TRAILER}: ${PREFIX}-####' trailer on code commits"
if [ -n "${DEPLOY_BRANCHES// /}" ]; then
  echo "  pre-push   : blocks pushes to [${DEPLOY_BRANCHES}] without a valid feature ID"
else
  echo "  pre-push   : tracking mode — no deploy branches gated"
fi
echo
echo "  Rebuild the registry any time you add/change a feature:"
echo "      python scripts/build-registry.py"
