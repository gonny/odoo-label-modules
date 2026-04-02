# ============================================================================
# Odoo Label Calculator – Development Makefile
# ============================================================================
# Requires: Docker, Docker Compose (v2 plugin), Doppler CLI (optional, for secrets management)
#
# Quick start:
#   make up        – start Odoo 19 + PostgreSQL 16
#   make reset     – drop DB, recreate, install module + seed data
#   make test      – run Odoo unit tests (23+ tests)
#   make smoke     – run end-to-end XML-RPC smoke test
#   make shell     – open interactive Odoo Python shell
#   make logs      – tail Odoo logs
# ============================================================================

DOPPLER := $(shell command -v doppler 2> /dev/null)

ifdef DOPPLER
  RUN = doppler run --
else
  RUN =
endif

.PHONY: help up down restart reset test seed shell logs logs-db db-shell \
        smoke build install format lint clean quality test-coverage \
        check validate dev update-module install-module

ODOO_DB      ?= odoo_label
ODOO_MODULE  ?= label_calculator
ODOO_PORT    ?= 8069

# ── Primary targets ────────────────────────────────────────────────────────

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up:  ## Start Odoo + PostgreSQL containers
	@echo "Starting Odoo …"
	$(RUN) docker compose up -d
	@echo "✓ Odoo starting at http://localhost:$(ODOO_PORT)"

down:  ## Stop and remove containers (keeps data volumes)
	@echo "Stopping Odoo …"
	docker compose down
	@echo "✓ Odoo stopped"

restart:  ## Restart Odoo and PostgreSQL containers
	docker compose restart
	@echo "✓ Odoo restarted"

reset:  ## Drop DB, recreate, install both modules with seed data
	@echo "Resetting database …"
	$(RUN) docker compose down -v
	$(RUN) docker compose up -d db
	@echo "Waiting for PostgreSQL …"
	@sleep 5
	$(RUN) docker compose up -d
	@echo "Waiting for Odoo to start …"
	@sleep 10
	$(RUN) docker compose run --rm odoo \
		odoo -d $(ODOO_DB) -i label_calculator,label_shipping \
		--stop-after-init --without-demo=all --log-level=warn
	$(RUN) docker compose restart odoo
	@echo "✓ Database reset complete – Odoo ready at http://localhost:$(ODOO_PORT)"

test:  ## Run Odoo unit tests for label_calculator and label_shipping
	$(RUN) docker compose run --rm odoo \
		odoo -d $(ODOO_DB) -u label_calculator,label_shipping \
		--test-tags label_calculator,label_shipping \
		--stop-after-init \
		--log-level=test

seed:  ## Update/install module without dropping DB (re-seed data)
	$(RUN) docker compose run --rm odoo \
		odoo -d $(ODOO_DB) -u $(ODOO_MODULE) \
		--stop-after-init --log-level=warn
	$(RUN) docker compose restart odoo
	@echo "✓ Module updated"

shell:  ## Open interactive Odoo Python shell
	docker compose run --rm odoo odoo shell -d $(ODOO_DB)

logs:  ## Tail Odoo container logs
	docker compose logs -f odoo

logs-db:  ## Tail PostgreSQL container logs
	docker compose logs -f db

db-shell:  ## Open a PostgreSQL shell
	docker compose exec db psql -U odoo -d $(ODOO_DB)

smoke:  ## Run end-to-end smoke test via XML-RPC
	$(RUN) python scripts/smoke_test.py

# ── Build & module management ─────────────────────────────────────────────

build:  ## Rebuild containers from scratch
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	@echo "✓ Containers rebuilt"

update-module:  ## Update a module (usage: make update-module MODULE=label_calculator)
	@if [ -z "$(MODULE)" ]; then \
		echo "Error: MODULE not specified. Usage: make update-module MODULE=module_name"; \
		exit 1; \
	fi
	docker compose exec odoo odoo -u $(MODULE) -d $(ODOO_DB) --stop-after-init
	docker compose restart odoo

install-module:  ## Install a module (usage: make install-module MODULE=label_calculator)
	@if [ -z "$(MODULE)" ]; then \
		echo "Error: MODULE not specified. Usage: make install-module MODULE=module_name"; \
		exit 1; \
	fi
	docker compose exec odoo odoo -i $(MODULE) -d $(ODOO_DB) --stop-after-init
	docker compose restart odoo

# ── Python quality tools (local, not Docker) ──────────────────────────────

install:  ## Install Python dependencies
	pip install -r requirements.txt

format:  ## Format code with black and isort
	@echo "Formatting code …"
	black .
	isort .
	@echo "✓ Code formatted"

lint:  ## Run linting tools
	@echo "Running linters …"
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=.git,__pycache__,.venv,venv
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics --exclude=.git,__pycache__,.venv,venv
	pylint **/*.py --exit-zero --disable=C,R
	@echo "✓ Linting complete"

test-coverage:  ## Run tests with coverage report (pytest, local)
	pytest --verbose --cov=. --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in htmlcov/"

quality:  ## Run all quality checks (format, lint)
	@$(MAKE) format
	@$(MAKE) lint

clean:  ## Clean up temporary files and caches
	@echo "Cleaning up …"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned up"

validate:  ## Validate all configuration files
	@echo "Validating configuration files …"
	@python -m json.tool .devcontainer/devcontainer.json > /dev/null && echo "✓ devcontainer.json is valid"
	@python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))" && echo "✓ dependabot.yml is valid"
	@python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" && echo "✓ docker-compose.yml is valid"
	@echo "✓ All configuration files are valid"

check:  ## Run validation and linting
	@$(MAKE) validate
	@$(MAKE) lint

dev:  ## Start development environment (alias for up)
	@$(MAKE) up
	@echo ""
	@echo "Development environment ready!"
	@echo "  Odoo:     http://localhost:$(ODOO_PORT)"
	@echo "  DB:       PostgreSQL on localhost:5433"
	@echo "  Login:    admin / admin"
	@echo ""
	@echo "Useful commands:"
	@echo "  make logs       – view Odoo logs"
	@echo "  make shell      – Odoo Python shell"
	@echo "  make test       – run unit tests"
	@echo "  make smoke      – run XML-RPC smoke test"
	@echo "  make reset      – reset DB to clean state"

.DEFAULT_GOAL := help
