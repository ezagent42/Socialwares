# End-to-End Test Plan

Manual test plan covering every feature. Run from a clean state.

## Prerequisites

```bash
git clone https://github.com/ezagent42/Socialwares.git
cd Socialwares
uv sync
```

---

## 1. Template Quick-Try

### 1.1 Make deploy from template

| | |
|---|---|
| **Action** | `make deploy` |
| **Purpose** | Verify deploy.sh compiles four primitives to .runtime/ |
| **Verify** | `.runtime/agents/default/` exists, `.runtime/agents/dev/` exists, `.runtime/agents/evolver/` exists |

```bash
make deploy
ls .runtime/agents/
# Expected: default  dev  evolver
```

### 1.2 Check .runtime/ structure

| | |
|---|---|
| **Action** | Inspect .runtime/ contents |
| **Purpose** | Verify deploy generates correct structure per role |
| **Verify** | Each role has: .claude/skills/, .claude/hooks/, SOUL.md, constraints.yaml, flow.yaml |

```bash
ls .runtime/agents/default/
# Expected: .claude  SOUL.md  constraints.yaml  flow.yaml

ls .runtime/agents/default/.claude/skills/
# Expected: check_health (symlink)
# NOT: setup_claude, evolve_* (those are for dev/evolver only)

ls .runtime/agents/evolver/.claude/skills/
# Expected: check_health, evolve_auto, evolve_diagnose, evolve_eval, evolve_improve, inspect

ls .runtime/agents/default/.claude/hooks/
# Expected: check_violations.sh  log_action.sh
```

### 1.3 Check SOUL.md merge

| | |
|---|---|
| **Action** | Read merged SOUL.md |
| **Purpose** | Verify scope.md + role.md merged correctly |
| **Verify** | Contains content from both scope/scope.md and role/default.md |

```bash
cat .runtime/agents/default/SOUL.md
# Should contain scope content ("Socialware App") AND role content ("Default Agent")
```

### 1.4 Skill filtering by role

| | |
|---|---|
| **Action** | Compare skills across roles |
| **Purpose** | Verify flow.yaml role filtering works |
| **Verify** | default has fewer skills than evolver |

```bash
ls .runtime/agents/default/.claude/skills/ | wc -l   # Expected: 1 (check_health)
ls .runtime/agents/dev/.claude/skills/ | wc -l        # Expected: 3 (check_health, setup_claude, inspect)
ls .runtime/agents/evolver/.claude/skills/ | wc -l     # Expected: 6 (all evolve_* + check_health + inspect)
```

### 1.5 Make start (template)

| | |
|---|---|
| **Action** | `make start` |
| **Purpose** | Verify agent launches in default role |
| **Verify** | Claude Code TUI opens, SOUL.md loaded, skills available |

```bash
make start
# In Claude Code:
#   - Type "/" → should see "check_health" in skill list
#   - Say "check health" → should attempt to call GET /health
#   - Exit: Ctrl+C
```

### 1.6 Make idempotency

| | |
|---|---|
| **Action** | Run `make deploy` twice |
| **Purpose** | Verify Make skips rebuild when nothing changed |
| **Verify** | Second run says "nothing to be done" |

```bash
make deploy    # first run: rebuilds
make deploy    # second run: should say "make: '.runtime/.deploy_stamp' is up to date."
```

### 1.7 Make change detection

| | |
|---|---|
| **Action** | Edit a file, run `make deploy` |
| **Purpose** | Verify Make detects source changes |
| **Verify** | Redeploys after edit |

```bash
echo "# test" >> agent/scope/scope.md
make deploy    # should rebuild
git checkout agent/scope/scope.md   # restore
```

---

## 2. Create Workspace

### 2.1 Create workspace

| | |
|---|---|
| **Action** | `uv run scripts/create-my-socialware.py --room test --app hello --description "Test App"` |
| **Purpose** | Verify workspace creation with room/app structure |
| **Verify** | Directory created, files copied, SOUL files customized, auto-deployed |

