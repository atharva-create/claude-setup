---
name: setup-governance
description: Install the Feature-ID governance system (features/ registry, epics, git hooks, CI gate) into this project.
allowed-tools:
  - Read
  - Bash
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

Read and follow the full runbook in `governance/INSTALL.md`, then execute it for the current
project. Pass along any arguments: $ARGUMENTS

The runbook installs the portable Feature-ID governance module: a committed `features/`
registry (features / bugs / backlog / epics), git-derived deploy status, a scoped sanity
sweep, git-tree code attribution, and hard enforcement via git hooks + a CI gate — so
nothing ships without a feature ID.

Key point: **ask the user for their deploy/state model** (single-branch / two-branch /
tracking) and module codes via AskUserQuestion before installing — the runbook explains the
options. All real logic lives in `governance/` (INSTALL.md + install.sh), so it ships with
that folder; this file is only a thin pointer Claude Code can discover.
