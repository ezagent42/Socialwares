# Release Checklist

## Pre-release Checks

Before committing or pushing, verify all of the following:

- [ ] **Deploy passes**: `socialwares deploy` completes with no errors
- [ ] **Structure check passes**: latest report in `.runtime/data/evolve/reports/check_*.json` shows PASS
- [ ] **API tests pass**: if backend is running, all API endpoints return expected results
- [ ] **No uncommitted changes in agent/**: all agent source files are either staged or intentionally excluded
- [ ] **No leftover debug code**: remove temporary prints, breakpoints, test-only hacks

## Git Workflow

Follow this sequence strictly:

1. **Stage** — add relevant files only
   ```bash
   git add agent/ socialware.py
   git add <other changed source files>
   ```
2. **Review** — inspect what will be committed
   ```bash
   git diff --staged
   ```
3. **Commit** — write a meaningful message
   ```bash
   git commit -m "feat: <description>"
   ```
4. **Tag** — create version tag if this is a release milestone
   ```bash
   git tag -a v0.X.Y -m "Release v0.X.Y: <summary>"
   ```
5. **Push** — send to remote
   ```bash
   git push origin <branch>
   git push origin --tags
   ```

## What NOT to Commit

These paths must never be committed. Ensure they are in `.gitignore`:

| Path                      | Reason                                      |
|---------------------------|---------------------------------------------|
| `.runtime/`               | Generated runtime data, reports, logs       |
| `.socialware/workspace/`  | Local workspace state and test artifacts    |
| `__pycache__/`            | Python bytecode cache                       |
| `*.pyc`                   | Compiled Python files                       |
| `.env`                    | Environment secrets                         |

## Version Tagging Convention

Follow [Semantic Versioning](https://semver.org/):

- **`v0.1.0`** — first working version (initial release)
- **`v0.2.0`** — new features added or breaking changes
- **`v0.2.1`** — bug fixes and minor improvements on v0.2.0
- **`v1.0.0`** — production-ready stable release

Tag format: `v<MAJOR>.<MINOR>.<PATCH>`

Examples:
```
git tag -a v0.1.0 -m "Release v0.1.0: initial four-primitive app"
git tag -a v0.2.0 -m "Release v0.2.0: add review flow + commitments"
git tag -a v0.2.1 -m "Release v0.2.1: fix commitment condition typo"
```

## Post-release

After pushing:

1. Run `socialwares install` to deploy to the target environment
2. Start the app and verify key flows work end-to-end
3. Notify collaborators of the new version if applicable
