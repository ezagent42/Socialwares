# Violation Format Reference

## Saving Violations

After running `diagnose.py` and judging commitment conditions, save violations using the script:

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
uv run agent/flow/evolve_session_diagnose/scripts/save_violation.py \
  --commitment C1 \
  --description "review not completed within 24h of submission" \
  --role reviewer \
  --action review_task \
  --evidence "submit_task at 02:33, no review_task event found within 24h"
```

## Fields

| Field | Required | Description |
|-------|----------|-------------|
| `--commitment` | yes | Commitment ID from commitment.yaml (e.g. C1) |
| `--description` | yes | What was violated (human-readable) |
| `--role` | yes | Which role is responsible for the violation |
| `--action` | no | Which action was involved |
| `--evidence` | no | Evidence from diagnose report (timestamps, counts, diffs) |

## JSONL Format

Each violation is appended as one JSON line to `.runtime/data/evolve/violations/current.jsonl`:

```json
{"id":"v-a1b2c3d4","commitment":"C1","description":"review overdue","role":"reviewer","action":"review_task","evidence":"submit at 02:33, no review within 24h","resolved":false,"created_at":"2025-03-26T12:00:00+00:00"}
```

## Resolving Violations

Violations can be resolved via the app's REST API:

```
GET  /violations              → list unresolved violations
POST /violations/{id}/resolve → mark as resolved
```

## When to Save Violations

Save a violation when ALL of these are true:
1. `diagnose.py` extracted matching from/to events
2. You (evolver LLM) judged the commitment condition as VIOLATED
3. The evidence is specific (timestamps, counts, not guesses)

Do NOT save violations for:
- FULFILLED commitments
- INSUFFICIENT DATA (say so in conversation instead)
- Guesses without evidence