```bash
uv run scripts/create-my-socialware.py --room test --app hello --description "Test App"

# Check structure
ls .socialware/workspace/test/hello/
# Expected: agent  app  pyproject.toml  src  .runtime

# Check customization
cat .socialware/workspace/test/hello/agent/scope/scope.md
# Should contain "hello" and "Test App"

cat .socialware/workspace/test/hello/agent/role/default.md
# Should contain "hello"

# Check auto-deploy
ls .socialware/workspace/test/hello/.runtime/agents/
# Expected: default  dev  evolver
```

### 2.2 Duplicate workspace fails

| | |
|---|---|
| **Action** | Run create again with same room/app |
| **Purpose** | Verify won't overwrite existing workspace |
| **Verify** | Exits with error |

```bash
uv run scripts/create-my-socialware.py --room test --app hello --description "Test"
# Expected: error message, non-zero exit code
```

### 2.3 Workspace self-contained

| | |
|---|---|
| **Action** | Deploy and start from within workspace |
| **Purpose** | Verify workspace works independently from repo root |
| **Verify** | deploy.sh and start.sh work using workspace's local agent/ |

```bash
cd .socialware/workspace/test/hello
./agent/deploy.sh        # should work (reads local agent/)
./agent/start.sh --role default
# Claude Code opens, check_health skill available
# Exit: Ctrl+C
cd ../../../..            # back to repo root
```

### 2.4 Independent pyproject.toml

| | |
|---|---|
| **Action** | Check workspace has its own pyproject.toml |
| **Purpose** | Verify dependency independence |
| **Verify** | pyproject.toml exists with app name |

```bash
cat .socialware/workspace/test/hello/pyproject.toml
# Should contain: name = "hello"
```

---

## 3. Four Primitives

### 3.1 Add a new skill

| | |
|---|---|
| **Action** | Create a new flow action in workspace |
| **Purpose** | Verify custom skills work |
| **Verify** | New skill appears in deployed .runtime/ |

```bash
cd .socialware/workspace/test/hello

mkdir -p agent/flow/greet
cat > agent/flow/greet/SKILL.md << 'EOF'
---
name: greet
description: "Say hello"
---
# Greet
## Trigger
User says "hello" or "greet"
## Flow
Respond with a greeting.
EOF

# Register in flow.yaml
echo '  - { action: greet, role: [default], description: "Say hello" }' >> agent/flow/flow.yaml

./agent/deploy.sh
ls .runtime/agents/default/.claude/skills/
# Expected: check_health  greet

cd ../../../..
```

### 3.2 Add a new role

| | |
|---|---|
| **Action** | Create a new role in workspace |
| **Purpose** | Verify new roles are deployed |
| **Verify** | New role directory in .runtime/agents/ |

```bash
cd .socialware/workspace/test/hello

cat > agent/role/admin.md << 'EOF'
# Admin Agent
Admin role.
## Identity
- Role: admin
- Permissions: all
## Responsibilities
1. Manage the app
EOF

./agent/deploy.sh
ls .runtime/agents/
# Expected: admin  default  dev  evolver

cd ../../../..
```

### 3.3 Remove a role

| | |
|---|---|
| **Action** | Delete a role file, redeploy |
| **Purpose** | Verify deploy cleans up removed roles |
| **Verify** | Removed role's .runtime/ directory is gone |

```bash
cd .socialware/workspace/test/hello

rm agent/role/admin.md
./agent/deploy.sh
ls .runtime/agents/
# Expected: default  dev  evolver  (no admin)

cd ../../../..
```

---

## 4. Constraints + Violations

### 4.1 Constraints copied to .runtime/

| | |
|---|---|
| **Action** | Check constraints.yaml in deployed roles |
| **Purpose** | Verify deploy copies constraints |
| **Verify** | constraints.yaml exists in each role's .runtime/ |

