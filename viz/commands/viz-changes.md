# /viz-changes — visualize what just changed (the 4 views of the diff)

**Goal:** Show a non-coder *what Claude just changed* — the pieces touched, how data flows
through them, how shapes change, and the step-by-step — so they can make a go / no-go call.

## Steps (follow exactly)

1. **Read `viz/VISUAL-STYLE.md`** and obey it (Clarity Standard, color block, escaping, recipes, §6 payload).
2. **Determine scope = uncommitted working-tree edits** (Decision 5):
   - `git status --porcelain` and `git diff` (and `git diff --staged`). Optional argument: a
     specific commit or range (e.g. `/viz-changes HEAD~1`) — if given, diff that instead.
3. **NO-CODE-SKIP (hard rule):** if there are **no code changes** in scope, print exactly
   **"No code changes — nothing to visualize"** and **write nothing**. Do not call build-viz. Stop.
4. **Ground in the diff:** read the actual changed files / hunks. The diagram describes *only the
   changed scope* — the pieces touched and their immediate neighbors, not the whole system.
5. **Build the `VIZ` payload** (VISUAL-STYLE §6):
   - `mapD2`: the touched pieces + immediate neighbors; mark the **changed** piece(s) with `here`.
   - `mapNodes`, `flow`, `shape`, `steps`, `narr`, `title`, `scope:"what just changed"`,
     `breadcrumb`, `legend:true`, `status:"ok"`.
   - `footer`: `Drawn from <changed files> · commit <SHA> · valid as of <timestamp>` — list the
     **actual changed files** (T5).
6. **Self-check (§7):** re-read the diff; does the picture match what changed? Fix or add
   `uncertain:[...]` notes. Keep scope to the change.
7. **Render:** `node viz/build-viz.cjs --payload <tmp>.json --name changes` (d2 on `PATH` or `~/.local/bin/d2`).
8. **Report** the `OPEN file://…/viz/output/changes.viz.html` line.

## Notes
- Overwrites `viz/output/changes.viz.{md,html}` in place (Decision 7).
- The "you are here" glow marks the changed node — the thing the user is judging.
