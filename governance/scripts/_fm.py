"""Minimal, dependency-free reader/writer for FEATURE.md YAML front-matter.

We fully control the front-matter grammar (see features/README.md), so this
handles exactly the constrained subset we emit and nothing more:

  key: scalar          # "quoted" | null | true | false | int | bare string
  key: [a, b, c]       # inline flow list (elements never contain commas)
  key: {k: v, k2: v2}  # inline flow map  (values never contain commas)

That keeps build-registry.py / sanity-scope.py runnable anywhere (git hooks,
CI, a bare checkout) without `pip install pyyaml`. The richer bootstrap seed
(.backfill-seed.yml) is parsed with PyYAML by backfill-stubs.py instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _config  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = REPO_ROOT / "features"

# Canonical front-matter key order (used by dump_frontmatter for stable output).
# `epic` (an MR-#### grouping ref on a phase) and `phase` (an ordering scalar) sit with
# the lineage cluster; both are plain scalars, so the parser handles them unchanged.
# `amends`/`amended_by` are the partial-edit lineage pair (N:M lists) — a feature that
# changed *part* of another without replacing it; distinct from supersedes (full replace).
FIELD_ORDER = [
    "id", "title", "type", "status", "module", "critical",
    "depends_on", "touches", "supersedes", "superseded_by", "amends", "amended_by",
    "related", "epic", "phase",
    "branch", "prs", "sit_sha", "prod_sha",
    "verification", "verified_at", "created", "links",
]


def _coerce(token: str):
    t = token.strip()
    if t == "" or t == "null" or t == "~":
        return None
    if t == "true":
        return True
    if t == "false":
        return False
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        return t[1:-1]
    if t.lstrip("-").isdigit():
        return int(t)
    return t


def _parse_value(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_coerce(x) for x in inner.split(",") if x.strip() != ""]
    if raw.startswith("{") and raw.endswith("}"):
        inner = raw[1:-1].strip()
        out = {}
        if not inner:
            return out
        for pair in inner.split(","):
            if ":" not in pair:
                continue
            k, v = pair.split(":", 1)
            out[k.strip()] = _coerce(v)
        return out
    return _coerce(raw)


def parse_frontmatter(text: str) -> dict:
    """Return the front-matter block (between the first two `---` fences) as a dict."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        data[key.strip()] = _parse_value(raw)
    return data


def read_feature(path: Path) -> dict:
    d = parse_frontmatter(path.read_text(encoding="utf-8"))
    d["_path"] = str(path)
    d["_dir"] = str(path.parent)
    return d


def _dump_scalar(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    s = str(v)
    # Quote when the value could confuse the reader (colon, leading special, empty).
    if s == "" or ":" in s or s.strip() != s or s in ("null", "true", "false"):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def dump_frontmatter(data: dict) -> str:
    """Serialize a feature dict to the controlled front-matter subset (stable order)."""
    out = ["---"]
    keys = [k for k in FIELD_ORDER if k in data] + [
        k for k in data if k not in FIELD_ORDER and not k.startswith("_")
    ]
    for k in keys:
        v = data[k]
        if isinstance(v, list):
            out.append(f"{k}: [" + ", ".join(_dump_scalar(x) for x in v) + "]")
        elif isinstance(v, dict):
            inner = ", ".join(f"{ik}: {_dump_scalar(iv)}" for ik, iv in v.items())
            out.append(f"{k}: {{{inner}}}")
        else:
            out.append(f"{k}: {_dump_scalar(v)}")
    out.append("---")
    return "\n".join(out)


def iter_feature_files():
    """Yield every features/<PREFIX>-*/FEATURE.md path, sorted by id."""
    if not FEATURES_DIR.exists():
        return
    for p in sorted(FEATURES_DIR.glob(_config.FEATURE_GLOB)):
        yield p


def load_all() -> list[dict]:
    return [read_feature(p) for p in iter_feature_files()]