```bash
cat .runtime/agents/default/constraints.yaml
# Should match agent/commitment/constraints.yaml
```

### 4.2 Violations API

| | |
|---|---|
| **Action** | Start backend, call violations endpoints |
| **Purpose** | Verify violations API works |
| **Verify** | GET /violations returns list, POST resolve works |

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2

curl http://localhost:8001/violations
# Expected: []

curl http://localhost:8001/health
# Expected: {"status":"ok"}

kill %1
```

### 4.3 Violations hook

| | |
|---|---|
| **Action** | Check hook exists and is executable |
| **Purpose** | Verify deploy generates violations hook |
| **Verify** | check_violations.sh is executable |

```bash
ls -la .runtime/agents/default/.claude/hooks/check_violations.sh
# Expected: -rwxr-xr-x
```

---

## 5. Conversation Logging

### 5.1 Logging hook exists

| | |
|---|---|
| **Action** | Check log_action.sh hook |
| **Purpose** | Verify deploy generates logging hook |
| **Verify** | log_action.sh is executable |

```bash
ls -la .runtime/agents/default/.claude/hooks/log_action.sh
# Expected: -rwxr-xr-x
```

---

## 6. Evolver

### 6.1 Start evolver

| | |
|---|---|
| **Action** | `./agent/start.sh --role evolver` |
| **Purpose** | Verify evolver role launches with correct skills |
| **Verify** | Claude Code opens, evolve skills available |

```bash
make start ROLE=evolver
# In Claude Code:
#   Type "/" → should see: evolve_diagnose, evolve_eval, evolve_improve, evolve_auto, inspect
#   Exit: Ctrl+C
```

### 6.2 Run diagnose

| | |
|---|---|
| **Action** | Run diagnose.py directly |
| **Purpose** | Verify diagnose works with no data |
| **Verify** | Produces report without errors |

```bash
uv run agent/flow/evolve_diagnose/scripts/diagnose.py \
  --data-dir .runtime/data \
  --constraints agent/commitment/constraints.yaml
# Expected: DIAGNOSTIC REPORT with "No conversation data yet"
```

### 6.3 Run eval

| | |
|---|---|
| **Action** | Run eval against live app |
| **Purpose** | Verify eval cases work |
| **Verify** | Reports score |

```bash
uv run uvicorn src.app:app --port 8001 &
sleep 2

uv run agent/flow/evolve_eval/scripts/run_eval.py \
  --cases agent/flow/evolve_eval/eval_cases.yaml \
  --base-url http://localhost:8001
# Expected: [PASS] Health check returns ok
#           Score: 1/1 (100%)

kill %1
```

---

## 7. Dev Role

### 7.1 Start dev

| | |
|---|---|
| **Action** | `./agent/start.sh --role dev` |
| **Purpose** | Verify dev role has correct skills |
| **Verify** | Claude Code opens with setup_claude + inspect skills |

```bash
./agent/start.sh --role dev
# In Claude Code:
#   Type "/" → should see: check_health, setup_claude, inspect
#   Say "inspect" → should show project structure
#   Exit: Ctrl+C
```

---

## 8. Platform Adapters

### 8.1 Adapter exists

| | |
|---|---|
| **Action** | Check adapter files |
| **Purpose** | Verify all 3 adapters are present |
| **Verify** | shell.sh executable for each |

```bash
ls -la agent/adapters/claude/shell.sh   # executable
ls -la agent/adapters/codex/shell.sh    # executable
ls -la agent/adapters/kimicode/shell.sh # executable
```

---

## 9. Automated Tests

### 9.1 Run pytest

| | |
|---|---|
| **Action** | `make test` |
| **Purpose** | Verify all automated tests pass |
| **Verify** | 36 tests pass |

```bash
make test
# Expected: 36 passed
```

---

## 10. Cleanup

```bash
rm -rf .socialware/workspace/test
make clean
```
