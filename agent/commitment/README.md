# Commitment — What

Defines trackable commitments and evaluation criteria.

## Core Concept

Commitment is **declarative**: it describes "what counts as meeting the standard", without prescribing "how to check".

Execution method is determined by the App's Biz layer (`src/`), for example:
- API middleware auto-checks
- Cron scheduled evaluations
- Eval scripts run on demand
- Agent self-checks

## Files

- `eval.yaml` — Commitment declarations

## eval.yaml Format

```yaml
commitments:
  C1:
    description: "Describe the commitment"
    metric: metric_name          # Evaluation metric name
    threshold: ">=4.5"           # Passing threshold (free format)
    debtor_role: reviewer        # Who is responsible (optional)
    creditor_role: submitter     # Who benefits (optional)
```

Commitments are not limited to time SLAs; they can be any measurable standard:
- Time: "Complete review within 72h"
- Quality: "Customer satisfaction ≥ 4.5"
- Quantity: "Complete ≥ 3 tasks per week"
- Custom: Any App-specific evaluation metric

## deploy.sh Processing

`eval.yaml` is copied to each role's `.runtime/agents/{name}/eval.yaml`,
so the Agent can reference commitment standards at runtime.
