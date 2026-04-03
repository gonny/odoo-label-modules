from odoo import fields, models


class LabelMaterialTierOverride(models.Model):
    _name = "label.material.tier.override"
    _description = "Přetížení hladiny pro konkrétní materiál"
    _order = "material_id, tier_id"

    material_id = fields.Many2one(
        "label.material",
        string="Materiál",
        required=True,
        ondelete="cascade",
    )
    tier_id = fields.Many2one(
        "label.production.tier",
        string="Hladina",
        required=True,
        ondelete="cascade",
    )
    pieces_per_hour_override = fields.Float(
        string="Výkon (ks/hod) – přetížení",
        required=True,
        help="Přepíše výkon z hladiny pro tento konkrétní materiál",
    )
