#!/usr/bin/env python3
"""Generate features/board.html — a self-contained, Jira/Linear-style board view of the
feature registry, from every features/<PREFIX>-*/FEATURE.md (+ SANITY.md).

Usage:
    python scripts/build-board.py            # write features/board.html
    python scripts/build-board.py --check    # do NOT write; exit non-zero if stale (CI mode)

The output is a single HTML file with all feature data embedded as JSON plus inlined
CSS/JS — zero external requests, double-click to open in any browser. Mirrors the
build-registry.py idiom (stdlib-only, reuses scripts/_fm.py) so it runs anywhere.
"""
from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _fm  # noqa: E402
import _config  # noqa: E402
import _deploy_state  # noqa: E402
from _deploy_state import eff_status, eff_shas  # noqa: E402

# Per-module board colors, assigned BY INDEX from these palettes (cycled if a project
# declares more modules than palette entries). Two sets keep the light/dark aesthetic —
# reused verbatim from the original hand-tuned indigo/teal/blue/pink/orange/violet/green.
MODULE_PALETTE_LIGHT = ["#6366f1", "#0d9488", "#2563eb", "#db2777", "#ea580c", "#7c3aed", "#059669"]
MODULE_PALETTE_DARK = ["#818cf8", "#2dd4bf", "#60a5fa", "#f472b6", "#fb923c", "#a78bfa", "#34d399"]
TYPES = ["epic", "feature", "bug", "backlog"]
STATUSES = [
    "backlog", "planned", "in-dev", "blocked",
    "shipped-sit", "shipped-prod", "archived",
]

BOARD_PATH = _fm.FEATURES_DIR / "board.html"


def _as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def epic_rollup_status(child_statuses):
    """Derive an epic's status from its phases (mirror of build-registry.epic_rollup_status).
    Returns (status, blocked_flag); archived phases ignored."""
    live = [s for s in child_statuses if s != "archived"]
    blocked = any(s == "blocked" for s in live)
    if not live:
        return ("planned", blocked)
    if all(s == "shipped-prod" for s in live):
        return ("shipped-prod", blocked)
    if all(s in ("shipped-sit", "shipped-prod") for s in live):
        return ("shipped-sit", blocked)
    return ("in-dev", blocked)


def github_base() -> str | None:
    """Best-effort https://github.com/org/repo from the origin remote. Fail-soft."""
    try:
        url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=str(_fm.REPO_ROOT), stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return None
    if not url:
        return None
    if url.startswith("git@"):                       # git@github.com:org/repo.git
        host, _, path = url[4:].partition(":")
        url = f"https://{host}/{path}"
    elif url.startswith("ssh://"):                    # ssh://git@github.com/org/repo.git
        url = "https://" + url.split("://", 1)[1].split("@")[-1]
    if url.endswith(".git"):
        url = url[:-4]
    return url if url.startswith("http") else None


def _body_from(text: str) -> str:
    """FEATURE.md content from the first `## ` heading onward (drops the duplicated
    H1 title + `<PREFIX>-… · type · MOD · **status**` subtitle we re-render from metadata)."""
    _, _, after = text.partition("\n---")          # skip front-matter block
    after = after.split("\n---", 1)[-1] if after.startswith("\n") else after
    idx = after.find("\n## ")
    return (after[idx + 1:] if idx != -1 else after).strip()


def _sanity_from(text: str) -> str:
    """SANITY.md content with the leading `# ` title line stripped."""
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def build_records(features: list[dict]) -> list[dict]:
    # Deploy status + SHAs come from git reality (develop = SIT, main = Prod), not the
    # stored field — see scripts/_deploy_state.py. Same source of truth as the registry.
    deploy_state, refs_ok = _deploy_state.derive()

    # Phase statuses per epic use the DERIVED leaf status, so an epic's card/drawer status
    # is the honest rollup of what actually shipped.
    children_by_epic: dict[str, list[str]] = {}
    for f in features:
        ep = f.get("epic")
        if ep:
            children_by_epic.setdefault(ep, []).append(eff_status(f, deploy_state))

    records = []
    for f in sorted(features, key=lambda x: x.get("id") or ""):
        d = Path(f["_dir"])
        feature_md = Path(f["_path"])
        sanity_md = d / "SANITY.md"

        status = eff_status(f, deploy_state)
        sit_sha, prod_sha = eff_shas(f, deploy_state, refs_ok)
        epic_blocked = False
        if f.get("type") == "epic":
            status, epic_blocked = epic_rollup_status(children_by_epic.get(f.get("id"), []))

        body = _body_from(feature_md.read_text(encoding="utf-8"))
        sanity = _sanity_from(sanity_md.read_text(encoding="utf-8")) if sanity_md.exists() else None

        extra = []
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.name not in ("FEATURE.md", "SANITY.md"):
                extra.append({"name": str(p.relative_to(d)), "path": str(p)})

        records.append({
            "id": f.get("id"),
            "title": f.get("title", ""),
            "type": f.get("type", "?"),
            "status": status,
            "epicBlocked": epic_blocked,
            "module": _as_list(f.get("module")),
            "critical": bool(f.get("critical")),
            "depends_on": _as_list(f.get("depends_on")),
            "touches": _as_list(f.get("touches")),
            "supersedes": f.get("supersedes"),
            "superseded_by": f.get("superseded_by"),
            "amends": _as_list(f.get("amends")),
            "amended_by": _as_list(f.get("amended_by")),
            "related": _as_list(f.get("related")),
            "epic": f.get("epic"),
            "phase": f.get("phase"),
            "branch": f.get("branch"),
            "prs": _as_list(f.get("prs")),
            "sit_sha": sit_sha or None,
            "prod_sha": prod_sha or None,
            "verification": f.get("verification", "untested"),
            "verified_at": f.get("verified_at"),
            "created": f.get("created"),
            "links": f.get("links") if isinstance(f.get("links"), dict) else {},
            "body": body,
            "sanity": sanity,
            "hasSanity": sanity is not None,
            "extraFiles": extra,
            "dirName": d.name,
            "dirPath": str(d),
            "featurePath": str(feature_md),
            "sanityPath": str(sanity_md) if sanity_md.exists() else None,
        })
    return records


# --- referenced-doc collection (for the in-board Doc Reader) ----------------------------
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
# Text extensions we render in the reader (markdown as prose, the rest as a code view).
TEXT_EXTS = {
    ".md", ".markdown", ".py", ".yml", ".yaml", ".json", ".sh", ".txt",
    ".toml", ".ini", ".cfg", ".env", ".js", ".ts", ".tsx", ".html", ".css", ".sql",
}
MD_EXTS = {".md", ".markdown"}
MAX_DOC_BYTES = 600_000   # skip absurdly large / binary blobs
MAX_DEPTH = 2             # how far to follow doc→doc links


def _repo_rel(abs_path: Path) -> str | None:
    """Repo-relative posix key, or None if the path is outside the repo."""
    try:
        return abs_path.resolve().relative_to(_fm.REPO_ROOT).as_posix()
    except Exception:
        return None


def _resolve_link(raw: str, base_dir: Path):
    """(repo_rel_key, abs_path) for an in-repo link target, else None (external/anchor/outside)."""
    raw = raw.strip().split("#", 1)[0].strip()
    if not raw or raw.startswith(("http://", "https://", "mailto:", "//")):
        return None
    p = Path(raw)
    abs_p = (p if p.is_absolute() else (base_dir / p)).resolve()
    key = _repo_rel(abs_p)
    return (key, abs_p) if key is not None else None


