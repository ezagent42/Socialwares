# Commitment and Evolution

## Commitment (Constraints)

See [003-four-primitives.md](003-four-primitives.md) for format reference.

### App Developer Responsibilities

The template provides the violation format and notification mechanism.
Detection logic is your responsibility because each app has different state machines and storage.

#### What you need to implement:

1. **Record timestamps** on state transitions in your data layer
2. **Implement detection** — choose one or more:

   **Option A: API middleware (passive)** — check on every request:
   ```python
   @app.middleware("http")
   async def check_constraints(request, call_next):
       violations = find_expired_constraints()
       for v in violations:
           write_violation(v)
       return await call_next(request)
   ```

   **Option B: Background task (active)**:
   ```python
   @app.on_event("startup")
   async def start_constraint_checker():
       asyncio.create_task(check_constraints_periodically(interval=3600))
   ```

   **Option C: Cron endpoint (external)**:
   ```bash
   curl -X POST http://localhost:8001/check-constraints
   ```

3. **Write violations** to `.runtime/data/violations/current.jsonl`

### Violation API

```bash
GET  /violations                    # list unresolved
POST /violations/{id}/resolve       # mark as resolved
```

---

## Evolver

Built-in role for improving your app based on runtime evidence.

### Getting Started

```bash
make start ROLE=evolver
```

### Manual Mode

```
You: "diagnose"        → scripts/diagnose.py scans runtime data → report
You: "evaluate"        → scripts/run_eval.py runs eval cases → score
You: "improve"         → propose changes based on evidence → apply
```

### Auto Mode

```
You: "auto-optimize, run 5 iterations"
Evolver: → evaluate → diagnose → propose → apply → re-evaluate
         → reports results, you decide whether to apply
```

### Data Sources

| Source | Location | What evolver looks for |
|--------|----------|----------------------|
| Conversation logs | .runtime/data/conversations/*.jsonl | Failed actions, missing capabilities |
| Violation queue | .runtime/data/violations/*.jsonl | Constraint violation patterns |
| Eval cases | agent/flow/evolve_eval/eval_cases.yaml | Performance score trends |
| Constraints | agent/commitment/constraints.yaml | Active constraint summary |

### Growing eval_cases.yaml

Your "correct answer set" — grows with the app:

| Phase | What to add |
|-------|-------------|
| P1 | Health check returns ok |
| P2 | Task CRUD works correctly |
| P3 | Quality metrics met |
| P5 | Role-based permissions enforced |

### Evolver vs Dev

| | dev | evolver |
|---|---|---|
| Purpose | Set up environment, navigate project | Analyze data, improve agent config |
| Data analysis | No | Yes (reads .runtime/data/) |
| When | Building the app | After running, has data |
