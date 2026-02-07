from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # === Práce ===
    label_hourly_rate = fields.Float(
        string="Hodinová sazba (Kč)",
        config_parameter="label_calc.hourly_rate",
        default=800,
    )
    label_admin_overhead_minutes = fields.Float(
        string="Admin overhead na zakázku (min)",
        config_parameter="label_calc.admin_overhead_minutes",
        default=15,
    )

    # === Fixní náklady ===
    label_fixed_rent_yearly = fields.Float(
        string="Pronájem (Kč/rok)",
        config_parameter="label_calc.fixed_rent_yearly",
        default=0,
    )
    label_fixed_energy_yearly = fields.Float(
        string="Elektřina (Kč/rok)",
        config_parameter="label_calc.fixed_energy_yearly",
        default=0,
    )
    label_fixed_other_yearly = fields.Float(
        string="Ostatní provozní náklady (Kč/rok)",
        config_parameter="label_calc.fixed_other_yearly",
        default=0,
    )
    label_working_hours_yearly = fields.Float(
        string="Pracovních hodin za rok",
        config_parameter="label_calc.working_hours_yearly",
        default=2000,
    )

    # === Marže a přirážky ===
    label_vat_surcharge_pct = fields.Float(
        string="DPH přirážka (%)",
        config_parameter="label_calc.vat_surcharge_pct",
        default=21,
    )
    label_default_material_margin_pct = fields.Float(
        string="Výchozí marže na materiál (%)",
        config_parameter="label_calc.material_margin_pct",
        default=30,
    )

    # === Minima (varování, NE blocker) ===
    label_min_order_price = fields.Float(
        string="Min. cena zakázky (Kč)",
        config_parameter="label_calc.min_order_price",
        default=250,
    )
    label_min_order_quantity = fields.Integer(
        string="Min. objednávané množství (ks)",
        config_parameter="label_calc.min_order_quantity",
        default=50,
    )
