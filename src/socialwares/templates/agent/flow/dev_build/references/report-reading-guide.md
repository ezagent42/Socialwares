# Evolve Report Reading Guide

## Report Types

| Filename Prefix | Source Skill | Content |
|----------------|-------------|---------|
| `check_*.json` | evolve_structure_check | Four-primitive consistency check |
| `eval_*.json` | evolve_api_check | API endpoint test results |
| `diagnose_*.json` | evolve_session_diagnose | Conversation data diagnosis |

## Report Format

```json
{
  "type": "check | eval | diagnose",
  "timestamp": "ISO 8601",
  "score": 0.0-1.0,
  "passed": 4,
  "total": 4,
  "summary": "human-readable summary",
  "details": ["issue 1", "issue 2"],
  "suggestions": [
    {
      "primitive": "flow | role | scope | commitment",
      "action": "what to do",
      "reason": "why"
    }
  ]
}
```

## Improvement Priority

1. **Structure issues** (structure check failures) — block other checks
2. **API failures** (eval failures) — functionality unavailable
3. **Insufficient coverage** (eval suggestions) — missing tests
4. **Commitment violations** (diagnose violations) — collaboration quality
5. **Scope gaps** (scope gaps) — mismatch between declaration and implementation

## Common Fix Patterns

### Missing SKILL.md
```bash
mkdir -p agent/flow/{action}
# Write SKILL.md
# Register app.action("action", role=[...]) in socialware.py
socialwares deploy
```

### Missing eval case
```yaml
# Add to agent/flow/evolve_api_check/eval_cases.yaml:
- description: "Test {action}"
  method: POST
  endpoint: /api/{resource}
  body: '{"key": "value"}'
  expected_status: 200
```

### Commitment violation
Check whether the Flow steps in SKILL.md guide the role to complete the committed actions.
