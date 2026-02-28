---
description: Tools and commands for Odoo development, including best practices and common tasks.
applyTo: '**/*.py'
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
- Doppler CLI (optional, for secrets management)

## Key Odoo 19 Differences (vs older versions)
- Use `<list>` NOT `<tree>` in XML views
- Use `target="main"` NOT `target="inline"` for settings actions
- `<search>` views: no `expand` attribute on `<group>`
- `<app>` tag in settings: use `name="module_name"` NOT `data-key`
- `groups="base.group_multi_currency"` does NOT exist in Community
- `groups="account.group_account_basic"` does NOT exist in Community

## Development Commands
- `make test` must pass (all unit tests) after every change
- `make reset` must work (clean install) after every change
- `make smoke` must pass (E2E flow) after every change
- Bank accounts in tests: search for existing before creating (avoid duplicate IBAN errors)
- Cash rounding in tests: ensure profit/loss accounts are set

Document covering additional details is in [CONTRIBUTING.md](./../../CONTRIBUTING.md) specification.

# API access (XML-RPC)
# URL: http://localhost:8069
# DB: odoo_label
# User: admin (or configured email)
# Password: admin (or configured password)

## Existing custom modules
- label_calculator -> addons/label_calculator/

## Environment Variables

This project uses Doppler for secrets management. All API keys and 
credentials are available as environment variables when running commands 
with `doppler run --` prefix.

If Doppler is not available (e.g., in CI without token), the Makefile 
falls back to standard environment variables.

### Available env vars:
- `PACKETA_API_KEY` – Packeta REST API key
- `PACKETA_API_PASSWORD` – Packeta API password
- `DPD_API_KEY` – DPD GeoAPI key
- `DPD_API_DSW` – DPD DSW token
- `CZECH_POST_API_KEY` – Czech Post B2B API key
- `CZECH_POST_SECRET_KEY` – Czech Post HMAC secret


## Calculation Logic Overview
- Materials have types: area (mm²), length (mm), time (seconds), pieces
- Waste formula: 1/(1-waste_pct/100) (NOT 1+waste_pct/100)
- Margin formula: raw_cost * (1 + margin_pct/100) (320% = ×4.2)
- Income tax: cost / (1 - tax_pct/100) (15% → /0.85)
- Rounding: math.ceil(price * 10) / 10 (always up to 10 haléřů)
- Addon materials (is_addon=True): only material cost, no labor
- Time addons: seconds × machine hourly_amortization / 3600



## Makefile Commands
- available in [Makefile](./../../Makefile) for common tasks:
  - `make install` – install dependencies
  - `make up` – start Odoo and PostgreSQL via Docker Compose
  - `make test` – run unit tests
  - `make reset` – reset database and install module
  - `make smoke` – run E2E smoke tests