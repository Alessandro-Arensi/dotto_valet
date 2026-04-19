.PHONY: help install install-backend install-frontend \
        dev dev-backend dev-frontend \
        build build-frontend \
        test test-backend test-docker lint lint-frontend typecheck \
        docker-up docker-down docker-build docker-logs docker-restart \
        db-shell db-schema db-test-create db-test-drop db-test-reset \
        env clean clean-backend clean-frontend

# ============================================================
# Dottò — Makefile
# ============================================================

BACKEND_DIR := backend
FRONTEND_DIR := frontend
# Pin to Python 3.11 to match backend Dockerfile (python:3.11-slim).
# Newer Pythons lack wheels for some pinned deps (Pillow, asyncpg, pydantic-core).
PYTHON := $(shell command -v python3.11 2>/dev/null)
VENV := $(BACKEND_DIR)/.venv
PIP := $(VENV)/bin/pip
PYBIN := $(VENV)/bin

# Test DB (uses compose `db` service)
TEST_DB_NAME := dotto_test
TEST_DB_USER := dotto
TEST_DB_PASS := dotto_dev
TEST_DB_HOST := localhost
TEST_DB_PORT := 5432
TEST_DATABASE_URL := postgresql+asyncpg://$(TEST_DB_USER):$(TEST_DB_PASS)@$(TEST_DB_HOST):$(TEST_DB_PORT)/$(TEST_DB_NAME)

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# -------- Setup --------

env: ## Copy env.example to .env
	@test -f .env || cp env.example .env && echo ".env ready"

install: install-backend install-frontend ## Install backend + frontend deps

install-backend: ## Create venv + install backend deps (requires python3.11)
	@if [ -z "$(PYTHON)" ]; then \
		echo "ERROR: python3.11 not found. Install it first:"; \
		echo "  brew install python@3.11"; \
		exit 1; \
	fi
	@echo "Using $(PYTHON)"
	rm -rf $(VENV)
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r $(BACKEND_DIR)/requirements.txt -r $(BACKEND_DIR)/requirements-dev.txt

install-frontend: ## Install frontend deps
	cd $(FRONTEND_DIR) && npm install

# -------- Dev --------

dev-backend: ## Run FastAPI with reload on :8000
	cd $(BACKEND_DIR) && ../$(PYBIN)/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-frontend: ## Run Vite dev server on :5173
	cd $(FRONTEND_DIR) && npm run dev

dev: ## Run full stack via docker-compose
	docker compose up

# -------- Build --------

build: build-frontend ## Build frontend production bundle

build-frontend: ## tsc + vite build
	cd $(FRONTEND_DIR) && npm run build

# -------- Quality --------

test: test-docker ## Run backend tests (via docker compose)

test-backend: ## pytest using host venv (needs DB reachable on localhost:5432)
	cd $(BACKEND_DIR) && TEST_DATABASE_URL="$(TEST_DATABASE_URL)" ../$(PYBIN)/pytest -v

test-docker: ## pytest inside backend container (uses compose network)
	docker compose exec -T backend bash -c "pip install -q -r requirements-dev.txt && TEST_DATABASE_URL=postgresql+asyncpg://$(TEST_DB_USER):$(TEST_DB_PASS)@db:5432/$(TEST_DB_NAME) pytest -v"

lint: lint-frontend ## Run linters

lint-frontend: ## ESLint frontend
	cd $(FRONTEND_DIR) && npm run lint

typecheck: ## TypeScript typecheck (no emit)
	cd $(FRONTEND_DIR) && npx tsc --noEmit

# -------- Docker --------

docker-up: ## Start stack detached
	docker compose up -d

docker-down: ## Stop stack
	docker compose down

docker-build: ## Rebuild images
	docker compose build

docker-logs: ## Tail logs
	docker compose logs -f

docker-restart: ## Restart stack
	docker compose restart

# -------- DB --------

db-shell: ## psql into compose db
	docker compose exec db psql -U dotto -d dotto

db-schema: ## Re-apply schema.sql to compose db
	docker compose exec -T db psql -U dotto -d dotto < db/schema.sql

db-test-create: ## Create dotto_test DB on compose db (idempotent)
	@docker compose exec -T db psql -U $(TEST_DB_USER) -d postgres -tc \
		"SELECT 1 FROM pg_database WHERE datname = '$(TEST_DB_NAME)'" | grep -q 1 || \
		docker compose exec -T db psql -U $(TEST_DB_USER) -d postgres -c "CREATE DATABASE $(TEST_DB_NAME)"
	@echo "Test DB ready: $(TEST_DB_NAME)"

db-test-drop: ## Drop dotto_test DB on compose db
	docker compose exec -T db psql -U $(TEST_DB_USER) -d postgres -c "DROP DATABASE IF EXISTS $(TEST_DB_NAME)"

db-test-reset: db-test-drop db-test-create ## Drop + recreate test DB

# -------- Clean --------

clean: clean-backend clean-frontend ## Remove build artifacts + venv + node_modules

clean-backend:
	rm -rf $(VENV) $(BACKEND_DIR)/__pycache__ $(BACKEND_DIR)/.pytest_cache
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} +

clean-frontend:
	rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist
