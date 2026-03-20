# Commitment — What

Defines constraints on flow transitions. Commitments bind to edges in the state machine (flow.yaml) and enforce time, quality, or certainty requirements.

## Core Concept

Commitment ≠ performance KPI. Commitment = **constraint on a flow edge**.

When a state transition happens (e.g., submitted → under_review), the bound constraint must be satisfied. If not, a violation is recorded and an escalation action is triggered for the responsible role.

## Files

- `constraints.yaml` — constraint definitions bound to flow edges

## constraints.yaml Format

### Transition constraints (bind to state machine edges)

```yaml
transition_constraints:
  C1:
    description: "Review within 72h"
    on:                              # Which edge this binds to
      flow: F1                       # flow.yaml flows.F1
      from: submitted                # source state
      action: review                 # action that triggers transition
    type: time                       # time | quality | certainty
    deadline: 72h
    on_violation:
      trigger_action: force_resolve  # escalation action
      trigger_role: admin            # who handles it
```

### Action constraints (postconditions on direct actions)

```yaml
action_constraints:
  C1:
    description: "Health check returns ok"
    on: { action: check_health }
    type: postcondition
    expected: '{"status": "ok"}'
```

## Constraint Types

| Type | What it constrains | Example |
|------|-------------------|---------|
| `time` | Transition must happen within deadline | "Review within 72h" |
| `quality` | Action output must meet standard | "Must include justification" |
| `certainty` | State must not get stuck | "Must leave 'pending' within 48h" |
| `postcondition` | Action result must match expected | "Health returns ok" |

## Violation Detection — App Developer Responsibilities

The template provides the **violation format and notification mechanism**.
Detection logic is the **app developer's responsibility** because each app has different state machines, storage, and timing needs.

### What you need to implement:

1. **Record timestamps** on state transitions in your data layer
2. **Implement detection** — choose one or more:

   **Option A: API middleware (passive)** — check on every request:
   ```python
   @app.middleware("http")
   async def check_constraints(request, call_next):
       # Check pending constraints against current time
       violations = find_expired_constraints()
       for v in violations:
           write_violation(v)
       return await call_next(request)
   ```

   **Option B: Background task (active)** — periodic check:
   ```python
   @app.on_event("startup")
   async def start_constraint_checker():
       asyncio.create_task(check_constraints_periodically(interval=3600))
   ```

   **Option C: Cron endpoint (external)** — external cron calls:
   ```bash
   curl -X POST http://localhost:8001/check-constraints
   ```

3. **Write violations** to `.runtime/data/violations/current.jsonl`:
   ```json
   {"id": "v-001", "constraint": "C1", "description": "review overdue", "trigger_action": "force_resolve", "trigger_role": "admin", "detected_at": "2026-03-20T10:00:00Z", "resolved": false}
   ```

## deploy.sh Processing

`constraints.yaml` is copied to each role's `.runtime/agents/{name}/constraints.yaml`.

## SessionStart Hook

deploy.sh generates a `check_violations.sh` hook for each role.
On session start, it reads `.runtime/data/violations/*.jsonl` and reports
unresolved violations assigned to the current role.
