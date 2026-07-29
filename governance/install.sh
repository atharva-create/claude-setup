#!/usr/bin/env bash
# Install the Feature-ID governance module into the current git repository.
#
# Materializes the generalized module into the repo's final locations (scripts/,
# .githooks/, features/, docs/adr/, and — for gated deploy models — .github/workflows/),
# renders the config from your answers, installs the git hooks, and appends the rules
# section to CLAUDE.md. Idempotent-ish: it will not clobber an existing scripts/_config.py
# or an already-present CLAUDE.md governance section.
#
# Usage (all optional — sensible defaults shown):
#   PREFIX=FT DEPLOY_MODEL=single PROD_BRANCH=main STAGING_BRANCH=develop \
#   MODULES="CORE,API,UI" TRAILER=Feature-ID  bash governance/install.sh
#
#   DEPLOY_MODEL ∈ single | two-branch | tracking
set -euo pipefail

# ── resolve locations ──────────────────────────────────────────────────────────────
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel 2>/dev/null || git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "${ROOT:-}" ]; then
  echo "✗ not inside a git repository — run 'git init' first." >&2
  exit 1
fi

# ── settings (env-overridable) ──────────────────────────────────────────────────────
PREFIX="${PREFIX:-FT}"
ID_WIDTH="${ID_WIDTH:-4}"
TRAILER="${TRAILER:-Feature-ID}"
DEPLOY_MODEL="${DEPLOY_MODEL:-single}"
PROD_BRANCH="${PROD_BRANCH:-main}"
STAGING_BRANCH="${STAGING_BRANCH:-develop}"
MODULES="${MODULES:-}"                 # comma-separated, e.g. "CORE,API,UI"

case "$DEPLOY_MODEL" in
  single|two-branch|tracking) ;;
  *) echo "✗ DEPLOY_MODEL must be single|two-branch|tracking (got '$DEPLOY_MODEL')" >&2; exit 1 ;;
esac

# deploy branches the pre-push hook gates
case "$DEPLOY_MODEL" in
  single)     DEPLOY_BRANCHES="$PROD_BRANCH" ;;
  two-branch) DEPLOY_BRANCHES="$STAGING_BRANCH $PROD_BRANCH" ;;
  tracking)   DEPLOY_BRANCHES="" ;;
esac

# python list literal from the comma list, e.g. CORE,API → ["CORE", "API"]
modules_py="[]"
if [ -n "$MODULES" ]; then
  modules_py="["
  IFS=',' read -ra _m <<< "$MODULES"
  for i in "${!_m[@]}"; do
    tok="$(echo "${_m[$i]}" | tr -d '[:space:]')"
    [ -z "$tok" ] && continue
    [ "$modules_py" != "[" ] && modules_py+=", "
    modules_py+="\"$tok\""
  done
  modules_py+="]"
fi

# ── helpers ─────────────────────────────────────────────────────────────────────────
sed_inplace() { local expr="$1" file="$2" tmp; tmp="$(mktemp)"; sed "$expr" "$file" > "$tmp" && mv "$tmp" "$file"; }
render() { # replace {{TOKENS}} in a file
  local f="$1"
  sed_inplace "s/{{PREFIX}}/${PREFIX}/g; s/{{TRAILER}}/${TRAILER}/g; s/{{PROD_BRANCH}}/${PROD_BRANCH}/g; s/{{ADR_FILE}}/${ADR_FILE}/g" "$f"
}

echo "→ installing Feature-ID governance into $ROOT"
echo "  prefix=$PREFIX  model=$DEPLOY_MODEL  prod=$PROD_BRANCH  staging=$STAGING_BRANCH  modules=${MODULES:-<any>}"

# ── 1. scripts/ ─────────────────────────────────────────────────────────────────────
mkdir -p "$ROOT/scripts"
for f in "$HERE"/scripts/*.py; do
  base="$(basename "$f")"
  if [ "$base" = "_config.py" ] && [ -f "$ROOT/scripts/_config.py" ]; then
    echo "  · scripts/_config.py exists — keeping your settings"
    continue
  fi
  cp "$f" "$ROOT/scripts/$base"
done
# render _config.py settings (only if freshly copied)
CFG="$ROOT/scripts/_config.py"
if grep -q 'PROJECT SETTINGS' "$CFG" 2>/dev/null && ! grep -q "already-configured-marker" "$CFG"; then
  sed_inplace "s/^PREFIX = .*/PREFIX = \"${PREFIX}\"/" "$CFG"
  sed_inplace "s/^ID_WIDTH = .*/ID_WIDTH = ${ID_WIDTH}/" "$CFG"
  sed_inplace "s/^TRAILER = .*/TRAILER = \"${TRAILER}\"/" "$CFG"
  sed_inplace "s/^DEPLOY_MODEL = .*/DEPLOY_MODEL = \"${DEPLOY_MODEL}\"/" "$CFG"
  sed_inplace "s/^PROD_BRANCH = .*/PROD_BRANCH = \"${PROD_BRANCH}\"/" "$CFG"
  sed_inplace "s/^STAGING_BRANCH = .*/STAGING_BRANCH = \"${STAGING_BRANCH}\"/" "$CFG"
  sed_inplace "s|^MODULES: list\[str\] = .*|MODULES: list[str] = ${modules_py}|" "$CFG"
fi

