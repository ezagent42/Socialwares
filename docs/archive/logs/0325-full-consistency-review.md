# 0325 Full Consistency Review

## Scope

Complete review of ALL active documents vs actual code. 19 files checked.

## Critical Fix

**agent/commitment/commitment.yaml** — was using OLD schema (`transition_constraints / action_constraints / type / deadline`). All docs described the NEW unified schema (`commitments: from/to/condition/on_violation`). Completely rewritten.

## commitment_watch.yaml phantom

Multiple docs referenced `commitment_watch.yaml` (deploy generates per-role watch list for hooks). **deploy.sh never generates this file.** Hooks capture ALL prompts/tools uniformly; diagnose.py matches events to commitments afterwards. Removed all false claims from:
- docs/guides/003-four-primitives.md
- docs/guides/004-commitment-and-evolve.md
- agent/commitment/README.md
- docs/discuss/commitment.md

## Terminology fixes

"Constraints on flow edges" → "Evaluation standards on flow edges" throughout.
"constraint violations" → "commitment violations"
"tagged with commitment IDs" → "diagnose.py matches events to commitment actions"

## Missing evolve_check

README, guides/001, flow/README, inspect/SKILL.md all missing `evolve_check` in directory listings and skill counts.

## Files fixed (11)

| File | Key fixes |
|------|-----------|
| agent/commitment/commitment.yaml | **Rewritten**: old → unified schema |
| README.md | Added evolve_check, evaluation standards, symlinks not copies, removed workspace agent/Makefile.template |
| agent/Makefile.template | CONSTRAINTS → COMMITMENT variable |
| docs/guides/001 | evolve_check, evaluation standards, removed workspace Makefile.template |
| docs/guides/003 | Removed commitment_watch.yaml claims |
| docs/guides/004 | Removed commitment_watch.yaml, fixed lifecycle, hooks capture uniformly |
| agent/commitment/README.md | Removed commitment_watch.yaml, fixed lifecycle |
| docs/discuss/commitment.md | Removed commitment_watch.yaml section, fixed data capture |
| agent/flow/README.md | Added evolve_check |
| agent/flow/inspect/SKILL.md | Evaluation standards, removed Makefile.template |
| agent/flow/evolve_improve/SKILL.md | "Constraint violations" → "Low fulfillment rate" |

## Files verified correct (8)

agent/role/README.md, agent/scope/README.md, docs/guides/002, pyproject.toml, src/app.py, deploy.sh, start.sh, flow.yaml, create-my-socialware.py, all evolver SKILL.md files.

## Cleaned

- .socialware/workspace/demo (test data)
- .runtime/ at root
- agent/flow/evolve_eval/last_eval_results.json
- __pycache__ dirs

51 tests passing.
