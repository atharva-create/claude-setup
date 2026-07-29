# Install Feature-ID Governance — runbook for Claude

**You are an AI agent installing the Feature-ID governance system into the current
project.** Follow these steps exactly. The system gives the repo a committed `features/`
registry (features, bugs, backlog, epics), git-derived deploy status, a scoped sanity
sweep, git-tree code attribution, and hard enforcement via git hooks + CI — so nothing
ships without a feature ID. Full spec: [`../features/README.md`](templates/features-README.md).

This runbook works for a **new** project (bootstrapped from claude-setup) and for
**retro-adding** governance to an **existing** repo. It is safe to re-run: it won't
clobber an existing `scripts/_config.py`, `.githooks/governance.conf`, or a CLAUDE.md that
already has the governance section.

---

## Step 1 — Preconditions

1. Confirm you are inside a git repository: `git rev-parse --show-toplevel`. If not, tell
   the user and offer to run `git init` (do not proceed without their OK).
2. Confirm the module is present: the `governance/` directory (containing `install.sh`,
   `scripts/`, `githooks/`, `templates/`) must exist at the repo root. If it is missing,
   the repo was not set up from claude-setup — tell the user to copy the `governance/`
   directory from their claude-setup clone into this repo, then re-run.
3. Confirm `python3` is available (`python3 --version`). The scripts are stdlib-only.

## Step 2 — Ask the user (do NOT assume)

Use the AskUserQuestion tool to collect these. The prefix default is **FT** (the fixed
neutral prefix); confirm it but let them override.

- **Deploy / state model** — this determines which gates are active. Options:
  - `single` — one production branch (usually `main`). A feature becomes `shipped-prod`
    once its commits reach that branch. pre-push gates the branch; CI gates PRs into it.
    *(Best default for most repos.)*
  - `two-branch` — a staging branch (e.g. `develop`) then production (e.g. `main`).
    `shipped-sit` at staging, `shipped-prod` at production. Gates both.
  - `tracking` — no deploy branches: registry + commit trailer + sanity sweep only, no
    deploy gate. For experimental / solo repos.
- If `single` or `two-branch`: confirm the **production branch name** (default `main`) and,
  for two-branch, the **staging branch name** (default `develop`).
- **Module / area codes** (optional) — a comma-separated list like `CORE,API,UI,INFRA`
  that features can be tagged with. Leave empty to accept any code (no allow-list). This
  can be changed later in `scripts/_config.py`.
- **Prefix** — confirm `FT` or take an override (short, UPPERCASE, permanent for the repo).

## Step 3 — Run the installer

Invoke `governance/install.sh` with the answers as environment variables. Examples:

```bash
# single-branch (main = prod), modules CORE/API/UI:
PREFIX=FT DEPLOY_MODEL=single PROD_BRANCH=main MODULES="CORE,API,UI" \
  bash governance/install.sh

# two-branch (develop = staging, main = prod):
PREFIX=FT DEPLOY_MODEL=two-branch PROD_BRANCH=main STAGING_BRANCH=develop \
  bash governance/install.sh

# tracking only (no deploy gate):
PREFIX=FT DEPLOY_MODEL=tracking bash governance/install.sh
```

The installer materializes: `scripts/` (the tools + `_config.py` rendered from the
answers), `.githooks/` (hooks + `governance.conf`), `features/README.md` +
`features/.templates/`, `docs/adr/NNNN-feature-id-governance.md`, and — for gated models —
`.github/workflows/feature-id-gate.yml`. It appends the rules section to `CLAUDE.md`, adds
`features/board.html` to `.gitignore`, installs the hooks (`core.hooksPath=.githooks`), and
builds the first registry.

## Step 4 — Verify (do this, don't skip)

1. `python3 scripts/build-registry.py` runs without error (says "no features" on a fresh
   repo — expected).
2. Hooks are active: `git config core.hooksPath` prints `.githooks`.
3. The commit-msg gate works: attempt a throwaway commit with no trailer on a scratch
   change and confirm it is **rejected**, then that a message with a valid
   `<TRAILER>: <PREFIX>-0001` trailer would pass. (Use `FEATURE_ID_SKIP=1` only to clean up
   any scratch commit.)
4. `scripts/_config.py` shows the chosen `PREFIX`, `DEPLOY_MODEL`, branches, and `MODULES`.

## Step 5 — Report next steps to the user

- Create the first feature by copying the scaffold:
  `cp -r features/.templates features/<PREFIX>-0001-my-thing`, then fill in `FEATURE.md`
  and `SANITY.md` (set `id`, `title`, real `module`/`touches`).
- Branch as `feat/<PREFIX>-0001-my-thing` and commit with a
  `<TRAILER>: <PREFIX>-0001` trailer.
- Run `python scripts/build-registry.py` to update `features/REGISTRY.md`; commit it.
- For gated models, make the CI check **required** via branch protection — the exact
  `gh api ... branches/<prod>/protection` command is in the generated
  `docs/adr/NNNN-feature-id-governance.md`.
- Regenerate the board any time with `python scripts/build-board.py` (it opens
  `features/board.html`, which is gitignored).

## If the user is NOT driving this through Claude

They can run the installer directly — it is fully non-interactive via env vars (see Step 3).
`governance/install.sh --help`-style usage is documented at the top of that file.
