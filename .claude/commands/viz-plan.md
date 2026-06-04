---
name: viz-plan
description: Visualize the current plan — the 4 views of what's about to be built (opt-in).
allowed-tools:
  - Read
  - Bash
  - Write
  - Grep
  - Glob
---

Read and follow the full instructions in `viz/commands/viz-plan.md`, then execute them for the
current project. Pass along any arguments: $ARGUMENTS

All real logic lives in `viz/commands/viz-plan.md` (so it ships with the viz/ folder and
survives deletion of viz/dev/). This file is only a thin pointer that Claude Code can discover.
