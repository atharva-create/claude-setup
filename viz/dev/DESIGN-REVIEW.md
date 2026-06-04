# Design Review — Visual Comprehension Layer (`viz/`)

> **Status:** `/plan-design-review` complete. Owns visual aesthetics + interaction design
> (the part `ENG-REVIEW.md` explicitly deferred). Backed by a web-research pass on best-in-class
> codebase visualization and a **working interactive prototype** (`viewer-prototype.html` in this
> folder, verified in Chrome).
> **Reviewing:** `viz/dev/DESIGN.md` + `viz/dev/ENG-REVIEW.md`.
> **Mandate from the user:** design the *full vision* — intuitive, eye-catching, interactive,
> **progressive disclosure** (one layer at a time, no overload), easy to read/navigate, best
> visuals for representing codebases.

**Overall design score: 4/10 → 8.5/10 after this review.**

---

## Context

The plan was strong on *comprehension logic* (the 7-rule Clarity Standard: plain language,
labeled arrows, narrative, numbered order — genuinely good) but nearly silent on the things the
user actually asked for: visual design, interactivity, and progressive disclosure. The single
biggest flaw: **Delivery §5 stacks all four diagrams (Map/Flow/Transform/Sequence) into one
file** — the exact opposite of "reveal one layer at a time." This review fixes that and adds the
visual + interaction design the plan lacked.

---

## Two decisions made (these override `ENG-REVIEW.md`)

### Decision A — Renderer: **D2, not Mermaid** (overrides ENG renderer choice)

ENG picked Mermaid for offline/vendorable reasons and flagged "reopen if clarity fails." Research
found Mermaid is the **weakest** choice for a non-coder tool on two axes that matter here:

- **Looks generic** — utilitarian "engineering-doc" output, the AI-slop read for a tool whose
  whole job is to feel trustworthy and premium to a non-coder.
- **Unstable layout** — practitioners report "tiny changes radically change the whole layout."
  A non-coder watching a diagram reshuffle on every edit loses their mental map.

