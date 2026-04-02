{
    "name": "Label Shipping",
    "version": "19.0.1.0.0",
    "category": "Inventory/Delivery",
    "summary": "Správa zásilek – Packeta, DPD",
    "description": """
        Modul pro tvorbu zásilek a tisk štítků přes API:
        - Packeta (Zásilkovna)
        - DPD CZ
    """,
    "author": "Jan Šnobl",
    "website": "https://etiketou.cz",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale_management",
        "label_calculator",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/default_data.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/label_shipment_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
    ],
    "post_init_hook": "_post_init_shipping",
    "installable": True,
    "application": True,
    "auto_install": False,
}
