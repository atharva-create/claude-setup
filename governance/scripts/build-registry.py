#!/usr/bin/env python3
"""Regenerate features/REGISTRY.md from every features/<PREFIX>-*/FEATURE.md front-matter,
and lint the registry for integrity.

Usage:
    python scripts/build-registry.py            # rewrite REGISTRY.md, print lint report
    python scripts/build-registry.py --check    # lint only, DO NOT write (CI mode)

Exit status: non-zero if any HARD error is found (duplicate/malformed id, unknown
enum value, dangling lineage reference), or (in --check mode) if REGISTRY.md is stale.
Soft issues (missing SHAs, non-reciprocal lineage, missing SANITY.md) print as
warnings and do not fail the build.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402
import _fm  # noqa: E402
import _deploy_state  # noqa: E402
from _deploy_state import eff_status, eff_shas  # noqa: E402

# Module allow-list. Empty ⇒ accept any code (no allow-list lint) — see _config.MODULES.
MODULES = set(_config.MODULES)
# `epic` is a pure umbrella feature: it groups a program's phases and never deploys
# itself (the deploy gate excludes it, like `backlog`). Each phase is an ordinary feature
# that points up via `epic: <PREFIX>-####`.
TYPES = {"feature", "bug", "backlog", "epic"}
# Superset across all deploy models; values a given model never produces simply never
# appear (e.g. `shipped-sit` in single-branch mode).
STATUSES = {
    "backlog", "planned", "in-dev", "shipped-sit", "shipped-prod",
    "archived", "blocked",
}
ID_RE = _config.ID_RE
DIR_RE = _config.DIR_RE
HAS_SIT = _config.has_staging()      # render the SIT column only in two-branch mode
DEPLOY_GATED = _config.deploy_gated()  # render deploy SHA columns only when gated

REGISTRY_PATH = _fm.FEATURES_DIR / "REGISTRY.md"


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def build_rows(features: list[dict]):
    return sorted(features, key=lambda f: f.get("id") or "")


def render_registry(features: list[dict], deploy_state: dict, refs_ok: bool) -> str:
    rows = build_rows(features)
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for f in rows:
        by_type[f.get("type", "?")] = by_type.get(f.get("type", "?"), 0) + 1
        if f.get("type") != "epic":                   # epics aren't status-tracked work items
            s = eff_status(f, deploy_state)
            by_status[s] = by_status.get(s, 0) + 1

    out = []
    out.append("# Feature Registry")
    out.append("")
    out.append("> **Generated file — do not hand-edit.** Run `python scripts/build-registry.py`")
    out.append(f"> after adding or changing any `features/{_config.PREFIX}-*/FEATURE.md`. Source of")
    if DEPLOY_GATED:
        cols = "Status / Prod" + (" / SIT" if HAS_SIT else "")
        derived = "`shipped-sit` / `shipped-prod`" if HAS_SIT else "`shipped-prod`"
        refs = (f"`{_config.staging_ref()}` / `{_config.prod_ref()}`" if HAS_SIT
                else f"`{_config.prod_ref()}`")
        out.append(f"> truth is the per-feature front-matter — **except the {cols} columns**,")
        out.append(f"> which are **derived live from git**: a feature is {derived} when its")
        out.append(f"> `{_config.TRAILER}:` commits are on {refs} (see `scripts/_deploy_state.py`).")
        out.append("> The stored `status` is only a pre-deploy lifecycle hint.")
    else:
        out.append("> truth is the per-feature front-matter. This project runs in **tracking** mode")
        out.append("> (no deploy branches), so the Status column reflects the stored `status` field.")
    out.append("")
    out.append(f"**{len(rows)} entries** · "
               + "types — " + ", ".join(f"{k}: {v}" for k, v in sorted(by_type.items()))
               + " · statuses — " + ", ".join(f"{k}: {v}" for k, v in sorted(by_status.items())))
    out.append("")

    # --- Epics rollup: each program umbrella with its phases' status breakdown. -------
    children_by_epic: dict[str, list[dict]] = {}
    for f in rows:
        ep = f.get("epic")
        if ep:
            children_by_epic.setdefault(ep, []).append(f)
    # Derived (honest) status per epic — computed from phases, never the hand-set field.
    epic_derived: dict[str, tuple[str, bool]] = {}
    for f in rows:
        if f.get("type") == "epic":
            statuses = [eff_status(k, deploy_state)
                        for k in children_by_epic.get(f.get("id"), [])]
            epic_derived[f.get("id")] = epic_rollup_status(statuses)

    epics = [f for f in rows if f.get("type") == "epic"]
    if epics:
        out.append("## Epics")
        out.append("")
        out.append("> Programs delivered across multiple phase-features. Each phase is its "
                   f"own shippable `{_config.ID_DISPLAY}`; the epic never deploys. **Overall "
                   "status is derived from the phases** (how far the whole program reached).")
        out.append("")
        for e in epics:
            kids = sorted(children_by_epic.get(e.get("id"), []),
                          key=lambda f: (_phase_key(f.get("phase")), f.get("id") or ""))
            st: dict[str, int] = {}
            for k in kids:
                ks = eff_status(k, deploy_state)
                st[ks] = st.get(ks, 0) + 1
            breakdown = ", ".join(f"{v} {k}" for k, v in sorted(st.items())) or "no phases yet"
            kid_ids = ", ".join(k.get("id", "?") for k in kids) or "—"
            derived, blocked = epic_derived.get(e.get("id"), ("planned", False))
            overall = f"**{derived}**" + (" ⚠ blocked" if blocked else "")
            title = str(e.get("title", "")).replace("|", "\\|")
            rel_dir = Path(e["_dir"]).name
            out.append(f"- **[{e.get('id','?')}]({rel_dir}/FEATURE.md)** {title} — "
                       f"overall: {overall} · {len(kids)} phase(s) ({breakdown})")
            out.append(f"  - phases: {kid_ids}")
        out.append("")

    # Deploy columns depend on the model: a Prod SHA column when the model is gated at
    # all, a SIT SHA column only when a staging branch exists. Tracking mode shows
    # neither (the Status column carries the lifecycle state).
    deploy_headers = (["Prod"] if DEPLOY_GATED else []) + (["SIT"] if HAS_SIT else [])
    headers = ["ID", "Title", "Type", "Module", "Status", "Crit", "Epic",
               *deploy_headers, "PRs", "Supersedes", "Amends"]
    out.append("| " + " | ".join(headers) + " |")
    out.append("|" + "|".join("----" for _ in headers) + "|")
    for f in rows:
        mods = " ".join(_as_list(f.get("module")))
        prs = " ".join(f"#{p}" for p in _as_list(f.get("prs")))
        crit = "★" if f.get("critical") else ""
        sup = f.get("supersedes") or ""
        amends = " ".join(_as_list(f.get("amends")))
        epic = f.get("epic") or ""
        # Epic rows show the derived rollup status (+ blocked marker); leaf rows show the
        # git-derived deploy status (falling back to the stored lifecycle field).
        if f.get("type") == "epic":
            d, blk = epic_derived.get(f.get("id"), (f.get("status", "?"), False))
            status_display = d + (" ⚠" if blk else "")
            sit_disp = prod_disp = ""            # epics deploy nothing
        else:
            status_display = eff_status(f, deploy_state)
            sit_disp, prod_disp = eff_shas(f, deploy_state, refs_ok)
        title = str(f.get("title", "")).replace("|", "\\|")
        rel_dir = Path(f["_dir"]).name
        deploy_cells = ([prod_disp] if DEPLOY_GATED else []) + ([sit_disp] if HAS_SIT else [])
        cells = [f"[{f.get('id','?')}]({rel_dir}/FEATURE.md)", title,
                 f.get("type", "?"), mods, status_display, crit, epic,
                 *deploy_cells, prs, sup, amends]
        out.append("| " + " | ".join(cells) + " |")
    out.append("")
    return "\n".join(out)


def _phase_key(v):
    """Sort phases numerically when phase is an int, else lexically after all ints."""
    return (0, v) if isinstance(v, int) else (1, str(v) if v is not None else "")


def epic_rollup_status(child_statuses):
    """Derive an epic's status from its phases — how far the WHOLE program has *uniformly*
    reached. Returns (status, blocked_flag). Archived phases are ignored. An epic never has
    a hand-set status of record; this is the single source of truth for display."""
    live = [s for s in child_statuses if s != "archived"]
    blocked = any(s == "blocked" for s in live)
    if not live:
        return ("planned", blocked)
    if all(s == "shipped-prod" for s in live):
        return ("shipped-prod", blocked)
    if all(s in ("shipped-sit", "shipped-prod") for s in live):
        return ("shipped-sit", blocked)
    return ("in-dev", blocked)


def lint(features: list[dict], deploy_state: dict, refs_ok: bool) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    ids: dict[str, dict] = {}

    for f in features:
        fid = f.get("id")
        name = Path(f["_dir"]).name
        where = f["_path"]

        if not fid or not ID_RE.match(str(fid)):
            errors.append(f"{where}: missing/malformed id (got {fid!r}); must match {_config.ID_DISPLAY}")
            continue
        if fid in ids:
            errors.append(f"{where}: duplicate id {fid} (also {ids[fid]['_path']})")
        ids[fid] = f

        if not DIR_RE.match(name):
            errors.append(f"{where}: folder name {name!r} must be {_config.ID_DISPLAY}-kebab-slug")
        elif not name.startswith(fid + "-"):
            errors.append(f"{where}: id {fid} does not match folder {name!r}")

        if f.get("type") not in TYPES:
            errors.append(f"{where}: type {f.get('type')!r} not in {sorted(TYPES)}")
        if f.get("status") not in STATUSES:
            errors.append(f"{where}: status {f.get('status')!r} not in {sorted(STATUSES)}")
        if MODULES:                       # empty allow-list ⇒ accept any module code
            for m in _as_list(f.get("module")):
                if m not in MODULES:
                    errors.append(f"{where}: module {m!r} not in {sorted(MODULES)}")

        # Deploy status (shipped-sit/prod) + SHAs are DERIVED from git ancestry
        # (scripts/_deploy_state.py), not stored, so there is no "missing sit_sha" to
        # warn about. Flag only a *governed* leaf whose stored status still claims a
        # deploy state that git contradicts — a leftover hand-set value to clean up.
        if f.get("type") != "epic" and refs_ok:
            ds = deploy_state.get(fid)
            stored = f.get("status")
            if ds and stored in ("shipped-sit", "shipped-prod") and stored != ds["status"]:
                warnings.append(
                    f"{fid}: stored status {stored!r} disagrees with git-derived "
                    f"{ds['status']!r} — deploy status is derived; set a lifecycle value")

    # Lineage integrity (second pass, now that all ids are known).
    for f in features:
        fid = f.get("id")
        if not fid:
            continue
        for field in ("depends_on", "related", "amends", "amended_by"):
            for ref in _as_list(f.get(field)):
                if ref not in ids:
                    errors.append(f"{fid}: {field} references unknown id {ref}")
        sup = f.get("supersedes")
        if sup:
            if sup not in ids:
                errors.append(f"{fid}: supersedes references unknown id {sup}")
            else:
                back = ids[sup].get("superseded_by")
                if back != fid:
                    warnings.append(
                        f"{fid} supersedes {sup}, but {sup}.superseded_by={back!r} "
                        f"(should be {fid}) — update the predecessor")
                if not (Path(ids[sup]["_dir"]) / "SANITY.md").exists():
                    warnings.append(
                        f"{fid} supersedes {sup} but {sup} has no SANITY.md to update")
        sby = f.get("superseded_by")
        if sby and sby not in ids:
            errors.append(f"{fid}: superseded_by references unknown id {sby}")

        # Partial-edit lineage (amends): same SANITY discipline as supersede, but the
        # amended feature stays live and the link is N:M (amended_by is a list).
        for amd in _as_list(f.get("amends")):
            if amd not in ids:
                continue                                   # unknown-id already flagged above
            back = _as_list(ids[amd].get("amended_by"))
            if fid not in back:
                warnings.append(
                    f"{fid} amends {amd}, but {amd}.amended_by={back!r} does not include "
                    f"{fid} — update the predecessor")
            if not (Path(ids[amd]["_dir"]) / "SANITY.md").exists():
                warnings.append(
                    f"{fid} amends {amd} but {amd} has no SANITY.md to update")

    # Epic grouping integrity: `epic:` must point at a real `type: epic` feature; a
    # `phase:` is only meaningful under an epic; an epic with no phases is dangling.
    epic_children: dict[str, list[str]] = {}
    for f in features:
        fid = f.get("id")
        if not fid:
            continue
        ep = f.get("epic")
        if ep:
            if ep not in ids:
                errors.append(f"{fid}: epic references unknown id {ep}")
            elif ids[ep].get("type") != "epic":
                errors.append(
                    f"{fid}: epic {ep} is type={ids[ep].get('type')!r}, must be type: epic")
            else:
                epic_children.setdefault(ep, []).append(fid)
        if f.get("phase") is not None and not ep:
            warnings.append(f"{fid}: has phase but no epic — phase only applies under an epic")
    for f in features:
        if f.get("type") != "epic":
            continue
        fid = f.get("id")
        kids = epic_children.get(fid)
        if not kids:
            warnings.append(f"{fid}: type epic but no feature references it via epic: (no phases yet)")
            continue
        derived, _blocked = epic_rollup_status(
            [eff_status(ids[k], deploy_state) for k in kids])
        if f.get("status") != derived:
            warnings.append(
                f"{fid}: stored status {f.get('status')!r} != derived phase rollup "
                f"{derived!r} — set status: {derived}")

    return errors, warnings


def main() -> int:
    check_only = "--check" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    features = _fm.load_all()
    if not features:
        print(f"no features/{_config.PREFIX}-*/FEATURE.md found", file=sys.stderr)
        return 0

    # Deploy status is read from git reality (the configured deploy branches), not hand-set.
    deploy_state, refs_ok = _deploy_state.derive()
    if DEPLOY_GATED and not refs_ok:
        refs = _config.prod_ref() + (f" and {_config.staging_ref()}" if HAS_SIT else "")
        print(f"NOTE deploy status not derived — {refs} absent (run `git fetch`); "
              "falling back to stored status fields.", file=sys.stderr)

    errors, warnings = lint(features, deploy_state, refs_ok)
    content = render_registry(features, deploy_state, refs_ok)

    # Warnings are enrichment flags — summarize by category so a new one is visible.
    if warnings and not verbose and len(warnings) > 12:
        cats: dict[str, int] = {}
        for w in warnings:
            key = "no prod_sha" if "no prod_sha" in w else \
                  "no sit_sha" if "no sit_sha" in w else \
                  "predecessor has no SANITY.md" if "no SANITY.md" in w else \
                  "non-reciprocal supersede" if "should be" in w else \
                  "non-reciprocal amend" if "does not include" in w else \
                  "phase without epic" if "phase only applies" in w else \
                  "epic without phases" if "no phases yet" in w else \
                  "epic status drift" if "derived phase rollup" in w else "other"
            cats[key] = cats.get(key, 0) + 1
        print(f"{len(warnings)} warnings (enrichment flags) — "
              + " · ".join(f"{k}: {v}" for k, v in sorted(cats.items())))
        print("  run with --verbose to list them all")
    else:
        for w in warnings:
            print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)

    if check_only:
        existing = REGISTRY_PATH.read_text(encoding="utf-8") if REGISTRY_PATH.exists() else ""
        if existing != content:
            print("ERROR REGISTRY.md is stale — run `python scripts/build-registry.py`",
                  file=sys.stderr)
            errors.append("stale-registry")
    else:
        REGISTRY_PATH.write_text(content, encoding="utf-8")
        print(f"wrote {REGISTRY_PATH} ({len(features)} entries)")

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
