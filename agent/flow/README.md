# Flow — How

Defines operations the Agent can execute (Skills) and their state machines.

## Structure

```
flow/
├── flow.yaml             ← Action registry: state machines + direct actions
├── check_health/
│   └── SKILL.md          ← Skill definition (how to execute this action)
├── setup_claude/
│   └── SKILL.md
└── create_task/
    ├── SKILL.md
    └── scripts/          ← Optional: helper scripts
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
  - { action: check_health, role: [default, dev], description: "Check app health" }
  - { action: setup_claude, role: [dev], description: "Configure Claude Code" }
```

## Role-Based Skill Allocation

`deploy.sh` reads `flow.yaml` and only symlinks actions allowed for each role:

- `default` role → gets `check_health` skill only
- `dev` role → gets `check_health` + `setup_claude` skills

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