# ── 2. .githooks/ ───────────────────────────────────────────────────────────────────
mkdir -p "$ROOT/.githooks"
cp "$HERE/githooks/commit-msg" "$ROOT/.githooks/commit-msg"
cp "$HERE/githooks/pre-push" "$ROOT/.githooks/pre-push"
cp "$HERE/githooks/setup-feature-governance.sh" "$ROOT/scripts/setup-feature-governance.sh"
# render governance.conf (do not clobber an existing one)
if [ ! -f "$ROOT/.githooks/governance.conf" ]; then
  cp "$HERE/githooks/governance.conf" "$ROOT/.githooks/governance.conf"
  GC="$ROOT/.githooks/governance.conf"
  sed_inplace "s/^PREFIX=.*/PREFIX=\"${PREFIX}\"/" "$GC"
  sed_inplace "s/^ID_WIDTH=.*/ID_WIDTH=\"${ID_WIDTH}\"/" "$GC"
  sed_inplace "s/^TRAILER=.*/TRAILER=\"${TRAILER}\"/" "$GC"
  sed_inplace "s/^DEPLOY_BRANCHES=.*/DEPLOY_BRANCHES=\"${DEPLOY_BRANCHES}\"/" "$GC"
fi
chmod +x "$ROOT/.githooks/commit-msg" "$ROOT/.githooks/pre-push" "$ROOT/scripts/setup-feature-governance.sh"

# ── 3. docs/adr/ (pick the next ADR number) ─────────────────────────────────────────
mkdir -p "$ROOT/docs/adr"
next=1
for f in "$ROOT"/docs/adr/[0-9][0-9][0-9][0-9]-*.md; do
  [ -e "$f" ] || continue
  n=$(basename "$f" | cut -c1-4 | sed 's/^0*//'); n=${n:-0}
  [ "$n" -ge "$next" ] && next=$((n+1))
done
ADR_FILE="$(printf '%04d-feature-id-governance.md' "$next")"
cp "$HERE/templates/adr-feature-id-governance.md" "$ROOT/docs/adr/$ADR_FILE"
render "$ROOT/docs/adr/$ADR_FILE"

# ── 4. features/ (spec + scaffolds) ─────────────────────────────────────────────────
mkdir -p "$ROOT/features/.templates"
cp "$HERE/templates/features-README.md" "$ROOT/features/README.md"; render "$ROOT/features/README.md"
cp "$HERE/templates/FEATURE.md.template" "$ROOT/features/.templates/FEATURE.md"
cp "$HERE/templates/SANITY.md.template" "$ROOT/features/.templates/SANITY.md"
sed_inplace "s/{{PREFIX}}/${PREFIX}/g" "$ROOT/features/.templates/FEATURE.md"
sed_inplace "s/{{PREFIX}}/${PREFIX}/g" "$ROOT/features/.templates/SANITY.md"

# ── 5. CI (gated models only) ───────────────────────────────────────────────────────
if [ "$DEPLOY_MODEL" != "tracking" ]; then
  mkdir -p "$ROOT/.github/workflows"
  WF="$ROOT/.github/workflows/feature-id-gate.yml"
  cp "$HERE/workflows/feature-id-gate.yml" "$WF"
  sed_inplace "/^# TEMPLATE —/,/^#   tracking/d" "$WF"   # drop the install-time note
  if [ "$DEPLOY_MODEL" = "two-branch" ]; then
    fetch="'+refs/heads/${STAGING_BRANCH}:refs/remotes/origin/${STAGING_BRANCH}' '+refs/heads/${PROD_BRANCH}:refs/remotes/origin/${PROD_BRANCH}'"
  else
    fetch="'+refs/heads/${PROD_BRANCH}:refs/remotes/origin/${PROD_BRANCH}'"
  fi
  sed_inplace "s/__PROD_BRANCH__/${PROD_BRANCH}/g" "$WF"
  sed_inplace "s|__FETCH_REFS__|${fetch}|g" "$WF"
fi

# ── 6. CLAUDE.md rules section ───────────────────────────────────────────────────────
tmpsec="$(mktemp)"; cp "$HERE/templates/CLAUDE-governance-section.md" "$tmpsec"; render "$tmpsec"
if [ -f "$ROOT/CLAUDE.md" ]; then
  if grep -q "Feature-ID Governance (MANDATORY)" "$ROOT/CLAUDE.md"; then
    echo "  · CLAUDE.md already has the governance section — leaving it"
  else
    { echo; echo; cat "$tmpsec"; } >> "$ROOT/CLAUDE.md"
    echo "  · appended governance section to CLAUDE.md"
  fi
else
  cp "$tmpsec" "$ROOT/CLAUDE.md"
  echo "  · created CLAUDE.md with the governance section"
fi
rm -f "$tmpsec"

# ── 7. .gitignore (board.html is regenerated on demand) ─────────────────────────────
touch "$ROOT/.gitignore"
grep -qxF "features/board.html" "$ROOT/.gitignore" || echo "features/board.html" >> "$ROOT/.gitignore"

# ── 8. activate hooks + first registry ──────────────────────────────────────────────
( cd "$ROOT" && bash scripts/setup-feature-governance.sh )
( cd "$ROOT" && python3 scripts/build-registry.py >/dev/null 2>&1 || true )

echo
echo "✓ Feature-ID governance installed."
echo "  Next:"
echo "    1. Create your first feature:  cp -r features/.templates features/${PREFIX}-0001-my-thing (then edit FEATURE.md/SANITY.md)"
echo "    2. Commit with a trailer:      git commit -m 'feat: ...' -m '${TRAILER}: ${PREFIX}-0001'"
echo "    3. Regenerate the index:       python scripts/build-registry.py"
if [ "$DEPLOY_MODEL" != "tracking" ]; then
  echo "    4. Make the CI check required (GitHub): see docs/adr/${ADR_FILE} for the gh api command"
fi
