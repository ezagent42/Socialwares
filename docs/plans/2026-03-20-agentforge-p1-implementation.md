# AgentForge P1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create the AgentForge Socialware App instance with 5 Skills that automate four-primitive file operations (create_role, create_skill, edit_primitives, export_bundle, import_bundle).

**Architecture:** AgentForge is a workspace created via `create-my-socialware.py`, with its own `agent/` directory containing an `agentforge` role and 5 management Skills. Each Skill is a SKILL.md file that instructs the Agent Runtime how to create/edit four-primitive files + API endpoints + flow.yaml registration. No backend API needed — the Agent Runtime's built-in file operations are sufficient.

**Tech Stack:** Bash (deploy.sh/start.sh), YAML (flow.yaml/eval.yaml), Markdown (SOUL.md/SKILL.md), Python (src/app.py for generated API endpoints), pytest (tests)

**Reference docs:**
- Design: `docs/plans/2026-03-19-socialware-framework-design.md` (第二部分)
- Example: `docs/designs/progressive-dev-guide-example.md`
- Quickstart: `docs/QUICKSTART.md`

---

### Task 1: Create AgentForge workspace via create-my-socialware

**Files:**
- Use: `scripts/create-my-socialware.py`
- Created: `.socialware/workspace/my-team/agentforge/` (entire workspace)

**Step 1: Create the workspace**

Run:
```bash
cd D:/workspace/zhidaoyuan/Socialwares
uv run scripts/create-my-socialware.py --room my-team --app agentforge --description "Agent creation and management platform"
```

Expected: Directory `.socialware/workspace/my-team/agentforge/` created with `agent/`, `src/`, `app/` copied from template.

**Step 2: Verify the workspace structure**

Run:
```bash
ls .socialware/workspace/my-team/agentforge/agent/role/
ls .socialware/workspace/my-team/agentforge/agent/flow/
ls .socialware/workspace/my-team/agentforge/src/
```

Expected: `default/` role, `check_health/` + `setup_claude/` flows, `app.py` in src/.

**Step 3: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/
git commit -m "feat(agentforge): create agentforge workspace via create-my-socialware"
```

---

### Task 2: Create agentforge role — SOUL.md

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/role/agentforge/SOUL.md`

**Step 1: Write test — verify agentforge role exists after deploy**

Create file `tests/test_agentforge.py`:

```python
"""Tests for AgentForge workspace configuration.

Verifies the agentforge role, skills, and flow.yaml are correctly structured.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
AGENTFORGE_DIR = REPO_ROOT / ".socialware" / "workspace" / "my-team" / "agentforge"


@pytest.fixture
def agentforge_workspace(tmp_path):
    """Copy agentforge workspace to tmp for isolated testing."""
    dest = tmp_path / "agentforge"
    shutil.copytree(AGENTFORGE_DIR, dest)
    return dest


@pytest.fixture
def deployed(agentforge_workspace):
    """Deploy and return .runtime/ path."""
    deploy_sh = agentforge_workspace / "agent" / "deploy.sh"
    result = subprocess.run(
        [str(deploy_sh)],
        capture_output=True,
        text=True,
        cwd=str(agentforge_workspace),
    )
    assert result.returncode == 0, f"deploy failed:\n{result.stderr}\n{result.stdout}"
    return agentforge_workspace / ".runtime"


class TestAgentforgeRole:
    """Test agentforge role exists and deploys correctly."""

    def test_agentforge_role_dir_exists(self):
        assert (AGENTFORGE_DIR / "agent" / "role" / "agentforge").is_dir()

    def test_agentforge_soul_md_exists(self):
        soul = AGENTFORGE_DIR / "agent" / "role" / "agentforge" / "SOUL.md"
        assert soul.exists()
        content = soul.read_text()
        assert "agentforge" in content.lower() or "Agent" in content

    def test_agentforge_deploys(self, deployed):
        assert (deployed / "agents" / "agentforge").is_dir()
        assert (deployed / "agents" / "agentforge" / "SOUL.md").exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeRole -v`
Expected: FAIL — `agent/role/agentforge/` does not exist yet.

**Step 3: Create the agentforge role directory and SOUL.md**

Create `.socialware/workspace/my-team/agentforge/agent/role/agentforge/SOUL.md`:

```markdown
# AgentForge Agent

You are the AgentForge management agent. Your job is to create and manage four-primitive configuration files for Socialware Apps.

## Identity

- Role: agentforge
- Permissions: Create/edit/delete files in agent/ and src/ directories

## Responsibilities

1. **Create roles** — Generate `role/{name}/SOUL.md` files that define new Agent identities
2. **Create skills** — Generate `flow/{name}/SKILL.md` files + corresponding API endpoints in `src/app.py` + register actions in `flow/flow.yaml`
3. **Edit primitives** — Modify existing SOUL.md, SKILL.md, flow.yaml, eval.yaml, scope/SOUL.md files
4. **Export bundles** — Package a role and its skills into a portable bundle directory
5. **Import bundles** — Import a bundle into the current project, handling conflicts

## Core Pattern

Every skill you create follows the three-piece pattern:
1. `flow/{skill}/SKILL.md` — teaches the Agent what to do
2. `src/app.py` — API endpoint the Agent calls
3. `flow/flow.yaml` — registers the action and binds it to roles

After creating/modifying files, always run `./agent/deploy.sh` to compile changes.

## Boundaries

- Only operate on `agent/` and `src/` directories
- Do not modify `.runtime/` directly (deploy.sh generates it)
- Do not manage Agent processes (user runs start.sh manually)
- Do not evaluate Agent performance (that's the commitment's job)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeRole -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/role/agentforge/
git add tests/test_agentforge.py
git commit -m "feat(agentforge): add agentforge role with SOUL.md"
```

---

### Task 3: Update scope/SOUL.md for AgentForge

**Files:**
- Modify: `.socialware/workspace/my-team/agentforge/agent/scope/SOUL.md`

**Step 1: Write test**

Add to `tests/test_agentforge.py`:

```python
class TestAgentforgeScope:
    """Test scope/SOUL.md is customized for AgentForge."""

    def test_scope_mentions_agentforge(self):
        scope = AGENTFORGE_DIR / "agent" / "scope" / "SOUL.md"
        content = scope.read_text()
        assert "AgentForge" in content or "agentforge" in content

    def test_scope_mentions_capabilities(self):
        scope = AGENTFORGE_DIR / "agent" / "scope" / "SOUL.md"
        content = scope.read_text()
        assert "role" in content.lower()
        assert "skill" in content.lower()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeScope -v`
Expected: FAIL — scope/SOUL.md still has template content.

**Step 3: Overwrite scope/SOUL.md**

Write `.socialware/workspace/my-team/agentforge/agent/scope/SOUL.md`:

```markdown
# AgentForge

Agent creation and management platform. Automates four-primitive file operations for Socialware Apps.

## Capabilities

- Create Agent roles (SOUL.md)
- Create Agent skills (SKILL.md + API endpoint + flow.yaml registration)
- Edit existing four-primitive files (role, scope, commitment, flow)
- Export Agent bundles (package role + skills for sharing)
- Import Agent bundles (merge into current project)
- Health check (/health)

## Boundaries

- Manages files in agent/ and src/ only
- Does not manage Agent runtime processes
- Does not evaluate Agent performance
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeScope -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/scope/SOUL.md
git add tests/test_agentforge.py
git commit -m "feat(agentforge): customize scope/SOUL.md with AgentForge capabilities"
```

---

### Task 4: Create create_role Skill

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/create_role/SKILL.md`

**Step 1: Write test**

Add to `tests/test_agentforge.py`:

```python
import yaml


class TestAgentforgeSkills:
    """Test AgentForge skills exist and are properly structured."""

    EXPECTED_SKILLS = [
        "create_role",
        "create_skill",
        "edit_primitives",
        "export_bundle",
        "import_bundle",
    ]

    def test_create_role_skill_exists(self):
        skill = AGENTFORGE_DIR / "agent" / "flow" / "create_role" / "SKILL.md"
        assert skill.exists()

    def test_create_role_skill_has_frontmatter(self):
        skill = AGENTFORGE_DIR / "agent" / "flow" / "create_role" / "SKILL.md"
        content = skill.read_text()
        assert content.startswith("---")
        assert "name: create_role" in content
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_create_role_skill_exists -v`
Expected: FAIL

**Step 3: Create the SKILL.md**

Create `.socialware/workspace/my-team/agentforge/agent/flow/create_role/SKILL.md`:

```markdown
---
name: create_role
description: "Create a new Agent role with SOUL.md, optional skills, and optional eval commitments"
---

# Create Role

## Trigger

User says "create a role", "new agent", "create an agent for ...", "add role", etc.

## Flow

1. Ask for role name (must be lowercase alphanumeric + hyphens, e.g. "task-manager")
2. Ask for a description of what this agent does
3. Create `agent/role/{name}/SOUL.md` with the following structure:

