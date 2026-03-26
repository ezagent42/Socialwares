# Flow — How

Defines operations the Agent can execute (Skills) and their state machines.

## Structure

```
flow/
├── flow.yaml             ← Action registry: state machines + direct actions
├── check_health/
│   └── SKILL.md
├── setup_claude/
│   └── SKILL.md
├── inspect/
│   └── SKILL.md
├── evolve_structure_check/
│   ├── SKILL.md
│   └── scripts/check_structure.py
├── evolve_session_diagnose/
│   ├── SKILL.md
│   └── scripts/diagnose.py
├── evolve_api_check/
│   ├── SKILL.md
│   ├── scripts/run_eval.py
│   └── eval_cases.yaml
├── evolve_improve/
│   ├── SKILL.md
│   ├── scripts/save_report.py
│   └── references/
└── evolve_auto/
    ├── SKILL.md
    ├── scripts/run_auto.py
    ├── conversation_tests/
    └── references/
```

## flow.yaml — Action Registry

Defines which actions exist and who can use them. Two types:

**State machine flows** — actions that transition between states:

```yaml
flows:
  F1:
    name: task_lifecycle
    resource: task              # what object has this state (task, order, user, etc.)
    states: [draft, submitted, approved, closed]
    transitions:
      - { from: _none_, action: create_task, to: draft, role: [admin] }
      - { from: draft,  action: submit,      to: submitted, role: [submitter] }
```

Each flow has a `resource` field identifying what object carries the state.

**Direct actions** — no state machine, execute immediately:

```yaml
direct_actions:
  - { action: check_health, role: [default, dev, evolver], description: "Check app health" }
  - { action: setup_claude, role: [dev], description: "Configure Claude Code" }
  - { action: inspect, role: [dev, evolver], description: "Show project structure" }
```

## Role-Based Skill Allocation

`deploy.sh` reads `flow.yaml` and **symlinks** only the actions allowed for each role into `.runtime/agents/{name}/.claude/skills/`. Symlinks within the workspace mean changes to `agent/flow/` are instantly visible without re-deploy. Template→workspace isolation is handled by `create-my-socialware` (which copies).

When flows define state machines, deploy also injects a workflow summary (states, transitions) into SOUL.md/AGENTS.md so the agent knows the valid state machine paths.

- `default` role → gets `check_health` skill only
- `dev` role → gets `check_health` + `setup_claude` + `inspect` skills
- `evolver` role → gets `check_health` + `inspect` + all `evolve_*` skills (check, diagnose, eval, improve, auto)

## SKILL.md Format

```yaml
---
name: action_name
description: "What this action does"
---
```

Followed by Markdown: trigger conditions, execution steps, API calls.

## Notes

- State machines are enforced by the App (`src/`), not by the agent infrastructure
- Permissions are checked by the App API
- flow.yaml is the single source of truth for "what actions exist and who can use them"
- SKILL.md is "how to execute the action" — should not contain hardcoded URLs (agent discovers endpoints from project config)
- Skills are **symlinks** in `.runtime/` pointing to `agent/flow/` — changes are instantly visible
- Template→workspace isolation is handled by `create-my-socialware` (copy), not by deploy
- `check_structure.py` validates flow graph completeness: all states reachable, terminal states exist, no isolated states
