# 0324 Evolve V3 Phase 2+3 — SDK Adapters + Evolver Functions

## Phase 2: SDK Adapter Rewrite

### agent/adapters/base.py
- `RoleConfig.from_runtime()`: tries both SOUL.md and AGENTS.md, reads .workspace_root, finds skills in .claude/ or .agents/
- New `save_session()`: saves complete SDK session to `.runtime/data/sessions/{role}_session_{timestamp}.json`
- `BaseAdapter.launch_sdk()`: now `async` generator yielding messages

### agent/adapters/claude/sdk.py
- Uses `claude_code_sdk.query()` with `ClaudeCodeOptions`
- `system_prompt` from merged SOUL.md
- `allowed_tools` explicitly listed
- Async generator: `yield message`

### agent/adapters/codex/sdk.py
- Uses `openai-agents` `Agent` + `Runner.run()`
- Built-in tracing (enabled by default in OpenAI SDK)
- Yields structured dict with role/content/trace_id

### agent/adapters/kimicode/sdk.py
- `launch_sdk()` raises `NotImplementedError` (Kimi has no SDK)
- Documented as platform limitation

### src/start_agent.py
- Fully async with `asyncio.run()`
- Streams messages from `adapter.launch_sdk(prompt)`
- Serializes and saves full session via `save_session()`
- Handles NotImplementedError (Kimi) + KeyboardInterrupt
- `--prompt` argument for initial message

### agent/Makefile.template
- `ADAPTER ?= claude` variable
- `make run ROLE=x` target for SDK mode

## Phase 3: Evolver Functions

### NEW: agent/flow/evolve_check/ (structure consistency)
- `SKILL.md`: trigger, usage, what it checks
- `scripts/check_structure.py`:
  1. flow.yaml actions → SKILL.md exists?
  2. commitment from/to roles → role/*.md exists?
  3. commitment from/to actions → flow.yaml exists?
  4. scope capabilities → listed for manual review
- Exit code 0 = pass, 1 = issues found
- No app needed (pure file check)

### REWRITTEN: agent/flow/evolve_diagnose/scripts/diagnose.py
- Reads `.runtime/data/prompts/*.jsonl` (hook data)
- Reads `.runtime/data/sessions/*.json` (SDK sessions)
- Reads `commitment.yaml` (new `--commitment` flag, was `--constraints`)
- Cursor-based: reads `evolve_state.yaml`, only analyzes new data
- Computes fulfillment rate per commitment: triggered/fulfilled
- Saves: last_diagnosis.txt + evolve_state.yaml

### REWRITTEN: agent/flow/evolve_auto/scripts/run_auto.py (replaces run_loop.py)
- Reads `conversation_checks` from eval_cases.yaml
- For each check: SDK launches agent → sends input → collects trace → checks expected_skill
- Scores: pass/fail per case + overall percentage
- Saves traces to `.runtime/data/auto_tests/`
- Deleted: old run_loop.py

### Updated: agent/flow/flow.yaml
- Added `evolve_check` action for evolver role

### Updated SKILL.md files
- evolve_auto: references run_auto.py, conversation testing
- evolve_diagnose: --commitment flag, prompts/sessions data sources

## Tests (50 passing, +4 new)

| New test | What it tests |
|----------|---------------|
| test_check_structure.py::test_template_passes | Template's own primitives pass structure check |
| test_check_structure.py::test_detects_missing_skill | Missing SKILL.md detected |
| test_check_structure.py::test_detects_missing_commitment_role | Non-existent role in commitment detected |
| test_diagnose.py (rewritten) | Uses --commitment flag, tests prompt data + fulfillment rate |
