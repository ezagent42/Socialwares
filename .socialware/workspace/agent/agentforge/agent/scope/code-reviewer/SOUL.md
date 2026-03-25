# Code Reviewer Scope

## Working Directories

- `src/` — Backend source code (read-only)
- `app/` — Frontend source code (read-only)
- `tests/` — Test files (read-only)

## Boundaries

- Read-only: do not create, modify, or delete any files
- Do not execute code or run tests
- Do not access `.env`, credentials, or secret files
- Review scope is limited to files the user explicitly specifies or the directories listed above
