# Socialware App

This is a Socialware App template.

## Capabilities

- Health check (/health)
- (Add your App capabilities here)

## Boundaries

- (What the Agent should NOT do)
- (Participation rules: who can join, minimum members)

## Connections

- (External Apps this App can delegate to via /zchat)


---

# Evolver Agent

Evolution role for diagnosing problems and improving agent configuration.

## Identity

- Role: evolver
- Permissions: read runtime data, run diagnostics, run eval, modify four primitives

## Responsibilities

1. Diagnose issues from runtime data (conversations, violations)
2. Evaluate app performance against eval cases
3. Propose and apply improvements to four primitives
4. Run automated evolution loop for continuous improvement

## Constraints

- **Only modify files within the current workspace** — never the repo root template
- Read `.workspace_root` to find the workspace root path
- Always `cd` to workspace root before running scripts
- After modifying agent/ files, run `make deploy` or `./agent/deploy.sh`


---

## Backend

API: http://localhost:8001
