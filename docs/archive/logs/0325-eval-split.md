# 0325 Eval Split — API Tests vs Conversation Tests

## What Changed

Separated two distinct testing mechanisms into different files and scripts.

### Before
```
agent/flow/evolve_eval/eval_cases.yaml
  ├── api_checks        (run by run_eval.py)
  └── conversation_checks (also in this file, listed by run_eval.py)
```

### After
```
agent/flow/evolve_eval/
  ├── eval_cases.yaml      ← API checks only (run_eval.py)
  └── scripts/run_eval.py  ← only runs api_checks

agent/flow/evolve_auto/
  ├── conversation_tests/  ← NEW directory
  │   └── default.yaml     ← per-role conversation test cases
  ├── scripts/run_auto.py  ← reads conversation_tests/, added failure analysis
  └── SKILL.md             ← updated usage
```

### Why

Two fundamentally different data sources:
- **API checks** (run_eval.py): direct HTTP calls, no agent needed
- **Conversation tests** (run_auto.py): run agent via SDK, collect traces

Conversation tests will grow large (multiple files per role), shouldn't be mixed with API checks.

### Files Changed

| File | Change |
|------|--------|
| agent/flow/evolve_eval/eval_cases.yaml | Removed conversation_checks, API only |
| agent/flow/evolve_eval/scripts/run_eval.py | load_cases returns list (not tuple), no conversation handling |
| agent/flow/evolve_eval/SKILL.md | Removed conversation references |
| agent/flow/evolve_auto/conversation_tests/default.yaml | NEW: per-role test cases |
| agent/flow/evolve_auto/scripts/run_auto.py | Reads from --tests-dir, added failure analysis with four-primitive suggestions |
| agent/flow/evolve_auto/SKILL.md | Updated usage |
| README.md | Evolver table updated |
| docs/guides/004-commitment-and-evolve.md | Eval section updated |
| tests/test_eval_script.py | Added test_api_only_no_conversation_checks |

### Evolver's 5 functions now:

| Function | Data Source | Script |
|----------|-----------|--------|
| evolve_check | agent/ files (static) | check_structure.py |
| evolve_eval | API endpoints (needs app) | run_eval.py + eval_cases.yaml |
| evolve_diagnose | prompts/*.jsonl + sessions/*.json (runtime data) | diagnose.py |
| evolve_auto | conversation_tests/*.yaml via SDK (active testing) | run_auto.py |
| evolve_improve | diagnose + eval + auto results (conversational) | evolver agent |

51 tests passing.
