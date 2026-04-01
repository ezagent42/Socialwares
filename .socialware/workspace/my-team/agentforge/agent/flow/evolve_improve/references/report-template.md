# Improve Report Template

After applying changes, save a report using the script:

```bash
uv run agent/flow/evolve_improve/scripts/save_report.py \
  --change '{"primitive":"flow","file":"agent/flow/create_task/SKILL.md","action":"Updated trigger phrases and API endpoint notation","reason":"40% error rate — SKILL.md lacked request format"}' \
  --based-on diagnose_20250326_120000.json \
  --based-on eval_20250326_120000.json \
  --next-step "Run 'evaluate' to check if score improved"
```

## Change Object Fields

Each `--change` is a JSON object:

| Field | Required | Description |
|-------|----------|-------------|
| `primitive` | yes | Which primitive was changed: flow, commitment, scope, role |
| `file` | yes | File path that was modified |
| `action` | yes | What was changed (human-readable) |
| `reason` | yes | Why — evidence from diagnostic reports |

## Multiple Changes

Pass `--change` multiple times for batch improvements:

```bash
uv run agent/flow/evolve_improve/scripts/save_report.py \
  --change '{"primitive":"flow","file":"agent/flow/create_task/SKILL.md","action":"Added JSON body format","reason":"Missing request format"}' \
  --change '{"primitive":"commitment","file":"agent/commitment/commitment.yaml","action":"Added on_violation for C1","reason":"C1 violated but no escalation path"}' \
  --based-on diagnose_20250326_120000.json
```

## Output

Report saved to `.runtime/data/evolve/reports/improve_<timestamp>.json` with structure:

```json
{
  "type": "improve",
  "timestamp": "2025-03-26T12:00:00+00:00",
  "changes": [
    {
      "primitive": "flow",
      "file": "agent/flow/create_task/SKILL.md",
      "action": "Updated trigger phrases and API endpoint notation",
      "reason": "40% error rate — SKILL.md lacked request format"
    }
  ],
  "based_on": ["diagnose_20250326_120000.json", "eval_20250326_120000.json"],
  "next_step": "Run 'evaluate' to check if score improved"
}
```
