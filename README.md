# claude-setup

Bootstrap configuration for new projects. Clone this into a new project folder to get a complete Claude Code setup out of the box.

## What's included

- **`CLAUDE.md`** — project-level instructions for Claude (workflow orchestration, verification cycle, skill routing)
- **`CLAUDE.local.md`** — private per-project config (staging URL, SIT settings); not committed
- **`.claude/`** — agents, commands, hooks, settings
- **`.mcp.json`** — MCP server registration (Chrome DevTools)
- **`plugins/superpowers/`** — vendored copy of [obra/superpowers](https://github.com/obra/superpowers): a complete development methodology with composable skills (TDD, systematic debugging, subagent-driven development, etc.)
- **`governance/`** — a portable **Feature-ID governance** module: a committed `features/` registry (features / bugs / backlog / epics), git-derived deploy status, a scoped sanity sweep, git-tree code attribution, and hard enforcement via git hooks + a CI gate — so nothing ships without a feature ID. Opt-in per project (see below).

## Feature governance — opt-in

The `governance/` module adds a committed feature/epic tracking system with real
enforcement. It is **not active until you install it** into the project. Run:

```
/setup-governance
```

Claude asks for your **deploy/state model** (single-branch `main` / two-branch
`develop`+`main` / tracking-only) and module codes, then materializes `features/`,
`scripts/`, `.githooks/`, the CI gate, and a `docs/adr/` entry, and appends the rules to
`CLAUDE.md`. Non-interactive equivalent: `bash governance/install.sh` (env-var driven).

The same `governance/INSTALL.md` runbook retro-adds governance to an **existing** project.
Full details: [`governance/README.md`](governance/README.md).

## Superpowers — auto-activated

Superpowers activates automatically. A `SessionStart` hook at `.claude/hooks/bootstrap-superpowers.sh` registers the vendored marketplace on first session; on the next session Claude Code prompts you to trust it once, and skills load automatically from then on. No manual `/plugin` commands needed.

Manual fallback (only if automation ever fails):

```
/plugin marketplace add ./plugins/superpowers
/plugin install superpowers@superpowers-dev
```

See `plugins/superpowers/README.md` for the full skill list.
