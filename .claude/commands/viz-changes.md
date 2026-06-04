---
name: viz-changes
description: Visualize what just changed — the 4 views of the diff (opt-in).
allowed-tools:
  - Read
  - Bash
  - Write
  - Grep
  - Glob
---

Read and follow the full instructions in `viz/commands/viz-changes.md`, then execute them for the
current project. Pass along any arguments: $ARGUMENTS

All real logic lives in `viz/commands/viz-changes.md` (so it ships with the viz/ folder and
survives deletion of viz/dev/). This file is only a thin pointer that Claude Code can discover.
