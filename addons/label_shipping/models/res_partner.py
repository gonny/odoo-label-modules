from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    label_preferred_carrier = fields.Selection(
        selection=[
            ("none", "Žádný"),
            ("packeta", "Packeta"),
            ("dpd", "DPD"),
        ],
        default="none",
        string="Preferovaný dopravce",
        help="Výchozí dopravce pro tuto doručovací adresu.",
    )
    label_carrier_service_code = fields.Char(
        string="Kód služby dopravce",
        help=(
            "Kód služby dopravce. Pro Packeta HD: ID přepravce."
            " Pro DPD: kód služby."
        ),
    )
    label_pickup_point_id = fields.Char(
        string="ID výdejního místa",
        help="Identifikátor výdejního místa z widgetu dopravce.",
    )
    label_pickup_point_name = fields.Char(
        string="Název výdejního místa",
        help="Lidsky čitelný název výdejního místa.",
    )
