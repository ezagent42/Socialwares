# 0325 Evolver Skills Rewrite — Context + Workflow + References

## What Changed

All 5 evolver SKILL.md files rewritten to give evolver LLM proper context.

### Added to all 5 skills:
- **Quick Start** — copy-paste ready command at the top
- **Four Primitives Reference** — table of what each primitive is and where it lives
- **Script vs Evolver responsibility** — what script does (mechanical) vs what LLM does (reasoning)

### Per-skill additions:

| Skill | Key additions |
|-------|-------------|
| evolve_check | Good/bad examples of report interpretation |
| evolve_eval | Failure→primitive mapping (500→Flow, 403→Role, missing→Scope) |
| evolve_diagnose | **Major**: 4 reference examples (time violation, sequence violation, partial fulfillment, insufficient data), violations→primitives mapping table |
| evolve_auto | Failure analysis workflow, good/bad trigger examples, failure pattern→cause→fix reference table |
| evolve_improve | Improvement reference per operation: add skill, fix skill (bad/good), adjust commitment (unmeasurable/verifiable), expand scope, add role |

### diagnose.py refactored:
- Script now ONLY extracts data (events + timestamps)
- Does NOT judge fulfillment (that's natural language → LLM's job)
- Fixed: postcondition example used old schema → replaced with unified from/to/condition

### run_auto.py cleaned:
- Removed scripted "Suggestion: Check SKILL.md" text (LLM's job)
- Report JSON has failures list, no suggestions

### Design pattern (from autoservice reference):
- Quick Start first (copy-paste ready)
- Workflow by phase
- Concrete examples (real input/output, not pseudocode)
- Explain why, not just what

51 tests passing.
