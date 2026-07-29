# Feature-ID Governance — portable module

A committed, git-derived, deploy-gated **feature registry** you can drop into any project.
Every shippable unit of work (feature, bug, backlog idea, or multi-phase epic) lives under
`features/<PREFIX>-####-slug/` with a `FEATURE.md` manifest, and **nothing ships without a
feature ID**. It gives you:

- a single `features/REGISTRY.md` spine linking work → design → deploys → tests → regressions;
- **deploy status derived from git** (a feature is `shipped-*` once its commits reach a deploy branch — never hand-set, never stale);
- **epics** (multi-phase programs) with a derived rollup status;
- **lineage** — `supersedes` (full replace) and `amends` (partial edit, N:M);
- **git-tree attribution** — which feature touched which file/line, from the commit trailer;
- a **scoped sanity sweep** (same-module + `touches` + `critical`) so a change re-tests only what it can break;
- **hard enforcement** — `commit-msg` + `pre-push` git hooks and a CI gate on the production branch.

Everything is **stdlib Python + bash** — no `pip install`, no dependencies.

## Install

Run the interactive runbook through Claude (it asks for your deploy model, modules, and
prefix, then installs everything):

```
Read and follow governance/INSTALL.md
```

…or install directly, non-interactively:

```bash
PREFIX=FT DEPLOY_MODEL=single PROD_BRANCH=main MODULES="CORE,API,UI" \
  bash governance/install.sh
```

## Deploy models (chosen at install; reconfigurable in `scripts/_config.py`)

| model | branches | gates | deploy status |
|-------|----------|-------|---------------|
| `single` | one prod branch (e.g. `main`) | pre-push on prod + CI on PRs to prod | `shipped-prod` (git-derived) |
| `two-branch` | staging (e.g. `develop`) + prod (`main`) | pre-push on both + CI on PRs to prod | `shipped-sit` → `shipped-prod` (git-derived) |
| `tracking` | none | none (registry + trailer + sanity only) | stored `status` field |

## What's in this module

```
governance/
  INSTALL.md          # runbook for Claude (asks deploy model, then installs)
  install.sh          # non-interactive installer (env-var driven, portable)
  README.md           # this file
  scripts/            # _config.py (settings) + the 7 governance tools
  githooks/           # commit-msg, pre-push, governance.conf, setup-feature-governance.sh
  workflows/          # feature-id-gate.yml CI template
  templates/          # features-README.md, adr, CLAUDE section, FEATURE/SANITY stubs
```

`scripts/_config.py` is the **single source of truth** — the id prefix, deploy model, and
module taxonomy live there; every tool and both hooks read it (the shell side reads the
mirrored `.githooks/governance.conf`).

## Relationship to GSD / other planning

The `features/` registry is the **committed, deploy-gated spine**. It does not replace a
planning tool's local artifacts (e.g. GSD `.planning/phases/*`) — a feature *references*
them via `links:`. Epics here group deployable phases; they are not the same as a planning
tool's milestones, though they map naturally.