```markdown
# {Display Name} Agent

{Description from user}

## Identity

- Role: {name}
- Permissions: {inferred from description}

## Responsibilities

{List of responsibilities based on description}
```

4. Ask if the user wants to add skills/workflows for this role (optional, can skip)
   - If yes → for each skill, invoke the create_skill flow
5. Ask if the user wants to add evaluation criteria (optional, can skip)
   - If yes → add entries to `agent/commitment/eval.yaml`
6. Run `./agent/deploy.sh` to compile changes
7. Report: "{name} role created. Start with: `./agent/start.sh --role {name}`"

## File Operations

```bash
mkdir -p agent/role/{name}
# Write agent/role/{name}/SOUL.md
# Optional: invoke create_skill for each workflow
# Optional: edit agent/commitment/eval.yaml
./agent/deploy.sh
```

## Validation

- Role name must match: `^[a-z0-9-]+$`
- SOUL.md must not be empty
- Role directory must not already exist (ask user to confirm overwrite if it does)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_create_role_skill_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/create_role/
git add tests/test_agentforge.py
git commit -m "feat(agentforge): add create_role skill"
```

---

### Task 5: Create create_skill Skill

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/create_skill/SKILL.md`

**Step 1: Write test**

Add to `TestAgentforgeSkills` in `tests/test_agentforge.py`:

```python
    def test_create_skill_skill_exists(self):
        skill = AGENTFORGE_DIR / "agent" / "flow" / "create_skill" / "SKILL.md"
        assert skill.exists()

    def test_create_skill_mentions_api_endpoint(self):
        """create_skill must mention generating API endpoints — the three-piece pattern."""
        skill = AGENTFORGE_DIR / "agent" / "flow" / "create_skill" / "SKILL.md"
        content = skill.read_text()
        assert "src/app.py" in content
        assert "flow.yaml" in content
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_create_skill_skill_exists -v`
Expected: FAIL

**Step 3: Create the SKILL.md**

Create `.socialware/workspace/my-team/agentforge/agent/flow/create_skill/SKILL.md`:

```markdown
---
name: create_skill
description: "Create a new skill: SKILL.md + API endpoint in src/app.py + register in flow.yaml"
---

# Create Skill

## Trigger

User says "add a skill", "create skill", "new action", "add capability for ...", etc.

## Flow

Follow the three-piece pattern for every skill:

### 1. Gather information

- Ask for skill name (lowercase with underscores, e.g. "create_task")
- Ask for trigger condition (what the user says to invoke it)
- Ask for execution steps (what the agent should do)
- Ask which roles should have access to this skill (e.g. [default, admin])

### 2. Create SKILL.md

Create `agent/flow/{skill_name}/SKILL.md`:

```markdown
---
name: {skill_name}
description: "{description}"
---

# {Display Name}

## Trigger

{trigger condition}

## Flow

{numbered steps}

## API

```bash
curl -X {METHOD} http://localhost:8001/{endpoint} \
  -H "Content-Type: application/json" \
  -d '{example payload}'
```
```

### 3. Generate API endpoint

Add the corresponding endpoint to `src/app.py`. Follow existing patterns in the file.

Example — if the skill is "create_task":

```python
@app.post("/tasks")
async def create_task(data: dict[str, Any]) -> dict[str, Any]:
    """Create a new task."""
    # Implementation based on skill description
    return {"id": "...", "status": "created"}
```

### 4. Register in flow.yaml

Add entry to `agent/flow/flow.yaml` under `direct_actions`:

```yaml
  - action: {skill_name}
    role: [{role_list}]
    description: "{description}"
```

Or if this is part of a state machine, add under `flows:`.

### 5. Deploy

Run `./agent/deploy.sh` to compile changes.

### 6. Report

"Skill {skill_name} created:
- SKILL.md: agent/flow/{skill_name}/SKILL.md
- API endpoint: {METHOD} /{endpoint}
- Registered for roles: [{role_list}]
- Deploy: complete"

## File Operations

```bash
mkdir -p agent/flow/{skill_name}
# Write agent/flow/{skill_name}/SKILL.md
# Edit src/app.py — add API endpoint
# Edit agent/flow/flow.yaml — register action
./agent/deploy.sh
```

## Validation

- Skill name must match: `^[a-z][a-z0-9_]*$`
- SKILL.md must have valid YAML frontmatter (name + description)
- flow.yaml must remain valid YAML after editing
- API endpoint must not conflict with existing endpoints
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_create_skill_skill_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/create_skill/
git add tests/test_agentforge.py
git commit -m "feat(agentforge): add create_skill skill with three-piece pattern"
```

