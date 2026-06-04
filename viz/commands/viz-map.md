# /viz-map — draw the whole-project module map (+ the 4 views)

**Goal:** Give a non-coder a picture of *what the pieces of this project are and what talks to
what* — grouped so it's never a hairball — plus the Journey / Shape / Steps views for the most
important flow.

## Steps (follow exactly)

1. **Read `viz/VISUAL-STYLE.md`** — obey the 7-rule Clarity Standard, the color-role block (§3),
   the label-escaping convention (§4), the recipes (§5), and the `VIZ` payload shape (§6).
2. **Determine scope = the whole project**, but **group into ≤~7 top-level areas** (Screens /
   Logic / Data / Outside services / …). Never draw a flat graph of every file. If an area has
   internal detail worth showing, note it in that node's `explain` text (Phase-1 drill-down =
   explain text; deep semantic zoom is deferred).
3. **Ground in real files:** list the project's top-level structure (entry points, main dirs,
   config) and read enough to know what each area *does* and which areas talk to which. Do not
   invent connections.
4. **Build the `VIZ` payload** (see VISUAL-STYLE §6) as JSON, including:
   - `mapD2`: the Map's D2 source (use the §3a class block verbatim; one node per area; every
     edge labeled in plain language; mark the area you're focused on — if any — with `here`).
   - `mapNodes`: one entry per area `{key,label,role,sub,explain}` (key MUST equal the D2 node key).
   - `flow` / `shape` / `steps`: the most representative end-to-end flow of the app.
   - `narr` (plain-English paragraph per view), `title`, `scope:"the whole project"`,
     `breadcrumb`, `legend:true`, `status:"ok"`.
   - `footer`: `Drawn from <key files/dirs> · commit <SHA> · valid as of <timestamp>`
     (get SHA via `git rev-parse --short HEAD`; timestamp via `date`).
5. **Self-check (VISUAL-STYLE §7):** re-read the structure. Does the picture contradict the code?
   Fix mismatches, or add plain `uncertain:[...]` notes ("not fully sure X connects to Y"). Keep
   areas to ≤~7.
6. **Render:** write the payload to a temp file and run
   `node viz/build-viz.cjs --payload <tmp>.json --name map`
   (ensure `d2` is reachable: it's on `PATH` or at `~/.local/bin/d2`).
7. **Report:** print the `OPEN file://…/viz/output/map.viz.html` line so the user can double-click
   it. If the build reported `[ERROR STATE]`, a label broke the D2 — fix per VISUAL-STYLE §4 and re-run.

## Notes
- Overwrites `viz/output/map.viz.{md,html}` in place each run (stable filename, Decision 7).
- `.viz.html` is fully self-contained/offline (SVG embedded) — already portable; `--inline` is a no-op.
