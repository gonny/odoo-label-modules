.PHONY: help install format lint test clean start stop restart logs shell db-shell

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python dependencies
	pip install -r requirements.txt

format:  ## Format code with black and isort
	@echo "Formatting code..."
	black .
	isort .
	@echo "✓ Code formatted"

lint:  ## Run linting tools
	@echo "Running linters..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=.git,__pycache__,.venv,venv
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics --exclude=.git,__pycache__,.venv,venv
	pylint **/*.py --exit-zero --disable=C,R
	@echo "✓ Linting complete"

test:  ## Run tests with pytest
	@echo "Running tests..."
	pytest --verbose --cov=. --cov-report=term
	@echo "✓ Tests complete"

test-coverage:  ## Run tests with coverage report
	pytest --verbose --cov=. --cov-report=html --cov-report=term
	@echo "✓ Coverage report generated in htmlcov/"

quality:  ## Run all quality checks (format, lint, test)
	@make format
	@make lint
	@make test

clean:  ## Clean up temporary files and caches
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned up"

start:  ## Start Odoo and PostgreSQL containers
	@echo "Starting Odoo..."
	docker-compose up -d
	@echo "✓ Odoo started at http://localhost:8069"

stop:  ## Stop Odoo and PostgreSQL containers
	@echo "Stopping Odoo..."
	docker-compose down
	@echo "✓ Odoo stopped"

restart:  ## Restart Odoo and PostgreSQL containers
	@echo "Restarting Odoo..."
	docker-compose restart
	@echo "✓ Odoo restarted"

logs:  ## Show Odoo logs
	docker-compose logs -f odoo

logs-db:  ## Show PostgreSQL logs
	docker-compose logs -f db

shell:  ## Open a shell in the Odoo container
	docker exec -it odoo19 bash

db-shell:  ## Open a PostgreSQL shell
	docker exec -it odoo_db psql -U odoo

build:  ## Rebuild containers
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

update-module:  ## Update a module in Odoo (usage: make update-module MODULE=module_name)
	@if [ -z "$(MODULE)" ]; then \
		echo "Error: MODULE not specified. Usage: make update-module MODULE=module_name"; \
		exit 1; \
	fi
	docker exec -it odoo19 odoo -u $(MODULE) -d odoo --stop-after-init

install-module:  ## Install a module in Odoo (usage: make install-module MODULE=module_name)
	@if [ -z "$(MODULE)" ]; then \
		echo "Error: MODULE not specified. Usage: make install-module MODULE=module_name"; \
		exit 1; \
	fi
	docker exec -it odoo19 odoo -i $(MODULE) -d odoo --stop-after-init

validate:  ## Validate all configuration files
	@echo "Validating configuration files..."
	@python -m json.tool .devcontainer/devcontainer.json > /dev/null && echo "✓ devcontainer.json is valid"
	@python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))" && echo "✓ dependabot.yml is valid"
	@python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" && echo "✓ docker-compose.yml is valid"
	@echo "✓ All configuration files are valid"

check:  ## Run validation, linting, and tests
	@make validate
	@make lint
	@make test

dev:  ## Start development environment
	@make start
	@echo ""
	@echo "Development environment ready!"
	@echo "  - Odoo: http://localhost:8069"
	@echo "  - Database: PostgreSQL on localhost:5432"
	@echo ""
	@echo "Useful commands:"
	@echo "  make logs       - View Odoo logs"
	@echo "  make shell      - Access Odoo container"
	@echo "  make stop       - Stop services"

.DEFAULT_GOAL := help
