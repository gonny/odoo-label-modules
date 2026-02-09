# models/account_move_line_ext.py

from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    label_material_id = fields.Many2one(
        "label.material",
        string="Varianta",
        readonly=True,
    )
    label_width_mm = fields.Float(
        string="Šířka (mm)",
        readonly=True,
    )
    label_height_mm = fields.Float(
        string="Výška/Délka (mm)",
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
