from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

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
    label_vat_surcharge_pct = fields.Float(
        string="DPH přirážka (%)",
        config_parameter="label_calc.vat_surcharge_pct",
        default=21,
    )
    label_default_material_margin_pct = fields.Float(
        string="Výchozí marže na materiál (%)",
        config_parameter="label_calc.material_margin_pct",
        default=30,
        help="Použije se, pokud tier ani skupina nemají vlastní marži",
    )
    label_min_order_price = fields.Float(
        string="Minimální cena zakázky (Kč)",
        config_parameter="label_calc.min_order_price",
        default=250,
    )
