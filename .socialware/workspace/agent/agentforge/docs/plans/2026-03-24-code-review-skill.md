# Code Review Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `code_review` skill to the agentforge agent that reviews code quality and generates Markdown reports.

**Architecture:** Single unified skill with three review modes (PR/commit, codebase scan, specific files). Pure file operations — no API endpoint needed. Report output to user-specified path.

**Tech Stack:** SKILL.md (YAML frontmatter + Markdown), flow.yaml (YAML), Bash (deploy.sh)

---

### Task 1: Create SKILL.md

**Files:**
- Create: `agent/flow/code_review/SKILL.md`

**Step 1: Create the SKILL.md file**

Write to `agent/flow/code_review/SKILL.md`:

```markdown
---
name: code_review
description: "Review code quality — supports PR/commit diff, codebase scan, and specific file review. Outputs a Markdown report."
---

# Code Review

Reviews code for quality and generates a structured Markdown report. Supports three modes: PR/commit diff review, full codebase scan, and specific file review.

## Trigger

User says "review code", "code review", "review this PR", "review this commit", "scan code quality", "review these files", etc.

## Flow

### Q1 — Review mode

Ask the user:

> What would you like to review?
> a) **PR/Commit** — review changes in a PR or commit
> b) **Codebase** — scan an entire directory
> c) **Specific files** — review a list of files

### Q2 — Scope (depends on mode)

- **PR/Commit:** Ask for commit hash or branch comparison. Default: current branch vs main (`git diff main...HEAD`).
- **Codebase:** Ask for target directory. Default: `src/`.
- **Specific files:** Ask for the file path list.

### Q3 — Report save path

Ask the user where to save the report. Default suggestion: `docs/reviews/review-YYYY-MM-DD.md`.

### Execution

1. **Gather code to review:**
   - PR/Commit mode: Use Bash tool to run `git diff` or `git show` to get the diff
   - Codebase mode: Use Glob tool to list files in target directory, then Read each file
   - Specific files mode: Use Read tool on each file in the list

2. **Review each file against five quality dimensions:**
   - **Naming** — Are variable/function/class names clear and consistent?
   - **Readability** — Is the logic easy to follow? Any unnecessary complexity?
   - **Code style** — Is formatting, indentation, and comment style consistent?
   - **Duplication** — Is there repeated logic that could be extracted?
   - **Function design** — Are functions short, single-responsibility, with reasonable parameter counts?

3. **Classify each finding by severity:**
   - 🔴 **Major** — Significant quality issue that should be fixed
   - 🟡 **Minor** — Small issue worth improving
   - 🔵 **Suggestion** — Optional improvement idea

4. **Generate the Markdown report** using Write tool at the specified path:

   ```
   # Code Review Report

   - Date: YYYY-MM-DD
   - Mode: PR Review / Codebase Scan / File Review
   - Scope: [description of what was reviewed]

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
   - **Issue:** description of the problem
   - **Suggestion:** recommended improvement

   ...

   ## Overall Assessment

   [Overall evaluation of code quality and key improvement directions]
   ```

5. **Output a summary** in the conversation:
   - Total number of findings by severity
   - Top 3 most important issues
   - Path to the saved report

## File Operations

- **Bash** — `git diff`, `git show` for PR/commit mode
- **Glob** — List files for codebase scan mode
- **Read** — Read file contents for review
- **Write** — Generate the Markdown report at user-specified path

## Validation

- At least one file must be found/provided to review
- Report path must be writable
- If no issues are found, still generate a report with a clean assessment
```

**Step 2: Verify the file was created**

Run: `ls agent/flow/code_review/SKILL.md`
Expected: file exists

---

### Task 2: Register in flow.yaml

**Files:**
- Modify: `agent/flow/flow.yaml:41` (insert before zchat_connect)

**Step 1: Add code_review action to flow.yaml**

Add the following block before the `zchat_connect` entry (after `evolve`):

```yaml

  - action: code_review
    role: [agentforge]
    description: "Review code quality — supports PR/commit, codebase scan, and specific files"
```

The result should show `code_review` in `direct_actions` between `evolve` and `zchat_connect`.

**Step 2: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('agent/flow/flow.yaml'))"`
Expected: no error

---

### Task 3: Deploy and verify

**Step 1: Run deploy.sh**

Run: `./agent/deploy.sh`
Expected: successful compilation, no errors

**Step 2: Verify skill was deployed**

Run: `ls .runtime/agents/agentforge/.claude/skills/code_review/`
Expected: SKILL.md exists (symlinked)

**Step 3: Commit**

```bash
git add agent/flow/code_review/SKILL.md agent/flow/flow.yaml docs/plans/2026-03-24-code-review-skill-design.md docs/plans/2026-03-24-code-review-skill.md
git commit -m "feat: add code_review skill for agentforge agent"
```