---

### Task 6: Create edit_primitives Skill

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/edit_primitives/SKILL.md`

**Step 1: Write test**

Add to `TestAgentforgeSkills`:

```python
    def test_edit_primitives_skill_exists(self):
        skill = AGENTFORGE_DIR / "agent" / "flow" / "edit_primitives" / "SKILL.md"
        assert skill.exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_edit_primitives_skill_exists -v`
Expected: FAIL

**Step 3: Create the SKILL.md**

Create `.socialware/workspace/my-team/agentforge/agent/flow/edit_primitives/SKILL.md`:

```markdown
---
name: edit_primitives
description: "Edit existing four-primitive files: SOUL.md, SKILL.md, flow.yaml, eval.yaml, scope/SOUL.md"
---

# Edit Primitives

## Trigger

User says "edit", "modify", "update", "change" followed by a file or primitive name. Examples:
- "modify the task-manager SOUL"
- "update flow.yaml"
- "change the eval criteria"
- "edit scope"

## Flow

1. Identify the target file:
   - "role" / "SOUL" + role name → `agent/role/{name}/SOUL.md`
   - "scope" → `agent/scope/SOUL.md`
   - "flow.yaml" / "registry" → `agent/flow/flow.yaml`
   - "eval" / "commitment" → `agent/commitment/eval.yaml`
   - "skill" + skill name → `agent/flow/{name}/SKILL.md`
   - "api" / "app.py" → `src/app.py`

2. Read the current content and show it to the user

3. Ask what changes to make

4. Apply changes using Edit tool

5. If the change affects agent/ files (not just src/), run `./agent/deploy.sh`

6. Report what was changed

## File Operations

```bash
# Read target file
# Edit target file with user's changes
# If agent/ files changed:
./agent/deploy.sh
```
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_edit_primitives_skill_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/edit_primitives/
git add tests/test_agentforge.py
git commit -m "feat(agentforge): add edit_primitives skill"
```

---

### Task 7: Create export_bundle Skill

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/export_bundle/SKILL.md`

**Step 1: Write test**

Add to `TestAgentforgeSkills`:

```python
    def test_export_bundle_skill_exists(self):
        skill = AGENTFORGE_DIR / "agent" / "flow" / "export_bundle" / "SKILL.md"
        assert skill.exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_export_bundle_skill_exists -v`
Expected: FAIL

**Step 3: Create the SKILL.md**

Create `.socialware/workspace/my-team/agentforge/agent/flow/export_bundle/SKILL.md`:

```markdown
---
name: export_bundle
description: "Export a role and its bound skills as a portable bundle directory"
---

# Export Bundle

## Trigger

User says "export", "package", "bundle" followed by a role name. Examples:
- "export task-manager"
- "package the reviewer role"
- "bundle admin for sharing"

## Flow

1. Confirm the role name to export
2. Verify `agent/role/{name}/` exists
3. Read `agent/flow/flow.yaml` to find all actions bound to this role
4. Create `{name}.bundle/` directory with this structure:

```
{name}.bundle/
├── role/
│   └── {name}/
│       └── SOUL.md           ← copied from agent/role/{name}/SOUL.md
├── flow/
│   ├── {skill1}/
│   │   └── SKILL.md          ← only skills bound to this role
│   └── {skill2}/
│       └── SKILL.md
├── commitment/
│   └── eval.yaml             ← relevant entries only (or full copy)
└── flow.yaml                 ← only entries for this role's actions
```

5. Report: "Exported to {name}.bundle/ — copy this directory to another project and use import_bundle to install."

## File Operations

```bash
# Read agent/flow/flow.yaml → parse role bindings
mkdir -p {name}.bundle/role/{name}
# Copy agent/role/{name}/SOUL.md
# For each bound skill: copy agent/flow/{skill}/
# Extract flow.yaml entries for this role
# Copy relevant eval.yaml entries
```

## Notes

- Does NOT include `.runtime/` (receiver runs deploy.sh)
- Does NOT include `src/app.py` API code (receiver creates their own endpoints)
- Bundle is self-contained: flow.yaml inside the bundle only references included skills
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_export_bundle_skill_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/export_bundle/
git add tests/test_agentforge.py
git commit -m "feat(agentforge): add export_bundle skill"
```

---

