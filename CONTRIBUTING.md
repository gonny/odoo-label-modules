# CONTRIBUTING.md – Development Guide

## Project: Odoo Label Calculator

Custom Odoo 19 CE module for calculating prices of engraved labels
and textile tags. Self-hosted via Docker.

## Tech Stack

- **Odoo 19** Community Edition (Python 3.12)
- **PostgreSQL 16**
- **Docker + Docker Compose** (v2 plugin)
- SvelteKit (Phase 2 – public calculator)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/gonny/odoo-label-modules.git
cd odoo-label-modules

# 2. Start the environment
make up                  # starts Odoo + PostgreSQL

# 3. Initialize the database with the module and seed data
make reset               # drops DB, installs module, seeds data

# 4. Open Odoo in your browser
#    URL:      http://localhost:8069
#    Login:    admin
#    Password: admin
#    Database: odoo_label
```

After `make reset`, Odoo should show:
- Menu **"Kalkulačka štítků"** with submenus
- 5 material groups (Koženka Royal, Satén, TTR pásky, Heat press, Komponenty)
- 2 products (Gravírovaný štítek, Textilní etiketa)
- Settings page with hourly rate, tax, margins

---

## Makefile Targets

| Target          | Description                                              |
| --------------- | -------------------------------------------------------- |
| `make up`       | Start Odoo + PostgreSQL containers                       |
| `make down`     | Stop and remove containers (keeps volumes)               |
| `make reset`    | Drop DB, recreate, install module + seed data            |
| `make test`     | Run all Odoo unit tests (`--test-tags /label_calculator`)|
| `make seed`     | Update module without dropping DB (re-seed `noupdate=0`) |
| `make shell`    | Open interactive Odoo Python shell                       |
| `make quality`  | Run code linters                          |
| `make logs`     | Tail Odoo container logs                                 |
| `make smoke`    | Run XML-RPC end-to-end smoke test                        |
| `make build`    | Rebuild containers from scratch                          |
| `make dev`      | Start environment + print useful commands                |

### Running Tests

```bash
# Run Odoo unit tests (23+ tests)
make test

# Full reset + test (clean state)
make reset && make test

# Run the XML-RPC smoke test (Odoo must be running)
make smoke
```

### Resetting the Database

```bash
make reset
# This will:
#   1. docker compose down -v  (remove containers + volumes)
#   2. Start fresh PostgreSQL + Odoo
#   3. Install label_calculator with seed data
#   4. Restart Odoo for normal operation
```

---

## XML-RPC API Access

The module can be accessed programmatically via Odoo's XML-RPC interface.

### Configuration

| Parameter | Default                  |
| --------- | ------------------------ |
| URL       | `http://localhost:8069`  |
| Database  | `odoo_label`             |
| User      | `admin`                  |
| Password  | `admin`                  |

### Using the RPC Client

```bash
# Run the interactive demo
python scripts/odoo_rpc.py

# Use as a library
python -c "
from scripts.odoo_rpc import OdooRPC
rpc = OdooRPC()
rpc.connect()
products = rpc.search_read('product.template',
    [('pricing_type', '=', 'calculator')], ['name'])
print(products)
"
```

### Smoke Test

```bash
# Runs all checks: seed data, create SO, confirm, invoice
python scripts/smoke_test.py
# or
make smoke
```

The smoke test verifies:
1. Seed data is present (groups, materials, tiers, products)
2. A customer can be created
3. A sale order with calculator pricing can be created
4. Price calculation populates all fields (price, breakdown, costs)
5. The order can be confirmed
6. An invoice can be generated with correct fields

---

## Key Odoo 19 Differences (vs older versions)

- Use `<list>` **NOT** `<tree>` in XML views
- Use `target="main"` **NOT** `target="inline"` for settings actions
- `<search>` views: no `expand` attribute on `<group>`
- `<app>` tag in settings: use `name="module_name"` **NOT** `data-key`
- `groups="base.group_multi_currency"` does **NOT** exist in Community
- `groups="account.group_account_basic"` does **NOT** exist in Community

## Project Conventions

- **File naming:** `label_machine.py`, `label_material.py` – no `_ext` suffix
- **Database:** single `odoo_label` database for dev and test
- **Seed data:** `data/default_data.xml` with `noupdate="1"`
- **No third-party modules:** only our `label_calculator` module
- **Docker Compose v2:** use `docker compose` (space) not `docker-compose`
- **Container names:** `odoo-label` (Odoo), `odoo-label-db` (PostgreSQL)

---

## Module Structure

```
addons/label_calculator/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── label_machine.py
│   ├── label_material_group.py
│   ├── label_material.py
│   ├── label_production_tier.py
│   ├── label_material_tier_override.py
│   ├── label_calculator.py          # Core calculation engine
│   ├── product_template.py
│   ├── sale_order.py
│   ├── sale_order_line.py
│   ├── account_move.py
│   ├── account_move_line.py
│   ├── partner_discount_tier.py
│   ├── res_partner.py
│   └── res_config_settings.py
├── views/
│   ├── label_machine_views.xml
│   ├── label_material_group_views.xml
│   ├── label_material_views.xml
│   ├── label_production_tier_views.xml
│   ├── product_template_views.xml
│   ├── sale_order_line_views.xml
│   ├── account_move_views.xml
│   ├── partner_discount_tier_views.xml
│   ├── res_partner_views.xml
│   ├── res_config_settings_views.xml
│   └── menu.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── default_data.xml
└── tests/
    ├── __init__.py
    └── test_calculator.py           # 23+ tests
```

## Calculation Logic Overview

- Materials have types: **area** (mm²), **length** (mm), **time** (seconds), **pieces**
- Waste formula: `1 / (1 - waste_pct / 100)` (NOT `1 + waste_pct / 100`)
- Margin formula: `raw_cost * (1 + margin_pct / 100)` (320% = ×4.2)
- Income tax: `cost / (1 - tax_pct / 100)` (15% → /0.85)
- Rounding: `math.ceil(price * 10) / 10` (always up to 10 haléřů)
- Addon materials (`is_addon=True`): only material cost, no labor
- Time addons: `seconds × machine.hourly_amortization / 3600`

---

## Development Workflow

1. Create a feature branch
2. Make changes following Odoo 19 and Python conventions
3. Run `make test` to verify unit tests pass
4. Run `make smoke` to verify end-to-end flow
5. Submit a pull request