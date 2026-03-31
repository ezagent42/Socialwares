---
name: dev_release
description: "Guide release workflow — verify, commit, tag, push"
---

# Release / Publish (Release Workflow Guide)

## Trigger

User says "release", "publish", "发布", "定版", "push", "commit" etc.

## Flow

### Step 1: Pre-release Checks

Run all verification steps before any git operations.

#### 1a. Recompile and deploy

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
socialwares deploy
```

Confirm output shows no errors. If errors exist, fix them before proceeding.

#### 1b. Check latest structure report

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
ls -t .runtime/data/evolve/reports/check_*.json | head -1 | xargs cat
```

Verify the structure check result is **PASS**. If not, guide the user to fix structure issues first (suggest `dev_iterate`).

#### 1c. Run API tests (if backend is running)

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
curl -sf http://localhost:8000/health && echo "Backend running — running API tests..." || echo "Backend not running — skipping API tests"
```

If the backend is available, run the API test flow to confirm endpoints work. If not running, note it and proceed.

### Step 2: Review Changes

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
git status
git diff
```

Present a summary of all changed files:
- **Modified**: list files that changed
- **Untracked**: list new files
- **Deleted**: list removed files

Flag any files that should NOT be committed (see references/release-checklist.md).

### Step 3: Guide Git Workflow

Walk the user through each step interactively.

#### 3a. Stage relevant files

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
git add <files>
```

- Stage `agent/`, `socialware.py`, and other app source files
- Do NOT stage: `.runtime/`, `.socialware/workspace/`, `__pycache__/`, `.pyc` files
- Show `git diff --staged` for the user to review before committing

#### 3b. Write commit message

Help the user write a meaningful commit message:
- Use conventional format: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- Summarize what changed and why
- Example: `feat: add review flow with approval commitment`

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
git commit -m "<message>"
```

#### 3c. Create version tag (if appropriate)

Ask the user: "要打版本标签吗？（如 v0.1.0）"

If yes:

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
git tag -a v<X.Y.Z> -m "Release v<X.Y.Z>: <summary>"
```

Follow semver convention:
- `v0.1.0` — first working version
- `v0.X.0` — new features or breaking changes
- `v0.X.Y` — bug fixes and minor improvements

#### 3d. Push to remote

```bash
WORKSPACE_ROOT=$(cat .workspace_root) && cd "$WORKSPACE_ROOT"
git push origin <branch>
git push origin --tags   # if tags were created
```

### Step 4: Post-release

After a successful push, suggest next steps:

1. **Deploy to target environment**:
   ```bash
   socialwares install
   ```
2. **Verify deployment** by starting the app and testing key flows
3. **Notify collaborators** if this is a shared project

## Important

- Always run pre-release checks before any git operations — do not skip
- Never stage `.runtime/`, `.socialware/workspace/`, or `__pycache__/` directories
- Let the user review `git diff --staged` before committing — don't auto-commit without confirmation
- If pre-release checks fail, guide the user to fix issues first (suggest `dev_iterate`)
- Use the user's language (Chinese or English based on their input)
- Refer to `references/release-checklist.md` for the full checklist
