---
name: setup_claude
description: "Configure Claude Code environment — install agent-setup plugin, settings, hooks, MCP"
---

# Setup Claude Code Environment

## Trigger

User says "setup claude", "configure environment", "install plugins" etc.

## What It Does

Runs the `claude.sh` bootstrap script within the current workspace's dev role
PROJECT_DIR (`.runtime/agents/dev/`). This installs:

- **agent-setup plugin** — hooks, commands, skills
- **settings.json** — permission mode, enabled plugins
- **mcp.json** — MCP server configuration
- **hooks/** — enforce-tools (block pip/npm), session-start health check

## Flow

1. Verify `.runtime/agents/dev/` exists (deploy must have been run)
2. Copy `claude.sh` from repo root to `.runtime/agents/dev/`
3. Execute `claude.sh` from within `.runtime/agents/dev/`
4. agent-setup plugin installs into `.runtime/agents/dev/.claude/`
5. Run `/agent-setup:init` to complete interactive configuration

## Usage

```bash
# From within the workspace:
# 1. Deploy first
./agent/deploy.sh

# 2. Start as dev role
./agent/start.sh --role dev

# 3. In Claude Code, say:
#    "Setup Claude environment"
#    Or manually:
#    /agent-setup:init
```

## Manual Alternative

If you prefer not to use this skill, you can configure manually:

```bash
cd .runtime/agents/dev
# Copy claude.sh from repo root
cp ../../../claude.sh .
# Run it
./claude.sh
# Inside Claude Code: /agent-setup:init
```

## Notes

- This configures the dev role's `.claude/` only, not other roles
- Each role has its own isolated `.claude/` directory
- After setup, the dev role has full agent-setup capabilities (hooks, skills, MCP)
- Other roles (default, admin, etc.) keep their minimal `.claude/` from deploy.sh
