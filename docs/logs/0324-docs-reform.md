# 0324 Documentation Reform

## What Changed

All documentation rewritten to match current codebase state.

### Test Data Cleaned
- Removed `.socialware/workspace/demo/` (E2E test todo app)
- Removed `.socialware/workspace/test/`
- Removed `agent/flow/evolve_eval/last_eval_results.json`
- Removed root `.runtime/`

### docs/guides/ (5 files rewritten)

| File | Key Changes |
|------|-------------|
| 001-architecture-and-concepts.md | Directory structure shows flat roles, scope.md, constraints.yaml, Makefile.template. Added Makefile split (root vs workspace). Commitment unified schema. |
| 002-quickstart.md | All commands use `make`. No quick-try from root. FAQ accurate. |
| 003-four-primitives.md | Role: flat .md files. Scope: scope.md. Commitment: completely replaced with unified from/to/condition/on_violation schema. Flow: skills are copies not symlinks. |
| 004-commitment-and-evolve.md | Removed all API middleware/cron content. Commitment = agent-readable spec with unified schema. Two-phase checking. Fulfillment rate. Four-primitive improvement mapping. |
| 005-claude-setup.md | Minor accuracy updates. |

### README.md (rewritten)

- Quick Start: `make create` → `cd workspace` → `make start`
- Directory structure: flat roles, scope.md, constraints.yaml, Makefile
- Commitment: unified schema (from/to/condition/on_violation)
- Deploy output: skills are copies, .workspace_root, settings.local.json
- Evolver: fulfillment rate based

### agent/ READMEs (4 files)

| File | Key Changes |
|------|-------------|
| agent/role/README.md | Flat .md files, deploy copies skills + writes .workspace_root |
| agent/scope/README.md | scope.md (not SOUL.md), added participation |
| agent/commitment/README.md | Complete rewrite: unified schema, two-phase checking, lifecycle. Removed API middleware/cron content. |
| agent/flow/README.md | All actual skill directories listed. "Copies" not "symlinks". |

### New Files
- `tests/test_hooks.py` — hook runtime tests (log_action.sh + check_violations.sh)
- `docs/discuss/commitment.md` — commitment design discussion
- `docs/logs/0324-docs-reform.md` — this file

### Test Updates
- `agent/flow/evolve_eval/eval_cases.yaml` — api_checks + conversation_checks format
- `agent/flow/evolve_eval/scripts/run_eval.py` — supports new format
- `docs/designs/e2e-test.md` — Section 10 rewritten for workspace-only flow
- 46 tests passing
