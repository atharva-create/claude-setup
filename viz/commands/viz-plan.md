# /viz-plan — visualize the current plan (the 4 views of what's *about* to be built)

**Goal:** Before any code is written, show a non-coder *what the plan will do* — the pieces it
will add/change, how data will flow, how shapes will change, and the step-by-step — so they can
approve or redirect with confidence.

## Steps (follow exactly)

1. **Read `viz/VISUAL-STYLE.md`** and obey it (Clarity Standard, color block, escaping, recipes, §6 payload).
2. **Determine scope = the current plan.** Use the active plan document / proposed approach in
   this session (e.g. the plan file under discussion). If no plan is evident, ask the user which
   plan to draw. This view is forward-looking: it depicts intended pieces, not existing code.
3. **Ground in the plan + the real code it touches:** read the plan, and the existing files it
   will modify, so the picture is honest about what exists vs. what's new. Mark new pieces
   clearly in their `explain` text ("new — will be added by this plan").
4. **Build the `VIZ` payload** (VISUAL-STYLE §6):
   - `mapD2`: the pieces the plan introduces/changes + their neighbors; mark the focal new/changed
     piece with `here`.
   - `mapNodes`, `flow`, `shape`, `steps`, `narr`, `title`, `scope:"the plan"`, `breadcrumb`,
     `legend:true`, `status:"ok"`.
   - `footer`: `Drawn from <plan file + touched files> · valid as of <timestamp>` (a plan has no
     commit SHA yet — say "planned, not yet built").
5. **Self-check (§7):** does the picture match the plan's intent? Distinguish *exists* from
   *planned*. Add `uncertain:[...]` notes for anything the plan leaves open.
6. **Render:** `node viz/build-viz.cjs --payload <tmp>.json --name plan` (d2 on `PATH` or `~/.local/bin/d2`).
7. **Report** the `OPEN file://…/viz/output/plan.viz.html` line.

## Notes
- Overwrites `viz/output/plan.viz.{md,html}` in place (Decision 7).
- Opt-in only — never auto-generated. The user runs `/viz-plan` when they want the picture.
