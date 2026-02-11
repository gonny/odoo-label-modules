from odoo import models, fields


class PartnerDiscountTier(models.Model):
    _name = "partner.discount.tier"
    _description = "Slevová hladina zákazníka"
    _order = "min_spent asc"

    name = fields.Char(
        string="Název",
        required=True,
        help="Např. Bronze, Silver, Gold",
    )
    sequence = fields.Integer(
        default=10,
    )
    min_spent = fields.Float(
        string="Min. útrata (Kč)",
        required=True,
        help="Minimální celková útrata zákazníka pro tuto hladinu.",
    )
    discount_pct = fields.Float(
        string="Sleva (%)",
        required=True,
        help="Sleva v procentech, která se aplikuje na objednávku.",
    )
    active = fields.Boolean(
        default=True,
    )
    color = fields.Char(
        string="Barva štítku",
        help="Volitelná barva pro vizuální rozlišení (hex kód).",
    )
