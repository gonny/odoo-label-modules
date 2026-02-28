from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    label_preferred_carrier = fields.Selection(
        selection=[
            ("none", "Žádný"),
            ("packeta", "Packeta"),
            ("dpd", "DPD"),
            ("czech_post", "Česká pošta"),
        ],
        default="none",
        string="Preferovaný dopravce",
        help="Výchozí dopravce pro tuto doručovací adresu.",
    )
    label_carrier_service = fields.Char(
        string="Služba dopravce",
        help="Např. Z-Box, Na adresu, DPD Classic.",
    )
    label_pickup_point_id = fields.Char(
        string="ID výdejního místa",
        help="Identifikátor výdejního místa z widgetu dopravce.",
    )
    label_pickup_point_name = fields.Char(
        string="Název výdejního místa",
        help="Lidsky čitelný název výdejního místa.",
    )
