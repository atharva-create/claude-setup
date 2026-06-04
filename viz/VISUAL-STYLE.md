# VISUAL-STYLE.md — the Clarity Standard + recipes (source of truth)

> This is the file Claude **must read before generating any visualization**. It defines
> *what* a good diagram is (the Clarity Standard), *how* to build each of the four views
> (the recipes), and the exact `VIZ` payload the viewer (`template.html`) consumes.
> The audience is a **non-coder, visual thinker**. Clarity is the product — the diagram is
> just the delivery.

Renderer: **D2 v0.7.1** (`d2` on `PATH`, or `~/.local/bin/d2`). Pinned for reproducible
layout. The Map view is compiled by D2 to SVG; the other three views are hand-authored HTML.

---

## 1. The Clarity Standard (seven rules — non-negotiable)

A non-technical reader must understand everything with **nothing left to assume**.

1. **Plain language first.** Node labels are human ("Login screen"); the technical name
   ("LoginForm.tsx") is small grey subtext — never the reverse.
2. **Every arrow is labeled** with what travels along it ("sends email + password"). No bare arrows.
3. **Color = role, always with a legend:**
   - 🔵 Blue = things you see (UI / screens)
   - 🟢 Green = logic / rules / decisions
   - 🟠 Orange = outside world (API / database / external service)
   - 🟣 Purple = stored data (state / cache / storage)
   Role is **never color-alone**: each node also carries a text role label + a role icon
   (person / box / cloud / cylinder) — colorblind-safe.
4. **Numbered reading order** (① ② ③ …) so sequence is never ambiguous.
5. **A one-line caption above each diagram** — "This shows what happens when you click Login."
6. **A plain-English narrative paragraph below each diagram**, retelling it for a non-coder.
7. **No orphan jargon** — any unavoidable technical term gets a one-line inline gloss the first time.

**Composition of one view:** caption → diagram (colored, labeled, numbered) → legend →
plain-English paragraph. Repeated for each of the 4 views.

---

## 2. The four views

| View (plain name) | Plain question | How it's built |
|---|---|---|
| **The Map** | "What are the pieces, and what talks to what?" | **D2** `direction: right` graph → SVG |
| **The Journey** | "Where does my data go on its journey?" | Hand-authored HTML chip-line |
| **The Shape** | "How does the data's shape change at each step?" | Hand-authored HTML stacked cards |
| **The Steps** | "Walk me through what happens, in order." | Hand-authored HTML numbered sequence |

The Map uses D2 because auto-layout keeps a module graph stable and readable as it scales.
The other three read clearest as the prototype's purpose-built HTML and need no graph engine.

---

## 3. Color-role + legend block (CQ1 — define ONCE, reuse everywhere)

### 3a. D2 classes for the Map (paste verbatim into every Map `.d2`)

```d2
classes: {
  ui:      { style: { fill: "#eaf1fe"; stroke: "#3b6fe0"; font-color: "#1d3f8f" } }
  logic:   { style: { fill: "#e6f7f0"; stroke: "#0fa672"; font-color: "#0a6e4c" } }
  outside: { style: { fill: "#fdf1e1"; stroke: "#e08b2f"; font-color: "#9a5a13" } }
  store:   { style: { fill: "#f0ebfd"; stroke: "#7d5ce0"; font-color: "#523a9c" } }
  here:    { style: { stroke-width: 3; bold: true; stroke: "#3b6fe0" } }
}
```

Apply with `node.class: ui` (and add `here` for the changed node: `node.class: [logic; here]`).

### 3b. The legend (identical wording in every view)

| Swatch | Role label | Icon |
|---|---|---|
| 🔵 `#3b6fe0` | Things you see | person/screen |
| 🟢 `#0fa672` | Logic & rules | box |
| 🟠 `#e08b2f` | Outside world | cloud |
| 🟣 `#7d5ce0` | Stored data | cylinder |

The viewer renders this legend from `VIZ.legend` (always all four, even if a view uses a subset),
so the legend can never drift between views.

### 3c. Role tokens (CSS variables — mirrored in `template.html`)

