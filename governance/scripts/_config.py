"""Central configuration for the Feature-ID governance system — the SINGLE source of
truth for the ID prefix, the deploy/branch model, and the module taxonomy.

Every governance script imports this instead of hard-coding its own regex/branch/module
constants (that duplication was the biggest cost of reusing the original system). The git
hooks read a parallel shell file, ``.githooks/governance.conf`` — keep the two in sync
(the installer writes both from your answers).

Edit the values in the "PROJECT SETTINGS" block once per project (the installer does this
for you), then run ``python scripts/build-registry.py``. Everything under "DERIVED" is
computed and must not be edited.
"""
from __future__ import annotations

import re

# ══════════════════════════════ PROJECT SETTINGS ══════════════════════════════════
# ── Feature-ID grammar ─────────────────────────────────────────────────────────────
# The id is a permanent, semantics-free handle (see features/README.md / the ADR): it
# never encodes module or type, and is never reassigned. Pick a short UPPERCASE prefix
# once and keep it for the project's life.
PREFIX = "FT"              # e.g. FT-0001
ID_WIDTH = 4               # zero-padded digits → FT-0001 … FT-9999
TRAILER = "Feature-ID"     # commit-trailer key that carries the id

# ── Deploy / state model ───────────────────────────────────────────────────────────
#   "single"     — one production branch (PROD_BRANCH). Features reach `shipped-prod`.
#   "two-branch" — a staging branch (STAGING_BRANCH) then production (PROD_BRANCH):
#                  `shipped-sit` (staging) then `shipped-prod` (production).
#   "tracking"   — no deploy branches: registry + commit trailer + sanity sweep only,
#                  with NO deploy gate. Deploy state is never derived from git; the
#                  stored `status` field is shown as-is.
DEPLOY_MODEL = "single"
PROD_BRANCH = "main"
STAGING_BRANCH = "develop"     # only used when DEPLOY_MODEL == "two-branch"

# ── Module taxonomy ────────────────────────────────────────────────────────────────
# Area/subsystem codes a feature may declare in front-matter `module:`. Leave EMPTY to
# accept any code (no allow-list lint). Set your project's codes to get validation and
# stable, distinct board colors.
MODULES: list[str] = []        # e.g. ["CORE", "API", "UI", "INFRA", "DOCS"]

# ══════════════════════════════════ DERIVED ════════════════════════════════════════
# (do not edit — computed from the settings above)
_W = "{%d}" % ID_WIDTH

ID_RE = re.compile(rf"^{PREFIX}-\d{_W}$")                       # exact id
ID_SCAN_RE = re.compile(rf"{PREFIX}-\d{_W}")                    # find ids in free text
DIR_RE = re.compile(rf"^{PREFIX}-\d{_W}-[a-z0-9][a-z0-9-]*$")   # folder name
FEATURE_GLOB = f"{PREFIX}-*/FEATURE.md"                          # glob under features/
ID_DISPLAY = f"{PREFIX}-" + "#" * ID_WIDTH                       # e.g. "FT-####" for messages

# Commit-trailer scan (Python multiline), captures the id.
TRAILER_RE = re.compile(rf"(?m)^{re.escape(TRAILER)}:[ \t]*({PREFIX}-\d{_W})[ \t]*$")
# ERE form handed to `git log --grep` (git uses POSIX ERE, where {n} is a quantifier).
TRAILER_GREP = rf"^{TRAILER}:[ \t]*{PREFIX}-[0-9]{_W}[ \t]*$"


def prod_ref() -> str:
    return f"origin/{PROD_BRANCH}"


def staging_ref() -> str | None:
    return f"origin/{STAGING_BRANCH}" if DEPLOY_MODEL == "two-branch" else None


def has_staging() -> bool:
    return DEPLOY_MODEL == "two-branch"


def deploy_gated() -> bool:
    """True when git ancestry drives deploy status (single / two-branch)."""
    return DEPLOY_MODEL in ("single", "two-branch")
