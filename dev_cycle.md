# Combined GSD + gstack Workflow

## The Combined Sprint

```
┌─────────────────────────────────────────────────────────────┐
│                    COMBINED SPRINT FLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  THINK          PLAN           BUILD         REVIEW & SHIP  │
│  (gstack)       (GSD)          (GSD)         (gstack)       │
│                                                             │
│  ┌──────────┐   ┌───────────┐  ┌──────────┐  ┌──────────┐  │
│  │ /office- │   │ /gsd:new- │  │ /gsd:    │  │ /review  │  │
│  │  hours   │──→│  project  │  │ execute- │  │ /cso     │  │
│  └──────────┘   └───────────┘  │  phase   │  │ /qa      │  │
│                 ┌───────────┐  └──────────┘  │ /ship    │  │
│                 │ /gsd:     │       │        └──────────┘  │
│                 │ discuss-  │       │        ┌──────────┐  │
│                 │  phase    │       │        │ /land-   │  │
│                 └───────────┘       │        │  and-    │  │
│                 ┌───────────┐       │        │  deploy  │  │
│                 │ /gsd:     │       │        └──────────┘  │
│                 │ plan-     │───────┘        ┌──────────┐  │
│                 │  phase    │                │ /retro   │  │
│                 └───────────┘                └──────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

> A hybrid development workflow combining **Get Shit Done** (context engineering & autonomous execution) with **gstack** (quality gates & virtual engineering team) for Claude Code.

---

## Overview

| Tool | Strength | Role in Workflow |
|------|----------|-----------------|
| **GSD** | Spec-driven planning, context window management, parallel wave execution | Think → Plan → Build |
| **gstack** | Multi-role review, real browser QA, security auditing, shipping pipeline | Review → Test → Ship |

The core idea: **GSD builds it right. gstack makes sure it's actually right.**

---

## Installation

```bash
# 1. Install GSD
npx get-shit-done-cc@latest
# Choose: Claude Code → Global or Local

# 2. Install gstack
git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup

# 3. Verify both are working
/gsd:help
/office-hours  # or /gstack-help
```

Both use different command prefixes (`/gsd:*` vs unprefixed or `/gstack-*`) so they coexist without conflict.

---

## Phase 1 — Think (gstack)

**Command:** `/office-hours`

Start here for every new feature or project. This is YC-style product thinking — it pushes back on your framing, challenges premises, and extracts what you're actually trying to build.

```
You:    /office-hours
You:    I want to build a real-time tracking dashboard for delivery partners.

