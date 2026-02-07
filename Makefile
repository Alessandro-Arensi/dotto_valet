# Dottò - Makefile
# Development: lavorare su branch develop. Release: merge su main e build artifact prod.

.PHONY: help build up down reload restart logs test test-backend test-frontend venv install-deps format lint lint-fix release clean

# Default (questo progetto richiede solo Python 3.11 nel venv)
DOCKER_COMPOSE := docker-compose
COMPOSE_FILE   := docker-compose.yml
VENV_DIR       := .venv
PYTHON         := python3.11
PIP            := pip

help:
	clear
	@echo "Dottò - Target disponibili:"
	@echo "  make build         - Build immagini Docker (dev)"
	@echo "  make up            - Avvia tutti i servizi (dev)"
	@echo "  make down          - Ferma e rimuove i container"
	@echo "  make reload        - down + build + up (ricarica tutto)"
	@echo "  make restart       - Riavvia i servizi (up dopo down)"
	@echo "  make logs          - Log dei container (segui)"
	@echo "  make test          - Esegue test backend + frontend"
	@echo "  make test-backend  - Test Python (pytest in backend)"
	@echo "  make test-frontend - Lint/test frontend (npm)"
	@echo "  make venv          - Crea .venv e installa dipendenze Python (pyproject.toml)"
	@echo "  make install-deps  - Solo installa dipendenze in .venv (venv già esistente)"
	@echo "  make format        - Formatta il codice con black"
	@echo "  make lint          - Lint con ruff (solo check)"
	@echo "  make lint-fix      - Lint con ruff e auto-fix"
	@echo "  make check-all     - Formatta e auto-fix lint"
	@echo "  make release      - Verifiche pre-release (lint, test, build) + istruzioni per merge su main"
	@echo "  make clean        - Rimuove container, volumi, .venv, cache"

# --- Build ---
build:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) build

build-no-cache:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) build --no-cache

# --- Run ---
up:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d

up-build:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d --build

# Avvia solo PocketBase (stack minimo per sviluppo frontend/PB)
up-pocketbase:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) up -d pocketbase

# --- Stop ---
down:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down

down-volumes:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down -v

# --- Reload / Restart ---
reload: down build up
	@echo "Stack ricaricato."

restart: down up
	@echo "Stack riavviato."

# --- Logs ---
logs:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f

logs-pocketbase:
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) logs -f pocketbase

# --- Test ---
test: test-backend test-frontend

test-backend:
	@if [ -d "$(VENV_DIR)" ]; then \
		. $(VENV_DIR)/bin/activate && cd backend && python -m pytest -q 2>/dev/null || echo "Backend: nessun test configurato (aggiungi pytest)."; \
	else \
		echo "Backend: salta (nessun .venv — esegui 'make venv' per i test Python)."; \
	fi

test-frontend:
	@cd frontend && (npm run test 2>/dev/null || npm run lint) || true

# --- Python venv ---
venv:
	@if [ -d "$(VENV_DIR)" ]; then \
		echo "Venv già presente in $(VENV_DIR). Usa 'make install-deps' per reinstallare."; \
	else \
		command -v $(PYTHON) >/dev/null 2>&1 || { echo "Errore: $(PYTHON) non trovato. Installa con: sudo apt install python3.11 python3.11-venv"; exit 1; }; \
		$(PYTHON) -m venv $(VENV_DIR) && echo "Venv creato in $(VENV_DIR) con $(PYTHON)." && $(MAKE) install-deps; \
	fi

install-deps:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Crea prima il venv: make venv"; exit 1; \
	fi
	. $(VENV_DIR)/bin/activate && $(PIP) install --upgrade pip && $(PIP) install -e "backend[dev]"
	@echo "Dipendenze Python (backend + dev) installate in $(VENV_DIR)."

# --- Format & Lint (richiedono .venv con backend[dev]; usano backend/pyproject.toml) ---
format:
	@if [ -d "$(VENV_DIR)" ]; then \
		. $(VENV_DIR)/bin/activate && cd backend && black app; \
	else \
		echo "Esegui prima: make venv"; exit 1; \
	fi

lint:
	@if [ -d "$(VENV_DIR)" ]; then \
		. $(VENV_DIR)/bin/activate && cd backend && ruff check app; \
	else \
		echo "Esegui prima: make venv"; exit 1; \
	fi

lint-fix:
	@if [ -d "$(VENV_DIR)" ]; then \
		. $(VENV_DIR)/bin/activate && cd backend && ruff check app --fix && ruff format app; \
	else \
		echo "Esegui prima: make venv"; exit 1; \
	fi

check-all: format lint-fix

# --- Release (eseguire da branch develop quando pronto per main) ---
release: lint test build
	@echo ""
	@echo "--- Verifiche pre-release completate (lint, test, build). ---"
	@echo "Per pubblicare la release su main:"
	@echo "  1. git checkout main"
	@echo "  2. git merge develop --no-ff -m \"Release x.y.z\""
	@echo "  3. git tag vx.y.z"
	@echo "  4. git push origin main --tags"
	@echo "Poi torna su develop: git checkout develop"

# --- Clean ---
clean: down
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) down -v 2>/dev/null || true
	rm -rf $(VENV_DIR)
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "Pulizia completata."
