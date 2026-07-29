# Feature-ID governance: a `features/` registry gates every deploy

**Status:** accepted

Work tracking tends to fragment across non-unifying conventions — a flat `tasks/` folder, a
`bugs/` folder, scattered `docs/`, and a planning tool's own directory — with no single spine
linking a shipped change to its design, deploy SHAs, tests, and regressions. We introduce
**`features/`**: a registry where every shippable unit is a folder `features/{{PREFIX}}-####-slug/`
whose `FEATURE.md` front-matter is the machine-readable record and whose links point out to the
existing artifacts (no duplication). One **global, permanent, semantics-free `{{PREFIX}}-####` id**
identifies each entry. The rule this enables: **no deploy without a feature ID.** See
[features/README.md](../../features/README.md). Project settings (prefix, deploy model, module
taxonomy) live in [scripts/_config.py](../../scripts/_config.py).

**Why the id carries no meaning:** it is deliberately a bare counter, not `OUT-012` or
`FEAT-0042`, because it must be a stable handle that never lies — a module-prefixed id becomes
wrong the moment a feature is reclassified or spans modules, and it can never be safely
reassigned. Module and type therefore live in front-matter (reclassifiable), while the id stays
constant so every inbound link and every historical `qa/` report remains valid forever.

**Why gating is layered.** Deploy paths are often **asymmetric**. A PR into the production branch
can be gated by a CI `pull_request` check. But a branch you `git push` directly (a staging branch
with no PR) can only be gated **client-side** by a `pre-push` hook. Hence: a `commit-msg` hook
(trailer present), a `pre-push` hook (deploy-branch gate: valid id whose folder exists), a
`feature-id-gate.yml` CI job (Prod gate: valid id + fresh lint-clean registry + predecessor sanity
updated), and host branch protection to make the checks required. Which layers are active depends
on the configured deploy model (`single` / `two-branch` / `tracking`).

Each feature also owns a `SANITY.md` regression checklist so any change runs a **scoped** sweep
(same-module + `touches`-intersecting + `critical`) — catching collateral breakage without running
every check every time.

**Operational note — branch protection is out-of-band.** Making the CI check *required* lives in
your host's settings, not the repo. On GitHub, after merge:
```bash
gh api -X PUT repos/:owner/:repo/branches/{{PROD_BRANCH}}/protection \
  -f 'required_status_checks[strict]=true' \
  -f 'required_status_checks[contexts][]=feature-id-gate' \
  -F 'enforce_admins=true' -F 'required_pull_request_reviews=null' \
  -F 'restrictions=null'
```
On a push-only staging branch, the `pre-push` hook is the primary gate (a required PR check there
would break the local-merge-and-push flow).

**Considered alternatives:**
- *Module-prefixed ids (`OUT-012`)* — rejected: encodes a fact (module) that changes; can't
  reclassify or span modules without the id lying, and ids can never be reassigned.
- *Absorb all `docs/` and `bugs/` into feature folders* — rejected: a large, link-breaking
  migration; the registry-of-links model gets the same spine by referencing artifacts in place.
- *Coarse epic-level features (one per module)* — rejected: an id would no longer map to a
  deployment, making "no deploy without a feature ID" fuzzy.
- *Physically move items between `backlog/ active/ shipped/`* — rejected: churns history and breaks
  relative links; a `status:` field moves nothing.
- *Docs-only enforcement (prose in CLAUDE.md)* — rejected as the sole mechanism: relies on
  discipline and leaves a manual `git push` ungated; kept as the human-facing contract on top of
  the hard hooks/CI.

## Addendum — epics as an optional grouping layer (multi-phase work)

**Status:** accepted (extends this ADR).

Multi-phase programs were modeled as N separate features with the phase name living only as free
text in the title — invisible to tooling and impossible to roll up. We add an **optional epic
layer**: a `type: epic` umbrella feature that groups a program's phases; each phase is an ordinary
feature carrying `epic: {{PREFIX}}-####` (+ an ordering `phase:`). The registry gains an `## Epics`
rollup and the board an epic lane; nothing else about the ID grammar, layout, branch convention,
or hooks changes.

**Why this does *not* re-open "coarse epic-level features":** that alternative was rejected because
*making the epic the unit of work* would leave an id that no longer maps to a deployment. Here
features stay **fine-grained and each phase still maps 1:1 to a deploy**; the epic is layered
*around* them, never *instead of* them, and is **excluded from the deploy gate** (like `backlog`) —
a push/PR must always name a real phase feature. An epic's status is **derived from its phases**,
so it never over-claims.

## Addendum — partial edits: the `amends` relation + git-tree attribution

**Status:** accepted (extends this ADR).

The original design gave lineage exactly one relation, `supersedes` — a whole-feature, 1:1 pointer
meaning "B **replaces** A." But most changes are *partial*: B edits only part of A's code and A
keeps living. `supersedes` is wrong for that (it implies the predecessor is obsolete), so partial
edits had nowhere to go, and there was no way to answer "which feature last touched this file/line."

Two additive mechanisms close the gap:

- **Feature level — a second relation, `amends` / `amended_by`.** N:M, reciprocal, validated
  exactly like `supersedes`: the Prod CI gate requires each amended predecessor's `SANITY.md` in
  the diff, lint checks reciprocity + unknown ids, the registry gains an `Amends` column, and the
  sanity sweep pulls amended predecessors in. The predecessor's **status is untouched** — that is
  the point (it still stands).
- **Git-tree level — `scripts/feature-attribution.py`, needing no new metadata.** The mandatory
  `{{TRAILER}}:` commit trailer already stamps every code commit, so file/line → feature is
  *already* recoverable from `git log`/`git blame`. The tool is a read-side surface over that
  ground truth (`--file` / `--blame` / `--feature`). Attribution is **forward-only**.

## Addendum — deploy status is derived from git, not stored

**Status:** accepted (extends this ADR).

Storing each feature's deploy state as hand-typed front-matter goes stale: a `FEATURE.md` is
versioned **per branch**, so a manual "flip to shipped" lands on whatever branch you run it on and
every *other* branch keeps showing the old status. The fix removes the hand-flip: **deploy state is
derived from git ancestry.** In a gated model a feature is `shipped-*` iff one of its `{{TRAILER}}:`
commits is reachable from the corresponding deploy branch (`scripts/_deploy_state.py`;
`build-registry.py` / `build-board.py` read it). This reuses the same trailer attribution reads, and
mirrors the epic rollup which was already derived. The stored `status` degrades to a pre-deploy
lifecycle hint; a bare clone with no fetched refs falls back to the stored fields with a NOTE.

**Consequences.** (1) Derivation reads remote-tracking refs, so consumers `git fetch` first; CI
fetches the deploy branches before `--check`. (2) `REGISTRY.md` stays committed as a browsable
snapshot but is **branch-independent** — regenerating on any branch yields the same rows. (3)
`board.html` is **not committed** (it embeds machine-specific paths and produces large diffs) — it
is gitignored and regenerated on demand. In `tracking` mode there are no deploy branches, so the
stored `status` is authoritative and none of this derivation runs.
