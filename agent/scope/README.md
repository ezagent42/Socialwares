# Scope — Where

Defines App-level capability declarations.

## Files

- `SOUL.md` — Agent capability declaration
  - Internal: Defines Agent operation boundaries
  - External: Public description, readable by other Agents

## deploy.sh Processing

`scope/SOUL.md` is merged with each `role/{name}/SOUL.md`
to generate the complete SOUL.md specific to that role.
