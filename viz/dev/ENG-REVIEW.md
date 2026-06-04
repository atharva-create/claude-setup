# Eng Review — Visual Comprehension Layer (`viz/`)

> **⚠️ SUPERSEDED IN PART (renderer) — read with this caveat.** This review predates the switch to
> **D2**. It was written when the renderer was **Mermaid** + a vendored `viz/vendor/mermaid.min.js`.
> The implementation instead uses **D2 v0.7.1**, which compiles each Map to a self-contained SVG
> embedded directly in the viewer — so there is **no `vendor/` dir and no `mermaid.min.js`**, and
> `--inline` is a no-op (every output is already portable). Wherever this doc says "Mermaid",
> "mermaid.min.js", "~2.8MB", or the light-default-vs-`--inline` split (Decision 6 / CMD-06 / T10),
> treat it as historical context. The live spec of record is `viz/VISUAL-STYLE.md` +
> `viz/commands/*` + `dev/.planning/REQUIREMENTS.md`. Everything else here — architecture, the
> accuracy/self-check mechanism (Decision 2), grouping (Decision 4), the footer, and the T1–T11
> test set — still applies.

> **Status:** Eng review complete. Ready for `/plan-design-review` (run separately), then GSD implementation.
> **Reviews:** `/plan-eng-review` (this doc) + outside-voice challenge (Claude subagent; Codex not installed).
> **Reviewing:** `viz/dev/DESIGN.md`.
> `/office-hours` and `/plan-ceo-review` were intentionally skipped — scope is predefined and personal.

---

## Context

The user is a strongly visual thinker who does not read code fluently. They need to judge
Claude's plans and changes from **diagrams**, not syntax. This builds a reusable "Visual
Comprehension Layer" into the `claude-setup` repo so it ships into every new project: it
turns plans/diffs into four self-explanatory Mermaid views (Module Map, Data Flow,
Transformation, Sequence), rendered both as `.viz.md` (source of truth) and a double-click
`.viz.html` (offline, zero-setup). Phase 1 = static clarity files + slash commands +
CLAUDE.md wiring. Phase 2 = live animated dashboard (deferred).

## Review constraints (from the user)

- Scope predefined and personal. Not re-litigating scope or product direction.
- `/plan-design-review` runs AFTER this, in a separate chat. This review does **not** judge
  visual aesthetics (colors, typography, diagram beauty) — that's design review's job. This
  review = architecture, code bucketing, correctness, accuracy, tests, performance.
- **GSD** handles implementation after planning.
- **Folder rule:** all dev artifacts (DESIGN, this review, plans, notes, fixtures) live under
  `viz/dev/`, which gets **deleted** after development. Anything required at runtime in every
  project must live **outside `dev/` but inside `viz/`** — except the 3 command stubs Claude
  Code physically requires in `.claude/commands/` (see Decision 1).
- Changes outside `viz/` require explicit approval. CLAUDE.md changes are pre-approved.

## What already exists

- `viz/` holds only `viz/dev/DESIGN.md`. No engine files yet — greenfield.
- `.claude/commands/` is the only location Claude Code discovers project slash commands.
  Commands are markdown instruction files (the prior `gsd/*` set was removed).
- `.claude/hooks/` + `.claude/settings.json` already wire a SessionStart hook (superpowers
  bootstrap) and a Stop-hook verification cycle.
- Root `.gitignore` exists. CLAUDE.md is the auto-loaded instruction file (pre-approved to
  edit). No `package.json` / npm tooling — this repo is config + markdown, so "tests" = the
  Chrome DevTools MCP verification cycle plus shell/file assertions, not a unit runner.
- No existing diagram/mermaid/viz tooling to reuse.

---

## Decisions locked

