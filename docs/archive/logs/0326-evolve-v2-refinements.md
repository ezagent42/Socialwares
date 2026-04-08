# 0326 Evolve V2 Refinements

## What Changed (since 0325-flow-state-machine.md)

### 1. auto-test expected_contains / expected_not_contains
- `run_auto.py`: 3 checks per case — expected_skill + expected_contains + expected_not_contains
- `default.yaml`: new format with field descriptions header
- `failure-analysis.md`: content check failure patterns added

### 2. evolve_improve enhancements
- Thinking order: Flow → Commitment → Scope → Role
- Primitive + backend chain: flow change → backend code change
- `scripts/save_report.py`: persist improvement decisions
- `references/report-template.md`: report format documentation
- `references/improvement-guide.md`: removed hardcoded URLs, fixed old commitment schema

### 3. Hardcoded URL cleanup
- `evolve_eval/SKILL.md`: `http://localhost:8001` → APP_PORT env var description
- `evolve_eval/eval_cases.yaml`: comment uses `<APP_BASE_URL>`
- `improvement-guide.md`: curl command → endpoint notation

### 4. make run requires PROMPT
- `Makefile.template`: `PROMPT=` required, error without it
- `start_agent.py`: `--prompt` is required, no default

### 5. start.sh multi-role tmux fix
- Validates all roles exist before launching tmux
- Checks tmux is installed
- Waits for session initialization with `has-session` check

### 6. make sync now syncs evolver scripts
- Added `agent/flow/*/scripts/*.py` to sync target
- Only copies scripts that exist in template (won't touch user-created skills)

### 7. SDK session filtering
- `base.py`: new `is_noise()` function filters ratelimit/hook/init/system messages
- `start_agent.py`: uses `is_noise()` + pre-serialized dicts from adapter (no duplicate serialization)
- `run_auto.py`: uses shared `is_noise()` from base.py

### 8. check_structure.py on_violation fix
- `on_violation` can be string or dict — added `isinstance(violation, dict)` guard

### 9. diagnose.py cursor fix
- Cursor save/load mismatch: saved under `last_extraction` key but read at top level
- Fixed to save directly at top level

### 10. save_violation.py
- New script for evolver to persist commitment violations
- `references/violation-format.md`: format documentation
- `evolve_diagnose/SKILL.md`: updated flow + output + references

### 11. Skill rename (clarity)
- `evolve_check` → `evolve_structure_check`
- `evolve_eval` → `evolve_api_check`
- `evolve_diagnose` → `evolve_session_diagnose`
- Updated: flow.yaml, all SKILL.md, README, guides, tests, e2e-test

### 12. Documentation audit fixes
- README: evolve_auto described as "conversation testing" (was "improvement loop")
- 002-quickstart: `log_conversation()` → `save_session()` + `is_noise()`
- 004-guide: auto mode description corrected
- evolve_check SKILL.md: added flow graph validation + role-flow check
- evolve_diagnose SKILL.md: removed false violations output claim
- Directory trees: added save_report.py, conversation_tests/, references/
- e2e-test: Phase 1.2 README.md excluded, Phase 2.3 reviewer skills, Phase 7.12 closed state reachable

### 13. .gitignore
- Added `docs/logs/` and `docs/discuss/`

## Files changed (~30+)
Key files: agent/flow/*/SKILL.md, agent/flow/flow.yaml, README.md, docs/guides/001-004, docs/designs/e2e-test.md, agent/Makefile.template, src/start_agent.py, agent/start.sh, agent/adapters/base.py, tests/*.py

51 tests passing.
