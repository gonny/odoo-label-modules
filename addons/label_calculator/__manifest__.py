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
    "author": "TVOJE JMENO",
    "website": "https://tvojestranka.cz",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "sale_management",
    ],
    "data": [
        # Pořadí je důležité!
        "security/ir.model.access.csv",
        "views/label_material_views.xml",
        "views/label_machine_views.xml",
        "views/label_production_tier_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu.xml",
        "data/default_data.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
