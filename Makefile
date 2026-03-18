.PHONY: dev api app install lint

dev: ## Run api and app concurrently
	@$(MAKE) -j2 api app

api: ## Run FastAPI dev server on :8000
	cd api && uv run uvicorn main:app --reload --port 8000

app: ## Run Next.js dev server on :3000
	pnpm --filter app run dev

install: ## Install all dependencies
	cd api && uv sync
	pnpm install

lint: ## Lint all code
	cd api && uv run ruff check .
	pnpm --filter app run lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
