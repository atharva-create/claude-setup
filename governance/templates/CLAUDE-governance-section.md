## Feature-ID Governance (MANDATORY)

**Nothing ships without a feature ID.** Every unit of work is registered under
`features/{{PREFIX}}-####-slug/` with a `FEATURE.md` manifest. Full spec:
[features/README.md](features/README.md). Project settings (prefix, deploy model, module
taxonomy) live in [scripts/_config.py](scripts/_config.py).

- **Every new functionality is a new feature ID.** Before shipping, create
  `features/{{PREFIX}}-####-slug/FEATURE.md` (+ `SANITY.md`) — claim the next id =
  highest `{{PREFIX}}-####` + 1.
- **Editing existing functionality = a NEW feature** that links to the predecessor:
  `supersedes: {{PREFIX}}-<old>` if it **fully replaces** it, or `amends: [{{PREFIX}}-<old>]`
  if it changes only **part** of it (predecessor stays live). Either way **update each named
  predecessor's `SANITY.md`** — the Prod CI gate enforces this on the diff for both relations.
- **Who owns this code?** `python scripts/feature-attribution.py --file <path>` (or
  `--blame <path>` / `--feature {{PREFIX}}-####`) reconstructs feature↔code from the
  `{{TRAILER}}:` commit trailer — forward-only; pre-governance commits show `(unattributed)`.
- **Carry the id** in the branch name `feat/{{PREFIX}}-####-slug` AND a
  `{{TRAILER}}: {{PREFIX}}-####` commit trailer.
- **Install the hooks once per clone:** `bash scripts/setup-feature-governance.sh`
  (`commit-msg` requires the trailer; `pre-push` blocks deploy-branch pushes without a valid id).
- **Regenerate the index after any feature change:** `git fetch && python scripts/build-registry.py`
  (CI runs `--check`; a stale or lint-failing registry blocks the Prod PR).
- **Deploy status is derived from git, not hand-set:** a feature is `shipped-sit`/`shipped-prod`
  once its `{{TRAILER}}:` commits reach the configured staging/production branch — so
  `git fetch` first, then regenerating renders the correct status on **any** branch.
  `board.html` is not committed (regenerate on demand: `python scripts/build-board.py`).
- **Run the scoped sanity sweep** for any change: `python scripts/sanity-scope.py --feature {{PREFIX}}-####`,
  then execute each affected feature's `SANITY.md`.
- Enforcement layers: `commit-msg` + `pre-push` git hooks (local), `feature-id-gate.yml` CI +
  branch protection (host). Emergency bypass `FEATURE_ID_SKIP=1` is discouraged and audited.
