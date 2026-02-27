---
name: python-oddo-skills
description: This skill is errata for common pitfalls and differences in Odoo 19, not a tutorial.
---
This document outlines key skills and patterns for developing Odoo 19 modules.

**Odoo 19 XML Views:**
- Use `<list>` NOT `<tree>` for list views
- Use `target="main"` NOT `target="inline"` for settings actions
- `<search>` views: no `expand` attribute on `<group>`
- `<app>` tag in settings: use `name="module_name"` NOT `data-key`
- Do NOT use `string` attribute as XPath selector in view inheritance
- Before writing XPath for QWeb report templates, extract actual structure first via Odoo shell

**Groups that do NOT exist in Community Edition:**
- `base.group_multi_currency`
- `account.group_account_basic`
- `account.group_account_manager`
- If inheriting views with these groups, remove the `groups` attribute

**Python / ORM:**
- `models.NewId` does NOT exist in Odoo 19 – use `isinstance(record.id, int)`
- `target="inline"` is NOT valid for `ir.actions.act_window.target` – use `target="main"`
- `button_immediate_install` cannot be called from `post_init_hook`
- For `res.config.settings`, value `0` may not save – use Boolean checkbox + conditional field
- `@api.model_create_multi` returns list – unwrap for single creates
- XML-RPC `read()` method: fields go in kwargs `{"fields": [...]}`, not positional args
- Sale order lines must be created with order using `(0, 0, vals)` command, not separately

**Code style:**
- Keep existing comments – do NOT remove them
- Add docstrings to all new methods
- File naming: no `_ext` suffix (e.g., `sale_order_line.py` not `sale_order_line_ext.py`)
- Seed data in `default_data.xml` with `noupdate="1"`

**Testing:**
- `make test` must pass (all unit tests) after every change
- `make reset` must work (clean install) after every change
- `make smoke` must pass (E2E flow) after every change
- Bank accounts in tests: search for existing before creating (avoid duplicate IBAN errors)
- Cash rounding in tests: ensure profit/loss accounts are set

### Boundaries
- Do NOT include implementation code examples (agent knows how to code)
- Keep it concise – bullet points, not paragraphs
- Focus on ERRATA (what's different/broken) not tutorials

## 9. Performance Tips

1. **Prefetch**: Access related fields together to benefit from prefetching
2. **Batch operations**: Use write/create with multiple records
3. **Avoid loops**: Use recordset operations instead of loops
4. **Store computed fields**: Store when frequently accessed
5. **Indexes**: Add indexes to frequently searched fields
6. **Limit queries**: Use proper domains to limit result sets

## 10. Debugging

```python
import logging
_logger = logging.getLogger(__name__)

# Log messages
_logger.info('Info message')
_logger.warning('Warning message')
_logger.error('Error message')

# Debug with pdb
import pdb; pdb.set_trace()
```
