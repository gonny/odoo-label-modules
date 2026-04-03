from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    label_hourly_rate = fields.Float(
        string="Hodinová sazba",
        config_parameter="label_calc.hourly_rate",
        default=800,
    )

    label_admin_overhead_enabled = fields.Boolean(
        string="Započítat admin overhead",
        config_parameter="label_calc.admin_overhead_enabled",
        default=False,
    )

    label_admin_overhead_minutes = fields.Float(
        string="Admin overhead na zakázku",
        config_parameter="label_calc.admin_overhead_minutes",
        default=15,
    )

    label_amortization_enabled = fields.Boolean(
        string="Započítat amortizaci strojů",
        config_parameter="label_calc.amortization_enabled",
        default=True,
    )

    label_fixed_costs_enabled = fields.Boolean(
        string="Započítat fixní náklady do sazby",
        config_parameter="label_calc.fixed_costs_enabled",
        default=True,
    )

    label_fixed_rent_yearly = fields.Float(
        string="Pronájem / servis",
        config_parameter="label_calc.fixed_rent_yearly",
        default=0,
    )

    label_fixed_energy_yearly = fields.Float(
        string="Elektřina / topení",
        config_parameter="label_calc.fixed_energy_yearly",
        default=0,
    )

    label_fixed_other_yearly = fields.Float(
        string="Ostatní provozní náklady",
        config_parameter="label_calc.fixed_other_yearly",
        default=0,
    )

    label_working_hours_yearly = fields.Float(
        string="Pracovních hodin za rok",
        config_parameter="label_calc.working_hours_yearly",
        default=2000,
    )

    label_vat_surcharge_pct = fields.Float(
        string="Daň z příjmu",
        config_parameter="label_calc.vat_surcharge_pct",
        default=15,
    )

    label_default_material_margin_pct = fields.Float(
        string="Výchozí marže na materiál",
        config_parameter="label_calc.material_margin_pct",
        default=30,
    )

    label_min_order_price = fields.Float(
        string="Min. cena zakázky",
        config_parameter="label_calc.min_order_price",
        default=250,
    )

    label_min_order_quantity = fields.Integer(
        string="Min. objednávané množství",
        config_parameter="label_calc.min_order_quantity",
        default=50,
    )
