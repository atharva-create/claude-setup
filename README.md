# claude-setup

Bootstrap configuration for new projects. Clone this into a new project folder to get a complete Claude Code setup out of the box.

## What's included

- **`CLAUDE.md`** — project-level instructions for Claude (workflow orchestration, verification cycle, skill routing)
- **`CLAUDE.local.md`** — private per-project config (staging URL, SIT settings); not committed
- **`.claude/`** — agents, commands, hooks, settings
- **`.mcp.json`** — MCP server registration (Chrome DevTools)
- **`plugins/superpowers/`** — vendored copy of [obra/superpowers](https://github.com/obra/superpowers): a complete development methodology with composable skills (TDD, systematic debugging, subagent-driven development, etc.)

## Superpowers — auto-activated

Superpowers activates automatically. A `SessionStart` hook at `.claude/hooks/bootstrap-superpowers.sh` registers the vendored marketplace on first session; on the next session Claude Code prompts you to trust it once, and skills load automatically from then on. No manual `/plugin` commands needed.

Manual fallback (only if automation ever fails):

```
/plugin marketplace add ./plugins/superpowers
/plugin install superpowers@superpowers-dev
```

See `plugins/superpowers/README.md` for the full skill list.
