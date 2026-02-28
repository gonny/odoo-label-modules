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

    def action_open_pickup_widget(self):
        """Open carrier-specific pickup point selection widget in new tab.

        LIMITATION: This opens the widget in a new browser tab. The user must
        manually copy the pickup point ID back to Odoo. A future enhancement
        will implement an OWL component with iframe + postMessage to auto-fill
        the pickup point fields.
        """
        self.ensure_one()
        urls = {
            "packeta": "https://widget.packeta.com/v6/",
            "dpd": "https://pickup.dpd.cz",
            "czech_post": "https://b2c.cpost.cz/locations/?type=BALIKOVNY",
        }
        carrier = self.label_preferred_carrier
        url = urls.get(carrier)
        if not url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Chyba",
                    "message": "Nejprve vyberte dopravce.",
                    "type": "warning",
                    "sticky": False,
                },
            }
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }
