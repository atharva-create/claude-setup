#!/usr/bin/env bash
# Stop hook: Enforce browser verification via Chrome DevTools MCP before Claude can complete.
# If code files were changed but no verification sentinel exists, block the stop.

set -euo pipefail

# Read stdin (hook payload) — required but not used
cat > /dev/null

CACHE_DIR="$HOME/.cache"
SENTINEL_PREFIX=".claude-verified-"
SENTINEL_MAX_AGE=300  # 5 minutes in seconds

# Not a git repo — nothing to enforce
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  exit 0
fi

# Detect code file changes (staged + unstaged)
CODE_EXTENSIONS="ts|tsx|js|jsx|py|rb|go|rs|java|c|cpp|h|hpp|css|scss|html|svelte|vue|swift|kt|sh|sql|php"

changed_files=""
changed_files+=$(git diff --name-only 2>/dev/null || true)
changed_files+=$'\n'
changed_files+=$(git diff --cached --name-only 2>/dev/null || true)

# Filter to code files only
code_changes=$(echo "$changed_files" | grep -E "\.($CODE_EXTENSIONS)$" | head -1 || true)

if [ -z "$code_changes" ]; then
  exit 0  # No code changes, allow stop
fi

# Check for fresh sentinel file
now=$(date +%s)
found_fresh=false
for f in "$CACHE_DIR"/${SENTINEL_PREFIX}*; do
  [ -e "$f" ] || continue
  # Extract timestamp from filename
  ts="${f##*-}"
  if [ -n "$ts" ] && [ "$((now - ts))" -lt "$SENTINEL_MAX_AGE" ]; then
    found_fresh=true
    rm -f "$f" 2>/dev/null || true  # Clean up used sentinel
    break
  fi
done

if [ "$found_fresh" = true ]; then
  exit 0  # Verified, allow stop
fi

# Block: code changed but not verified
cat <<'BLOCK_JSON'
{"decision":"block","reason":"You changed code files but did not verify them in the browser using Chrome DevTools MCP. Before completing:\n1. Navigate to the relevant page: mcp__chrome-devtools__navigate_page\n2. Take a screenshot: mcp__chrome-devtools__take_screenshot\n3. Check console for errors: mcp__chrome-devtools__list_console_messages\n4. Test the user flow (click, fill, etc.)\n5. After verification passes, run: touch $HOME/.cache/.claude-verified-$(date +%s)"}
BLOCK_JSON