Claude: [asks forcing questions about the pain point]
        [challenges your framing — "you're not building a dashboard,
         you're building an ops nerve center"]
        [generates implementation alternatives with effort estimates]
        [writes design doc]
```

**Output:** Design doc that feeds into Phase 2.

**Why gstack here:** GSD's `/gsd:new-project` also asks questions, but `/office-hours` is specifically designed for product-level pushback and reframing. It thinks like a founder/CEO, not a project manager.

---

## Phase 2 — Spec & Plan (GSD)

### 2a. Initialize Project

**Command:** `/gsd:new-project`

Feed the design doc from Phase 1 into GSD. It will:
- Extract requirements (v1, v2, out of scope)
- Create a phased roadmap
- Generate `PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`

```
You:    /gsd:new-project
        [reference the design doc from /office-hours]
```

### 2b. Discuss Phase Implementation

**Command:** `/gsd:discuss-phase <N>`

Before planning, capture your design decisions and preferences for this phase. GSD surfaces gray areas and asks targeted questions.

```
You:    /gsd:discuss-phase 1
```

**Output:** `CONTEXT.md` — your decisions that guide research and planning.

### 2c. Plan Phase

**Command:** `/gsd:plan-phase <N>`

GSD researches implementation approaches, creates atomic XML-structured task plans, and verifies them. Each plan is sized to fit in a fresh context window.

```
You:    /gsd:plan-phase 1
```

**Output:** `RESEARCH.md`, `PLAN.md` files — atomic tasks with dependencies, verification steps.

**Why GSD here:** gstack has `/plan-eng-review` and `/plan-ceo-review` but they're review-oriented, not planning-oriented. GSD's planning system is purpose-built for breaking specs into executable atomic tasks with dependency management.

---

## Phase 3 — Build (GSD)

**Command:** `/gsd:execute-phase <N>`

This is GSD's strongest feature. It:
- Groups plans into **waves** based on dependencies
- Spawns **parallel sub-agents**, each with a fresh 200k context window
- Executes tasks simultaneously where possible
- Creates atomic git commits per task
- Runs automated verification against phase goals

```
You:    /gsd:execute-phase 1

        WAVE 1 (parallel)         WAVE 2 (parallel)
        ┌─────────┐ ┌─────────┐   ┌─────────┐ ┌─────────┐
        │ Plan 01 │ │ Plan 02 │ → │ Plan 03 │ │ Plan 04 │
        │ Models  │ │ Config  │   │ APIs    │ │ Services│
        └─────────┘ └─────────┘   └─────────┘ └─────────┘
```

**Output:** Working code with atomic commits, `SUMMARY.md`, `VERIFICATION.md`.

**Why GSD here:** gstack doesn't have autonomous execution. It expects you to write the code. GSD's wave execution with fresh context windows per agent is what prevents quality degradation on large features.

---

## Phase 4 — Review & QA (gstack)

This is where you switch to gstack's specialist roles. Run these in order:

### 4a. Code Review

**Command:** `/review`

Staff-engineer-level review of all changes. Auto-fixes obvious issues, flags production bugs, checks completeness.

```
You:    /review
Claude: [AUTO-FIXED] 3 issues (unused imports, missing error handling, typo)
        [ASK] Potential race condition in WebSocket handler → approve fix?
        [INFO] Review Readiness: 94% — missing edge case test for timeout
```

### 4b. Security Audit (if applicable)

**Command:** `/cso`

Run this for features touching auth, payments, user data, or external APIs. OWASP Top 10 + STRIDE threat modeling.

```
You:    /cso
Claude: [runs OWASP Top 10 + STRIDE analysis]
        [each finding includes confidence score + concrete exploit scenario]
        [filters out false positives — only 8/10+ confidence findings]
```

### 4c. Design Review (if frontend)

**Command:** `/design-review`

For UI features — audits design quality, catches AI-generated design slop, makes fixes with atomic commits.

```
You:    /design-review
Claude: [rates each design dimension 0-10]
        [fixes spacing, color consistency, responsive issues]
        [before/after screenshots]
```

### 4d. QA Testing

**Command:** `/qa <staging-url>`

The big one. Opens a **real Chromium browser**, navigates your app, clicks through flows, finds bugs, fixes them, and writes regression tests.

```
You:    /qa https://staging.myapp.com
Claude: [opens browser, navigates to app]
        [clicks through user flows]
        [FOUND] Button doesn't respond on mobile viewport
        [FIXED] Added touch event handler + regression test
        [VERIFIED] Re-tested — working on all viewports
```

**Why gstack here:** GSD has `/gsd:verify-work` but it's a manual walkthrough. gstack's `/qa` with real browser automation is significantly more thorough. The `/cso` security audit and `/design-review` have no equivalent in GSD at all.

---

## Phase 5 — Ship (gstack)

### 5a. Ship PR

**Command:** `/ship`

Runs tests, audits coverage, bootstraps test framework if needed, pushes to branch, opens PR.

```
You:    /ship
Claude: Tests: 42 → 51 (+9 new). Coverage: 78% → 84%.
        PR: github.com/you/project/pull/42
```

### 5b. Land & Deploy

**Command:** `/land-and-deploy`

Merges PR, waits for CI, deploys, verifies production health.

```
You:    /land-and-deploy
Claude: [merges PR #42]
        [CI passing — 51/51 tests]
        [deployed to production]
        [health check: all endpoints responding]
```

### 5c. Post-Deploy Monitoring (optional)

**Command:** `/canary`

Watches for console errors, performance regressions, and page failures after deploy.

---

## Phase 6 — Reflect & Next

### GSD: Complete Phase & Move On

```
/gsd:discuss-phase 2
/gsd:plan-phase 2
/gsd:execute-phase 2
... repeat ...
/gsd:complete-milestone
```

### gstack: Weekly Retro

```
/retro              # stats for current project
/retro global       # stats across all projects
```

### gstack: Document Changes

```
/document-release   # updates README, ARCHITECTURE, CONTRIBUTING, etc.
```

---

## Command Routing Cheat Sheet

| Stage | Use | Command | Skip |
|-------|-----|---------|------|
| **Product ideation** | gstack | `/office-hours` | GSD's question phase |
| **Requirements & roadmap** | GSD | `/gsd:new-project` | — |
| **Design decisions** | GSD | `/gsd:discuss-phase <N>` | — |
| **Implementation planning** | GSD | `/gsd:plan-phase <N>` | gstack `/plan-eng-review` |
| **Autonomous execution** | GSD | `/gsd:execute-phase <N>` | — |
| **Code review** | gstack | `/review` | GSD's built-in verifier |
| **Security audit** | gstack | `/cso` | — |
| **Design review** | gstack | `/design-review` | — |
| **Browser QA** | gstack | `/qa <url>` | GSD `/gsd:verify-work` |
| **Ship & PR** | gstack | `/ship` | GSD `/gsd:ship` |
| **Deploy & verify** | gstack | `/land-and-deploy` | — |
| **Post-deploy watch** | gstack | `/canary` | — |
| **Debugging** | gstack | `/investigate` | — |
| **Ad-hoc tasks** | GSD | `/gsd:quick` | — |
| **Fast inline fixes** | GSD | `/gsd:fast <text>` | — |
| **Milestone tracking** | GSD | `/gsd:complete-milestone` | — |
| **Weekly retro** | gstack | `/retro` | — |
| **Doc updates** | gstack | `/document-release` | — |
| **Multi-AI review** | gstack | `/codex` | — |

---

## Quick Mode — For Smaller Tasks

Not everything needs the full pipeline. For quick features or bug fixes:

### Option A: GSD Quick Mode
```
/gsd:quick
> "Add rate limiting to the API endpoints"
```
Then run gstack's `/review` and `/qa` on the result.

### Option B: gstack Only
For tasks that don't need spec-level planning:
```
/plan-eng-review    # quick architecture check
# ... build ...
/review             # code review
/qa                 # browser test
/ship               # ship it
```

---

## Tips for the Combined Setup

1. **Context window management** — Both tools add commands to your CLAUDE.md. Be selective about which gstack skills you register if context is tight. The essential gstack commands are: `/office-hours`, `/review`, `/qa`, `/ship`, `/cso`.

2. **Git hygiene** — GSD creates atomic commits per task during execution. gstack's `/review` may add more commits for auto-fixes. Use gstack's `/ship` (which handles squashing) rather than manually managing the commit history.

3. **State tracking** — GSD tracks project state in `.planning/STATE.md`. gstack doesn't have persistent state. GSD is your source of truth for "where am I in the project."

4. **When to skip the full pipeline** — Use `/gsd:quick` + `/review` for small changes. Use the full pipeline only for substantial features or milestone-level work.

5. **Parallel work** — GSD handles parallelism during execution (wave-based). For running multiple features simultaneously, use Conductor with gstack's sprint model across separate Claude Code sessions.

---

## Resources

| Resource | Link |
|----------|------|
| GSD GitHub | https://github.com/gsd-build/get-shit-done |
| GSD User Guide | https://github.com/gsd-build/get-shit-done/blob/main/docs/USER-GUIDE.md |
| gstack GitHub | https://github.com/garrytan/gstack |
| gstack Skill Deep Dives | https://github.com/garrytan/gstack/blob/main/docs/skills.md |
| gstack Architecture | https://github.com/garrytan/gstack/blob/main/ARCHITECTURE.md |
| Task Master (alternative) | https://github.com/eyaltoledano/claude-task-master |