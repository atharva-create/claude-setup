#!/usr/bin/env python3
"""Reconstruct which feature (MR-####) touched which code, straight from git history.

This is the git-tree half of partial-code-update tracking. The registry says *that*
MR-B amends MR-A (see `amends:` in features/README.md); this tool answers the
line-level question the manifest can't: **which feature last touched this file / this
region?** No per-feature bookkeeping is needed — every code commit already carries a
`Feature-ID: MR-####` trailer (enforced by .githooks/commit-msg), so the answer is
already latent in the tree. We just read it out with `git log` / `git blame`.

Modes:
    python scripts/feature-attribution.py --file scripts/build-registry.py
        Chronological list of features that touched a path (commit counts + dates).

    python scripts/feature-attribution.py --blame scripts/_fm.py
    python scripts/feature-attribution.py --blame scripts/_fm.py --lines 40-98
        Current per-line ownership, summarized into contiguous regions
        (e.g. "lines 40-58  MR-0072").

    python scripts/feature-attribution.py --feature MR-0083
        Reverse: every file that feature's commits touched.

Add --json for machine-readable output.

Caveats (reported, never hidden):
  * Forward-only. Commits made before feature-ID governance existed — plus merge/
    revert/`docs:`/`chore:` commits the commit-msg hook exempts — carry no trailer and
    show as `(unattributed)`. Working-tree edits show as `(uncommitted)`.
  * Attribution is by the trailer a human wrote, i.e. the feature the author claimed.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402

# Record / unit separators — safe delimiters that never appear in commit metadata.
RS, US = "\x1e", "\x1f"
ID_RE = _config.TRAILER_RE                      # captures the id from a commit body
UNATTRIBUTED = "(unattributed)"
UNCOMMITTED = "(uncommitted)"
NULL_SHA = "0" * 40


def _git(args: list[str]) -> str:
    """Run a git command from the repo, returning stdout (raises on failure)."""
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True,
    ).stdout


def _feature_of_body(body: str) -> str:
    m = ID_RE.search(body or "")
    return m.group(1) if m else UNATTRIBUTED


def _features_for_shas(shas) -> dict:
    """Map each commit sha → its Feature-ID trailer (or UNATTRIBUTED). One git call."""
    uniq = sorted({s for s in shas if s and s != NULL_SHA})
    out: dict[str, str] = {}
    if not uniq:
        return out
    # `git show -s` accepts many revs at once; RS-separate each commit's [sha, body].
    raw = _git(["show", "-s", f"--format={US}%H{US}%B{RS}", *uniq])
    for chunk in raw.split(RS):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(US)
        if len(parts) < 3:
            continue
        sha, body = parts[1], parts[2]
        out[sha] = _feature_of_body(body)
    return out


# --------------------------------------------------------------------------- --file
def attribute_file(path: str) -> dict:
    """Features that touched `path` over time, chronological, with counts + date span."""
    raw = _git(["log", "--follow", f"--format={US}%H{US}%aI{US}%B{RS}", "--", path])
    commits = []
    for chunk in raw.split(RS):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(US)
        if len(parts) < 4:
            continue
        sha, date, body = parts[1], parts[2], parts[3]
        commits.append((sha, date, _feature_of_body(body)))

    agg: dict[str, dict] = {}
    for sha, date, feat in commits:
        d = date[:10]
        a = agg.setdefault(feat, {"feature": feat, "commits": 0, "first": d, "last": d})
        a["commits"] += 1
        a["first"] = min(a["first"], d)
        a["last"] = max(a["last"], d)
    # Chronological by first touch, then id.
    order = sorted(agg.values(), key=lambda a: (a["first"], a["feature"]))
    return {"path": path, "total_commits": len(commits), "features": order}


# -------------------------------------------------------------------------- --blame
def attribute_blame(path: str, lines: str | None) -> dict:
    """Current per-line ownership of `path`, summarized into contiguous feature regions."""
    cmd = ["blame", "--line-porcelain"]
    start = 1
    if lines:
        m = re.fullmatch(r"(\d+)-(\d+)", lines.strip())
        if not m:
            raise SystemExit(f"--lines must look like L1-L2 (got {lines!r})")
        start = int(m.group(1))
        cmd += ["-L", f"{m.group(1)},{m.group(2)}"]
    cmd += ["--", path]
    raw = _git(cmd)

    # Porcelain: each line group begins "<sha> <orig> <final> [count]"; the actual
    # source line is the one starting with a literal TAB. Collect (lineno, sha).
    per_line: list[tuple[int, str]] = []
    cur_sha = None
    lineno = start
    for ln in raw.split("\n"):
        if re.match(r"^[0-9a-f]{40} ", ln):
            cur_sha = ln.split(" ", 1)[0]
        elif ln.startswith("\t"):
            per_line.append((lineno, cur_sha or NULL_SHA))
            lineno += 1

    feat_of = _features_for_shas([s for _, s in per_line])

    def label(sha: str) -> str:
        if sha == NULL_SHA:
            return UNCOMMITTED
        return feat_of.get(sha, UNATTRIBUTED)

    # Contiguous same-feature regions + per-feature line totals.
    regions = []
    totals: dict[str, int] = {}
    for no, sha in per_line:
        feat = label(sha)
        totals[feat] = totals.get(feat, 0) + 1
        if regions and regions[-1]["feature"] == feat and regions[-1]["end"] == no - 1:
            regions[-1]["end"] = no
        else:
            regions.append({"feature": feat, "start": no, "end": no})
    total = len(per_line)
    summary = sorted(
        ({"feature": f, "lines": n, "pct": round(100 * n / total, 1) if total else 0.0}
         for f, n in totals.items()),
        key=lambda s: (-s["lines"], s["feature"]),
    )
    return {"path": path, "total_lines": total, "regions": regions, "summary": summary}


# ------------------------------------------------------------------------ --feature
def attribute_feature(fid: str) -> dict:
    """Reverse lookup: every file this feature's trailered commits touched."""
    if not _config.ID_RE.match(fid):
        raise SystemExit(f"--feature must be {_config.ID_DISPLAY} (got {fid!r})")
    raw = _git([
        "log", "--all", "-E", f"--grep=^{_config.TRAILER}:[ \\t]*{fid}$",
        f"--format={RS}%H{US}%aI", "--name-only",
    ])
    commits = 0
    files: dict[str, int] = {}
    for chunk in raw.split(RS):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        head, _, rest = chunk.partition("\n")
        if US not in head:
            continue
        commits += 1
        for line in rest.split("\n"):
            line = line.strip()
            if line:
                files[line] = files.get(line, 0) + 1
    ordered = sorted(files.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"feature": fid, "commits": commits,
            "files": [{"path": p, "commits": n} for p, n in ordered]}


