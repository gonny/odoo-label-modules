# Python Odoo Development Skills

This document outlines key skills and patterns for developing Odoo 19 modules.

## 1. Module Scaffolding

### Basic Module Structure
```
module_name/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── model_name.py
├── views/
│   └── model_name_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── data/
│   └── data.xml
├── static/
│   └── description/
│       └── icon.png
├── tests/
│   ├── __init__.py
│   └── test_model.py
└── README.md
```

### __manifest__.py Template
```python
{
    'name': 'Module Name',
    'version': '19.0.1.0.0',
    'category': 'Category',
    'summary': 'Short description',
    'description': """
        Detailed description of the module
    """,
    'author': 'Your Name',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/model_name_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
```

## 2. Model Development

### Basic Model
```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ModelName(models.Model):
    _name = 'module.model'
    _description = 'Model Description'
    _order = 'name'
    
    name = fields.Char(string='Name', required=True, index=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='State', default='draft')
```

### Computed Fields
```python
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True
    )
    
    @api.depends('line_ids.amount')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.line_ids.mapped('amount'))
```

### Constraints
```python
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end and record.date_start > record.date_end:
                raise ValidationError("End date must be after start date")
```

### Onchange Methods
```python
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.address = self.partner_id.address
```

## 3. Inheritance Patterns

### Classic Inheritance (_inherit)
```python
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    custom_field = fields.Char(string='Custom Field')
```

### Delegation Inheritance (_inherits)
```python
class CustomUser(models.Model):
    _name = 'custom.user'
    _inherits = {'res.partner': 'partner_id'}
    
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
```

## 4. View Development

### Form View
```xml
<odoo>
    <record id="view_model_form" model="ir.ui.view">
        <field name="name">module.model.form</field>
        <field name="model">module.model</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <button name="action_confirm" string="Confirm" type="object"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="description"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>
</odoo>
```

### Tree View
```xml
<record id="view_model_tree" model="ir.ui.view">
    <field name="name">module.model.tree</field>
    <field name="model">module.model</field>
    <field name="arch" type="xml">
        <tree>
            <field name="name"/>
            <field name="state"/>
        </tree>
    </field>
</record>
```

### Search View
```xml
<record id="view_model_search" model="ir.ui.view">
    <field name="name">module.model.search</field>
    <field name="model">module.model</field>
    <field name="arch" type="xml">
        <search>
            <field name="name"/>
            <filter name="active" string="Active" domain="[('active', '=', True)]"/>
            <group expand="0" string="Group By">
                <filter name="group_state" string="State" context="{'group_by': 'state'}"/>
            </group>
        </search>
    </field>
</record>
```

### Action
```xml
<record id="action_model" model="ir.actions.act_window">
    <field name="name">Models</field>
    <field name="res_model">module.model</field>
    <field name="view_mode">tree,form</field>
</record>
```

### Menu
```xml
<menuitem id="menu_model_root" name="Module Name"/>
<menuitem id="menu_model" name="Models" parent="menu_model_root" action="action_model"/>
```

## 5. Security Configuration

### ir.model.access.csv
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_module_model_user,module.model.user,model_module_model,base.group_user,1,1,1,1
access_module_model_manager,module.model.manager,model_module_model,base.group_system,1,1,1,1
```

### Record Rules
```xml
<record id="module_model_rule" model="ir.rule">
    <field name="name">Model: user can only see own records</field>
    <field name="model_id" ref="model_module_model"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
</record>
```

## 6. Testing

### Unit Test
```python
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestModel(TransactionCase):
    
    def setUp(self):
        super().setUp()
        self.Model = self.env['module.model']
    
    def test_create_model(self):
        record = self.Model.create({'name': 'Test'})
        self.assertEqual(record.name, 'Test')
    
    def test_constraint(self):
        with self.assertRaises(ValidationError):
            self.Model.create({
                'name': 'Test',
                'date_start': '2024-01-01',
                'date_end': '2023-01-01',
            })
```

## 7. Common Patterns

### CRUD Operations
```python
# Create
record = self.env['module.model'].create({'name': 'New Record'})

# Read
records = self.env['module.model'].search([('active', '=', True)])
record = self.env['module.model'].browse(record_id)

# Update
record.write({'name': 'Updated Name'})

# Delete
record.unlink()
```

### Working with Recordsets
```python
# Filtering
active_records = records.filtered(lambda r: r.active)

# Mapping
names = records.mapped('name')

# Sorting
sorted_records = records.sorted(key=lambda r: r.name)
```

### Context and Environment
```python
# With different context
records = self.env['module.model'].with_context(lang='en_US').search([])

# With different user
records = self.env['module.model'].with_user(user_id).search([])

# Sudo (bypass access rights)
records = self.env['module.model'].sudo().search([])
```

## 8. API Decorators

- `@api.model`: Method operates on the model, not records
- `@api.depends('field')`: Recompute when field changes
- `@api.onchange('field')`: Trigger when field changes in UI
- `@api.constrains('field')`: Validate field values
- `@api.returns('model')`: Specify return type

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