def collect_docs(features: list[dict]) -> dict:
    """Embed every markdown/text file the features reference (directly + up to MAX_DEPTH of
    doc→doc links), so the board can render them in-app instead of opening raw file://."""
    seeds: list[tuple[str, Path]] = []
    for f in features:
        d = Path(f["_dir"])
        links = f.get("links")
        if isinstance(links, dict):
            for v in links.values():                       # links-map values are repo-root-relative
                r = _resolve_link(str(v), _fm.REPO_ROOT)
                if r:
                    seeds.append(r)
        for fname in ("FEATURE.md", "SANITY.md"):          # body references are feature-dir-relative
            fp = d / fname
            if fp.exists():
                for m in MD_LINK_RE.findall(fp.read_text(encoding="utf-8", errors="replace")):
                    r = _resolve_link(m, d)
                    if r:
                        seeds.append(r)

    docs: dict = {}
    seen: set = set()
    queue = deque((k, a, 0) for (k, a) in seeds)
    while queue:
        key, abs_p, depth = queue.popleft()
        if key in seen:
            continue
        seen.add(key)
        ext = abs_p.suffix.lower()
        if not abs_p.exists() or not abs_p.is_file():
            docs[key] = {"path": key, "abs": str(abs_p), "exists": False, "kind": "missing"}
            continue
        if ext not in TEXT_EXTS:
            docs[key] = {"path": key, "abs": str(abs_p), "exists": True, "kind": "binary"}
            continue
        try:
            data = abs_p.read_bytes()
            if len(data) > MAX_DOC_BYTES or b"\x00" in data[:4096]:
                docs[key] = {"path": key, "abs": str(abs_p), "exists": True, "kind": "binary"}
                continue
            content = data.decode("utf-8", errors="replace")
        except Exception:
            docs[key] = {"path": key, "abs": str(abs_p), "exists": True, "kind": "binary"}
            continue
        is_md = ext in MD_EXTS
        docs[key] = {
            "path": key, "abs": str(abs_p), "exists": True,
            "kind": "md" if is_md else "code",
            "lang": ext.lstrip("."), "content": content,
        }
        if is_md and depth < MAX_DEPTH:                     # follow one more level of doc→doc links
            base = abs_p.parent
            for m in MD_LINK_RE.findall(content):
                r = _resolve_link(m, base)
                if r and r[0] not in seen:
                    queue.append((r[0], r[1], depth + 1))
    return docs


def summary_line(records: list[dict]) -> str:
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for r in records:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
        if r["type"] != "epic":                       # epics aren't status-tracked work items
            by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    return (f"{len(records)} entries · "
            + "types — " + ", ".join(f"{k}: {v}" for k, v in sorted(by_type.items()))
            + " · statuses — " + ", ".join(f"{k}: {v}" for k, v in sorted(by_status.items())))


def effective_modules(records: list[dict]) -> list[str]:
    """The module list that drives board colors + the Module filter/lane order.
    Use the configured taxonomy (_config.MODULES) when set; otherwise fall back to the
    sorted union of every `module` value actually present across the loaded features — so
    the board still colors modules even with no fixed taxonomy. May be empty (fine)."""
    if _config.MODULES:
        return list(_config.MODULES)
    seen = set()
    for r in records:
        for m in r.get("module") or []:
            if m:
                seen.add(m)
    return sorted(seen)


def module_color_css(modules: list[str], palette: list[str]) -> str:
    """`--m-<MODULE>:<hex>;` declarations, one color per module BY INDEX (palette cycles)."""
    if not modules or not palette:
        return ""
    return " ".join(
        f"--m-{m}:{palette[i % len(palette)]};" for i, m in enumerate(modules)
    )


def render_html(records: list[dict], docs: dict) -> str:
    payload = {
        "repoRoot": str(_fm.REPO_ROOT),
        "ghBase": github_base(),
        "features": records,
        "docs": docs,
    }
    # Escape "<" so an embedded "</script>" (or "<" in body text) can't break the tag.
    data_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    generated = datetime.date.today().isoformat()

    # Module palette is config-driven, not hard-coded: color each effective module by index
    # and inject the CSS custom-properties + the JS MODULE_ORDER into the template.
    modules = effective_modules(records)
    css_light = module_color_css(modules, MODULE_PALETTE_LIGHT)
    css_dark = module_color_css(modules, MODULE_PALETTE_DARK)  # dark token appears twice

    return (
        TEMPLATE
        .replace("__SUMMARY__", summary_line(records))
        .replace("__ENTRY_COUNT__", str(len(records)))
        .replace("__GENERATED__", generated)
        .replace("/*MODULE_COLORS_LIGHT*/", css_light)
        .replace("/*MODULE_COLORS_DARK*/", css_dark)
        .replace("/*MODULE_ORDER*/[]", json.dumps(modules))
        .replace("__PAYLOAD_JSON__", data_json)
    )


def main() -> int:
    check_only = "--check" in sys.argv
    features = _fm.load_all()
    if not features:
        print(f"no features/{_config.PREFIX}-*/FEATURE.md found", file=sys.stderr)
        return 0

    records = build_records(features)
    docs = collect_docs(features)
    content = render_html(records, docs)

    if check_only:
        existing = BOARD_PATH.read_text(encoding="utf-8") if BOARD_PATH.exists() else ""
        if existing != content:
            print("ERROR board.html is stale — run `python scripts/build-board.py`",
                  file=sys.stderr)
            return 1
        print(f"board.html up to date ({len(records)} entries)")
        return 0

    BOARD_PATH.write_text(content, encoding="utf-8")
    rendered = sum(1 for d in docs.values() if d.get("kind") in ("md", "code"))
    print(f"wrote {BOARD_PATH} ({len(records)} entries, {len(docs)} referenced docs, "
          f"{rendered} embedded for rendering)")
    print(f"  {summary_line(records)}")
    print(f"  open: file://{BOARD_PATH}")
    return 0


