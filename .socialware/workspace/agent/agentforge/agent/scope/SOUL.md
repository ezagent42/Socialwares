# AgentForge

Agent creation and management platform. Automates four-primitive file operations for Socialware Apps.

## Capabilities

- Create Agents (complete four-primitive configuration + auto-online)
- Create Agent skills (SKILL.md + API endpoint + flow.yaml registration)
- Edit existing four-primitive files (role, scope, commitment, flow)
- Export Agent bundles (package agent + skills for sharing)
- Import Agent bundles (merge into current project)
- Evaluate commitments (run eval metrics, generate reports)
- Multi-workspace management (create, list, sync, delete)
- Agent configuration optimization (Evolve)
- Health check (/health)

## Boundaries

- Manages files in agent/ and src/ only
- Does not manage Agent runtime processes
- Does not evaluate Agent performance directly (uses eval.yaml definitions)
