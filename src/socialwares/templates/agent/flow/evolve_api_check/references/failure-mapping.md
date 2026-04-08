# Eval — Failure Analysis Reference

## Failure → Primitive Mapping

For each failure, **map it to a primitive**:
- Endpoint returns wrong data? -> Flow (SKILL.md has wrong API instructions)
- Endpoint returns 403/401? -> Role (permissions misconfigured)
- Endpoint doesn't exist? -> Scope (capability not implemented) or Flow (action not registered)
- Response too slow / quality issue? -> Commitment (condition not met)

## Good analysis example

Script output:
```
[FAIL] POST /tasks — expected 201, got 500
[FAIL] GET /tasks/1 — expected {"title": "test"}, got 404
[PASS] GET /health — 200 ok
```

Your interpretation:
"Eval score: 1/3 (33%). Two failures, both in task CRUD:
1. **POST /tasks returns 500** — the backend crashes on task creation. This is a **Flow** issue: check `agent/flow/create_task/SKILL.md` for the correct request format, and verify the app's `/tasks` endpoint handler.
2. **GET /tasks/1 returns 404** — likely a consequence of failure #1 (no task was created). Fix #1 first, then re-run eval.

Suggest: run `evolve_session_diagnose` to check if the create_task skill is being invoked correctly, then `evolve_improve` to fix the SKILL.md."

## Bad analysis example

"1 out of 3 tests passed. Score is 33%."
(No root cause analysis, no primitive mapping, no next steps.)