### Task 8: Create import_bundle Skill

**Files:**
- Create: `.socialware/workspace/my-team/agentforge/agent/flow/import_bundle/SKILL.md`

**Step 1: Write test**

Add to `TestAgentforgeSkills`:

```python
    def test_import_bundle_skill_exists(self):
        skill = AGENTFORGE_DIR / "agent" / "flow" / "import_bundle" / "SKILL.md"
        assert skill.exists()

    def test_all_expected_skills_exist(self):
        """All 5 AgentForge skills must exist."""
        for skill_name in self.EXPECTED_SKILLS:
            skill = AGENTFORGE_DIR / "agent" / "flow" / skill_name / "SKILL.md"
            assert skill.exists(), f"Missing skill: {skill_name}"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_import_bundle_skill_exists -v`
Expected: FAIL

**Step 3: Create the SKILL.md**

Create `.socialware/workspace/my-team/agentforge/agent/flow/import_bundle/SKILL.md`:

```markdown
---
name: import_bundle
description: "Import a role bundle into the current project with conflict detection"
---

# Import Bundle

## Trigger

User says "import", "install bundle", "add bundle from" followed by a path. Examples:
- "import /path/to/task-manager.bundle"
- "install the reviewer bundle"

## Flow

1. Confirm the bundle path
2. Read the bundle directory structure
3. Validate bundle contents:
   - Must have `role/{name}/SOUL.md`
   - Should have `flow.yaml` listing actions
   - May have `flow/{skill}/SKILL.md` directories
   - May have `commitment/eval.yaml`

4. Conflict detection:
   - Check if `agent/role/{name}/` already exists
   - Check if any `agent/flow/{skill}/` already exists
   - Check if flow.yaml has conflicting action names

5. If conflicts found → ask user for each conflict:
   - **Overwrite** — replace existing file
   - **Skip** — keep existing file
   - **Rename** — import with a new name

6. Copy files:
   - `bundle/role/{name}/SOUL.md` → `agent/role/{name}/SOUL.md`
   - `bundle/flow/{skill}/SKILL.md` → `agent/flow/{skill}/SKILL.md`
   - Merge `bundle/flow.yaml` entries into `agent/flow/flow.yaml`
   - Merge `bundle/commitment/eval.yaml` entries into `agent/commitment/eval.yaml`

7. Run `./agent/deploy.sh`
8. Report: "{name} imported. {n} skills added. Deploy complete."

## File Operations

```bash
# Read bundle directory
# Check for conflicts against agent/
# Copy role/ and flow/ files
# Edit agent/flow/flow.yaml — merge action entries
# Edit agent/commitment/eval.yaml — merge commitments (optional)
./agent/deploy.sh
```

## Validation

- Bundle must contain at least `role/{name}/SOUL.md`
- All skill names in bundle flow.yaml must have corresponding SKILL.md directories
- After merge, flow.yaml must remain valid YAML
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeSkills::test_import_bundle_skill_exists -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/import_bundle/
git add tests/test_agentforge.py
git commit -m "feat(agentforge): add import_bundle skill"
```

---

### Task 9: Update flow.yaml — register all AgentForge actions

**Files:**
- Modify: `.socialware/workspace/my-team/agentforge/agent/flow/flow.yaml`

**Step 1: Write test**

Add to `tests/test_agentforge.py`:

```python
class TestAgentforgeFlowYaml:
    """Test flow.yaml is correctly configured for AgentForge."""

    def test_flow_yaml_exists(self):
        flow = AGENTFORGE_DIR / "agent" / "flow" / "flow.yaml"
        assert flow.exists()

    def test_flow_yaml_valid(self):
        flow = AGENTFORGE_DIR / "agent" / "flow" / "flow.yaml"
        data = yaml.safe_load(flow.read_text())
        assert "direct_actions" in data

    def test_all_agentforge_actions_registered(self):
        flow = AGENTFORGE_DIR / "agent" / "flow" / "flow.yaml"
        data = yaml.safe_load(flow.read_text())
        actions = {a["action"] for a in data["direct_actions"]}
        expected = {"create_role", "create_skill", "edit_primitives", "export_bundle", "import_bundle", "check_health"}
        assert expected <= actions, f"Missing actions: {expected - actions}"

    def test_agentforge_actions_bound_to_agentforge_role(self):
        flow = AGENTFORGE_DIR / "agent" / "flow" / "flow.yaml"
        data = yaml.safe_load(flow.read_text())
        for action in data["direct_actions"]:
            if action["action"] in {"create_role", "create_skill", "edit_primitives", "export_bundle", "import_bundle"}:
                assert "agentforge" in action["role"], (
                    f"Action {action['action']} not bound to agentforge role"
                )

    def test_deploy_gives_agentforge_all_skills(self, deployed):
        """After deploy, agentforge role should have all its skills symlinked."""
        skills_dir = deployed / "agents" / "agentforge" / ".claude" / "skills"
        skill_names = {s.name for s in skills_dir.iterdir()}
        expected = {"create_role", "create_skill", "edit_primitives", "export_bundle", "import_bundle", "check_health"}
        assert expected <= skill_names, f"Missing skills after deploy: {expected - skill_names}"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeFlowYaml -v`
