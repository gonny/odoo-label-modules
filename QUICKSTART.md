# Quick Start Guide

Get up and running with Odoo Label Modules in 5 minutes!

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) (or Docker Engine + Docker Compose)
- [Visual Studio Code](https://code.visualstudio.com/)
- [Dev Containers Extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## Step 1: Clone the Repository

```bash
git clone https://github.com/gonny/odoo-label-modules.git
cd odoo-label-modules
```

## Step 2: Open in VSCode

```bash
code .
```

When prompted, click **"Reopen in Container"** or:
- Press `F1` or `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
- Type "Dev Containers: Reopen in Container"
- Press Enter

## Step 3: Wait for Container Setup

The DevContainer will automatically:
- ✅ Install Python 3.12
- ✅ Set up Docker-in-Docker
- ✅ Install development dependencies
- ✅ Configure VSCode extensions

This may take 2-5 minutes on first run.

## Step 4: Start Odoo

Open a terminal in VSCode (`` Ctrl+` ``) and run:

```bash
docker-compose up -d
```

Wait for the services to start (~30 seconds).

## Step 5: Access Odoo

Open your browser and navigate to:
```
http://localhost:8069
```

**Initial Setup:**
1. Master password: `admin`
2. Database name: `odoo`
3. Email: Your email
4. Password: Your choice
5. Language: Your preference
6. Country: Your country
7. Demo data: Optional (check for testing)

Click **"Create Database"**

## Step 6: Install the Example Module

1. In Odoo, go to **Apps**
2. Remove the "Apps" filter in the search bar
3. Search for "Example Label Module"
4. Click **"Install"**

## Step 7: Try the Example Module

1. Go to **Labels** menu (top navigation)
2. Click **"Create"**
3. Fill in the form:
   - **Name**: My First Label
   - **Product**: Search and select a product
   - **Label Type**: Barcode
   - **Size**: Medium
   - **Quantity**: 10
4. Click **"Save"**
5. Click **"Confirm"**
6. Click **"Print"**

Congratulations! You've successfully created and printed your first label! 🎉

## Development Workflow

### Creating a New Module

See the `example_label_module/` directory for reference.

```bash
# Create module structure
mkdir -p my_module/{models,views,security,data,static/description,tests}

# Create required files
touch my_module/__init__.py
touch my_module/__manifest__.py
touch my_module/models/__init__.py
touch my_module/README.md
```

### Code Quality Checks

Run before committing:

```bash
# Format code
black .
isort .

# Lint code
flake8 .
pylint **/*.py

# Run tests
pytest
```

### Updating Modules

After making changes to your module:

```bash
# Restart Odoo
docker-compose restart odoo

# Update the module in Odoo
# Go to Apps → Search for your module → Upgrade
```

Or use the command line:

```bash
docker exec -it odoo19 odoo -u your_module_name -d odoo
```

## Troubleshooting

### Container won't start

```bash
# Rebuild the container
docker-compose down
docker-compose up --build
```

### Can't access Odoo

Check if services are running:
```bash
docker-compose ps
```

Check logs:
```bash
docker-compose logs odoo
```

### Module not appearing

1. Update the apps list: **Apps → Update Apps List**
2. Remove filters in the search
3. Make sure `installable: True` in `__manifest__.py`

### Database connection issues

```bash
# Restart database
docker-compose restart db

# Check database logs
docker-compose logs db
```

## Next Steps

- 📖 Read the full [README.md](README.md)
- 🤝 Check [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- 📚 Review [Agent Skills](.github/agents/python-odoo-skills.md) for coding patterns
- 🔍 Explore the [example_label_module/](example_label_module/) code

## Common Commands

```bash
# Start Odoo
docker-compose up -d

# Stop Odoo
docker-compose down

# View logs
docker-compose logs -f odoo

# Access Odoo container shell
docker exec -it odoo19 bash

# Access PostgreSQL
docker exec -it odoo_db psql -U odoo

# Run tests
pytest

# Format code
black . && isort .

# Check code quality
flake8 . && pylint **/*.py
```

## Getting Help

- 📧 Check existing [GitHub Issues](https://github.com/gonny/odoo-label-modules/issues)
- 💬 Open a new issue for questions
- 📖 Review [Odoo Documentation](https://www.odoo.com/documentation/19.0/)

Happy coding! 🚀