# --------------------------------------------------------------------------- output
def _print_file(r: dict) -> None:
    print(f"{r['path']} — {r['total_commits']} commit(s), {len(r['features'])} feature(s)")
    if not r["features"]:
        print("  (no history — untracked or new file)")
        return
    for a in r["features"]:
        span = a["first"] if a["first"] == a["last"] else f"{a['first']} … {a['last']}"
        print(f"  {a['feature']:<16} {a['commits']:>3} commit(s)   {span}")


def _print_blame(r: dict) -> None:
    print(f"{r['path']} — current line ownership ({r['total_lines']} line(s))")
    for reg in r["regions"]:
        span = f"{reg['start']}" if reg["start"] == reg["end"] else f"{reg['start']}-{reg['end']}"
        print(f"  lines {span:<12} {reg['feature']}")
    print("  " + "-" * 40)
    for s in r["summary"]:
        print(f"  {s['feature']:<16} {s['lines']:>4} line(s)  {s['pct']:>5}%")


def _print_feature(r: dict) -> None:
    print(f"{r['feature']} — touched {len(r['files'])} file(s) across {r['commits']} commit(s)")
    for frec in r["files"]:
        print(f"  {frec['commits']:>3}×  {frec['path']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Attribute code to features via the Feature-ID commit trailer.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="path → features that touched it (chronological)")
    g.add_argument("--blame", help="path → current per-line feature ownership")
    g.add_argument("--feature", help="MR-#### → files this feature touched")
    ap.add_argument("--lines", help="with --blame: restrict to a region, e.g. 40-98")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    try:
        if args.file:
            result, printer = attribute_file(args.file), _print_file
        elif args.blame:
            result, printer = attribute_blame(args.blame, args.lines), _print_blame
        else:
            result, printer = attribute_feature(args.feature), _print_feature
    except subprocess.CalledProcessError as e:
        print((e.stderr or str(e)).strip(), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        printer(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
