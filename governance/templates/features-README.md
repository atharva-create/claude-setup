# Feature Registry & ID Governance

This directory is the **single, queryable spine** that ties every unit of work to its
design, its deploys, its tests, and its regressions. It exists so we can backtrack any
change and so **nothing ships without a feature ID.**

> This file is the **process authority** (feature / bug / backlog / epic / sanity check /
> feature ID). Keep it separate from any *domain* glossary your project keeps — that
> describes the product; this describes the process. The engineering decision behind it
> is [ADR — Feature-ID governance](../docs/adr/{{ADR_FILE}}).
>
> **Project settings** (id prefix, deploy model, module taxonomy) live in
> [`../scripts/_config.py`](../scripts/_config.py) — the single source of truth every
> tool and hook reads. This project's prefix is **`{{PREFIX}}`**.

## What is a feature?

One **shippable unit of functionality** — roughly a PR or a small cluster of PRs. Not a
whole module (too coarse) and not a single commit (too fine). Editing existing
functionality does **not** rewrite its entry in place — it becomes a **new feature** that
links back to its predecessor: `supersedes:` when it **fully replaces** the old feature,
or `amends:` when it changes only **part** of the old feature's code and the old feature
stays live (see *Supersede vs amend*). Both form a lineage chain. Bugs and backlog ideas
live in the same registry, distinguished by `type:`.

Design artifacts (plans, specs, ADRs, GSD `.planning/`) are **referenced** by a feature
via `links:`, never duplicated into it.

## Epics & phases (multi-phase work)

Some work is too big for one ship and lands as a **series of independently deployable
slices**. Model that as an **epic**: a `type: epic` feature that is a pure umbrella — it
holds the overarching design + epic-level acceptance criteria and **never deploys itself**.
Each phase is an ordinary feature that points up at the epic:

- `epic: {{PREFIX}}-####` on the phase → its umbrella (validated: must be a real `type: epic`).
- `phase: <int>` on the phase → ordering within the epic.

The ID grammar, one-folder-per-id layout, branch convention, and git hooks are
**unchanged** — every phase is a normal `{{PREFIX}}-####` with its own branch and status.
The epic just groups them (rollup in `REGISTRY.md` + a board lane).

**The rule that decides when to make an epic:** a "phase" is an **independently deployable
slice** (its own ship). If the parts are merely internal build steps of a *single* deploy,
they are **not** epic-phases — they stay **one feature** and live in your implementation
plan, not the registry. This keeps epics rare and meaningful and prevents ID proliferation.

**An epic's status is *derived* from its phases, not hand-set** — **all** phases at
production → `shipped-prod`; **all** at staging-or-better → `shipped-sit`; otherwise
`in-dev`, with a **⚠ blocked** flag if any phase is blocked. `build-registry.py` shows the
derived value and **warns** if a stored epic `status` drifts from the rollup.

An epic is excluded from the deploy gate (like `backlog`): a PR/push must reference a real
**phase** feature, never the epic.

## Layout

```
features/
  README.md                 # this file — the system spec
  REGISTRY.md               # GENERATED index (do not hand-edit; run build-registry.py)
  {{PREFIX}}-0042-accounts-manage/
    FEATURE.md              # the manifest: front-matter + required sections
    SANITY.md               # per-feature regression checklist
    qa/                     # dated QA/eval reports written by testing agents
      2026-07-28-report.md
```

The manifest filename is **always `FEATURE.md`** (even for bugs/backlog) so tooling can
glob one deterministic path `features/*/FEATURE.md`. Type is a front-matter field.

## The ID

`{{PREFIX}}-####` — one **global, zero-padded, monotonic** counter for every type. The ID
is a **permanent, semantics-free handle**: it never encodes the module or type (those are
front-matter, and reclassifiable), and it is **never reassigned or reordered** once minted.
Inbound links stay valid forever. (Width and prefix are set in `scripts/_config.py`.)

## `FEATURE.md` front-matter (the machine contract)

Testing/eval agents parse these keys — keep them present and valid.

