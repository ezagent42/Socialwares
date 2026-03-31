---
name: dev_iterate
description: "Guide iterative development — read evolve reports and apply improvements"
---

# Iterate (Continuous Improvement Guide)

## Trigger

User says "继续改进", "看报告", "iterate", "improve based on report", "what should I fix" etc.

## Flow

### Step 1: Read Latest Reports

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
ls -t .runtime/data/evolve/reports/ | head -5
```

Read the most recent report files (check_*.json, eval_*.json, diagnose_*.json).

### Step 2: Summarize Findings

For each report, summarize:
- **Score**: pass rate or score
- **Issues**: list of problems found
- **Suggestions**: recommended changes (primitive, file, action, reason)

Present in a clear table:

```
| Report     | Score | Issues | Top Suggestion          |
|------------|-------|--------|-------------------------|
| structure  | 4/4   | 0      | —                       |
| eval       | 1/3   | 2      | Add eval for create_task|
| diagnose   | —     | 1 C1   | C1 violated: 2 of 3     |
```

### Step 3: Guide Improvements

For each suggestion, guide the user through the fix:

**Flow issues** (missing SKILL.md, missing eval case):
1. Show what needs to be created
2. Provide a template
3. Help user write the content
4. Register in socialware.py if needed

**Commitment violations**:
1. Explain what went wrong (which commitment, how many violations)
2. Suggest SKILL.md improvements (better trigger, clearer flow)
3. Or suggest commitment condition adjustment

**Scope gaps**:
1. Show which capabilities are declared but not implemented
2. Or which actions exist but aren't in scope

### Step 4: Re-deploy + Re-verify

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
socialwares deploy
```

After deploy, suggest running the relevant evolve check again to verify the fix.

## Important

- Always read the actual report files, don't guess
- If no reports exist, suggest: "先运行 evolver 生成报告: socialwares start --role evolver, 然后 'check structure' / 'evaluate' / 'diagnose'"
- Prioritize: structure issues > eval failures > commitment violations > scope gaps
- After each fix, re-deploy and verify before moving to the next issue