| # | Decision | Choice |
|---|----------|--------|
| 1 | Command file location (viz-only goal vs Claude Code requirement) | **Thin stubs in `.claude/commands/` + real logic in `viz/commands/`.** Each stub is a one-line pointer ("Read and follow `viz/commands/<name>.md`") so all real logic lives in `viz/`. **Must be spiked first** (see Pre-implementation spike) — if `@`-include resolution is unreliable, the plain-instruction stub is the fallback. |
| 2 | Diagram accuracy (the core trust problem) | **Ground in real files + self-check pass + small-scope + footer.** For every diagram: (a) read the actual diff/files, (b) draw, (c) **second pass — re-read the code and ask "does this picture contradict what the code does?"**; fix mismatches or add a plain-English ⚠ uncertainty note ("not fully sure box X connects to Y"), (d) **restrict diagrams to small/changed scope where correctness is checkable** — lean away from whole-system causal claims the tool can't verify, (e) footer: "Drawn from: `<files>` (commit SHA) · valid as of `<timestamp>`". This protects the *user* (who can't read code), not just Claude. |
| 3 | Draw trigger | **Opt-in only — no auto-draw.** The user runs `/viz-plan` / `/viz-changes` / `/viz-map` when they want a picture; Claude never auto-generates on plans. Fully predictable, zero token waste. Trade-off accepted: the user must remember to ask. **Overrides DESIGN §4's "every plan → auto" trigger.** |
| 4 | `/viz-map` at scale | **Group into ~7 top-level areas with drill-down**, never one flat hairball. Top-level map shows big areas (Screens / Logic / Database / …); the user can zoom into any one area for its detail. |
| 5 | `/viz-changes` default scope | **Uncommitted working-tree edits**; optional argument for a specific commit/range later. |
| 6 | HTML bundling | **Light by default, inline on request.** Each `.viz.html` references the single `viz/vendor/mermaid.min.js` by relative path (tiny files, offline, double-click). An explicit `--inline` flag produces a fully self-contained portable single file for sharing. Prevents ~2.8MB-per-diagram git bloat. |
| 7 | Output file naming | **Stable filename per command, overwrite in place.** `/viz-map` → `viz/output/map.viz.{md,html}`, `/viz-changes` → `changes.viz.{md,html}`, `/viz-plan` → `plan.viz.{md,html}`. Re-running a command overwrites its own pair. `viz/output/` never exceeds **6 files**. The 3 stay separate so a map and a diff don't clobber each other; bookmark the 3 HTML files once, each always shows the latest. `--inline` writes a one-off `<name>.inline.viz.html` the user can move/email. |

---

## Final file layout

```
viz/                              # ships into every project (survives dev/ deletion)
  VISUAL-STYLE.md                 # Clarity Standard + 4 Mermaid recipes (source of truth)
  template.html                   # self-contained offline viewer (relative mermaid ref)
  vendor/
    mermaid.min.js                # pinned, offline renderer (ONE copy)
  commands/                       # REAL command logic (the brains)
    viz-plan.md
    viz-changes.md
    viz-map.md
  output/                         # generated diagrams (git-ignored, capped at 6 files)
    map.viz.md      map.viz.html      # /viz-map     — overwritten each run
    changes.viz.md  changes.viz.html  # /viz-changes — overwritten each run
    plan.viz.md     plan.viz.html     # /viz-plan    — overwritten each run
  dev/                            # DELETED after development
    DESIGN.md
    ENG-REVIEW.md                 # this document
    (login fixture, plans, notes — all dev-only)

.claude/commands/                 # required by Claude Code for slash-command discovery
  viz-plan.md                     # 1-line stub → viz/commands/viz-plan.md
  viz-changes.md                  # 1-line stub → viz/commands/viz-changes.md
  viz-map.md                      # 1-line stub → viz/commands/viz-map.md

CLAUDE.md                         # + "Visual Comprehension Layer" section (pre-approved)
.gitignore                        # + viz/output/  (approved)
```

## Approvals (changes outside `viz/`)

1. **`.claude/commands/viz-{plan,changes,map}.md`** — 3 one-line stubs. Unavoidable: Claude
   Code only discovers slash commands here. (Decision 1.)
2. **`CLAUDE.md`** — new "Visual Comprehension Layer" section. Pre-approved.
3. **`.gitignore`** — add `viz/output/`. **Approved by the user.**

Nothing else outside `viz/` is touched. No new hooks, no settings.json changes, no new
dependencies beyond the one vendored `mermaid.min.js`.

---

## Code Quality findings

- **CQ1 — DRY the color roles.** Define the 4 color roles + legend block ONCE in
  `VISUAL-STYLE.md` (a reusable `classDef` snippet + legend subgraph); all four recipes
  reference it. Prevents the legend drifting between view types.
- **CQ2 — Single-source the two output files.** Generate `.viz.md` content first, then build
  `.viz.html` by injecting that SAME content into `template.html` in the same run. The
  `.html` **embeds** the content (not a runtime fetch of the `.md`) — `file://` double-click
  can't reliably fetch a sibling file, and offline-zero-setup is a hard requirement. One
  authored source per run → no drift.
