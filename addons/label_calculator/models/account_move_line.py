from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    label_material_id = fields.Many2one(
        "label.material",
        string="Varianta",
        readonly=True,
    )
    label_width_mm = fields.Float(
        string="Šířka (mm)",
        digits=(8, 1),
        readonly=True,
    )
    label_height_mm = fields.Float(
        string="Výška/Délka (mm)",
        digits=(8, 1),
        readonly=True,
    )
    label_material_cost_only = fields.Float(
        string="Náklad materiálu/ks",
        digits=(12, 4),
        readonly=True,
    )
    label_price_breakdown = fields.Text(
        string="Rozpad ceny",
        readonly=True,
    )
