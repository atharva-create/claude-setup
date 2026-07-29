#!/usr/bin/env python3
"""Resolve which features' SANITY.md a regression agent should run for a change.

Scope rule (see features/README.md): the affected set is
    the changed feature
  + every feature sharing >=1 `module:` with it
  + every feature whose `touches:` intersects the change's touches
  + every feature with `critical: true`
minus `archived` features.

Usage:
    # Primary: scope from the feature being shipped (its branch carries the id).
    python scripts/sanity-scope.py --feature FT-0042

    # Manual override: scope from raw module/touches (no feature id yet).
    python scripts/sanity-scope.py --module CORE --touches auth,payments

Options:
    --json     emit machine-readable JSON instead of a human list
    --paths    also match features declaring `paths:` globs against these changed files
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fm  # noqa: E402


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


# Horizontal tech layers — everything uses them, so a change to one such-tagged
# feature does NOT imply a regression risk to another. Excluded from touches-
# intersection (module + critical still apply). Real *subsystems* (unipile, ma-flow,
# warmup-pool, dead-letter, …) are NOT here and do drive the sweep.
# Generic horizontal layers. Extend with your own stack's cross-cutting tags (e.g.
# "mongo-indexes", "atlas-query") — anything on >30% of features is auto-ignored too.
LAYER_TAGS = {
    "react", "frontend", "backend", "api", "ui", "css",
    "database", "db", "http", "docs", "config", "types", "tests",
}


def broad_tags(features, threshold_frac=0.30):
    """Tags that can't discriminate a blast radius. Union of the fixed LAYER_TAGS
    stop-list and any dataset-specific tag present on more than `threshold_frac` of
    features. Ignored for touches-intersection so the sweep stays affordable even
    with coarse tagging; module + critical still apply."""
    n = len(features) or 1
    freq: dict[str, int] = {}
    for f in features:
        for t in set(_as_list(f.get("touches"))):
            freq[t] = freq.get(t, 0) + 1
    cutoff = max(4, int(threshold_frac * n))
    return LAYER_TAGS | {t for t, c in freq.items() if c > cutoff}


def resolve(features, seed_modules, seed_touches, changed_files=None, ignore_tags=None,
            seed_epics=None, seed_amends=None):
    seed_modules = set(seed_modules)
    ignore_tags = ignore_tags or set()
    seed_touches = set(seed_touches) - ignore_tags
    seed_epics = set(seed_epics or ())
    seed_amends = set(seed_amends or ())
    changed_files = changed_files or []
    affected = {}
    reasons = {}

    def add(f, reason):
        fid = f.get("id")
        if f.get("status") == "archived":
            return
        affected[fid] = f
        reasons.setdefault(fid, []).append(reason)

    for f in features:
        mods = set(_as_list(f.get("module")))
        touches = set(_as_list(f.get("touches"))) - ignore_tags
        if f.get("critical"):
            add(f, "critical")
        if mods & seed_modules:
            add(f, f"module:{','.join(sorted(mods & seed_modules))}")
        if touches & seed_touches:
            add(f, f"touches:{','.join(sorted(touches & seed_touches))}")
        # Phases of one epic are tightly coupled: sweep the siblings and the umbrella.
        if seed_epics and f.get("epic") in seed_epics:
            add(f, f"epic-sibling:{f.get('epic')}")
        if seed_epics and f.get("id") in seed_epics:
            add(f, "epic")
        # A feature the change amends had part of its code edited → regression-check it.
        if seed_amends and f.get("id") in seed_amends:
            add(f, "amended-by-change")
        for pat in _as_list(f.get("paths")):
            if any(fnmatch.fnmatch(cf, pat) for cf in changed_files):
                add(f, "path-match")
    return affected, reasons


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feature", help="feature id of the change being shipped (e.g. FT-0042)")
    ap.add_argument("--module", help="comma-separated module codes (override)")
    ap.add_argument("--touches", help="comma-separated subsystem tags (override)")
    ap.add_argument("--paths", nargs="*", default=None, help="changed file paths")
    ap.add_argument("--broad-threshold", type=float, default=0.30,
                    help="touches tags on more than this fraction of features are ignored")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    features = _fm.load_all()
    by_id = {f.get("id"): f for f in features}
    ignore_tags = broad_tags(features, args.broad_threshold)

    seed_modules, seed_touches, seed_epics, seed_amends = set(), set(), set(), set()
    self_id = None
    if args.feature:
        f = by_id.get(args.feature)
        if not f:
            print(f"unknown feature {args.feature}", file=sys.stderr)
            return 2
        self_id = args.feature
        seed_modules |= set(_as_list(f.get("module")))
        seed_touches |= set(_as_list(f.get("touches")))
        if f.get("epic"):                       # a phase → sweep its siblings + the epic
            seed_epics.add(f.get("epic"))
        if f.get("type") == "epic":             # the epic itself → sweep all its phases
            seed_epics.add(f.get("id"))
        seed_amends |= set(_as_list(f.get("amends")))   # partially-edited predecessors
    if args.module:
        seed_modules |= {m.strip() for m in args.module.split(",") if m.strip()}
    if args.touches:
        seed_touches |= {t.strip() for t in args.touches.split(",") if t.strip()}
    if not seed_modules and not seed_touches and not args.paths:
        print("provide --feature, or --module/--touches", file=sys.stderr)
        return 2

    affected, reasons = resolve(features, seed_modules, seed_touches, args.paths, ignore_tags,
                                seed_epics, seed_amends)
    if self_id and self_id in by_id and by_id[self_id].get("status") != "archived":
        affected.setdefault(self_id, by_id[self_id])
        reasons.setdefault(self_id, []).insert(0, "self")

    items = []
    for fid in sorted(affected):
        f = affected[fid]
        sanity = Path(f["_dir"]) / "SANITY.md"
        items.append({
            "id": fid,
            "title": f.get("title"),
            "module": _as_list(f.get("module")),
            "sanity_md": str(sanity.relative_to(_fm.REPO_ROOT)) if sanity.exists() else None,
            "reasons": reasons[fid],
        })

    effective_touches = sorted(seed_touches - ignore_tags)
    if args.json:
        print(json.dumps({"seed_modules": sorted(seed_modules),
                          "seed_touches": effective_touches,
                          "ignored_broad_tags": sorted(seed_touches & ignore_tags),
                          "affected": items}, indent=2))
        return 0

    print(f"Scope: modules={sorted(seed_modules)} touches={effective_touches}")
    if seed_touches & ignore_tags:
        print(f"  (ignored over-broad tags: {sorted(seed_touches & ignore_tags)})")
    print(f"{len(items)} feature(s) to sanity-check:\n")
    missing = 0
    for it in items:
        mark = it["sanity_md"] or "(NO SANITY.md — write one)"
        if not it["sanity_md"]:
            missing += 1
        print(f"  {it['id']:<9} {mark}")
        print(f"            {it['title']}  [{', '.join(it['reasons'])}]")
    if missing:
        print(f"\n{missing} affected feature(s) lack a SANITY.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
