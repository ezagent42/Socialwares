# 0324 Evolve V3 Final — Doc Consistency + E2E Rewrite

## Documentation Consistency Fixes

### Violation authorship corrected (6 files)
- README.md: "Written by app backend" → "Written by evolver's diagnose.py"
- agent/commitment/commitment.yaml: header comments updated, removed app developer responsibilities
- docs/designs/evolve-v2-plan.md: added superseded notice
- docs/designs/e2e-test.md: fixed hook names, symlinks vs copies
- docs/guides/001-architecture-and-concepts.md: removed "API checks constraints" from runtime flow
- docs/guides/003-four-primitives.md: "copies actions" → "symlinks the actions"

### Stale references fixed (5 files)
- README.md + 3 guides + flow/README: run_loop.py → run_auto.py
- E2E test plan: all old hook names updated

## E2E Test Plan Complete Rewrite

`docs/designs/e2e-test.md` rewritten as Task Review App development journey.

8 phases + cleanup covering 34 features:

| Phase | Features tested |
|-------|----------------|
| 1. Template & Workspace | Root guards, create, deploy output, skill filtering, idempotency, change detection |
| 2. Build the App | Backend API, flow skills, roles, TUI mode, hook data capture |
| 3. Commitment | commitment.yaml, eval_cases.yaml (api + conversation checks) |
| 4. Evolver | check_structure, eval, diagnose (fulfillment rates + cursor), auto (SDK), improve (TUI), violations API |
| 5. Adapter Awareness | claude/codex/kimi deploy output differences |
| 6. SDK Mode | start_agent.py, session saving |
| 7. Cross-Feature | multi-role tmux, all adapters, dev role, template tests |
| 8. Scope Update | scope.md reflects actual capabilities |

Every feature has: action, purpose, expected result with concrete commands.
A feature not in this plan is considered non-existent.
