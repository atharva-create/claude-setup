# Design Doc — "See What Claude Is Doing": A Visual Comprehension Layer

> **Status:** Documentation only. Not yet implemented.
> This doc is for review by other agents before any code is written.
> Scope of this doc: describe *what* we will build and *why*, precisely enough
> that a reviewer can poke holes in it.

---

## 1. The Problem (who this is for)

The user is **not a fluent coder** and is a **strongly visual thinker**. Today the
workflow is:

1. Claude writes code.
2. Claude shows a text plan before executing.

Two things break down:

- The user **can't read syntax**, so the code itself is opaque.
- The user is **visual** — they understand *data flow*, *data transformation*, and
  *major coding concepts*, but they want to **see** them, not read them.

**Consequence:** the user can't confidently judge whether Claude is heading in the
right direction, and can't make an informed go / no-go decision before (or after)
changes happen.

### Goal

A reusable system — built into the `claude-setup` repo so it **ships into every new
project** — that turns Claude's plans and changes into **self-explanatory diagrams a
non-technical person can fully understand**, so the user can steer.

### Non-goals

- Not a code-review tool for engineers.
- Not auto-generated API docs.
- Not a replacement for the text plan — a **companion** to it.

---

## 2. What "understand" means here — the four views

Every feature or change is explained through **four complementary views**. Together
they answer four plain questions:

| View | Plain question it answers | Mermaid type |
|------|---------------------------|--------------|
| **A. Module Map** | "What are the pieces, and what talks to what?" | `graph LR` |
| **B. Data Flow** | "Where does my data go on its journey?" | `graph LR` |
| **C. Transformation** | "How does the data's *shape* change at each step?" | `graph TD` |
| **D. Sequence** | "Walk me through what happens, in order, when I do X." | `sequenceDiagram` |

### Inline preview of all four (the "login" example)

**A. Module Map** — *what are the pieces, what talks to what*
```
[Login screen] --sends email+password--> [Auth logic] --calls--> [Login API]
                                              |
                                          saves token
                                              v
                                        [Token store]
```

**B. Data Flow** — *follow the data on its journey*
```
[email + password] -> validate -> POST /login -> [JWT token] -> save -> redirect
```

**C. Transformation** — *how the data's shape changes*
```
{ email, password }            (what the user types)
   -> hash + package ->
{ email, passwordHash }        (what is sent to the API)
   -> server responds ->
{ token, userId, expiresAt }   (what comes back)
   -> keep essentials ->
{ token }                      (what is stored)
```

**D. Sequence** — *step by step, who calls whom, in order*
```
① User      -> Login screen : types credentials, clicks submit
② Login     -> Auth logic   : login(email, password)
③ Auth      -> Login API    : POST /login
④ Login API -> Auth logic   : 200 { token }
⑤ Auth      -> Token store  : save(token)
⑥ Auth      -> Login screen : success
⑦ Login     -> Router       : go to dashboard
```

---

## 3. The Clarity Standard (the actual product)

The diagrams are not the product — **clarity is**. A non-technical reader must
understand everything with **nothing left to assume**. Every diagram MUST obey
these seven rules. This standard becomes the single source of truth that Claude
reads before generating any visual.

1. **Plain language first.** Node labels are human ("Login screen"), with the
   technical name ("LoginForm.tsx") as small grey subtext — never the reverse.
2. **Every arrow is labeled** with what travels along it ("sends email + password").
   No bare/unlabeled arrows allowed.
3. **Color = role, always with a legend on the diagram:**
   - 🔵 Blue = things you see (UI / screens)
   - 🟢 Green = logic / rules / decisions
   - 🟠 Orange = outside world (API / database / external service)
   - 🟣 Purple = stored data (state / cache / storage)
4. **Numbered reading order** (① ② ③ …) so sequence is never ambiguous.
5. **A one-line caption above each diagram** — e.g. "This shows what happens when you
   click Login."
6. **A plain-English narrative paragraph below each diagram**, retelling it for a
   non-coder.
7. **No orphan jargon** — any unavoidable technical term gets a one-line inline gloss
   the first time it appears.

**Composition of one visualization:**
> caption → diagram (colored, labeled, numbered) → legend → plain-English paragraph
> … repeated for each of the 4 views (Map / Flow / Transform / Sequence).

### Future enhancement (Phase 2): animation
"Animated if possible" was requested. Static diagrams satisfy the Clarity Standard in
Phase 1. Animation (watch the data travel the arrows step-by-step) lands in Phase 2's
dashboard, where the renderer can drive it.

---

## 4. When visuals are produced (triggering)

| Trigger | Behavior |
|---------|----------|
| **Every plan** | Automatically produce the 4-view visualization *alongside* the text plan, so the user never approves blind. |
| **On demand** | Slash commands let the user pull a visual whenever they want (see §6). |
| **No code changed** | If the task/turn produced **no code changes**, Claude says *"No code changes — nothing to visualize"* and renders nothing. **No tokens wasted on empty diagrams.** (Explicit user requirement.) |

---

## 5. Delivery — two formats, every time

Each visualization is emitted in **both** forms:

1. **`<name>.viz.md`** — Mermaid markdown. Portable, git-diffable, the **source of truth**.
2. **`<name>.viz.html`** — a self-contained styled viewer that opens by **double-click**.
   - Bundles the renderer locally → **renders beautifully with zero setup**: no server,
     no VS Code extension.
   - This matters because VS Code's *plain* markdown preview does **not** render
     Mermaid without an extension; the HTML guarantees the user actually sees the picture.

