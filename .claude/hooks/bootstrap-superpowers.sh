#!/usr/bin/env bash
# SessionStart hook: bootstrap the vendored Superpowers plugin.
#
# Writes an absolute-path marketplace entry into .claude/settings.local.json
# on first run, then exits silently on every subsequent session.
#
# Why absolute path: Claude Code Issue #23978 — extraKnownMarketplaces with
# `directory` source doesn't resolve relative paths; they are passed through
# literally and break at runtime.

set -euo pipefail

# Hook payload arrives on stdin; we don't consume it.
cat > /dev/null 2>&1 || true

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
PLUGIN_DIR="$PROJECT_DIR/plugins/superpowers"
LOCAL_SETTINGS="$PROJECT_DIR/.claude/settings.local.json"

# Plugin not vendored here — nothing to bootstrap.
[ -d "$PLUGIN_DIR/.claude-plugin" ] || exit 0

# Fast idempotency check: already bootstrapped with the correct absolute path.
if [ -f "$LOCAL_SETTINGS" ] && grep -qF "\"path\": \"$PLUGIN_DIR\"" "$LOCAL_SETTINGS" 2>/dev/null; then
  exit 0
fi

python3 - "$LOCAL_SETTINGS" "$PLUGIN_DIR" <<'PY'
import json, os, sys

settings_path, plugin_dir = sys.argv[1], sys.argv[2]

try:
    with open(settings_path) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data = {}

data.setdefault("extraKnownMarketplaces", {})["superpowers-dev"] = {
    "source": {"source": "directory", "path": plugin_dir}
}
data.setdefault("enabledPlugins", {})["superpowers@superpowers-dev"] = True

os.makedirs(os.path.dirname(settings_path), exist_ok=True)
tmp = settings_path + ".tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, settings_path)
PY

echo "Superpowers bootstrapped — restart this session (or open a new one) to activate."
exit 0
