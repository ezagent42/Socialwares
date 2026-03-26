# Socialware App — Workspace Makefile
# Run from within your workspace directory.

AGENT_DIR  := agent
RUNTIME    := .runtime
STAMP      := $(RUNTIME)/.deploy_stamp
ADAPTER    ?= claude

ROLES      := $(filter-out $(AGENT_DIR)/role/README.md, $(wildcard $(AGENT_DIR)/role/*.md))
SCOPE      := $(AGENT_DIR)/scope/scope.md
COMMITMENT := $(AGENT_DIR)/commitment/commitment.yaml
FLOW_YAML  := $(AGENT_DIR)/flow/flow.yaml
SKILLS     := $(wildcard $(AGENT_DIR)/flow/*/SKILL.md)
# Include directories as deps so file additions/deletions trigger rebuild
ROLE_DIR   := $(AGENT_DIR)/role
FLOW_DIR   := $(AGENT_DIR)/flow
SOURCES    := $(ROLES) $(SCOPE) $(COMMITMENT) $(FLOW_YAML) $(SKILLS) $(ROLE_DIR) $(FLOW_DIR)

# Template root (for sync command)
TEMPLATE_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null)

.PHONY: start run test clean sync help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: $(STAMP) ## Compile four primitives → .runtime/ (only if sources changed)

$(STAMP): $(SOURCES)
	./$(AGENT_DIR)/deploy.sh --adapter $(ADAPTER)
	@mkdir -p $(RUNTIME)
	@touch $@

start: deploy ## TUI mode: make start ROLE=default
	./$(AGENT_DIR)/start.sh --role $(or $(ROLE),default) --adapter $(ADAPTER)

run: deploy ## SDK mode: make run ROLE=default PROMPT="check health"
	@if [ -z "$(PROMPT)" ]; then echo "Error: PROMPT is required. Usage: make run ROLE=default PROMPT=\"check health\""; exit 1; fi
	uv run src/start_agent.py --role $(or $(ROLE),default) --adapter $(ADAPTER) --prompt "$(PROMPT)"

test: ## Run tests
	uv run pytest -v

clean: ## Remove .runtime/
	rm -rf $(RUNTIME)

sync: ## Sync scripts from template (adapters, deploy, start, evolver scripts, Makefile, start_agent.py)
	@if [ -z "$(TEMPLATE_ROOT)" ]; then echo "Error: not in a git repo, cannot find template root"; exit 1; fi
	@echo "Syncing from template: $(TEMPLATE_ROOT)"
	@cp "$(TEMPLATE_ROOT)/agent/adapters/base.py" $(AGENT_DIR)/adapters/base.py
	@cp "$(TEMPLATE_ROOT)/agent/adapters/claude/sdk.py" $(AGENT_DIR)/adapters/claude/sdk.py
	@cp "$(TEMPLATE_ROOT)/agent/adapters/claude/shell.sh" $(AGENT_DIR)/adapters/claude/shell.sh
	@cp "$(TEMPLATE_ROOT)/agent/adapters/codex/sdk.py" $(AGENT_DIR)/adapters/codex/sdk.py
	@cp "$(TEMPLATE_ROOT)/agent/adapters/codex/shell.sh" $(AGENT_DIR)/adapters/codex/shell.sh
	@cp "$(TEMPLATE_ROOT)/agent/adapters/kimicode/sdk.py" $(AGENT_DIR)/adapters/kimicode/sdk.py
	@cp "$(TEMPLATE_ROOT)/agent/adapters/kimicode/shell.sh" $(AGENT_DIR)/adapters/kimicode/shell.sh
	@cp "$(TEMPLATE_ROOT)/agent/deploy.sh" $(AGENT_DIR)/deploy.sh
	@cp "$(TEMPLATE_ROOT)/agent/start.sh" $(AGENT_DIR)/start.sh
	@cp "$(TEMPLATE_ROOT)/agent/Makefile.template" Makefile
	@cp "$(TEMPLATE_ROOT)/src/start_agent.py" src/start_agent.py
	@for script_dir in "$(TEMPLATE_ROOT)"/agent/flow/*/scripts; do \
		[ -d "$$script_dir" ] || continue; \
		skill_name=$$(basename $$(dirname "$$script_dir")); \
		target_dir="$(AGENT_DIR)/flow/$$skill_name/scripts"; \
		mkdir -p "$$target_dir"; \
		cp "$$script_dir"/*.py "$$target_dir/" 2>/dev/null || true; \
	done
	@echo "Synced. Run 'make clean && make deploy' to rebuild."
