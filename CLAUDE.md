## Workflow Orchestration

### 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One tack per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management
1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

## gstack

- Available skills: `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/retro`, `/investigate`, `/document-release`, `/codex`, `/cso`, `/autoplan`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`
- If gstack skills aren't working, run `cd .claude/skills/gstack && ./setup` to build the binary and register skills.

## Superpowers

Vendored at `plugins/superpowers/` (upstream: https://github.com/obra/superpowers). A complete development methodology built on composable skills: brainstorming, TDD, systematic debugging, subagent-driven development, verification-before-completion, writing-plans, using-git-worktrees, and more.

Install into Claude Code from this repo:

```
/plugin marketplace add ./plugins/superpowers
/plugin install superpowers@superpowers-dev
```

After install, skills trigger automatically — no slash commands needed. Verify with: "Tell me about your superpowers". To update, re-run `git pull` on the upstream URL inside `plugins/superpowers/` (or re-vendor) and reinstall.

## Browser Automation — Chrome DevTools ONLY

- **Chrome DevTools MCP is the ONLY browser automation tool. No Playwright, no Puppeteer, no alternatives. Ever.**
- All browser testing and verification MUST use `mcp__chrome-devtools__*` tools.
- Never use `mcp__claude-in-chrome__*` tools.
- For general web browsing (not testing), `/browse` from gstack may be used.
- **MCP config location**: MCP servers MUST be registered in `~/.claude.json` (user scope) or `.mcp.json` (project scope). NOT in `settings.json` — that file is for permissions/hooks only. Use `claude mcp add chrome-devtools --scope user -- npx -y chrome-devtools-mcp@latest --viewport 1024x768` to register correctly.
- **If `mcp__chrome-devtools__*` tools are not available**: Check that `.mcp.json` exists at project root, kill stale processes (`pkill -f chrome-devtools-mcp`), and restart the session.

## SIT Verification Config (opt-in)

Enable SIT (System Integration Testing) verification by configuring these values. If not set, only local verification (Stage 1) is active.

```
SIT Enabled: true
SIT URL: <sit-server-url>
SIT Health Endpoint: <sit-server-url>/api/health
SIT Branch: develop
```

- **Branch model**: `main` = production, `develop` = SIT server. Feature branches branch off `develop`.
- **Auto-deploy**: Pushing to `develop` triggers auto-deploy to the SIT server.
- **Deploy detection**: Claude polls the SIT Health Endpoint until the deployed commit SHA matches what was pushed. Timeout: 5 minutes.
- **Revert strategy**: On SIT test failure, `git revert` the merge commit on `develop` (safe, preserves history). Feature branch is preserved for fixing.
- **Post-revert note**: After revert, auto-deploy triggers again with the reverted code. Expect a brief window (roughly deploy time) where the failed build is still live on SIT.

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## Self-Verifying Development Cycle

For EVERY feature, bug fix, or code change — this is MANDATORY and enforced by a Stop hook.

### 0. Clean Up
- Run: `rm -f $HOME/.cache/.claude-verified-*`
- This clears any stale verification sentinel from a previous task

### 1. Define Done First
- Before writing any code, state what "done" looks like
- List specific things to verify (UI renders correctly, API returns expected data, form submits, etc.)
- Write these as checkable criteria

### 2. Make the Change
- Write the code
- If backend: test API endpoints via curl or the browser
- If frontend: verify in browser via Chrome DevTools MCP

### 3. Verify with Chrome DevTools MCP (MANDATORY)
- Use Chrome DevTools MCP tools to open the app at the staging URL in a real Chrome window
- NEVER test against production. Staging/localhost only.
- Navigate to the affected page/feature (`mcp__chrome-devtools__navigate_page`)
- Take screenshots to verify visual state (`mcp__chrome-devtools__take_screenshot`)
- Check console for errors (`mcp__chrome-devtools__list_console_messages`)
- Test the actual user flow — click buttons (`mcp__chrome-devtools__click`), fill forms (`mcp__chrome-devtools__fill`), submit
- Wait for elements to render (`mcp__chrome-devtools__wait_for`)
- Run assertions if needed (`mcp__chrome-devtools__evaluate_script`)
- Verify each "done" criterion from step 1

### 4. Self-Heal
- If ANY verification fails: fix the issue, then re-verify from step 3
- Do NOT tell the user "done" until ALL criteria pass
- Loop steps 3-4 until everything works
- Maximum 5 fix-verify cycles before escalating to user

### 5. Mark Verified
- After all verifications pass, create the sentinel file:
  ```
  touch $HOME/.cache/.claude-verified-$(date +%s)
  ```
- Show screenshot evidence of working state
- List all verifications performed and their results
- If any criteria couldn't be verified automatically, flag them

### What Counts as Verification
- **Frontend changes**: Navigate to page, screenshot, check console, test interactions
- **Backend API changes**: Use `mcp__chrome-devtools__evaluate_script` to fetch endpoints and verify responses, or use curl then verify the frontend consumer
- **Backend-only (no UI)**: If the project has no frontend at all, skip browser verification and touch the sentinel after running tests via CLI
- **Config/docs only changes**: No verification needed (the Stop hook ignores non-code files)
- **Subagent-produced changes**: Subagents do NOT have Chrome DevTools MCP access. The stop hook auto-detects subagent context (worktree or marker file) and skips enforcement. Browser verification is the MAIN AGENT's responsibility after subagent completion. After a subagent returns with code changes, the main agent MUST verify before marking the task complete.

### Staging URL
Each project should set its staging URL in CLAUDE.local.md:
```
Staging URL: http://localhost:3000
```

### Stage 2: SIT Verification (triggered by /ship)

This stage only runs if `SIT Enabled: true` is set in the project's CLAUDE.md. If not configured, /ship skips SIT and proceeds with local-only verification.

The full two-stage flow:
```
Stage 1 (local)  →  Stage 2 (SIT)  →  PR to main
localhost test       deployed test      production-ready
Stop hook enforces   /ship triggers     /ship creates PR
```

#### 2a. Merge Queue Check
Before merging to develop, verify the queue is clear:
- Check if a `.sit-testing` lock file exists at `$HOME/.cache/.sit-testing-lock`
- If locked: another feature is being SIT-tested. Wait or alert the user.
- If clear: create the lock file with current branch name and timestamp
- Lock format: `echo "$(git branch --show-current) $(date +%s)" > $HOME/.cache/.sit-testing-lock`

#### 2b. Push and Merge to Develop
- Push feature branch to remote: `git push origin <feature-branch>`
- Merge feature into develop (no-ff): `git checkout develop && git merge --no-ff <feature-branch>`
- Push develop: `git push origin develop`
- Record the merge commit SHA for later verification

#### 2c. Wait for Deploy
- Poll the SIT Health Endpoint every 10 seconds
- Check that the response includes the expected commit SHA (from step 2b)
- Example health check: `curl -s <SIT Health Endpoint> | jq -r '.commit'`
- Timeout: **5 minutes**. If not ready by then, proceed to revert (step 2f)

#### 2d. Verify on SIT
- Use Chrome DevTools MCP tools to test against the **SIT URL** (not localhost)
- Navigate to affected pages (`mcp__chrome-devtools__navigate_page` with SIT URL)
- Take screenshots to verify visual state
- Check console for errors
- Test the actual user flows
- Verify each "done" criterion from Stage 1, step 1

#### 2e. On SIT Pass
- Remove the `.sit-testing` lock file
- Create PR from develop to main via /ship
- Report success with screenshot evidence from SIT

#### 2f. On SIT Failure
- **First failure**: Wait 30 seconds, then retry the full SIT verification (step 2d) once. This catches transient issues (network blips, timing).
- **Second failure or timeout**: Revert the merge on develop:
  ```
  git checkout develop
  git revert <merge-commit-sha> --no-edit
  git push origin develop
  ```
- Remove the `.sit-testing` lock file
- Preserve the feature branch for debugging
- Report failure with details: what failed, screenshots, console errors
- Do NOT create a PR to main

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
