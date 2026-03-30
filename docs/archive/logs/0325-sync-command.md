# 0325 Sync Command + SDK Fix + Chain Verification

## make sync

Added `make sync` command to workspace Makefile.template:
- Copies adapters, deploy.sh, start.sh, Makefile, start_agent.py from template root
- Uses `git rev-parse --show-toplevel` to find template root
- Does NOT sync skills (those are app-specific)
- After sync: `make clean && make deploy` to rebuild

Why needed: `create-my-socialware` copies files to workspace. When template changes,
workspace files become stale. Write tool breaks hardlinks (creates new inode).

## claude-agent-sdk (replacing claude-code-sdk)

| | claude-code-sdk (old) | claude-agent-sdk (new) |
|---|---|---|
| Version | 0.0.25 | 0.1.50 |
| rate_limit_event | Throws exception (crashes) | Silently collected |
| Message types | Throws on unknown types | Handles all types |
| Client pattern | `async for msg in query()` | `ClaudeSDKClient` context manager |
| Used by | (nobody mainstream) | EvoSkill |

## Full chain verification

All 11 checkpoints passed:
1. Deploy output: skills(symlinks) + hooks + SOUL.md + settings ✅
2. Skills are symlinks to workspace agent/flow/ ✅
3. Hooks: UserPromptSubmit + PreToolUse registered ✅
4. SDK: cwd=project_dir, 4 skills loaded ✅
5. Data dirs: prompts + sessions + evolve/ ✅
6. Hook data: 95 entries in prompts/current.jsonl ✅
7. Reports: check + eval + diagnose + auto_test all present ✅
8. Auto sessions isolated from real sessions ✅
9. Violations API reads evolve/violations/ ✅
10. Commitment.yaml deployed to all roles ✅
11. Adapter sync: now via `make sync` ✅ (was broken by hardlink issue)

## Files changed

- agent/Makefile.template: added sync target + TEMPLATE_ROOT
- README.md: documented make sync, updated Makefile description
- docs/designs/e2e-test.md: claude-code-sdk → claude-agent-sdk
- pyproject.toml: claude = ["claude-agent-sdk>=0.1.16"]

51 tests passing.