# --------------------------------------------------------------------------------------
# Self-contained page template. __PAYLOAD_JSON__ / __SUMMARY__ / __ENTRY_COUNT__ /
# __GENERATED__ are substituted above. All CSS + JS are inlined (no external requests).
# --------------------------------------------------------------------------------------
TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feature Registry Board</title>
<style>
:root{
  --bg:#f6f7f9; --panel:#ffffff; --panel-2:#fbfcfd; --lane:#eef0f3;
  --text:#1a1d24; --muted:#5b6472; --faint:#8a93a3; --border:#e3e6ea; --border-2:#d7dbe0;
  --accent:#3b5bdb; --accent-soft:#e8ecfb; --shadow:0 1px 2px rgba(20,24,33,.06),0 2px 8px rgba(20,24,33,.05);
  --shadow-lg:0 10px 40px rgba(20,24,33,.18);
  --st-backlog:#6b7280; --st-planned:#64748b; --st-in-dev:#d97706; --st-blocked:#dc2626;
  --st-shipped-sit:#2563eb; --st-shipped-prod:#16a34a; --st-archived:#9aa3af;
  /*MODULE_COLORS_LIGHT*/
}
:root[data-theme="dark"]{
  --bg:#0d1017; --panel:#161a22; --panel-2:#1b2029; --lane:#12151c;
  --text:#e6e9ef; --muted:#9aa4b2; --faint:#6b7482; --border:#252b36; --border-2:#2f3644;
  --accent:#6c8cff; --accent-soft:#1e2740; --shadow:0 1px 2px rgba(0,0,0,.4);
  --shadow-lg:0 16px 50px rgba(0,0,0,.55);
  --st-backlog:#8b93a1; --st-planned:#94a3b8; --st-in-dev:#f59e0b; --st-blocked:#f87171;
  --st-shipped-sit:#60a5fa; --st-shipped-prod:#4ade80; --st-archived:#6b7482;
  /*MODULE_COLORS_DARK*/
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#0d1017; --panel:#161a22; --panel-2:#1b2029; --lane:#12151c;
    --text:#e6e9ef; --muted:#9aa4b2; --faint:#6b7482; --border:#252b36; --border-2:#2f3644;
    --accent:#6c8cff; --accent-soft:#1e2740; --shadow:0 1px 2px rgba(0,0,0,.4);
    --shadow-lg:0 16px 50px rgba(0,0,0,.55);
    --st-backlog:#8b93a1; --st-planned:#94a3b8; --st-in-dev:#f59e0b; --st-blocked:#f87171;
    --st-shipped-sit:#60a5fa; --st-shipped-prod:#4ade80; --st-archived:#6b7482;
    /*MODULE_COLORS_DARK*/
  }
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{
  background:var(--bg); color:var(--text);
  font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased; display:flex; flex-direction:column; height:100vh; overflow:hidden;
}
.mono{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace}
a{color:var(--accent); text-decoration:none}
a:hover{text-decoration:underline}
button{font:inherit; cursor:pointer}

/* Top bar */
header{
  padding:12px 20px 10px; border-bottom:1px solid var(--border); background:var(--panel);
  display:flex; flex-direction:column; gap:10px; flex:0 0 auto; z-index:5;
}
.titlerow{display:flex; align-items:center; gap:12px; flex-wrap:wrap}
.titlerow h1{font-size:16px; font-weight:650; margin:0; letter-spacing:-.01em}
.titlerow .sub{color:var(--faint); font-size:12px}
.spacer{flex:1}
.iconbtn{
  background:var(--panel-2); border:1px solid var(--border); color:var(--muted);
  border-radius:8px; padding:6px 10px; font-size:13px; display:inline-flex; align-items:center; gap:6px;
}
.iconbtn:hover{border-color:var(--border-2); color:var(--text)}

/* Stat chips */
.stats{display:flex; gap:6px; flex-wrap:wrap}
.stat{
  display:inline-flex; align-items:center; gap:7px; padding:4px 10px; border-radius:20px;
  background:var(--panel-2); border:1px solid var(--border); font-size:12px; color:var(--muted);
}
.stat:hover{border-color:var(--border-2)}
.stat.active{background:var(--accent-soft); border-color:var(--accent); color:var(--text)}
.stat .dot{width:8px; height:8px; border-radius:50%}
.stat b{color:var(--text); font-weight:600}