- **CQ3 — Robust HTML injection.** `template.html` uses a unique sentinel comment
  (`<!--VIZ_CONTENT-->`) as the single injection point, not a generic token that could
  collide with diagram text.
- **CQ4 — [P1] Mermaid label fragility (confidence 8/10).** The Clarity Standard demands
  rich plain-language labels with punctuation ("email + password", "200 { token }", "(what
  is stored)"). Mermaid's parser breaks on unescaped `(){}":;` etc. `VISUAL-STYLE.md` MUST
  mandate: wrap every node label in double quotes and escape/encode special chars (`#quot;`,
  `<br/>` for line breaks). Without this, diagrams silently fail to render — the worst
  outcome for a user who can't read the source. Highest-risk correctness item; the recipes
  must encode the escaping convention explicitly, with a fully-worked golden example.

---

## Test review

Markdown + 1 HTML template + vendored JS + command prompts. No unit-test framework, so
"tests" = Chrome DevTools MCP verification (per CLAUDE.md) plus shell/file assertions.
DESIGN §7 covers the happy path. Opt-in trigger (Decision 3) means there is **no** auto-draw
behavior to test — only the on-demand commands.

```
BEHAVIOR / PATH                                          VERIFICATION
[+] /viz-map (whole project)
  ├── [★★ COVERED]  writes both .viz.md AND .viz.html    DESIGN §7.2 — assert both exist
  ├── [★★ COVERED]  .html renders mermaid OFFLINE        DESIGN §7.3 — Chrome MCP, network off
  ├── [★★ COVERED]  4 views, caption/legend/narrative    DESIGN §7.3 — screenshot + DOM assert
  ├── [★★ COVERED]  console clean                        DESIGN §7.3 — list_console_messages
  └── [GAP] [→E2E]  grouping: >7 modules ⇒ ≤~7 top boxes  Decision 4 — run on THIS repo
[+] /viz-changes
  ├── [★★ COVERED]  no-code-skip on clean tree           DESIGN §7.5 — "No code changes"
  ├── [GAP]         default scope = uncommitted edits     Decision 5
  └── [GAP]         "Drawn from" footer lists real files  Decision 2
[+] /viz-plan (on demand)
  └── [GAP]         produces 4 views for current plan      Decision 3
[+] command wiring (the bucketing architecture)
  ├── [GAP] [CRIT]  /viz stub resolves viz/commands/       Decision 1 — SPIKE FIRST
  └── [GAP] [CRIT]  survives dev/ deletion                 move viz/dev/ aside, commands still work
[+] rendering robustness
  ├── [GAP] [P1]    special chars in labels still render   CQ4
  └── [GAP]         malformed mermaid ⇒ visible error      template shows error box, not blank

CRITICAL gaps: 2 (stub resolution, dev/-deletion survival)
```

**Required test additions (GSD writes alongside the code):**
- **T1 [CRIT] Stub→logic resolution** — see the pre-implementation spike.
- **T2 [CRIT] dev/-deletion survival** — with `viz/dev/` removed, all 3 commands + the HTML viewer still work. Literal acceptance test for the folder rule.
- **T3 [P1] Special-character labels (CQ4)** — labels with `+ ( ) { } " :` render cleanly, console clean.
- **T4 Grouping cap** — `/viz-map` on this repo ⇒ ≤~7 top-level boxes + working drill-down.
- **T5 Accuracy footer** — "Drawn from" lists exactly the changed files (+ SHA + timestamp).
- **T6 viz-changes scope** — uncommitted edit shows up; clean tree → no-code-skip.
- **T7 /viz-plan on demand** — produces the 4 views for the current plan.
- **T8 Malformed-mermaid path** — viewer shows an error box, never a silent blank.
- **T9 Self-check catches a wrong diagram** — feed a deliberately-wrong relationship in the fixture; the self-check pass either fixes it or emits a ⚠ uncertainty note (Decision 2).
- **T10 Inline flag** — `--inline` produces a single self-contained `.html`; default does not (Decision 6).
- **T11 Stable overwrite** — running `/viz-map` twice leaves exactly one `map.viz.html`; `viz/output/` never exceeds 6 files (Decision 7).