---

## 6. Phased build

### Phase 1 — Clarity Files (build first; works immediately, no server)

Proposed file layout (subject to review):

```
viz/
  VISUAL-STYLE.md      # the Clarity Standard + the 4 Mermaid recipes (source of truth)
  template.html        # self-contained viewer template (CSS + injection placeholders)
  vendor/
    mermaid.min.js     # vendored renderer — offline, zero runtime deps
  output/              # generated <name>.viz.md + <name>.viz.html  (git-ignored)
  dev/
    DESIGN.md          # this document

.claude/commands/
  viz-plan.md          # render the 4 views for the CURRENT PLAN (before code)
  viz-changes.md       # render the 4 views for WHAT JUST CHANGED (diff); no-code-skip
  viz-map.md           # render the WHOLE-PROJECT living module map + key flows
```

Plus wiring:
- **`CLAUDE.md`** — a new "Visual Comprehension Layer" section: auto-on-plan, the
  no-code skip rule, "always obey `viz/VISUAL-STYLE.md`", and the output convention.
- **`.gitignore`** — ignore `viz/output/`; keep `VISUAL-STYLE.md`, `template.html`,
  `vendor/` tracked.

**The four Mermaid recipes** (encoded in `VISUAL-STYLE.md` so output is consistent):
- **Map** → `graph LR` with `classDef` color roles + a legend subgraph.
- **Flow** → `graph LR` data pipeline; every edge labeled with the data moving.
- **Transform** → vertical `graph TD`; nodes list the data object's fields at each
  stage; edges say "what changed".
- **Sequence** → `sequenceDiagram` with plain-language actors and numbered messages.

**How Claude generates one visualization:**
1. Read `viz/VISUAL-STYLE.md`.
2. Determine scope (plan / changes / whole project).
3. Write Mermaid into `<name>.viz.md` per the recipes (colors, labeled edges,
   numbering, captions, narrative).
4. Copy `template.html`, inject the same content → `<name>.viz.html`.
5. Tell the user the exact file to open.

### Phase 2 — Live Animated Dashboard (build second, after Phase 1 is validated)

A browser dashboard (a `/viz-dashboard` command + small local server) that:
- **Animates data flow** — press ▶ to watch data travel the labeled arrows
  step-by-step; the active step lights up.
- **"You are here" glow** — highlights the module/file Claude is editing right now.
- **Click-to-explain** — click any box for a plain-English panel.
- **Auto-refreshing living map** — re-renders as project files change (file watcher).

Phase 2 reuses the Phase 1 Clarity Standard, color roles, and Mermaid content; it adds
interactivity, animation, and live highlighting. **De-risking rationale:** the dashboard
is the heaviest/riskiest piece, so we ship the portable files first and lock the visual
language before building the live surface.

---

## 7. How Phase 1 will be verified (when built)

1. Run `/viz-map` on this repo (or a small sample feature) end-to-end.
2. Confirm both `viz/output/<name>.viz.md` and `.../<name>.viz.html` are written.
3. Open the `.html` in real Chrome via Chrome DevTools MCP:
   - Screenshot → diagrams render (not raw text); colors + legend present.
   - All four views present, each with caption, labeled arrows, numbered steps, and a
     plain-English narrative.
   - Console clean (no Mermaid load/render errors).
4. **Non-technical read-through:** is anything left to assume? If yes, fix
   `VISUAL-STYLE.md` and regenerate.
5. **No-code skip:** run `/viz-changes` on a clean tree → expect "No code changes —
   nothing to visualize", nothing rendered.
6. **Auto-on-plan:** trivial planning scenario → confirm the 4-view visualization
   accompanies the text plan.

**Done when:** the sample renders beautifully and self-explanatorily in the browser,
both formats are produced, and the no-code-skip + auto-on-plan behaviors work — then
proceed to Phase 2 sign-off.

---

## 8. Open questions for reviewers

1. **Renderer choice.** Mermaid is the proposed engine (declarative, vendorable,
   widely supported). Is there a better fit for *non-technical clarity* (e.g.
   hand-tuned SVG, D2, Excalidraw-style)? Mermaid's tradeoff: easy + consistent, but
   limited fine-grained layout control.
2. **Who writes the narrative?** Plan assumes Claude authors the plain-English prose
   per diagram. Acceptable token cost, or should narrative be optional/terser?
3. **Scope detection for `/viz-changes`.** Diff the working tree, last commit, or a
   range? What's the most useful default?
4. **"Living map" freshness in Phase 1.** Without the Phase 2 watcher, the map is a
   snapshot regenerated on `/viz-map`. Is on-demand refresh enough for Phase 1?
5. **Output location.** `viz/output/` in-repo (git-ignored) vs a temp dir. In-repo is
   easy to find; temp keeps the repo clean. Preference?
6. **Auto-on-plan cost.** Generating 4 diagrams on *every* plan adds tokens. Should it
   be auto-always, auto-only-for-code-plans, or opt-in per plan?
7. **Accuracy risk.** Diagrams are Claude's *interpretation* of the code. How do we
   keep them honest (avoid confidently-wrong pictures)? Cross-check against the diff?