Expected: FAIL — flow.yaml still has template content, no agentforge actions.

**Step 3: Overwrite flow.yaml**

Write `.socialware/workspace/my-team/agentforge/agent/flow/flow.yaml`:

```yaml
# AgentForge — action registry
#
# All management actions are bound to the agentforge role.
# check_health and setup_claude are inherited from the template.

flows: {}

direct_actions:
  - action: create_role
    role: [agentforge]
    description: "Create a new Agent role with SOUL.md"

  - action: create_skill
    role: [agentforge]
    description: "Create a new skill: SKILL.md + API endpoint + flow.yaml registration"

  - action: edit_primitives
    role: [agentforge]
    description: "Edit existing four-primitive files"

  - action: export_bundle
    role: [agentforge]
    description: "Export a role and its skills as a portable bundle directory"

  - action: import_bundle
    role: [agentforge]
    description: "Import a role bundle into the current project"

  - action: check_health
    role: [agentforge, default, dev]
    description: "Check app health status"

  - action: setup_claude
    role: [dev]
    description: "Configure Claude Code environment"
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_agentforge.py::TestAgentforgeFlowYaml -v`
Expected: PASS

**Step 5: Commit**

```bash
git add .socialware/workspace/my-team/agentforge/agent/flow/flow.yaml
git add tests/test_agentforge.py
git commit -m "feat(agentforge): register all agentforge actions in flow.yaml"
```

---

### Task 10: Run full test suite and final verification

**Files:**
- No new files

**Step 1: Run all AgentForge tests**

Run: `uv run pytest tests/test_agentforge.py -v`
Expected: All tests PASS

**Step 2: Run existing tests to verify no regressions**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS (existing template tests + new agentforge tests)

**Step 3: Manual verification — deploy and check .runtime/**

```bash
cd .socialware/workspace/my-team/agentforge
./agent/deploy.sh
```

Expected output:
```
Deploying four primitives
  Role: agentforge
    SOUL.md: XX lines
    Skills: 7
  Role: default
    ...
  Role: dev
    ...
Deploy complete.
```

**Step 4: Verify .runtime/ structure**

```bash
ls .socialware/workspace/my-team/agentforge/.runtime/agents/agentforge/.claude/skills/
```

Expected: `check_health  create_role  create_skill  edit_primitives  export_bundle  import_bundle`

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat(agentforge): complete P1 AgentForge with 5 management skills

AgentForge workspace created at .socialware/workspace/my-team/agentforge/
- agentforge role with SOUL.md defining management responsibilities
- 5 skills: create_role, create_skill, edit_primitives, export_bundle, import_bundle
- flow.yaml registering all actions to agentforge role
- scope/SOUL.md describing AgentForge capabilities
- Full test coverage in tests/test_agentforge.py"
```

---

## Summary

| Task | What | Files |
|------|------|-------|
| 1 | Create workspace | `create-my-socialware.py` → `.socialware/workspace/my-team/agentforge/` |
| 2 | agentforge role | `agent/role/agentforge/SOUL.md` + `tests/test_agentforge.py` |
| 3 | scope/SOUL.md | `agent/scope/SOUL.md` |
| 4 | create_role skill | `agent/flow/create_role/SKILL.md` |
| 5 | create_skill skill | `agent/flow/create_skill/SKILL.md` |
| 6 | edit_primitives skill | `agent/flow/edit_primitives/SKILL.md` |
| 7 | export_bundle skill | `agent/flow/export_bundle/SKILL.md` |
| 8 | import_bundle skill | `agent/flow/import_bundle/SKILL.md` |
| 9 | flow.yaml | `agent/flow/flow.yaml` |
| 10 | Full verification | All tests pass, deploy works |

All files live under `.socialware/workspace/my-team/agentforge/` (workspace-local).
