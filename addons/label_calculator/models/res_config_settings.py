from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # === Práce ===
    label_hourly_rate = fields.Float(
        string="Hodinová sazba (Kč)",
        config_parameter="label_calc.hourly_rate",
        default=800,
        help="Tvoje požadovaná hodinová sazba (hrubá)",
    )
    label_admin_overhead_minutes = fields.Float(
        string="Admin overhead na zakázku (min)",
        config_parameter="label_calc.admin_overhead_minutes",
        default=15,
        help="Čas na komunikaci, fakturaci, balení, cestu na poštu per objednávka",
    )

    # === Marže a přirážky ===
    label_vat_surcharge_pct = fields.Float(
        string="DPH přirážka (%)",
        config_parameter="label_calc.vat_surcharge_pct",
        default=21,
        help="Přirážka za DPH (neplátce – nakupuješ s DPH)",
    )
    label_material_margin_pct = fields.Float(
        string="Marže na materiál (%)",
        config_parameter="label_calc.material_margin_pct",
        default=30,
    )
    label_min_order_price = fields.Float(
        string="Minimální cena zakázky (Kč)",
        config_parameter="label_calc.min_order_price",
        default=250,
        help="Pod touto cenou se zakázka nevyplatí",
    )