**D2** ([d2lang.com](https://d2lang.com/)) keeps *every* property the plan wanted — offline,
vendorable, declarative text → diagram, double-click `.html` — and adds designer themes, stable
layout, and **native animation**. Research ranked it #1 for the offline + declarative + beautiful
constraint. (React Flow + ELK wins on raw interactivity but at a heavy custom-styling cost;
Mermaid drops to fallback-only.)

> **Architecture:** D2 draws the SVG; a hand-authored **HTML viewer shell** provides the
> interactivity (view switching, progressive reveal, "you are here," click-to-explain, animated
> flow). The prototype's experience is delivered by the shell layered over D2 output — fully
> offline. The `.viz.md` source stays declarative (D2 instead of Mermaid).

### Decision B — Entry view **matches the command**

Research is clear: "overview first, then details on demand" (Shneiderman) is safest for general
comprehension — but for explaining a specific *change*, a guided step-by-step story is better.
So entry view depends on the command's job:

| Command | Opens on |
|---|---|
| `/viz-map`, `/viz-plan` | **Overview Map** — ≤~7 labeled "rooms," drill in on demand |
| `/viz-changes` | **Guided "Watch what changed" story** — scrollytelling the diff |

---

## The design system (becomes the visual half of `viz/VISUAL-STYLE.md`)

Source of truth = `viewer-prototype.html` (this folder). Tokens, as CSS variables:

- **Color = role, never decoration. One accent reserved for "the change."**
  - 🔵 UI / things you see — `#3b6fe0` · 🟢 Logic / rules — `#0fa672` · 🟠 Outside world —
    `#e08b2f` · 🟣 Stored data — `#7d5ce0` (each with `ink`/`bg` pairs).
  - Neutral surface `#f6f7f9` / `#fff`, ink `#161b25`, muted `#697084`.
  - **Role is never color-alone:** every node also carries a text role label + a role icon
    (person / cylinder / cloud / box) — colorblind-safe.
  - Restraint: 2–3 colors in view at once; saturated accent reserved for the changed node.
- **Typography:** a real humanist sans for UI (Söhne/Inter stack — **not** system-ui, the "gave
  up on typography" signal), a serif (Tiempos/Georgia) for the plain-English narrative so it reads
  like a typeset explainer, not an app dialog.
- Radius 12–14px, soft two-layer shadow, 22px dotted-grid canvas, generous whitespace.
- **Motion only on the active flow.** Default animation = SVG `<animateMotion>` traveling tokens
  (research: most legible per cost — a literal "packet" gliding the wire reads as "data moving
  here"), not flowing dashes. `prefers-reduced-motion` → static staged reveal.

## The interaction model

- **One view at a time.** Left rail, four views in plain words: *The Map* (pieces), *The Journey*
  (data flow), *The Shape* (data transformation), *The Steps* (sequence). Never all four stacked.
- **Progressive reveal** ("Watch it build"): nodes/edges appear one step at a time; progress dots;
  Back/Next; auto-play; each step a one-line plain caption.
- **"You are here" spotlight:** changed node(s) full-color + glow + pill; everything else dimmed
  one ring out; plain breadcrumb ("Whole app › Login feature"). Per NN/g — over-signal it.
- **Semantic-zoom drill-down:** overview = ~5–7 labeled rooms; click a room to expand into its
  detail (representation changes per level, not geometric zoom into tiny text). Honors ENG
  Decision 4's ≤7-box grouping.
- **Click-to-explain:** click any node → plain-English side panel; code name shown as small grey
  subtext / tooltip, never the primary label.

## Interaction states (Pass 2 — plan specified none)

| State | What the non-coder sees |
|---|---|
| Loading | Skeleton diagram (ghost rooms), "Drawing your map…" |
| Empty | "No code changed — nothing to visualize." (already an ENG requirement) |
| Error | Visible error box, never a blank canvas (matches ENG CQ4 / T8) |
| Uncertain | Dashed amber node + ⚠ "not fully sure this connects" (ENG Decision 2 self-check) |
| Partial | Loaded rooms render; unresolved ones show a "still mapping" chip |

## Accessibility (Pass 6)

Keyboard nav for view-switch + step reveal; ARIA roles/labels on the diagram; 44px touch
targets; contrast ≥4.5:1 on body text; reduced-motion fallback; role conveyed by label + icon,
not color alone; visible focus rings.

---

## The 7 passes — before → after

| Pass | Before | After | What was added to the design |
|---|---|---|---|
| 1 Information Architecture | 5 | 9 | Overview-first + one-view-at-a-time + semantic-zoom drill-down (fixes 4-in-one-file overload) |
| 2 Interaction States | 3 | 8 | Loading / empty / error / uncertain / partial state table |
| 3 User Journey | 4 | 9 | Nervous-non-coder emotional arc; scrollytelling the change |
| 4 AI-Slop Risk | 6 | 9 | 2–3 colors, one accent for the change, role icons, "rooms," motion only on active flow |
| 5 Design System | 2 | 8 | Real token system (color/type/space/motion) extracted from the prototype |
| 6 Responsive & A11y | 3 | 7 | Keyboard nav, ARIA, 44px targets, contrast, reduced-motion, color-independent role |
| 7 Unresolved Decisions | — | — | 2 resolved (renderer, entry view); 0 deferred |

---

## What already exists (reuse, don't reinvent)

- `DESIGN.md`'s 7-rule Clarity Standard, the 4-view model, and the role-color concept.
- `ENG-REVIEW.md`'s grouping (Decision 4), accuracy/self-check (Decision 2), output naming
  (Decision 7), scope (Decision 5), and CQ1–CQ4.
- **`viewer-prototype.html`** encodes the entire new design system + interaction model in
  self-contained HTML/CSS/JS — `viz/VISUAL-STYLE.md` (visual half) and `viz/template.html`
  (viewer shell) should be **extracted from it**, not authored fresh.

## NOT in scope (deferred, with rationale)

- **Live file-watcher dashboard / auto-refresh** — ENG Phase 2; ship the static-but-interactive
  viewer first.
- **Full semantic-zoom for arbitrarily deep trees** — Phase 1 ships 2 levels (rooms → detail).
- **WAAPI labeled-chip-along-path animation** — `<animateMotion>` tokens suffice for Phase 1.
- **AI-generated PNG mockups** — gstack designer needs an OpenAI key (absent); the hand-built
  HTML prototype is the better artifact here anyway (it *is* the real medium).

## Proposed TODOs (for the build phase)

- A11y deep pass against the built viewer (screen-reader walk-through of a real diagram).
- Animation perf guard: cap `<animateMotion>` tokens; never animate >1 path; flag dense rooms.
- Source/vendor 4 role icons (person / cylinder / cloud / box) offline.

---

## Research sources (key)

[Shneiderman — The Eyes Have It](https://www.cs.umd.edu/~ben/papers/Shneiderman1996eyes.pdf) ·
[Cockburn — Overview+Detail / Zoom / Focus+Context](https://worrydream.com/refs/Cockburn_2007_-_A_Review_of_Overview+Detail,_Zooming,_and_Focus+Context_Interfaces.pdf) ·
[Semantic Zoom for Software Cities](https://arxiv.org/html/2510.00003v1) ·
[D2](https://d2lang.com/) · [Mermaid vs D2 (Becker)](https://aaronjbecker.com/posts/mermaid-vs-d2-comparing-text-to-diagram-tools/) ·
[Mermaid revisited (Korny)](https://blog.korny.info/2025/03/14/mermaid-js-revisited) ·
[React Flow — animating edges](https://reactflow.dev/examples/edges/animating-edges) ·
[Untangling the hairball](https://skewed.de/lab/posts/hairball/) ·
[NN/g — You Are Here](https://www.nngroup.com/articles/navigation-you-are-here/) ·
[Data dimming (Map UI Patterns)](https://mapuipatterns.com/data-dimming/) ·
[ciechanow.ski (explorable explanations)](https://ciechanow.ski/)
