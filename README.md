# Odoo Label Modules

Custom Odoo 19 modules for label management (Odoo etiketou).

## 🚀 Features

- Modern development environment with DevContainer support
- Docker-in-Docker for running Odoo instances
- Automated dependency management with Dependabot
- Auto-merging for patch and minor dependency updates
- VSCode extensions pre-configured for Odoo development
- Python development tools (linting, formatting, testing)

## 📋 Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) or Docker Engine
- [Visual Studio Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

## 🛠️ Development Setup

### Option 1: Using DevContainer (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/gonny/odoo-label-modules.git
   cd odoo-label-modules
   ```

2. Open in VSCode:
   ```bash
   code .
   ```

3. When prompted, click "Reopen in Container" or run the command:
   - Press `F1` or `Ctrl+Shift+P`
   - Type "Dev Containers: Reopen in Container"
   - Select and press Enter

4. Wait for the container to build and start. The environment will automatically:
   - Install Python 3.12
   - Configure Docker-in-Docker
   - Install development dependencies
   - Set up all VSCode extensions

### Option 2: Local Development

1. Install Python 3.12 or higher
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 📦 Installed VSCode Extensions

The DevContainer comes pre-configured with:

- **Python** (ms-python.python) - Python language support
- **Pylance** (ms-python.vscode-pylance) - Fast, feature-rich Python language server
- **XML Tools** (dotjoshjohnson.xml) - XML formatting and tools
- **Docker** (ms-azuretools.vscode-docker) - Docker support
- **GitLens** (eamodio.gitlens) - Git visualization and history
- **Odoo Snippets** (jigar-patel.odoosnippets) - Odoo development snippets

## 🏗️ Module Structure

Each Odoo module should follow this structure:

```
module_name/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── *.py
├── views/
│   └── *.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── data/
│   └── *.xml
├── static/
│   └── description/
│       ├── icon.png
│       └── index.html
├── tests/
│   ├── __init__.py
│   └── test_*.py
└── README.md
```

## 🧪 Development Workflow

### Creating a New Module

See `.github/agents/python-odoo-skills.md` for detailed examples and patterns.

### Running Odoo

Within the DevContainer, you can run Odoo using Docker:

```bash
# Pull Odoo 19 image
docker pull odoo:19

# Run Odoo with PostgreSQL
docker run -d -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres --name db postgres:16

docker run -d -v $(pwd):/mnt/extra-addons -p 8069:8069 --name odoo --link db:db -t odoo:19
```

Access Odoo at http://localhost:8069

### Code Quality

Run linting and formatting:

```bash
# Format code with Black
black .

# Sort imports
isort .

# Run Pylint
pylint **/*.py

# Run Flake8
flake8 .
```

### Testing

```bash
# Run tests with pytest
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## 🤖 Agent Skills

This repository includes agent configurations for AI-assisted development:

- **Odoo Developer Agent** (`.github/agents/odoo-developer.md`): Expert Odoo 19 developer with comprehensive knowledge
- **Python Odoo Skills** (`.github/agents/python-odoo-skills.md`): Code patterns, examples, and best practices

## 🔄 Automated Dependency Management

This repository uses Dependabot to automatically:
- Check for Python package updates (weekly on Mondays)
- Check for GitHub Actions updates (weekly on Mondays)
- Check for Docker image updates (weekly on Mondays)

Patch and minor updates are automatically approved and merged via GitHub Actions.

## 📚 Resources

- [Odoo 19 Documentation](https://www.odoo.com/documentation/19.0/)
- [Odoo Development Tutorials](https://www.odoo.com/documentation/19.0/developer.html)
- [OCA Guidelines](https://github.com/OCA/odoo-community.org)
- [Python Style Guide (PEP 8)](https://www.python.org/dev/peps/pep-0008/)

## 🤝 Contributing

1. Create a new branch for your feature/fix
2. Make your changes following Odoo and Python best practices
3. Ensure all tests pass and code is properly formatted
4. Submit a pull request

## 📝 License

LGPL-3 (Odoo standard license)

## 👤 Author

gonny

## 🐛 Issues

Report issues at: https://github.com/gonny/odoo-label-modules/issues
