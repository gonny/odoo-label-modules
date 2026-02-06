# 🏷️ Odoo Label ERP

Vlastní ERP systém pro výrobu gravírovaných štítků a textilních etiket.
Postaveno na **Odoo 19 Community Edition**.

## Tech Stack

- **ERP:** Odoo 19 CE (Python 3.12)
- **DB:** PostgreSQL 16
- **Runtime:** Docker + Docker Compose
- **Vývoj:** VS Code + WSL2

## Rychlý start

### Požadavky

- Docker + Docker Compose
- Git

### Spuštění

```bash
# 1. Naklonuj repo
git clone git@github.com:TVUJ-USERNAME/odoo-label-modules.git
cd odoo-label-modules

# 2. Spusť kontejnery
docker compose up -d

# 3. Otevři prohlížeč
# http://localhost:8069