| key | values / type | notes |
|-----|---------------|-------|
| `id` | `{{PREFIX}}-####` | matches the folder prefix; permanent |
| `title` | string | human title |
| `type` | `feature` \| `bug` \| `backlog` \| `epic` | `epic` = a multi-phase umbrella |
| `status` | `backlog` \| `planned` \| `in-dev` \| `shipped-sit` \| `shipped-prod` \| `archived` \| `blocked` | **pre-deploy lifecycle hint.** In gated deploy models the `shipped-*` state shown in `REGISTRY.md`/board is **derived from git**, not this field — hand-set only pre-deploy values (`backlog`→`in-dev`, or `blocked`/`archived`). In *tracking* mode this field is authoritative |
| `module` | list of codes | your area codes (see `_config.MODULES`); empty allowed |
| `critical` | bool | `true` ⇒ always in the sanity sweep |
| `depends_on` | list of `{{PREFIX}}-####` | features this builds on |
| `touches` | list of kebab tags | shared subsystems, e.g. `auth` `payments` `cache` — drives the sanity sweep |
| `supersedes` | id \| null | lineage: what this **fully replaces** (predecessor → superseded/archived). 1:1 |
| `superseded_by` | id \| null | reciprocal of another feature's `supersedes` |
| `amends` | list of ids | **partial edit**: predecessors whose code this changed *without* replacing them (they stay live). N:M |
| `amended_by` | list of ids | reciprocal of another feature's `amends` |
| `related` | list of ids | see-also links |
| `epic` | id \| null | this feature is a **phase** of that `type: epic` umbrella |
| `phase` | int \| null | ordering label within the epic |
| `branch` | string \| null | `feat/{{PREFIX}}-####-slug` |
| `prs` | list of ints | PR numbers |
| `sit_sha` / `prod_sha` | short SHA \| null | **derived from git** in gated models; the stored field is only a fallback for a bare clone with no fetched refs |
| `verification` | `pass` \| `fail` \| `untested` | flipped by testing agents |
| `verified_at` | ISO date \| null | |
| `created` | ISO date | |
| `links` | map of `type: repo/relative/path` | design, adr, eval, runbook, … |

Required body sections: **Summary** · **Acceptance Criteria** (checkable) · **How to
Verify** (flow, URLs, creds pointer) · **Known Bugs** (links to `type: bug` entries).

## Lifecycle

`backlog → planned → in-dev → shipped-sit → shipped-prod` (or `archived` / `blocked`).
A backlog idea is a lightweight entry with `type: backlog`. When picked up it gets a full
`FEATURE.md`, `type: feature`, and `status: in-dev` — **the ID never changes**.

The **pre-deploy** hops are hand-set in `status`. The **deploy** hops depend on your
**deploy model** (`_config.DEPLOY_MODEL`):

- **`single`** — one production branch. A feature is `shipped-prod` once its `{{TRAILER}}:`
  commits reach `origin/{{PROD_BRANCH}}`. Derived from git — never hand-flip it.
- **`two-branch`** — a staging branch then production. `shipped-sit` once commits reach the
  staging branch, `shipped-prod` once they reach production. Derived from git.
- **`tracking`** — no deploy branches. No deploy gate; the stored `status` field is shown
  as-is.

In the gated models there is no "flip the status on the deploy branch" step to forget:
run `git fetch` and regenerate the registry on **any** branch for the same, correct answer.
(`board.html` is not committed — regenerate on demand with `python scripts/build-board.py`.)

## The deploy gate — no deploy without a feature ID

The ID rides in the **branch name** `feat/{{PREFIX}}-####-slug` and a **`{{TRAILER}}:
{{PREFIX}}-####` commit trailer**. Enforcement is layered (active layers depend on the
deploy model):

