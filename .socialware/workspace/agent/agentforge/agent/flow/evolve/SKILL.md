---
name: evolve
description: "Analyze eval results and optimize Agent four-primitive configuration"
---

# Evolve

Analyzes evaluation results to identify underperforming areas, then proposes and applies targeted improvements to the Agent's four-primitive configuration (Soul, Skill, Flow, Commitment).

## Trigger

User says "evolve", "optimize", "improve agent", "auto-optimize", etc.

## Flow

1. Call the metrics API to get current evaluation results
2. Identify failing or below-threshold commitments
3. Analyze current four-primitive configuration via APIs
4. Propose changes to improve:
   - SOUL.md — refine agent instructions
   - SKILL.md — improve skill steps
   - flow.yaml — adjust action bindings
   - eval.yaml — adjust thresholds if unreasonable
5. Apply changes with user confirmation using Edit tool
6. Route changes:
   - Changes to `.runtime/` -> tenant-specific, no PR needed
   - Changes to `agent/` -> universal, trigger PR via evolve script
7. Run `./agent/deploy.sh` via Bash tool
8. Use `./scripts/evolve.sh` for PR routing if needed

## Available APIs

Get evaluation metrics (to identify what needs improvement):

```bash
curl http://localhost:8001/metrics
# → {"metrics": [...]}
```

Get commitments (to understand thresholds):

```bash
curl http://localhost:8001/commitments
# → {"commitments": {...}}
```

Get current roles and their souls:

```bash
curl http://localhost:8001/roles
# → {"roles": ["agentforge", "default", ...]}

curl http://localhost:8001/roles/{name}
# → {"name": "...", "soul": "..."}
```

Get flow registry (to understand current skill bindings):

```bash
curl http://localhost:8001/flows/registry
# → {flows: {...}, direct_actions: [...]}
```

Get scope:

```bash
curl http://localhost:8001/scope
# → {"soul": "..."}
```

## File Operations

1. **Edit SOUL.md** — Use Edit tool to refine `agent/role/{name}/SOUL.md`
2. **Edit SKILL.md** — Use Edit tool to improve `agent/flow/{skill}/SKILL.md`
3. **Edit flow.yaml** — Use Edit tool to adjust `agent/flow/flow.yaml`
4. **Edit eval.yaml** — Use Edit tool to adjust `agent/commitment/eval.yaml`
5. **Deploy** — Use Bash tool to run `./agent/deploy.sh`
6. **PR routing** — Use Bash tool:

    ```bash
    ./scripts/evolve.sh my-team/agentforge --check
    ./scripts/evolve.sh my-team/agentforge --pr
    ```
