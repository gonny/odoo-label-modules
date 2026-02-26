{
    "name": "Label Calculator",
    "version": "19.0.1.0.0",
    "category": "Manufacturing",
    "summary": "Kalkulace cen gravírovaných štítků a textilních etiket",
    "description": """
        Modul pro kalkulaci cen na základě:
        - Materiálu (plošný m², stuha bm, TTR páska, komponenty)
        - Množstevních hladin (úspory z rozsahu)
        - Amortizace strojů
        - Konfigurovatelných marží a přirážek
    """,
    "author": "Jan Šnobl",
    "website": "https://etiketou.cz",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "sale_management",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/default_data.xml",
        "views/label_machine_views.xml",
        "views/label_material_group_views.xml",
        "views/label_material_views.xml",
        "views/label_production_tier_views.xml",
        "views/product_template_views.xml",
        "views/sale_order_line_views.xml",
        "views/account_move_views.xml",
        "views/partner_discount_tier_views.xml",
        "views/res_partner_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
