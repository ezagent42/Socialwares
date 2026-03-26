# Socialwares Template — Root Makefile
# Template-level operations only. For deploy/start, cd into a workspace.

.PHONY: create test help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

create: ## Create new workspace: make create ROOM=my-team APP=my-app DESC="description"
	uv run scripts/create-my-socialware.py --room $(ROOM) --app $(APP) --description "$(or $(DESC),$(APP) Socialware App)"
	$(MAKE) -C .socialware/workspace/$(ROOM)/$(APP) deploy
	@echo ""
	@echo "Next: cd .socialware/workspace/$(ROOM)/$(APP)"

test: ## Run template tests
	uv run pytest -v

deploy start clean: ## Not available at root — cd into a workspace first
	@echo "Error: '$@' is a workspace command, not a root command."
	@echo ""
	@echo "  make create ROOM=my-team APP=my-app    # create workspace first"
	@echo "  cd .socialware/workspace/my-team/my-app  # then cd into it"
	@echo "  make $@                                  # then run $@"
	@exit 1
