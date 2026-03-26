# 0324 Evolve V3 Phase 1 — Adapter-Aware Deploy + Hook Overhaul

## Overview

deploy.sh rewritten to support --adapter parameter. Hook system overhauled: replaced PostToolUse + SessionStart with UserPromptSubmit + PreToolUse (cross-platform Claude + Codex).

## Code Changes

### agent/deploy.sh (rewritten)
- Added `--adapter` parameter (claude/codex/kimi, default: claude)
- Per-adapter output:
  - Claude: `.claude/skills/`, `.claude/hooks/`, `settings.local.json`, `SOUL.md`
  - Codex: `.agents/skills/`, `.codex/hooks/`, `.codex/hooks.json` + `config.toml`, `AGENTS.md`
  - Kimi: `.agents/skills/`, `AGENTS.md`, no hooks
- Removed: SessionStart `check_violations.sh` (violations don't need hook broadcast)
- Removed: PostToolUse `log_action.sh` (Codex doesn't support PostToolUse)
- Added: UserPromptSubmit `log_prompt.sh` (Claude + Codex)
- Added: PreToolUse `log_tool.sh` (Claude + Codex)
- New data dirs: `.runtime/data/prompts/` + `.runtime/data/sessions/`

### agent/Makefile.template
- Added `ADAPTER ?= claude` variable
- Fixed `CONSTRAINTS` path: `constraints.yaml` → `commitment.yaml`
- deploy/start pass `--adapter $(ADAPTER)`
- Added `run` target (SDK mode via start_agent.py)

### Tests (46 passing)

| File | Changes |
|------|---------|
| test_deploy.py | TestHooksGenerated: log_prompt + log_tool + hooks_registered (no PostToolUse/SessionStart). Added data/prompts + data/sessions dir tests. Added codex/kimi AGENTS.md tests. |
| test_hooks.py | Removed TestLogActionHook + TestCheckViolationsHook. Added TestLogPromptHook + TestLogToolHook. |

## Documentation Fixes (11 files)

All stale references updated to match new hook names and data paths:

| File | What changed |
|------|-------------|
| README.md | hooks listing, deploy output, runtime data section (prompts/ not conversations/) |
| docs/guides/002-quickstart.md | FAQ on conversation logging |
| docs/guides/003-four-primitives.md | deploy hook tagging section |
| docs/guides/004-commitment-and-evolve.md | data flow, lifecycle, data sources |
| agent/commitment/README.md | lifecycle, deploy processing |
| agent/commitment/commitment.yaml | header comment |
| agent/role/README.md | deploy processing steps |
| agent/flow/evolve_diagnose/SKILL.md | data sources table |
| agent/flow/inspect/SKILL.md | directory structure |
| docs/discuss/commitment.md | data capture, hook names, improvement cycle |

## Cross-Platform Compatibility (verified)

| Feature | Claude | Codex | Kimi |
|---------|--------|-------|------|
| UserPromptSubmit hook | ✅ | ✅ (needs codex_hooks=true) | ❌ |
| PreToolUse hook | ✅ | ✅ (needs codex_hooks=true) | ❌ |
| Skills dir | .claude/skills/ | .agents/skills/ | .agents/skills/ |
| Prompt file | SOUL.md | AGENTS.md | AGENTS.md |
| Hook config | settings.local.json | .codex/hooks.json | none |
