"""Derive each feature's deploy state (shipped-sit / shipped-prod + the SHAs) from git,
instead of a hand-typed field that goes stale.

`develop` = SIT and `main` = Prod (see CLAUDE.md), so git ancestry *is* the ground truth:
a feature is **shipped-sit** iff one of its `Feature-ID:`-trailered commits is reachable
from `origin/develop`, **shipped-prod** iff reachable from `origin/main`. This mirrors
`build-registry.epic_rollup_status()` — which already derives an epic's status from its
phases rather than trusting a stored field — and reuses the same trailer scan
`feature-attribution.py` relies on. The single source of truth is what actually shipped,
not what someone remembered to type on some branch.

No app surface; stdlib + git only.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402

# Record separator + unit separator: control chars that never appear in commit metadata.
RS, US = "\x1e", "\x1f"
ID_RE = _config.TRAILER_RE            # captures the id from a commit body
GREP = _config.TRAILER_GREP           # ERE handed to `git log --grep`

# Deploy branches → the status each confers. Prod is strongest and wins over staging.
PROD_REF = _config.prod_ref()
SIT_REF = _config.staging_ref()       # None unless DEPLOY_MODEL == "two-branch"


def _git(args: list[str]) -> str:
    """Run git, return stdout (raises CalledProcessError on failure)."""
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True,
    ).stdout


def _ref_exists(ref: str) -> bool:
    try:
        _git(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
        return True
    except subprocess.CalledProcessError:
        return False


def _ids_on(ref: str) -> dict[str, str] | None:
    """Map ``{MR-#### -> newest trailered sha on ref}`` in one git call.

    Returns ``None`` when the ref is absent (bare clone / no fetch) so the caller can
    tell "no ref" apart from "ref present, zero governed features".
    """
    if not _ref_exists(ref):
        return None
    raw = _git(["log", ref, "-E", f"--grep={GREP}", f"--format={RS}%H{US}%B"])
    newest: dict[str, str] = {}
    for chunk in raw.split(RS):
        chunk = chunk.strip("\n")
        if not chunk or US not in chunk:
            continue
        sha, body = chunk.split(US, 1)
        m = ID_RE.search(body)
        if not m:
            continue
        # git log is newest-first, so the first sha seen for an id is its newest commit.
        newest.setdefault(m.group(1), sha.strip())
    return newest


def derive() -> tuple[dict[str, dict], bool]:
    """Compute deploy state for every governed feature from git.

    Returns ``(state, refs_ok)`` where ``state`` maps only the ids that are on a deploy
    branch::

        {"MR-0083": {"status": "shipped-sit", "sit_sha": "<sha>", "prod_sha": None}, ...}

    An id absent from ``state`` is on neither deploy branch — the caller falls back to the
    feature's stored *lifecycle* status (backlog/planned/in-dev/blocked/archived).
    ``refs_ok`` is False only when neither deploy ref exists (fetch first) or when the
    project runs in "tracking" mode (no deploy branches); the caller then falls back to
    the stored fields entirely.
    """
    if not _config.deploy_gated():        # tracking mode — no deploy branches to read
        return {}, False
    prod = _ids_on(PROD_REF)
    sit = _ids_on(SIT_REF) if SIT_REF else None
    refs_ok = prod is not None or sit is not None
    prod = prod or {}
    sit = sit or {}

    state: dict[str, dict] = {}
    for fid in set(prod) | set(sit):
        status = "shipped-prod" if fid in prod else "shipped-sit"
        state[fid] = {
            "status": status,
            "sit_sha": sit.get(fid),
            "prod_sha": prod.get(fid),
        }
    return state, refs_ok


# --- shared display helpers (used by both build-registry.py and build-board.py) --------
def eff_status(f: dict, state: dict) -> str:
    """Effective status of a LEAF feature: the git-derived deploy state when the feature
    is on a deploy branch, else its stored *lifecycle* field (backlog/planned/in-dev/…)."""
    ds = state.get(f.get("id"))
    if ds and ds.get("status"):
        return ds["status"]
    return f.get("status", "?")


def eff_shas(f: dict, state: dict, refs_ok: bool) -> tuple[str, str]:
    """(sit_sha, prod_sha) for display. Derived from git when refs are available; a feature
    not on a deploy branch shows blank SHAs (genuinely unshipped). Only when neither origin
    ref exists (bare clone) do we fall back to the stored fields."""
    ds = state.get(f.get("id"))
    if ds:
        return (ds.get("sit_sha") or "", ds.get("prod_sha") or "")
    if not refs_ok:
        return (f.get("sit_sha") or "", f.get("prod_sha") or "")
    return ("", "")
