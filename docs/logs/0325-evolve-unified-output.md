# 0325 Unified Evolve Output — All Reports to data/evolve/

## What Changed

All 4 evolver scripts now output to unified `.runtime/data/evolve/` directory with consistent JSON report format.

### New Directory Structure

```
.runtime/data/evolve/
├── reports/              ← all 4 report types (unified JSON)
│   ├── check_*.json
│   ├── eval_*.json
│   ├── diagnose_*.json
│   └── auto_test_*.json
├── violations/           ← commitment violations (diagnose/auto_test write)
│   └── current.jsonl
├── auto_sessions/        ← auto-test conversations (isolated from real sessions/)
└── state.yaml            ← cursor for incremental analysis
```

### Unified Report JSON Format

```json
{
  "type": "check | eval | diagnose | auto_test",
  "timestamp": "ISO-8601",
  "source": "what data was analyzed",
  "score": 0.85,
  "passed": 17,
  "total": 20,
  "summary": "human-readable summary",
  "details": [...],
  "suggestions": [
    { "primitive": "flow|commitment|scope|role", "action": "...", "reason": "..." }
  ]
}
```

### Files Changed

| File | Change |
|------|--------|
| agent/deploy.sh | Creates evolve/reports + evolve/violations + evolve/auto_sessions dirs |
| agent/flow/evolve_check/scripts/check_structure.py | Saves report to evolve/reports/check_*.json |
| agent/flow/evolve_eval/scripts/run_eval.py | evolve/reports/eval_*.json (was last_eval_results.json) |
| agent/flow/evolve_diagnose/scripts/diagnose.py | evolve/reports/diagnose_*.json + evolve/state.yaml + evolve/violations/ |
| agent/flow/evolve_auto/scripts/run_auto.py | evolve/reports/auto_test_*.json + evolve/auto_sessions/ |
| src/app.py | VIOLATIONS_DIR → .runtime/data/evolve/violations |
| 5 SKILL.md files | Updated output paths |
| agent/flow/inspect/SKILL.md | Updated directory tree |
| README.md | Updated .runtime/ tree + violations path |

### Key Design Decisions

- violations/ and reports/ are parallel outputs (not sequential)
- auto_sessions/ isolated from sessions/ (diagnose won't re-analyze test data)
- state.yaml cursor in evolve/ (not scattered)
- improve reads all reports from evolve/reports/*.json

51 tests passing.
