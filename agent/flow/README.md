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
├── evolve_diagnose/
│   ├── SKILL.md
│   └── scripts/diagnose.py
├── evolve_eval/
│   ├── SKILL.md
│   ├── scripts/run_eval.py
│   └── eval_cases.yaml
├── evolve_improve/
│   └── SKILL.md
└── evolve_auto/
    ├── SKILL.md
    └── scripts/run_loop.py
```

## flow.yaml — Action Registry

Defines which actions exist and who can use them. Two types:

**State machine flows** — actions that transition between states:

```yaml
flows:
  F1:
    name: task_lifecycle
    states: [draft, submitted, approved, closed]
    transitions:
      - { from: _none_, action: create_task, to: draft, role: [admin] }
      - { from: draft,  action: submit,      to: submitted, role: [submitter] }
```

**Direct actions** — no state machine, execute immediately:

```yaml
direct_actions:
  - { action: check_health, role: [default, dev, evolver], description: "Check app health" }
  - { action: setup_claude, role: [dev], description: "Configure Claude Code" }
  - { action: inspect, role: [dev, evolver], description: "Show project structure" }
```

## Role-Based Skill Allocation

`deploy.sh` reads `flow.yaml` and **symlinks** only the actions allowed for each role into `.runtime/agents/{name}/.claude/skills/`. Symlinks within the workspace mean changes to `agent/flow/` are instantly visible without re-deploy. Template→workspace isolation is handled by `create-my-socialware` (which copies).

- `default` role → gets `check_health` skill only
- `dev` role → gets `check_health` + `setup_claude` + `inspect` skills
- `evolver` role → gets `check_health` + `inspect` + all `evolve_*` skills

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
- SKILL.md is "how to execute the action"
- Skills are **symlinks** in `.runtime/` pointing to `agent/flow/` — changes are instantly visible
- Template→workspace isolation is handled by `create-my-socialware` (copy), not by deploy