```
--ui:#3b6fe0  --logic:#0fa672  --outside:#e08b2f  --store:#7d5ce0
--ui-bg:#eaf1fe  --logic-bg:#e6f7f0  --outside-bg:#fdf1e1  --store-bg:#f0ebfd
```

---

## 4. Label-escaping convention (CQ4 — the #1 render-correctness rule)

The Clarity Standard demands rich labels with punctuation: `email + password`, `200 { token }`,
`(what is stored)`. D2's parser breaks on unquoted `: { } | < > " ; #`. **Therefore:**

1. **Always wrap a node key's display label in a quoted `label`**, never inline punctuation in the key:
   ```d2
   screen: { label: "Login screen"; class: ui }
   auth:   { label: "Auth logic"; class: [logic; here] }
   ```
2. **Edge labels go in quotes too:**
   ```d2
   screen -> auth: "sends email + password"
   ```
3. **Escape a literal double-quote** inside a label as `\"`. Newlines: use `\n`.
4. **Never put `{` `}` `:` `|` raw in an unquoted position.** When in doubt, quote.
5. **Keys are ASCII slugs** (`screen`, `auth`, `loginApi`); humans never see keys — they see `label`.
   D2 emits each node as `<g class="<base64(key)> <role> [here]">`, so the viewer binds
   interactivity to the **base64 of the KEY** (see §6). Keep keys stable and unique.
6. **Nested nodes use the dotted path.** A child inside a D2 container is emitted as the base64 of its
   **fully-qualified path** (`Screens.login`, *not* `login`). So if you put a *nested* node in
   `mapNodes`, its `key` must be that dotted path: `{ key: "Screens.login", … }`. (The viewer also
   falls back to a `.<key>` suffix match, but the dotted path is unambiguous — prefer it.) Top-level
   area nodes — the normal `/viz-map` case — are just the slug, so this only matters if you surface a
   child node directly.

A label that violates these silently fails to render — the worst outcome for a non-coder. The
self-check pass (§7) must confirm the compiled SVG actually contains every node before shipping.

---

## 5. The recipes

### 5a. The Map (D2 → SVG)

```d2
direction: right
classes: { /* §3a block verbatim */ }

screen:   { label: "Login screen"; class: ui }
auth:     { label: "Auth logic"; class: [logic; here] }
loginApi: { label: "Login API"; class: outside }
store:    { label: "Token store"; class: store }

screen   -> auth:     "sends email + password"
auth     -> loginApi: "calls the server"
auth     -> store:    "saves token"
```

- Group into **≤~7 top-level boxes** for `/viz-map` (Decision 4); use D2 nested containers for
  drill-down areas (Screens / Logic / Database …) rather than one flat hairball.
- Mark the **one changed node** with `class: [<role>; here]` ("you are here").
- Compile: `d2 --theme 0 --pad 24 map.d2 map.svg`. Embed the SVG string into `VIZ.mapSVG`.

### 5b. The Journey (HTML chip-line) — `VIZ.flow`
Array of steps; each is `{ role, label }` chips joined by labeled arrows `{ arrow }`:
```
[ {role:"ui",label:"email + password"}, {arrow:"check it's filled in"},
  {role:"logic",label:"validate"}, {arrow:"send securely"},
  {role:"outside",label:"POST /login"}, {arrow:"server replies"},
  {role:"store",label:"token"}, {arrow:"remember you"},
  {role:"ui",label:"go to dashboard"} ]
```

### 5c. The Shape (HTML stacked cards) — `VIZ.shape`
Array alternating cards and transition arrows; each card `{ role, lbl, code }`:
```
[ {lbl:"What you type", code:"{ email, password }", role:"ui"},
  {t:"scramble the password, package it"},
  {lbl:"What is sent to the server", code:"{ email, passwordHash }", role:"outside"},
  {t:"server answers"},
  {lbl:"What comes back", code:"{ token, userId, expiresAt }", role:"outside"},
  {t:"keep only what's needed"},
  {lbl:"What is stored", code:"{ token }", role:"store"} ]
```