A tiny 2-file "login" fixture (mirroring the DESIGN's running example) makes T3/T5/T8/T9
cheap and deterministic, and doubles as the **golden example** for `VISUAL-STYLE.md`. Commit
it under `viz/dev/` (dies with dev/, fine — build-time only).

## Pre-implementation spike (DE-RISK BEFORE GSD BUILDS)

The whole "logic lives in `viz/`" bucketing rests on one unverified assumption: that a
`.claude/commands/viz-map.md` stub can pull in `viz/commands/viz-map.md`. The outside voice
found real precedent that `@`-includes ARE expanded, but every working example uses a
differently-rooted path — so whether `@viz/commands/...` resolves from project root (works)
or relative to the stub's dir (breaks) is unverified.

**5-minute test, run first:** create one throwaway stub + target, type the command, confirm
the real logic executes. Fallbacks, in order of preference:
1. Stub body = plain instruction: "Read and follow `viz/commands/<name>.md`" (no magic
   include — Claude reads the file as step 1). Keeps all logic in `viz/`. **Most likely fix,
   and robust regardless of include semantics — recommended default.**
2. Full logic in `.claude/commands/` (logic leaves `viz/` — least preferred; only if 1 fails).

## Performance review

- **Token cost** — addressed by Decision 3 (opt-in; nothing generated unless asked).
- **Render cost on a huge map** — addressed by Decision 4 (≤~7 boxes + drill-down).
- **`mermaid.min.js` weight (~2.8MB)** — committed once under `viz/vendor/`. Default `.viz.html`
  references it by relative path (small files, offline via `file://`); inlining happens only
  on `--inline` (Decision 6). A default 5-diagram session writes ~100KB, not ~14MB. **Pin the
  mermaid version** in `VISUAL-STYLE.md` for reproducible renders. Consider the smaller
  mermaid build (only `graph` + `sequenceDiagram` are used) — flag for implementation.

---

## NOT in scope (deferred)

- **Phase 2 live animated dashboard** — heaviest/riskiest; ship + validate static files first.
- **Animation** — Phase 2 (static diagrams satisfy the Clarity Standard now).
- **Auto-draw on plans** — dropped (Decision 3: opt-in). DESIGN §4 trigger overridden.
- **Visual aesthetics tuning** (colors, typography, beauty) — owned by `/plan-design-review`.
- **Renderer alternatives** (D2/Excalidraw/hand-SVG) — Mermaid chosen: declarative,
  vendorable, offline, supports all 4 view types. Flag for design-review only if clarity fails.
- **Narrative terseness toggle** (DESIGN Q2) — narrative required by Clarity Standard; no toggle.

## Failure modes (per new codepath)

| Codepath | Realistic failure | Test? | Error handling? | User sees? |
|----------|-------------------|-------|-----------------|------------|
| Stub reference not expanded | command does nothing | T1/spike | fallback instruction-stub | caught by spike before build |
| Mermaid special-char label | fails to parse | T3 | escaping rule (CQ4) | **was silent blank → clean render** |
| Malformed generated mermaid | renders nothing | T8 | error box in template | error box, not blank |
| `mermaid.min.js` missing | viewer blank | T8-adj | template load-error box | error message |
| `/viz-map` on huge repo | hairball | T4 | grouping cap (Decision 4) | readable top-level map |
| Diagram invented/wrong | confidently-wrong picture | T5+T9 | grounding + self-check + small-scope + footer (Decision 2) | ⚠ uncertainty notes + footer + freshness stamp |

No remaining failure mode is both untested AND silent → no critical gaps after T1–T11 + spike.

---

## Parallelization strategy (for GSD)

- **Lane 0 (gate) — Spike:** verify stub→logic resolution. Blocks everything.
- **Lane A — Engine:** `viz/VISUAL-STYLE.md` (color roles CQ1 + escaping CQ4 + worked golden
  example) → `viz/template.html` (CQ3, error box, relative mermaid ref) + pinned
  `viz/vendor/mermaid.min.js`. Sequential within lane (recipes inform the template).
- **Lane B — Commands:** `viz/commands/{viz-plan,viz-changes,viz-map}.md` + 3
  `.claude/commands/` stubs. Depends on Lane A.
- **Lane C — Wiring:** CLAUDE.md section + `.gitignore` line. Independent.

Execution: **Spike → (A + C parallel) → B → verify (T1–T11).** No file conflicts between lanes.

## Implementation steps (for GSD)

0. **Spike** the stub→logic resolution (above). Lock the stub style based on the result.
1. **Engine.** `viz/VISUAL-STYLE.md` first — it carries most of the quality risk: the 7-rule
   Clarity Standard, the 4 recipes, the single reusable color/legend block (CQ1), the **label
   escaping convention** (CQ4), and a **fully-worked golden example** (the login sample
   rendered end-to-end). Then `viz/template.html` (one `<!--VIZ_CONTENT-->` sentinel CQ3,
   mermaid load/error box T8, relative `../vendor/mermaid.min.js` ref). Vendor a pinned
   `mermaid.min.js`.
2. **Commands.** 3 real files under `viz/commands/` — each: read `VISUAL-STYLE.md`, determine
   scope (Decision 5 / grouping Decision 4), read the real files, draw, **run the self-check
   pass and add ⚠ uncertainty notes** (Decision 2), keep scope small/checkable, emit `.viz.md`
   + light `.viz.html` (CQ2; relative mermaid ref Decision 6; `--inline` flag for a portable
   copy), **write to the stable filename and overwrite in place** (Decision 7), append the
   "Drawn from `<files>` (SHA) · valid as of `<time>`" footer, print the exact file to open.
   Add the 3 stubs.
3. **Wiring.** CLAUDE.md "Visual Comprehension Layer" section: the 3 commands and what each
   does, "always obey `viz/VISUAL-STYLE.md` when generating", the `/viz-changes` no-code-skip
   rule, output convention. **No auto-draw language** (opt-in). Add `viz/output/` to
   `.gitignore` (approved).
4. **Verify (T1–T11).** Critical pair first (T1 spike, T2 dev/-deletion), then render checks
   in Chrome DevTools MCP per DESIGN §7 + the new gaps.

## Verification (end-to-end)

1. `/viz-map` on this repo → both `viz/output/map.viz.md` and `map.viz.html` written.
2. Open the `.html` by double-click and via Chrome DevTools MCP: 4 views, colors + legend,
   labeled arrows, numbered steps, narrative; console clean; renders offline (network off).
   Top-level map ≤~7 boxes (T4). Confirm `.html` is small (does NOT inline the 2.8MB lib).
3. Small edit → `/viz-changes` shows it + correct "Drawn from + valid as of" footer (T5/T6).
   Clean tree → "No code changes — nothing to visualize" (no files written). Run `/viz-map`
   twice → still exactly one `map.viz.html`; `viz/output/` ≤ 6 files (T11).
4. Move `viz/dev/` aside → all 3 commands still work (T2). Restore.
5. Label with `+ ( ) { } "` → renders clean (T3). Malformed mermaid → error box (T8).
   Deliberately-wrong fixture relationship → self-check fixes or flags it (T9).
6. `/viz-plan` on a current plan → 4 views on demand (T7). `--inline` → one portable file (T10).

---

## Outside-voice findings (Claude subagent; Codex not installed)

Eight findings; disposition:
1. **`@`-include unverified, paths differently-rooted** → folded in as the **pre-implementation spike** (Lane 0) with the plain-instruction-stub fallback.
2. **Stub indirection is tidiness, not function** → kept the stub model per user's viz-only preference (Decision 1), but the spike + fallback de-risk it.
3. **Accuracy mechanism too thin for a non-coder** → accepted; hardened Decision 2 (self-check pass + small-scope + ⚠ uncertainty notes). The single biggest risk, now mitigated.
4. **2.8MB mermaid bloat / "which build"** → Decision 6 (light by default) + note to consider the smaller `graph`+`sequence` build.
5. **`.md` near-dead-weight for this persona** → kept `.md` as the diffable/regen source but single-sourced (CQ2); embedding source in the `.html` covers portability.
6. **Opt-in kills "never approve blind"** → user explicitly chose opt-in (Decision 3); trade-off documented.
7. **Sequencing unsafe + DESIGN §7 still tests deleted auto-on-plan** → fixed via Lane 0 gate; this doc supersedes DESIGN §4 and the auto-on-plan part of §7.
8. **Minor:** `.html`→browser association, filename collisions, real per-run token cost → filename collisions solved by Decision 7; the rest noted for implementation.

## Status

- **Eng Review:** CLEAR — 5 architecture decisions + 4 code-quality items + 11 test additions; 0 critical gaps remaining after the spike + T1–T11.
- **Outside voice:** ran; biggest risk (confidently-wrong diagrams) mitigated by Decision 2.
- **Next:** `/plan-design-review` (separate chat) owns colors / typography / diagram
  aesthetics; then GSD implements following the steps above.
