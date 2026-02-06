{
    'name': 'Example Label Module',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Example module for label management',
    'description': """
        Example Label Module
        ====================
        
        This is an example module demonstrating the structure and best practices
        for Odoo 19 label management modules.
        
        Features:
        ---------
        * Label creation and management
        * Label printing
        * Label templates
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/label_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
