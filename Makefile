# Socialware App Makefile
# Entry point for deploy, start, test. Leverages Make's timestamp-based idempotency.

AGENT_DIR  := agent
RUNTIME    := .runtime
STAMP      := $(RUNTIME)/.deploy_stamp

# Source files that trigger redeploy
ROLES      := $(wildcard $(AGENT_DIR)/role/*.md)
SCOPE      := $(AGENT_DIR)/scope/scope.md
CONSTRAINTS:= $(AGENT_DIR)/commitment/constraints.yaml
FLOW_YAML  := $(AGENT_DIR)/flow/flow.yaml
SKILLS     := $(wildcard $(AGENT_DIR)/flow/*/SKILL.md)
SOURCES    := $(ROLES) $(SCOPE) $(CONSTRAINTS) $(FLOW_YAML) $(SKILLS)

.PHONY: start test clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: $(STAMP) ## Compile four primitives → .runtime/ (only if sources changed)

$(STAMP): $(SOURCES)
	./$(AGENT_DIR)/deploy.sh
	@mkdir -p $(RUNTIME)
	@touch $@

start: deploy ## Start agent (ROLE=default by default)
	./$(AGENT_DIR)/start.sh --role $(or $(ROLE),default)

test: ## Run tests
	uv run pytest -v

clean: ## Remove .runtime/
	rm -rf $(RUNTIME)
