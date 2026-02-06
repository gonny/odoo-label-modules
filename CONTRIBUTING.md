# Contributing to Odoo Label Modules

Thank you for your interest in contributing to the Odoo Label Modules project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment](#development-environment)
- [Code Standards](#code-standards)
- [Module Development](#module-development)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Review Process](#code-review-process)

## Getting Started

### Prerequisites

- Docker Desktop or Docker Engine
- Visual Studio Code with Dev Containers extension
- Git
- Basic knowledge of Python and Odoo framework

### Setting Up Your Development Environment

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/odoo-label-modules.git
   cd odoo-label-modules
   ```
3. Open in VSCode and reopen in container when prompted
4. Create a new branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Environment

### Using DevContainer

The project includes a pre-configured DevContainer with all necessary tools:

- Python 3.12
- Docker-in-Docker
- VSCode extensions for Python, XML, Docker, and Odoo development
- Code quality tools (black, pylint, flake8, isort)
- Testing framework (pytest)

### Running Odoo Locally

Use Docker Compose to run Odoo 19 with PostgreSQL:

```bash
docker-compose up -d
```

Access Odoo at http://localhost:8069

To view logs:
```bash
docker-compose logs -f odoo
```

To stop services:
```bash
docker-compose down
```

## Code Standards

### Python Code Style

We follow PEP 8 and use automated tools to enforce code quality:

1. **Black** for code formatting:
   ```bash
   black .
   ```

2. **isort** for import sorting:
   ```bash
   isort .
   ```

3. **Flake8** for linting:
   ```bash
   flake8 .
   ```

4. **Pylint** for additional checks:
   ```bash
   pylint **/*.py
   ```

### Odoo Specific Guidelines

Follow the [OCA Guidelines](https://github.com/OCA/odoo-community.org) for Odoo development:

- Use proper module structure
- Follow naming conventions
- Add proper documentation
- Include security configurations
- Write unit tests

### XML Formatting

- Use 4 spaces for indentation
- Use proper XML formatting
- Add comments for complex logic

## Module Development

### Creating a New Module

1. Use the standard Odoo module structure (see `example_label_module/`)
2. Required files:
   - `__init__.py`
   - `__manifest__.py`
   - `models/` directory with model definitions
   - `views/` directory with XML views
   - `security/ir.model.access.csv`
   - `README.md` with module documentation

### Module Structure

```
module_name/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   └── model_name.py
├── views/
│   ├── model_views.xml
│   └── menu_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml (if needed)
├── data/
│   └── data.xml (if needed)
├── static/
│   └── description/
│       ├── icon.png or icon.svg
│       └── index.html (optional)
└── tests/
    ├── __init__.py
    └── test_model.py
```

### __manifest__.py Requirements

```python
{
    'name': 'Module Name',
    'version': '19.0.1.0.0',  # Odoo version.major.minor.patch
    'category': 'Category',
    'summary': 'Short description',
    'description': """Long description""",
    'author': 'Your Name',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
```

## Testing

### Writing Tests

Create tests in the `tests/` directory:

```python
from odoo.tests.common import TransactionCase

class TestMyModel(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Model = self.env['my.model']
    
    def test_something(self):
        record = self.Model.create({'name': 'Test'})
        self.assertEqual(record.name, 'Test')
```

### Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

Run specific test file:
```bash
pytest path/to/test_file.py
```

### Test Requirements

- All new features must include tests
- Maintain or improve code coverage
- Tests must pass before submitting PR

## Submitting Changes

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add label printing feature

- Implement print action
- Add print date tracking
- Update documentation
```

Commit message prefixes:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `test:` - Test additions or changes
- `chore:` - Build process or auxiliary tool changes

### Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Run code quality checks:
   ```bash
   black .
   isort .
   flake8 .
   pylint **/*.py
   ```
4. Push to your fork
5. Create a pull request with:
   - Clear title describing the change
   - Detailed description of what changed and why
   - Reference to any related issues
   - Screenshots for UI changes

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Code quality checks pass

## Screenshots (if applicable)
Add screenshots here

## Related Issues
Fixes #123
```

## Code Review Process

### Review Checklist

Reviewers will check:
- Code follows style guidelines
- Tests are present and passing
- Documentation is updated
- No security vulnerabilities
- Performance considerations
- Compatibility with Odoo 19

### Addressing Feedback

- Respond to all review comments
- Make requested changes
- Push updates to the same branch
- Request re-review when ready

## Additional Resources

- [Odoo 19 Documentation](https://www.odoo.com/documentation/19.0/)
- [OCA Guidelines](https://github.com/OCA/odoo-community.org)
- [Python PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [Agent Skills Documentation](.github/agents/python-odoo-skills.md)

## Getting Help

- Check existing documentation
- Review the example module
- Ask questions in pull request discussions
- Contact maintainers

## License

By contributing, you agree that your contributions will be licensed under the LGPL-3 license.

Thank you for contributing! 🎉
