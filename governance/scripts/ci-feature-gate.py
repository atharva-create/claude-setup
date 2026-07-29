#!/usr/bin/env python3
"""CI Prod gate: a PR into `main` must carry a valid feature ID.

Checks (fails the PR on any):
  1. At least one MR-#### appears in the head branch, PR title, or PR body, whose
     features/MR-####/FEATURE.md exists and is not type:backlog / status:archived.
  2. For each such feature that `supersedes: MR-X`, the PR diff must also modify
     features/MR-X/SANITY.md (superseding a feature keeps its sanity doc current).

Changed files are read from stdin (one path per line).

Usage (see .github/workflows/feature-id-gate.yml):
    git diff --name-only "$BASE_SHA...HEAD" \\
      | python scripts/ci-feature-gate.py --head-ref "$HEAD" --title "$T" --body "$B"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402
import _fm  # noqa: E402

ID_RE = _config.ID_SCAN_RE


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head-ref", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--body", default="")
    args = ap.parse_args()

    changed = {line.strip() for line in sys.stdin if line.strip()}
    haystack = " ".join([args.head_ref, args.title, args.body])
    candidates = sorted(set(ID_RE.findall(haystack)))

    features = {f.get("id"): f for f in _fm.load_all()}
    errors: list[str] = []

    valid = []
    for cid in candidates:
        f = features.get(cid)
        if not f:
            print(f"note: {cid} referenced but no features/{cid}-*/ folder")
            continue
        # backlog ideas, archived work, and epic umbrellas are not deploy targets —
        # a real PR must name the phase feature that actually ships.
        if f.get("type") in ("backlog", "epic") or f.get("status") == "archived":
            print(f"note: {cid} is type={f.get('type')} status={f.get('status')} — not a deploy target")
            continue
        valid.append(f)

    if not valid:
        errors.append(
            f"no valid feature ID on this PR. Put {_config.ID_DISPLAY} in the branch name, "
            f"PR title, or body, and ensure features/{_config.ID_DISPLAY}/FEATURE.md exists "
            f"(non-backlog, non-archived). Candidates seen: {candidates or '<none>'}")

    for f in valid:
        # Both full replacement (supersedes) and partial edit (amends) change a
        # predecessor's behavior, so each named predecessor's SANITY.md must be updated
        # in this same PR. supersedes is 1:1, amends is N:M — treat both as a list.
        rel_of = {}
        for pid in _as_list(f.get("supersedes")):
            rel_of[pid] = "supersedes"
        for pid in _as_list(f.get("amends")):
            rel_of.setdefault(pid, "amends")
        for pid, rel in rel_of.items():
            expected = f"features/{pid}-"
            touched = any(c.startswith(expected) and c.endswith("SANITY.md") for c in changed)
            if not touched:
                errors.append(
                    f"{f.get('id')} {rel} {pid} but this PR does not modify "
                    f"{pid}'s SANITY.md — update the predecessor's sanity checklist.")

    if errors:
        print("\n✗ Feature-ID gate FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("✓ Feature-ID gate passed: " + ", ".join(f.get("id") for f in valid))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
