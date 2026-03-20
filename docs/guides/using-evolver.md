# Using the Evolver

The evolver is a built-in role that helps you improve your Socialware App by analyzing runtime data and modifying the four primitives.

## When to Use Evolver

- Skills aren't working → evolver diagnoses and fixes Flow
- Constraint violations are frequent → evolver adjusts Commitment
- Users request things outside scope → evolver expands Scope
- Need more agent roles → evolver creates new Roles

## Getting Started

```bash
# From your workspace:
./agent/deploy.sh
./agent/start.sh --role evolver
```

## Manual Mode

### Step 1: Diagnose

```
You: "diagnose"
Evolver: → runs scripts/diagnose.py
         → "Found 3 issues:
            1. [Flow] create_task has 40% error rate
            2. [Commitment] C1 violated 5 times (review overdue)
            3. [Scope] 2 out-of-scope requests detected"
```

### Step 2: Evaluate

```
You: "evaluate"
Evolver: → runs scripts/run_eval.py
         → "Score: 3/5 (60%). Failing: create_task, review_task"
```

### Step 3: Improve

```
You: "improve the create_task skill"
Evolver: → reads diagnosis + eval
         → "Proposal: update create_task/SKILL.md to include
            the required JSON body format. Want me to apply?"
You: "yes"
Evolver: → edits SKILL.md → runs deploy.sh
         → "Done. Run 'evaluate' to check improvement."
```

## Auto Mode

For automated optimization:

```
You: "auto-optimize, run 5 iterations"
Evolver: → runs scripts/run_loop.py --iterations 5
         → evaluates → diagnoses → proposes → applies → re-evaluates
         → "Completed 5 iterations. Score: 60% → 80%.
            Changes: updated scope/SOUL.md, added error_handling skill.
            Apply these changes?"
You: "show diff"
Evolver: → shows what changed
You: "apply"
Evolver: → runs deploy.sh
```

## Growing eval_cases.yaml

The eval cases file is your "correct answer set". Grow it with your app:

| Phase | What to add |
|-------|-------------|
| P1 | Health check returns ok |
| P2 | Task CRUD works correctly |
| P3 | Quality metrics met (review time, etc.) |
| P4 | Team features work (notifications, assignments) |
| P5 | Role-based permissions enforced |

```bash
vim agent/flow/evolve_eval/eval_cases.yaml
```

## Data Sources

The evolver reads from `.runtime/data/`:

| Directory | Contains | Written by |
|-----------|----------|------------|
| `conversations/*.jsonl` | Agent interaction logs | PostToolUse hook (shell) or adapter (SDK) |
| `violations/*.jsonl` | Constraint violations | App backend (your responsibility) |

## Evolver vs Dev Role

| | dev | evolver |
|---|---|---|
| Purpose | Set up environment, navigate project | Analyze data, improve agent config |
| Skills | setup_claude, check_health | diagnose, eval, improve, auto |
| Data analysis | No | Yes (reads .runtime/data/) |
| When to use | Building the app | Improving the app after it runs |
