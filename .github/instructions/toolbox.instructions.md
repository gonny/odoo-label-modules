---
description: Tools and commands for Odoo development, including best practices and common tasks.
applyTo: '**/*'
# applyTo: 'Describe when these instructions should be loaded' # when provided, instructions will automatically be added to the request context when the pattern matches an attached file
---

# Project: Odoo Label Calculator

Custom Odoo 19 CE module for calculating prices of engraved labels 
and textile tags. Self-hosted via Docker.

## Tech Stack
- Odoo 19 Community Edition (Python 3.12)
- PostgreSQL 16
- Docker + Docker Compose
- SvelteKit (Phase 2 – public calculator)

## Key Odoo 19 Differences (vs older versions)
- Use `<list>` NOT `<tree>` in XML views
- Use `target="main"` NOT `target="inline"` for settings actions
- `<search>` views: no `expand` attribute on `<group>`
- `<app>` tag in settings: use `name="module_name"` NOT `data-key`
- `groups="base.group_multi_currency"` does NOT exist in Community
- `groups="account.group_account_basic"` does NOT exist in Community

## Development Commands
```bash
# Start environment
docker compose up -d

# Run tests
docker compose stop odoo
docker compose run --rm odoo odoo \
    -d odoo_label \
    -u label_calculator \
    --test-tags /label_calculator \
    --stop-after-init
docker compose start odoo

# Reset database
docker compose down
docker volume rm odoo-label-db odoo-label-data
docker compose up -d
# Then install module via UI or CLI

# Update module (no DB reset)
docker compose exec odoo odoo \
    -u label_calculator \
    -d odoo_label \
    --stop-after-init
docker compose restart odoo

# Odoo shell (interactive Python)
docker compose exec odoo odoo shell -d odoo_label

# API access (XML-RPC)
# URL: http://localhost:8069
# DB: odoo_label
# User: admin (or configured email)
# Password: admin (or configured password)

## Module Structure

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
    └── test_calculator.py           # 23 tests

## Calculation Logic Overview
- Materials have types: area (mm²), length (mm), time (seconds), pieces
- Waste formula: 1/(1-waste_pct/100) (NOT 1+waste_pct/100)
- Margin formula: raw_cost * (1 + margin_pct/100) (320% = ×4.2)
- Income tax: cost / (1 - tax_pct/100) (15% → /0.85)
- Rounding: math.ceil(price * 10) / 10 (always up to 10 haléřů)
- Addon materials (is_addon=True): only material cost, no labor
- Time addons: seconds × machine hourly_amortization / 3600