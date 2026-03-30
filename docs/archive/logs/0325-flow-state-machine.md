# 0325 Flow State Machine + Hardcoded URL Fix

## What Changed

### Task 1: Hardcoded URLs removed from SKILL.md
- check_health/SKILL.md: `curl http://localhost:8001` → generic `GET /health` description
- evolve_eval/SKILL.md: `--base-url http://localhost:8001` → `--base-url <APP_BASE_URL>`
- Principle: SKILL.md is DSL, no implementation details (ports, URLs)
- run_eval.py keeps `--base-url` default as CLI convenience (configurable)

### Task 2: flow.yaml `resource` field
- State machine example now includes `resource: task` to clarify what object has the state
- Template flows still empty (`flows: {}`), resource is in commented example

### Task 3: deploy.sh injects workflow into SOUL.md
- After merging scope + role, reads flow.yaml `flows` section
- Generates workflow text: `## Workflows → draft → submit (by default) → submitted → ...`
- Appends to SOUL.md (claude) or AGENTS.md (codex/kimi) — adapter-aware
- Only when flows are defined (empty flows = no injection)

### Task 4: check_structure.py graph validation
- New function `check_flow_graph()` validates per flow:
  - All transition from/to states in states list
  - All states reachable from first state
  - Terminal states exist (no infinite loops)
  - No isolated states
- Added as check #3 between Role and Commitment
- Report now has 4 checks: flow→skill, role↔flow, graph, commitment

### Task 5: diagnose.py flow transition extraction
- New function `extract_flow_transitions()` matches observed Skill calls against declared transitions
- Outputs per-flow: declared order vs observed order (with timestamps)
- Does NOT judge order compliance — evolver LLM does
- Added to both text report and JSON report

### Task 6: Documentation updated
- README.md: flows schema, workflow injection, evolve_check graph
- docs/guides/003: resource field, DSL principle, deploy injection
- docs/guides/004: check + diagnose enhanced descriptions
- agent/flow/README.md: resource, injection, graph validation
- docs/designs/e2e-test.md: Phase 4 + Phase 8 updated

## Cross-platform
- Workflow injection: appends to $PROMPT_FILE (SOUL.md or AGENTS.md) — adapter-aware
- Graph validation: pure file check, no platform dependency
- Transition extraction: reads prompts/*.jsonl — same format across platforms

## Files changed (14)
- agent/flow/check_health/SKILL.md
- agent/flow/evolve_eval/SKILL.md
- agent/flow/evolve_eval/scripts/run_eval.py
- agent/flow/flow.yaml
- agent/deploy.sh
- agent/flow/evolve_check/scripts/check_structure.py
- agent/flow/evolve_diagnose/scripts/diagnose.py
- agent/flow/evolve_diagnose/SKILL.md
- README.md
- docs/guides/003-four-primitives.md
- docs/guides/004-commitment-and-evolve.md
- agent/flow/README.md
- docs/designs/e2e-test.md
- docs/logs/0325-flow-state-machine.md (this file)

51 tests passing.
