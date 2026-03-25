# Code Review Skill Design

**Date:** 2026-03-24
**Type:** New skill for agentforge agent
**Approach:** Single unified skill (方案 A)

## Overview

Add a `code_review` skill to the agentforge agent that reviews code for quality and generates a Markdown report. Supports three review modes: PR/commit diff, full codebase scan, and specific file review.

## Skill Definition

- **Name:** `code_review`
- **File:** `agent/flow/code_review/SKILL.md`
- **Role binding:** `[agentforge]`
- **Tools used:** Read, Write, Bash (git), Glob

## Three Review Modes

1. **PR/Commit review** — `git diff` or `git show` to get changes, review per-file
2. **Codebase scan** — Glob + Read to traverse a target directory, review per-file
3. **Specific files** — Read user-specified file list directly

## Review Criteria (Code Quality)

| Dimension | What to check |
|-----------|--------------|
| Naming | Variables/functions/classes — clear, consistent naming |
| Readability | Logic clarity, unnecessary complexity |
| Code style | Formatting, indentation, comment style consistency |
| Duplication | Extractable repeated logic |
| Function design | Length, single responsibility, parameter count |

## Report Format

```markdown
# Code Review Report

- Date: YYYY-MM-DD
- Mode: PR Review / Codebase Scan / File Review
- Scope: [review scope description]

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Major | N |
| 🟡 Minor | N |
| 🔵 Suggestion | N |

## Findings

### [file path]

#### [issue title] — [Major/Minor/Suggestion]
- **Line:** L42-L50
- **Issue:** description
- **Suggestion:** recommended fix

## Overall Assessment

[overall evaluation and improvement directions]
```

**Report save path:** Ask user each time, default suggestion `docs/reviews/review-YYYY-MM-DD.md`.

## Flow Steps

1. Ask user for review mode (PR / codebase / specific files)
2. Collect input based on mode:
   - PR → commit hash or branch comparison (default: current branch vs main)
   - Codebase → target directory (default: `src/`)
   - Specific files → file path list
3. Ask for report save path (default: `docs/reviews/review-YYYY-MM-DD.md`)
4. Read code (git diff / Glob+Read / Read)
5. Review each file against the five quality dimensions
6. Generate Markdown report, write to specified path
7. Output summary in conversation (total issues + severity distribution)

## Integration

### flow.yaml addition

```yaml
  - action: code_review
    role: [agentforge]
    description: "Review code quality — supports PR/commit, codebase scan, and specific files"
```

### No API endpoint needed

Pure file operation skill — no `src/app.py` changes required.

### No eval.yaml changes

Code review is a tool capability, not a self-evaluation commitment.

## Files to Create/Modify

| File | Action |
|------|--------|
| `agent/flow/code_review/SKILL.md` | Create |
| `agent/flow/flow.yaml` | Add `code_review` action |
| `deploy.sh` | Run to compile changes |