/* Filter bar */
.filters{display:flex; gap:8px; align-items:center; flex-wrap:wrap}
.search{
  flex:1 1 220px; min-width:180px; max-width:340px; position:relative;
}
.search input{
  width:100%; padding:7px 10px 7px 30px; border-radius:8px; border:1px solid var(--border);
  background:var(--panel-2); color:var(--text); font-size:13px;
}
.search input:focus{outline:none; border-color:var(--accent)}
.search svg{position:absolute; left:9px; top:8px; width:14px; height:14px; color:var(--faint)}
.seg{display:inline-flex; background:var(--panel-2); border:1px solid var(--border); border-radius:8px; overflow:hidden}
.seg button{background:transparent; border:none; color:var(--muted); padding:6px 11px; font-size:12px}
.seg button.on{background:var(--accent); color:#fff}
.fgroup{display:inline-flex; gap:5px; align-items:center; flex-wrap:wrap}
.fgroup .lbl{color:var(--faint); font-size:11px; text-transform:uppercase; letter-spacing:.04em; margin-right:2px}
.chip{
  padding:3px 9px; border-radius:14px; font-size:11.5px; border:1px solid var(--border);
  background:var(--panel-2); color:var(--muted); user-select:none;
}
.chip:hover{border-color:var(--border-2)}
.chip.on{color:#fff; border-color:transparent}
.chip.mod.on{color:#fff}
.chip.star.on{background:#f59e0b; border-color:#f59e0b; color:#111}
.clearbtn{background:transparent; border:none; color:var(--accent); font-size:12px; padding:4px 6px}
.count{color:var(--faint); font-size:12px; margin-left:auto}

/* Board */
.board{flex:1 1 auto; overflow-x:auto; overflow-y:hidden; padding:16px 20px 20px; display:flex; gap:14px}
.lane{
  flex:0 0 300px; width:300px; background:var(--lane); border:1px solid var(--border);
  border-radius:12px; display:flex; flex-direction:column; max-height:100%;
}
.lane-h{
  padding:11px 13px; display:flex; align-items:center; gap:8px; position:sticky; top:0;
  border-bottom:1px solid var(--border); border-radius:12px 12px 0 0; background:var(--lane);
}
.lane-h .name{font-weight:600; font-size:13px; letter-spacing:-.01em}
.lane-h .bar{width:3px; height:15px; border-radius:2px}
.lane-h .n{margin-left:auto; color:var(--muted); font-size:12px; background:var(--panel);
  border:1px solid var(--border); border-radius:10px; padding:1px 8px}
.lane-body{overflow-y:auto; padding:10px; display:flex; flex-direction:column; gap:9px}
.lane-empty{color:var(--faint); font-size:12px; text-align:center; padding:16px 6px}

.card{
  background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:11px 12px 10px 14px;
  position:relative; box-shadow:var(--shadow); cursor:pointer; transition:border-color .12s, transform .06s;
}
.card:hover{border-color:var(--border-2); transform:translateY(-1px)}
.card::before{content:""; position:absolute; left:0; top:0; bottom:0; width:4px; border-radius:10px 0 0 10px; background:var(--acc,#999)}
.card .top{display:flex; align-items:center; gap:8px; margin-bottom:6px}
.card .id{font-size:11px; color:var(--muted); font-weight:600}
.card .star{color:#f59e0b; margin-left:auto; font-size:13px}
.card .ttl{font-size:13px; font-weight:550; line-height:1.35; letter-spacing:-.01em;
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden}
.card .meta{display:flex; align-items:center; gap:6px; margin-top:9px; flex-wrap:wrap}
.mchip{font-size:10px; font-weight:650; letter-spacing:.02em; padding:1.5px 6px; border-radius:5px;
  color:#fff}
.tbadge{font-size:10px; padding:1.5px 6px; border-radius:5px; border:1px solid var(--border-2); color:var(--muted); text-transform:capitalize}
.echip{font-size:10px; font-weight:600; padding:1.5px 6px; border-radius:5px; border:1px solid var(--accent);
  color:var(--accent); background:var(--accent-soft); font-family:ui-monospace,Menlo,Consolas,monospace; cursor:pointer}
.echip:hover{filter:brightness(1.06); text-decoration:none}
.scap{font-size:10px; font-weight:600; padding:1.5px 6px; border-radius:5px; border:1px solid var(--border-2)}
.lane-h .epstat{margin-left:auto; margin-right:6px; font-size:10.5px; font-weight:600; color:#fff;
  padding:1px 8px; border-radius:10px}
.lane-h .epstat + .n{margin-left:0}
.card .foot{display:flex; align-items:center; gap:10px; margin-top:8px; color:var(--faint); font-size:11px}
.sdot{width:8px; height:8px; border-radius:50%; display:inline-block}

/* Drawer */
.scrim{position:fixed; inset:0; background:rgba(10,12,18,.42); opacity:0; pointer-events:none; transition:opacity .18s; z-index:20}
.scrim.open{opacity:1; pointer-events:auto}
.drawer{
  position:fixed; top:0; right:0; height:100vh; width:min(640px,94vw); background:var(--panel);
  border-left:1px solid var(--border); box-shadow:var(--shadow-lg); transform:translateX(102%);
  transition:transform .22s cubic-bezier(.4,0,.2,1); z-index:21; display:flex; flex-direction:column;
}
.drawer.open{transform:translateX(0)}
.dh{padding:16px 20px 14px; border-bottom:1px solid var(--border); display:flex; flex-direction:column; gap:9px}
.dh .row1{display:flex; align-items:center; gap:9px}
.dh .id{font-size:12px; color:var(--muted); font-weight:600}
.dh .close{margin-left:auto; background:var(--panel-2); border:1px solid var(--border); color:var(--muted);
  width:30px; height:30px; border-radius:8px; font-size:16px; line-height:1}
.dh .close:hover{color:var(--text); border-color:var(--border-2)}
.dh h2{margin:0; font-size:17px; font-weight:650; line-height:1.3; letter-spacing:-.01em}
.dh .row2{display:flex; align-items:center; gap:7px; flex-wrap:wrap}
.pill{font-size:11px; font-weight:600; padding:2.5px 10px; border-radius:20px; color:#fff}
.dbody{overflow-y:auto; padding:18px 20px 40px}
.sect{margin-bottom:20px}
.sect > h3{font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--faint);
  margin:0 0 9px; font-weight:600}
.grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:10px 16px}
.kv .k{font-size:11px; color:var(--faint); margin-bottom:1px}
.kv .v{font-size:13px; color:var(--text)}
.reflist{display:flex; flex-wrap:wrap; gap:6px}
.ref{
  display:inline-flex; align-items:center; gap:6px; padding:3px 9px; border-radius:7px;
  border:1px solid var(--border); background:var(--panel-2); font-size:12px; color:var(--text);
}
.ref:hover{border-color:var(--accent)}
.ref .rid{font-weight:600; font-size:11px; color:var(--muted)}
.ref.rel{cursor:pointer}
.tag{font-size:11px; padding:2px 8px; border-radius:12px; background:var(--panel-2); border:1px solid var(--border); color:var(--muted)}
.linkline{display:flex; gap:8px; align-items:baseline; margin-bottom:5px; font-size:13px}
.linkline .lk{color:var(--faint); font-size:11px; min-width:64px; text-transform:capitalize}
.diskrow{display:flex; gap:8px; flex-wrap:wrap; margin-top:2px}
.diskbtn{display:inline-flex; align-items:center; gap:6px; padding:6px 11px; border-radius:8px;
  border:1px solid var(--border); background:var(--panel-2); color:var(--text); font-size:12.5px}
.diskbtn:hover{border-color:var(--accent); text-decoration:none}

/* Rendered markdown */
.md{color:var(--text); font-size:13.5px}
.md h1{font-size:16px; margin:16px 0 10px; font-weight:700; letter-spacing:-.01em}
.md h2{font-size:14px; margin:18px 0 8px; font-weight:650}
.md h4{font-size:12.5px; margin:12px 0 5px; font-weight:600; color:var(--muted)}
.md h3{font-size:13px; margin:14px 0 6px; font-weight:600; color:var(--muted)}
.md p{margin:8px 0}
.md ul,.md ol{margin:8px 0; padding-left:20px}
.md li{margin:3px 0}
.md li.task{list-style:none; margin-left:-20px; display:flex; gap:8px; align-items:flex-start}
.md li.task .cb{flex:0 0 auto; width:15px; height:15px; border-radius:4px; border:1.5px solid var(--border-2);
  margin-top:2px; position:relative; background:var(--panel-2)}
.md li.task .cb.on{background:var(--st-shipped-prod); border-color:var(--st-shipped-prod)}
.md li.task .cb.on::after{content:"✓"; color:#fff; font-size:11px; position:absolute; left:2px; top:-2px}
.md code{font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12px; background:var(--panel-2);
  border:1px solid var(--border); border-radius:4px; padding:.5px 4px}
.md pre{background:var(--panel-2); border:1px solid var(--border); border-radius:8px; padding:11px 13px;
  overflow-x:auto; margin:10px 0}
.md pre code{background:none; border:none; padding:0; font-size:12px; line-height:1.5}
.md blockquote{margin:10px 0; padding:6px 13px; border-left:3px solid var(--border-2);
  color:var(--muted); background:var(--panel-2); border-radius:0 6px 6px 0}
.md hr{border:none; border-top:1px solid var(--border); margin:14px 0}
.md a{word-break:break-word}
.sanitybox{background:var(--panel-2); border:1px solid var(--border); border-radius:10px; padding:6px 14px}
.emptybody{color:var(--faint); font-style:italic; font-size:13px}

/* Doc reader (layered above the drawer) */
.reader-scrim{z-index:30}
.reader{
  position:fixed; top:0; right:0; height:100vh; width:min(920px,96vw); background:var(--panel);
  border-left:1px solid var(--border); box-shadow:var(--shadow-lg); transform:translateX(102%);
  transition:transform .2s cubic-bezier(.4,0,.2,1); z-index:31; display:flex; flex-direction:column;
}
.reader.open{transform:translateX(0)}
.reader-head{display:flex; align-items:center; gap:12px; padding:12px 16px; border-bottom:1px solid var(--border); background:var(--panel); flex:0 0 auto}
.rh-left{display:flex; align-items:center; gap:10px; min-width:0}
.rh-title{display:flex; flex-direction:column; min-width:0}
.rh-name{font-weight:650; font-size:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.rh-path{font-size:11px; color:var(--faint); white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.rh-right{margin-left:auto; display:flex; align-items:center; gap:8px}
.riconbtn{background:var(--panel-2); border:1px solid var(--border); color:var(--muted); width:30px; height:30px; border-radius:8px; font-size:16px; line-height:1; flex:0 0 auto}
.riconbtn:hover{color:var(--text); border-color:var(--border-2)}
.rraw{font-size:12px; color:var(--accent); padding:6px 10px; border:1px solid var(--border); border-radius:8px; white-space:nowrap}
.rraw:hover{border-color:var(--accent); text-decoration:none}
.reader-body{overflow-y:auto; padding:24px 28px 64px; flex:1 1 auto}
.reader-col{max-width:820px; margin:0 auto}
.reader-md{font-size:14.5px; line-height:1.68}
.reader-md h1{font-size:24px; margin:6px 0 16px; padding-bottom:10px; border-bottom:1px solid var(--border)}
.reader-md h2{font-size:19px; margin:24px 0 10px}
.reader-md h3{font-size:16px; color:var(--text); margin:18px 0 7px}
.reader-md pre{max-height:none}
.reader-code{border:1px solid var(--border); border-radius:10px; overflow:hidden}
.reader-code .codehead{background:var(--panel-2); border-bottom:1px solid var(--border); padding:8px 13px; font-size:11px; color:var(--muted)}
.reader-code pre{margin:0; border:none; border-radius:0; background:var(--panel)}
.docnote{color:var(--muted); font-size:14px; padding:48px 6px; text-align:center}
.docnote .np{margin-top:10px}
.docnote .mono.np{color:var(--faint); font-size:12px}
@media (max-width:640px){ .reader{width:100vw} }
.noresults{margin:60px auto; color:var(--faint); text-align:center}
::-webkit-scrollbar{width:10px; height:10px}
::-webkit-scrollbar-thumb{background:var(--border-2); border-radius:6px; border:2px solid transparent; background-clip:content-box}
::-webkit-scrollbar-thumb:hover{background:var(--faint); background-clip:content-box}
</style>
</head>
<body>
<header>
  <div class="titlerow">
    <h1>Feature Registry</h1>
    <span class="sub" id="summary">__SUMMARY__</span>
    <span class="spacer"></span>
    <button class="iconbtn" id="themeBtn" title="Toggle theme">◐ Theme</button>
  </div>
  <div class="stats" id="stats"></div>
  <div class="filters">
    <div class="search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
      <input id="search" type="text" placeholder="Search id, title, tags…" autocomplete="off">
    </div>
    <div class="fgroup"><span class="lbl">Group</span>
      <div class="seg" id="groupSeg">
        <button data-g="status" class="on">Status</button>
        <button data-g="module">Module</button>
        <button data-g="type">Type</button>
        <button data-g="epic">Epic</button>
      </div>
    </div>
    <div class="fgroup" id="modFilter"><span class="lbl">Module</span></div>
    <div class="fgroup" id="typeFilter"><span class="lbl">Type</span></div>
    <div class="fgroup" id="verFilter"><span class="lbl">Verify</span></div>
    <span class="chip star" id="critChip">★ Critical</span>
    <button class="clearbtn" id="clearBtn">Clear</button>
    <span class="count" id="count"></span>
  </div>
</header>

<div class="board" id="board"></div>

<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" aria-hidden="true"></aside>

<div class="scrim reader-scrim" id="readerScrim"></div>
<aside class="reader" id="reader" aria-hidden="true"></aside>

<script type="application/json" id="board-data">__PAYLOAD_JSON__</script>
<script>
"use strict";
const PAYLOAD = JSON.parse(document.getElementById("board-data").textContent);
const REPO_ROOT = PAYLOAD.repoRoot, GH = PAYLOAD.ghBase, FEATURES = PAYLOAD.features;
const DOCS = PAYLOAD.docs || {};
const BY_ID = {}; FEATURES.forEach(f => BY_ID[f.id] = f);

const MODULE_ORDER = /*MODULE_ORDER*/[];
const TYPE_ORDER = ["epic","feature","bug","backlog"];
const STATUS_ORDER = ["backlog","planned","in-dev","blocked","shipped-sit","shipped-prod","archived"];
const STATUS_LABEL = {"backlog":"Backlog","planned":"Planned","in-dev":"In dev","blocked":"Blocked",
  "shipped-sit":"Shipped · SIT","shipped-prod":"Shipped · Prod","archived":"Archived"};
// Epic ids present, sorted — the lane order when grouping by epic ("(no epic)" last).
const EPIC_IDS = FEATURES.filter(f=>f.type==="epic").map(f=>f.id).sort();
const NO_EPIC = "(no epic)";

const state = {group:"status", q:"", modules:new Set(), types:new Set(),
  statuses:new Set(), verify:new Set(), crit:false};

/* ---------- helpers ---------- */
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,c=>(
  {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));}
function statusVar(s){return "var(--st-"+s+")";}
// Fall back to a neutral color for a module that has no assigned CSS var (undefined
// module, or the "(none)" bucket) so chips/lanes never render broken.
function modVar(m){return "var(--m-"+m+", var(--muted, #888))";}

function normPath(base, rel){
  const parts = (base + "/" + rel).split("/"); const out=[];
  for(const p of parts){ if(p==="."||p==="") continue; if(p===".."){out.pop();} else out.push(p); }
  return "/" + out.join("/");
}
function fileUrl(abs){return "file://" + encodeURI(abs);}
function resolveHref(href, baseDir){
  if(/^(https?:|mailto:|#)/.test(href)) return href;
  return fileUrl(normPath(baseDir, href));
}
function dirOf(abs){ return abs.slice(0, abs.lastIndexOf("/")) || "/"; }
function repoRelFromAbs(abs){ return abs.indexOf(REPO_ROOT+"/")===0 ? abs.slice(REPO_ROOT.length+1) : null; }
function docKeyFor(href, baseDir){
  if(/^(https?:|mailto:|\/\/|#)/.test(href)) return null;
  const clean = href.split("#")[0].trim();
  if(!clean) return null;
  const abs = clean[0]==="/" ? normPath("", clean) : normPath(baseDir, clean);
  const key = repoRelFromAbs(abs);
  return (key && DOCS[key]) ? key : null;
}
// Build the attributes for an anchor: embedded docs get data-doc (→ in-board reader),
// external links open in a new tab, other in-repo files stay raw file:// (open on disk).
function docLinkAttrs(href, baseDir){
  if(/^(https?:|mailto:)/.test(href)) return 'href="'+esc(href)+'" target="_blank" rel="noopener"';
  const key = docKeyFor(href, baseDir);
  const url = resolveHref(href, baseDir);
  return key ? 'href="'+esc(url)+'" data-doc="'+esc(key)+'"' : 'href="'+esc(url)+'"';
}

/* ---------- markdown ---------- */
function renderInline(text, baseDir){
  const toks=[]; let s = esc(text);
  s = s.replace(/`([^`]+)`/g, (_,c)=>"\ue000"+(toks.push("<code>"+c+"</code>")-1)+"\ue000");
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_,t,u)=>{
    const a='<a '+docLinkAttrs(u.trim(), baseDir)+'>'+t+'</a>'; return "\ue000"+(toks.push(a)-1)+"\ue000";});
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
  s = s.replace(/(^|[\s(])_([^_\s][^_]*?)_(?=[\s).,;:!?]|$)/g, "$1<em>$2</em>");
  for(let k=0; k<4 && s.indexOf("")>=0; k++)
    s = s.replace(/(\d+)/g, (_,i)=>toks[+i]===undefined?"":toks[+i]);
  return s;
}
function mdToHtml(md, baseDir){
  if(!md) return '<p class="emptybody">No content.</p>';
  const L = md.replace(/\r\n/g,"\n").split("\n"); let i=0, out=[];
  const flushInline = t => out.push("<p>"+renderInline(t.join(" ").trim(), baseDir)+"</p>");
  while(i<L.length){
    let ln=L[i];
    if(/^```/.test(ln)){ i++; const buf=[]; while(i<L.length && !/^```/.test(L[i])) buf.push(L[i++]);
      i++; out.push("<pre><code>"+esc(buf.join("\n"))+"</code></pre>"); continue; }
    let hm = ln.match(/^(#{1,6})\s+(.*)$/);
    if(hm){ const lvl=Math.min(hm[1].length,4); out.push("<h"+lvl+">"+renderInline(hm[2],baseDir)+"</h"+lvl+">"); i++; continue; }
    if(/^(---+|\*\*\*+)\s*$/.test(ln)){ out.push("<hr>"); i++; continue; }
    if(/^>\s?/.test(ln)){ const buf=[]; while(i<L.length && /^>\s?/.test(L[i])) buf.push(L[i++].replace(/^>\s?/,""));
      out.push("<blockquote>"+renderInline(buf.join(" "),baseDir)+"</blockquote>"); continue; }
    if(/^\s*[-*]\s+/.test(ln)){ const items=[];
      while(i<L.length && /^\s*[-*]\s+/.test(L[i])){ items.push(L[i].replace(/^\s*[-*]\s+/,"")); i++; }
      out.push("<ul>"+items.map(it=>{
        const t=it.match(/^\[([ xX])\]\s+(.*)$/);
        if(t) return '<li class="task"><span class="cb'+(t[1].toLowerCase()==="x"?" on":"")+'"></span><span>'+renderInline(t[2],baseDir)+"</span></li>";
        return "<li>"+renderInline(it,baseDir)+"</li>";
      }).join("")+"</ul>"); continue; }
    if(/^\s*\d+\.\s+/.test(ln)){ const items=[];
      while(i<L.length && /^\s*\d+\.\s+/.test(L[i])){ items.push(L[i].replace(/^\s*\d+\.\s+/,"")); i++; }
      out.push("<ol>"+items.map(it=>"<li>"+renderInline(it,baseDir)+"</li>").join("")+"</ol>"); continue; }
    if(!ln.trim()){ i++; continue; }
    const buf=[]; while(i<L.length && L[i].trim() && !/^(#{2,4}\s|```|>\s?|\s*[-*]\s+|\s*\d+\.\s+|---+\s*$)/.test(L[i])) buf.push(L[i++]);
    flushInline(buf);
  }
  return out.join("\n");
}

/* ---------- filter model ---------- */
function laneKeys(f, group){
  if(group==="module") return f.module.length ? f.module : ["(none)"];
  if(group==="type") return [f.type];
  if(group==="epic") return [f.epic ? f.epic : (f.type==="epic" ? f.id : NO_EPIC)];
  return [f.status];
}
function laneOrder(group){
  if(group==="module") return MODULE_ORDER.concat(["(none)"]);
  if(group==="type") return TYPE_ORDER;
  if(group==="epic") return EPIC_IDS.concat([NO_EPIC]);
  return STATUS_ORDER;
}
function laneLabel(group, key){
  if(group==="status") return STATUS_LABEL[key]||key;
  if(group==="epic") return key===NO_EPIC ? "No epic" : (BY_ID[key] ? BY_ID[key].title : key);
  return key;
}
function laneColor(group, key){
  if(group==="status") return statusVar(key);
  if(group==="module") return modVar(key);
  return "var(--accent)";
}
function matches(f){
  if(state.crit && !f.critical) return false;
  if(state.modules.size && !f.module.some(m=>state.modules.has(m))) return false;
  if(state.types.size && !state.types.has(f.type)) return false;
  if(state.statuses.size && !state.statuses.has(f.status)) return false;
  if(state.verify.size && !state.verify.has(f.verification)) return false;
  if(state.q){
    const q=state.q.toLowerCase();
    const hay=(f.id+" "+f.title+" "+f.module.join(" ")+" "+f.touches.join(" ")+" "+(f.body||"")).toLowerCase();
    if(!hay.includes(q)) return false;
  }
  return true;
}

/* ---------- render: stats + filters ---------- */
function renderStats(){
  // Epics aren't status-tracked work items — keep them out of the status census.
  const el=document.getElementById("stats"); const counts={};
  FEATURES.forEach(f=>{ if(f.type!=="epic") counts[f.status]=(counts[f.status]||0)+1; });
  el.innerHTML = STATUS_ORDER.filter(s=>counts[s]).map(s=>
    '<span class="stat'+(state.statuses.has(s)?" active":"")+'" data-st="'+s+'">'+
    '<span class="dot" style="background:'+statusVar(s)+'"></span>'+STATUS_LABEL[s]+' <b>'+counts[s]+'</b></span>'
  ).join("");
  el.querySelectorAll(".stat").forEach(n=>n.onclick=()=>{ toggleSet(state.statuses,n.dataset.st); render(); });
}
function buildChipRow(containerId, values, set, colorFn){
  const el=document.getElementById(containerId);
  values.forEach(v=>{
    const c=document.createElement("span"); c.className="chip"+(colorFn?" mod":""); c.textContent=v;
    c.dataset.v=v; el.appendChild(c);
    c.onclick=()=>{ toggleSet(set,v); syncChip(c,set.has(v),colorFn?colorFn(v):null); render(); };
  });
}
function syncChip(el,on,color){ el.classList.toggle("on",on); if(color) el.style.background=on?color:""; }
function toggleSet(set,v){ set.has(v)?set.delete(v):set.add(v); }

/* ---------- render: board ---------- */
// Epics are containers, not status-tracked work items — hide them from the Status and
// Module lanes (they'd read as peers of features). They remain in Type + Epic groupings.
function epicsHidden(){ return state.group==="status" || state.group==="module"; }
function visible(f){ return matches(f) && !(epicsHidden() && f.type==="epic"); }

function render(){
  const g=state.group, order=laneOrder(g);
  const universe = FEATURES.filter(f => !(epicsHidden() && f.type==="epic"));
  const present = order.filter(k => universe.some(f=>laneKeys(f,g).includes(k)));
  const shown = FEATURES.filter(visible);
  document.getElementById("count").textContent = shown.length+" / "+universe.length+" shown";
  document.getElementById("stats").querySelectorAll(".stat").forEach(n=>
    n.classList.toggle("active", state.statuses.has(n.dataset.st)));

  const board=document.getElementById("board");
  if(!shown.length){ board.innerHTML='<div class="noresults">No features match these filters.</div>'; return; }
  board.innerHTML="";
  present.forEach(key=>{
    const cards = shown.filter(f=>laneKeys(f,g).includes(key)).sort((a,b)=>cardCmp(a,b,g));
    const lane=document.createElement("div"); lane.className="lane";
    // In the Epic view, the lane header carries the epic's derived rollup status.
    let epStat = '';
    if(g==="epic" && key!==NO_EPIC && BY_ID[key]){
      const ep=BY_ID[key];
      epStat = '<span class="epstat" style="background:'+statusVar(ep.status)+'" title="derived rollup">'+
        (STATUS_LABEL[ep.status]||ep.status)+(ep.epicBlocked?' ⚠':'')+'</span>';
    }
    lane.innerHTML='<div class="lane-h"><span class="bar" style="background:'+laneColor(g,key)+'"></span>'+
      '<span class="name">'+esc(laneLabel(g,key))+'</span>'+epStat+'<span class="n">'+cards.length+'</span></div>';
    const body=document.createElement("div"); body.className="lane-body";
    if(!cards.length) body.innerHTML='<div class="lane-empty">No matching cards</div>';
    cards.forEach(f=>body.appendChild(cardEl(f)));
    lane.appendChild(body); board.appendChild(lane);
  });
}
// Epic lanes: the umbrella card first, then phases by ascending phase, then id.
function phaseKey(p){ return (typeof p==="number") ? p : (p==null ? Infinity : String(p)); }
function cardCmp(a,b,g){
  if(g==="epic"){
    const ae=a.type==="epic"?0:1, be=b.type==="epic"?0:1;
    if(ae!==be) return ae-be;
    const pa=phaseKey(a.phase), pb=phaseKey(b.phase);
    if(pa<pb) return -1; if(pa>pb) return 1;
  }
  return a.id.localeCompare(b.id);
}
function cardEl(f){
  const el=document.createElement("div"); el.className="card"; el.style.setProperty("--acc",statusVar(f.status));
  const mods=f.module.map(m=>'<span class="mchip" style="background:'+modVar(m)+'">'+m+'</span>').join("");
  const foot=[];
  if(f.prs.length) foot.push(f.prs.length+" PR"+(f.prs.length>1?"s":""));
  if(f.prod_sha) foot.push("● prod"); else if(f.sit_sha) foot.push("● sit");
  if(f.verification==="pass") foot.push("✓ verified");
  // In Epic view show each phase's own stage as a labelled caption; elsewhere a dot suffices.
  const sdot = (state.group!=="status" && state.group!=="epic") ? '<span class="sdot" title="'+f.status+'" style="background:'+statusVar(f.status)+'"></span>' : '';
  const statusCap = state.group==="epic"
    ? '<span class="scap" style="border-color:'+statusVar(f.status)+'; color:'+statusVar(f.status)+'">'+(STATUS_LABEL[f.status]||f.status)+'</span>' : '';
  const phaseBadge = f.phase!=null ? '<span class="tbadge">Phase '+esc(f.phase)+'</span>' : '';
  // Epic tag: show the umbrella's id on the card (redundant when already grouping by epic).
  const epicTitle = BY_ID[f.epic] ? BY_ID[f.epic].title : f.epic;
  const epicChip = (f.epic && state.group!=="epic")
    ? '<span class="echip" data-epic="'+esc(f.epic)+'" title="Epic: '+esc(epicTitle)+'">◆ '+esc(f.epic)+'</span>' : '';
  el.innerHTML =
    '<div class="top"><span class="id mono">'+f.id+'</span>'+(f.critical?'<span class="star">★</span>':'')+'</div>'+
    '<div class="ttl">'+esc(f.title)+'</div>'+
    '<div class="meta">'+mods+'<span class="tbadge">'+f.type+'</span>'+phaseBadge+epicChip+statusCap+sdot+'</div>'+
    (foot.length?'<div class="foot">'+foot.map(x=>'<span>'+x+'</span>').join("")+'</div>':'');
  el.onclick=()=>{ location.hash = f.id; };
  const ec = el.querySelector(".echip");
  if(ec) ec.onclick=(e)=>{ e.stopPropagation(); location.hash = ec.dataset.epic; };
  return el;
}

/* ---------- drawer ---------- */
function refChip(id, clickable){
  const f=BY_ID[id];
  if(!f) return '<span class="ref"><span class="rid mono">'+esc(id)+'</span>?</span>';
  const t=esc(f.title.length>42?f.title.slice(0,40)+"…":f.title);
  return '<span class="ref'+(clickable?" rel":"")+'" data-goto="'+esc(id)+'">'+
    '<span class="rid mono">'+esc(id)+'</span>'+t+'</span>';
}
function ghLink(kind, val){
  if(!GH) return '<span class="mono">'+esc(val)+'</span>';
  const url = kind==="pr" ? GH+"/pull/"+val : GH+"/commit/"+val;
  return '<a class="mono" href="'+esc(url)+'" target="_blank" rel="noopener">'+esc(kind==="pr"?"#"+val:val)+'</a>';
}
function openDrawer(id){
  const f=BY_ID[id]; if(!f) return;
  const dr=document.getElementById("drawer");
  const mods=f.module.map(m=>'<span class="mchip" style="background:'+modVar(m)+'">'+m+'</span>').join("");
  const kv=[];
  kv.push(["Created", f.created||"—"]);
  if(f.phase!=null) kv.push(["Phase", esc(f.phase)]);
  kv.push(["Verification", f.verification + (f.verified_at?(" · "+f.verified_at):"")]);
  if(f.branch) kv.push(["Branch", '<span class="mono">'+esc(f.branch)+'</span>']);
  if(f.prs.length) kv.push(["PRs", f.prs.map(p=>ghLink("pr",p)).join(" ")]);
  if(f.sit_sha) kv.push(["SIT", ghLink("sha",f.sit_sha)]);
  if(f.prod_sha) kv.push(["Prod", ghLink("sha",f.prod_sha)]);

  const lineage=[];
  const addLin=(label,arr)=>{ if(arr && arr.length) lineage.push('<div class="kv"><div class="k">'+label+'</div><div class="reflist">'+arr.map(x=>refChip(x,true)).join("")+'</div></div>'); };
  if(f.epic) lineage.push('<div class="kv"><div class="k">Epic</div><div class="reflist">'+refChip(f.epic,true)+'</div></div>');
  if(f.type==="epic"){
    const kids=FEATURES.filter(x=>x.epic===f.id).sort((a,b)=>cardCmp(a,b,"epic"));
    addLin("Phases", kids.map(k=>k.id));
  }
  addLin("Depends on", f.depends_on);
  if(f.supersedes) lineage.push('<div class="kv"><div class="k">Supersedes</div><div class="reflist">'+refChip(f.supersedes,true)+'</div></div>');
  if(f.superseded_by) lineage.push('<div class="kv"><div class="k">Superseded by</div><div class="reflist">'+refChip(f.superseded_by,true)+'</div></div>');
  addLin("Amends", f.amends);
  addLin("Amended by", f.amended_by);
  addLin("Related", f.related);

  const linkKeys=Object.keys(f.links||{});
  const linksHtml = linkKeys.map(k=>
    '<div class="linkline"><span class="lk">'+esc(k)+'</span><a '+docLinkAttrs(f.links[k], REPO_ROOT)+'>'+esc(f.links[k])+'</a></div>'
  ).join("");

  const touches = f.touches.length ? '<div class="reflist" style="margin-top:8px">'+f.touches.map(t=>'<span class="tag">'+esc(t)+'</span>').join("")+'</div>' : '';

  const disk=[];
  disk.push('<a class="diskbtn" href="'+fileUrl(f.featurePath)+'">📄 FEATURE.md</a>');
  if(f.sanityPath) disk.push('<a class="diskbtn" href="'+fileUrl(f.sanityPath)+'">🧪 SANITY.md</a>');
  disk.push('<a class="diskbtn" href="'+fileUrl(f.dirPath)+'">📁 '+esc(f.dirName)+'</a>');
  f.extraFiles.forEach(x=>disk.push('<a class="diskbtn" href="'+fileUrl(x.path)+'">📎 '+esc(x.name)+'</a>'));

  dr.innerHTML =
    '<div class="dh">'+
      '<div class="row1"><span class="id mono">'+f.id+'</span>'+(f.critical?'<span class="star" style="color:#f59e0b">★ critical</span>':'')+
        '<button class="close" id="drClose">×</button></div>'+
      '<h2>'+esc(f.title)+'</h2>'+
      '<div class="row2"><span class="pill" style="background:'+statusVar(f.status)+'">'+(STATUS_LABEL[f.status]||f.status)+(f.epicBlocked?' ⚠':'')+'</span>'+
        (f.type==="epic"?'<span class="tbadge" title="status is the derived phase rollup">rollup</span>':'')+
        '<span class="tbadge">'+f.type+'</span>'+mods+'</div>'+
    '</div>'+
    '<div class="dbody">'+
      '<div class="sect"><h3>Details</h3><div class="grid">'+
        kv.map(([k,v])=>'<div class="kv"><div class="k">'+k+'</div><div class="v">'+v+'</div></div>').join("")+
        '</div>'+touches+'</div>'+
      (lineage.length?'<div class="sect"><h3>Lineage</h3><div class="grid">'+lineage.join("")+'</div></div>':'')+
      (linksHtml?'<div class="sect"><h3>Doc links</h3>'+linksHtml+'</div>':'')+
      '<div class="sect"><h3>Feature</h3><div class="md">'+mdToHtml(f.body, f.dirPath)+'</div></div>'+
      (f.hasSanity?'<div class="sect"><h3>Sanity checks</h3><div class="md sanitybox">'+mdToHtml(f.sanity, f.dirPath)+'</div></div>':'')+
      '<div class="sect"><h3>Open on disk</h3><div class="diskrow">'+disk.join("")+'</div></div>'+
    '</div>';

  dr.querySelector("#drClose").onclick=closeDrawer;
  dr.querySelectorAll("[data-goto]").forEach(n=>n.onclick=()=>{ location.hash=n.dataset.goto; });
  dr.classList.add("open"); dr.setAttribute("aria-hidden","false");
  document.getElementById("scrim").classList.add("open");
  dr.querySelector(".dbody").scrollTop=0;
}
function closeDrawer(){
  document.getElementById("drawer").classList.remove("open");
  document.getElementById("drawer").setAttribute("aria-hidden","true");
  document.getElementById("scrim").classList.remove("open");
  if(location.hash) history.replaceState(null,"", location.pathname+location.search);
}

/* ---------- doc reader ---------- */
let readerStack = [];
function openDoc(key){ if(!DOCS[key]) return; readerStack.push(key); renderReader(); }
function readerBack(){ readerStack.pop(); if(readerStack.length) renderReader(); else closeReader(); }
function closeReader(){
  readerStack = [];
  const r=document.getElementById("reader");
  r.classList.remove("open"); r.setAttribute("aria-hidden","true");
  document.getElementById("readerScrim").classList.remove("open");
}
function renderReader(){
  const key = readerStack[readerStack.length-1];
  const doc = DOCS[key];
  const r = document.getElementById("reader");
  if(!doc){ closeReader(); return; }
  const name = key.split("/").pop();
  const raw = doc.abs ? '<a class="rraw" href="'+fileUrl(doc.abs)+'" title="Open the raw file on disk">Open raw ↗</a>' : '';
  let body;
  if(doc.kind==="md")
    body = '<div class="md reader-md">'+mdToHtml(doc.content, dirOf(doc.abs))+'</div>';
  else if(doc.kind==="code")
    body = '<div class="reader-code"><div class="codehead mono">'+esc(doc.lang||"text")+'  ·  '+esc(key)+'</div><pre><code>'+esc(doc.content)+'</code></pre></div>';
  else if(doc.kind==="missing")
    body = '<div class="docnote">This document hasn’t been written yet.<div class="mono np">'+esc(key)+'</div></div>';
  else
    body = '<div class="docnote">Large or binary file — open it on disk.'+(raw?'<div class="np">'+raw+'</div>':'')+'</div>';
  const back = readerStack.length>1 ? '<button class="riconbtn" id="rBack" title="Back">←</button>' : '';
  r.innerHTML =
    '<div class="reader-head">'+
      '<div class="rh-left">'+back+
        '<div class="rh-title"><span class="rh-name">'+esc(name)+'</span><span class="rh-path mono">'+esc(key)+'</span></div>'+
      '</div>'+
      '<div class="rh-right">'+(doc.kind!=="binary"?raw:'')+'<button class="riconbtn" id="rClose" title="Close">×</button></div>'+
    '</div>'+
    '<div class="reader-body"><div class="reader-col">'+body+'</div></div>';
  const b=r.querySelector("#rBack"); if(b) b.onclick=readerBack;
  r.querySelector("#rClose").onclick=closeReader;
  r.classList.add("open"); r.setAttribute("aria-hidden","false");
  document.getElementById("readerScrim").classList.add("open");
  r.querySelector(".reader-body").scrollTop=0;
}

/* ---------- theme ---------- */
function applyTheme(t){
  if(t) document.documentElement.setAttribute("data-theme",t);
  else document.documentElement.removeAttribute("data-theme");
}
(function initTheme(){ const t=localStorage.getItem("board-theme"); if(t) applyTheme(t); })();
document.getElementById("themeBtn").onclick=()=>{
  const cur=document.documentElement.getAttribute("data-theme");
  const dark=matchMedia("(prefers-color-scheme:dark)").matches;
  const next = cur ? (cur==="dark"?"light":"dark") : (dark?"light":"dark");
  applyTheme(next); localStorage.setItem("board-theme",next);
};

/* ---------- wire up ---------- */
buildChipRow("modFilter", MODULE_ORDER, state.modules, modVar);
buildChipRow("typeFilter", TYPE_ORDER, state.types, null);
buildChipRow("verFilter", ["pass","untested","fail"], state.verify, null);
document.getElementById("groupSeg").querySelectorAll("button").forEach(b=>b.onclick=()=>{
  state.group=b.dataset.g;
  document.getElementById("groupSeg").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b));
  render();
});
document.getElementById("critChip").onclick=function(){ state.crit=!state.crit; this.classList.toggle("on",state.crit); render(); };
document.getElementById("search").addEventListener("input",e=>{ state.q=e.target.value.trim(); render(); });
document.getElementById("clearBtn").onclick=()=>{
  state.q=""; state.crit=false; state.modules.clear(); state.types.clear(); state.statuses.clear(); state.verify.clear();
  document.getElementById("search").value="";
  document.querySelectorAll(".chip").forEach(c=>{c.classList.remove("on"); if(c.classList.contains("mod"))c.style.background="";});
  render();
};
document.getElementById("scrim").onclick=closeDrawer;
document.getElementById("readerScrim").onclick=closeReader;
document.addEventListener("click",e=>{
  const a = e.target.closest ? e.target.closest("a[data-doc]") : null;
  if(!a) return;
  e.preventDefault();
  openDoc(a.getAttribute("data-doc"));
});
window.addEventListener("keydown",e=>{
  if(e.key!=="Escape") return;
  if(document.getElementById("reader").classList.contains("open")) readerBack();
  else closeDrawer();
});
window.addEventListener("hashchange",syncHash);
function syncHash(){
  closeReader();
  const id=decodeURIComponent(location.hash.replace(/^#/,""));
  if(id && BY_ID[id]) openDrawer(id); else closeDrawer();
}

renderStats();
render();
syncHash();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