### 5d. The Steps (HTML numbered sequence) — `VIZ.steps`
Array of `{ who, what }`; the viewer numbers them ① ②:
```
[ {who:"You", what:"type your email and password, click Sign in"},
  {who:"Login screen", what:"hands them to the Auth logic"},
  {who:"Auth logic", what:"asks the Login API to check them"},
  {who:"Login API", what:"replies \"looks good, here's a token\""},
  {who:"Auth logic", what:"saves the token so you stay logged in"},
  {who:"Auth logic", what:"sends you to your dashboard"} ]
```

---

## 6. The `VIZ` payload (what a command injects into `template.html`)

Each command authors ONE `VIZ` object and (a) writes it + the D2 source into `<name>.viz.md`,
(b) injects `<script>window.VIZ = {…}</script>` at the `<!--VIZ_CONTENT-->` sentinel of a copy
of `template.html` → `<name>.viz.html`. One authored source per run (CQ2).

```js
window.VIZ = {
  title: "Login",
  scope: "what just changed",                 // pill text
  breadcrumb: ["Whole app", "Login feature"], // last item bold
  footer: "Drawn from LoginForm.tsx, auth.ts · commit a1b2c3d · valid as of 2026-06-01",
  legend: true,                               // always render all 4 roles
  mapSVG: "<svg …>…</svg>",                   // D2-compiled Map (string)
  mapNodes: [                                 // key = the D2 node key; viewer finds <g> by base64(key)
    { key:"screen",   label:"Login screen", role:"ui",      sub:"LoginForm.tsx", explain:"The page with the email + password boxes…" },
    { key:"auth",     label:"Auth logic",   role:"logic",   sub:"auth.ts", here:true, explain:"The decision-maker… being changed." },
    { key:"loginApi", label:"Login API",    role:"outside", sub:"POST /login", explain:"A service on the internet…" },
    { key:"store",    label:"Token store",  role:"store",   sub:"localStorage", explain:"A small safe spot in your browser…" }
  ],
  flow:  [ /* §5b */ ],
  shape: [ /* §5c */ ],
  steps: [ /* §5d */ ],
  narr: {
    map:   "This is the Login feature as four connected pieces…",
    flow:  "Follow your data on its journey…",
    shape: "Watch how your data changes shape…",
    steps: "The same story, told in order…"
  },
  uncertain: [ /* optional ⚠ notes: "not fully sure Token store connects to Auth logic" */ ],
  status: "ok"   // "ok" | "empty" | "error" — drives viewer states
}
```

The viewer maps `role` → CSS class/color, derives the Map's clickable node by computing
`btoa(key)` (D2's node `<g>` carries the base64 of the key as a CSS class) and attaches the
explain panel, "you are here" glow (`here:true`), and the spotlight walk-through.

---

## 7. Accuracy: grounding + self-check (Decision 2 — protects the non-coder)

For every diagram:
1. **Ground:** read the actual diff/files. Never draw from memory.
2. **Draw** per the recipes.
3. **Self-check (second pass):** re-read the code and ask *"does this picture contradict what
   the code does?"* Fix mismatches, OR add a plain `uncertain[]` note ("not fully sure box X
   connects to Y"). Also confirm the **compiled SVG contains every node** (catches CQ4 escapes).
4. **Small scope:** prefer the changed/asked scope where correctness is checkable; avoid
   whole-system causal claims the tool can't verify.
5. **Footer:** `Drawn from <files> · commit <SHA> · valid as of <timestamp>`.

---

## 8. Golden example — "login", end to end

The worked example is fully inline above and self-contained — it depends on nothing outside
this file plus `template.html` + `build-viz.cjs`. The exact pieces above (the §5a Map `.d2`,
the §5b–§5d arrays, the §6 `VIZ` object) together ARE the golden "login" visualization: the
Login screen (blue) sends email + password to the Auth logic (green, the changed piece), which
calls the Login API (orange) and saves a token (purple). Rendering this `VIZ` through
`build-viz.cjs` must produce: 4 switchable views, a 4-role legend, labeled arrows, ① ②
numbering on the Steps, a serif narrative under each view, the "you are here" glow on Auth
logic, click-to-explain on every Map node, and the footer — all offline by double-click.

This example is the canonical regression check: special-char labels render (§4), a malformed
Map yields the viewer's error box (not a blank), and a deliberately-wrong edge is caught by the
self-check pass (§7).
