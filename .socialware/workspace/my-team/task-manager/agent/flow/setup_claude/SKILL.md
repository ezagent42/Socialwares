---
name: setup_claude
description: "Configure Claude Code environment — install agent-setup plugin, settings, hooks, MCP"
---

# Setup Claude Code Environment

## Trigger

User says "setup claude", "configure environment", "install plugins" etc.

## What It Does

Installs the [agent-setup](https://github.com/ezagent42/agent-setup) plugin
into the current role's PROJECT_DIR. This adds hooks, commands, skills, and MCP config.

## Flow

1. Register the agent-setup marketplace (one-time per machine)
2. Install the agent-setup plugin for this project
3. Run `/agent-setup:init` to interactively configure hooks, plugins, MCP

## Commands to Execute

```bash
# Step 1: Register marketplace
claude plugin marketplace add https://github.com/ezagent42/agent-setup

# Step 2: Install plugin
claude plugin install agent-setup@agent-setup --scope project

# Step 3: Interactive configuration (inside Claude Code)
/agent-setup:init
```

## What Gets Installed

After `/agent-setup:init`:

- **Hooks** — enforce-tools (block pip/npm), session-start health check
- **Plugins** — superpowers, impeccable, etc. (user selects)
- **MCP** — context7 and other MCP servers
- **Settings** — permission mode, enabled plugins

## Notes

- This configures the current role's `.claude/` only, not other roles
- Each role has its own isolated `.claude/` directory
- No dependency on `claude.sh` — runs the plugin commands directly