| Layer | Gates | Mechanism |
|-------|-------|-----------|
| `commit-msg` hook | every code commit | requires a `{{TRAILER}}:` trailer (exempts merge/revert, `docs:`/`chore:`) |
| `pre-push` hook | push → a deploy branch | requires a valid id whose folder exists (a push-only branch with no PR has no other gate) |
| `feature-id-gate.yml` | PR → the production branch | CI asserts a valid ID + fresh, lint-clean registry + predecessor SANITY updated |
| branch protection | deploy branches | makes the checks required (configure in your host's settings) |

Install the hooks once per clone:

```bash
bash scripts/setup-feature-governance.sh     # sets core.hooksPath=.githooks
```

## The sanity sweep — catching collateral breakage

Every actively-worked feature carries a **`SANITY.md`**: a short, stable regression
checklist ("is this feature still alive after an unrelated change?"), distinct from
Acceptance Criteria.

When any change ships, run the sanity checks of the **affected set**:

```
scope = the changed feature
      + every feature sharing a `module:` with it
      + every feature whose `touches:` intersects the change
      + every `critical: true` feature      (minus archived)
      + epic siblings + any amended predecessors
```

Compute it with:

```bash
python scripts/sanity-scope.py --feature {{PREFIX}}-0042
python scripts/sanity-scope.py --module CORE --touches auth,cache   # manual override
```

**Tag `touches` with real subsystems, not layers.** Good: `auth`, `payments`, `cache`,
`scheduler`. Bad: `react`, `api`, `database` — horizontal layers are on everything, so
`sanity-scope` auto-ignores them (a `LAYER_TAGS` stop-list plus any tag on >30% of
features) to keep the sweep affordable; `module` and `critical` still apply.

**Supersede & amend rule:** whenever `{{PREFIX}}-B` names a predecessor — `supersedes:` (full
replace) or `amends:` (partial edit) — shipping it **must update each named predecessor's
`SANITY.md`** to match the new behavior. The Prod CI gate enforces this on the diff for
*both* relations.

## Supersede vs amend (full replace vs partial edit)

| relation | meaning | predecessor after | cardinality |
|----------|---------|-------------------|-------------|
| `supersedes` | B **replaces** A — A is obsolete | superseded / `archived` | 1:1 (+ reciprocal `superseded_by`) |
| `amends` | B changed **part** of A; A still stands and owns the rest | stays active | **N:M** (+ reciprocal `amended_by`) |

Use `supersedes` when the predecessor should no longer be the source of truth for that
functionality. Use `amends` for the common case — you touched a slice of an existing
feature's code without retiring it. `build-registry.py` lints reciprocity and unknown ids
for both, and renders an `Amends` column.

**Which feature owns a given file or line?** The git tree answers it with **no extra
bookkeeping** — every code commit carries a `{{TRAILER}}:` trailer, so
`scripts/feature-attribution.py` reconstructs it directly:

```bash
python scripts/feature-attribution.py --file scripts/build-registry.py   # features that touched a path
python scripts/feature-attribution.py --blame scripts/_fm.py             # current per-line/region owner
python scripts/feature-attribution.py --feature {{PREFIX}}-0001          # reverse: files a feature touched
```

Attribution is **forward-only**: commits before governance existed (and exempted merge/
`docs:`/`chore:` commits) carry no trailer and show as `(unattributed)`.

## How testing/eval agents use this (two-way contract)

1. **Read** `FEATURE.md`: Acceptance Criteria + How-to-Verify + `links`.
2. **Run** the verification, plus the sanity sweep for the affected set above.
3. **Write** a dated report into `features/{{PREFIX}}-####/qa/YYYY-MM-DD-<slug>.md`.
4. **Flip** `verification:` (and `verified_at:`) in the front-matter to record the result.

## Tooling

| script | purpose |
|--------|---------|
| `scripts/_config.py` | **the single source of truth** — id prefix, deploy model, module taxonomy |
| `scripts/build-registry.py` | regenerate `REGISTRY.md`; lint ids/enums/lineage (`--check` for CI) |
| `scripts/build-board.py` | regenerate the on-demand `board.html` |
| `scripts/sanity-scope.py` | resolve the affected set for a change |
| `scripts/feature-attribution.py` | reconstruct feature↔code from the trailer (`--file`/`--blame`/`--feature`) |
| `scripts/ci-feature-gate.py` | the Prod PR gate check |
| `scripts/setup-feature-governance.sh` | install the git hooks (once per clone) |

## Adding a new feature (quick start)

```bash
# 1. claim the next id: highest {{PREFIX}}-#### in features/ + 1
# 2. scaffold
mkdir -p features/{{PREFIX}}-0058-my-thing/qa
$EDITOR features/{{PREFIX}}-0058-my-thing/FEATURE.md   # front-matter + 4 sections
$EDITOR features/{{PREFIX}}-0058-my-thing/SANITY.md    # 3–5 must-still-work checks
# 3. branch + commit with the trailer
git checkout -b feat/{{PREFIX}}-0058-my-thing
git commit -m "feat(x): ...

{{TRAILER}}: {{PREFIX}}-0058"
# 4. regenerate the index
python scripts/build-registry.py
```
