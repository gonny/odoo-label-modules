from odoo import api, fields, models


class LabelShipment(models.Model):
    _name = "label.shipment"
    _description = "Zásilka"
    _order = "create_date desc"

    name = fields.Char(
        string="Číslo zásilky",
        readonly=True,
        required=True,
        copy=False,
        default="New",
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Objednávka",
        required=True,
        ondelete="cascade",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Zákazník",
        related="sale_order_id.partner_id",
        store=True,
    )
    partner_shipping_id = fields.Many2one(
        "res.partner",
        string="Doručovací adresa",
        related="sale_order_id.partner_shipping_id",
        store=True,
    )
    carrier_type = fields.Selection(
        selection=[
            ("packeta", "Packeta"),
            ("dpd", "DPD"),
            ("czech_post", "Česká pošta"),
        ],
        string="Dopravce",
        required=True,
    )
    carrier_service = fields.Char(
        string="Služba",
    )
    tracking_number = fields.Char(
        string="Sledovací číslo",
    )
    tracking_url = fields.Char(
        string="Sledovací odkaz",
        compute="_compute_tracking_url",
        store=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Koncept"),
            ("sent", "Odesláno"),
            ("in_transit", "Na cestě"),
            ("delivered", "Doručeno"),
            ("cancelled", "Zrušeno"),
            ("error", "Chyba"),
        ],
        default="draft",
        string="Stav",
        required=True,
    )
    label_pdf = fields.Binary(
        string="Štítek PDF",
    )
    label_pdf_filename = fields.Char(
        string="Název souboru",
    )
    weight = fields.Float(
        string="Hmotnost (kg)",
        default=0.5,
    )
    error_message = fields.Text(
        string="Chybová zpráva",
    )
    pickup_point_id = fields.Char(
        string="ID výdejního místa",
    )
    pickup_point_name = fields.Char(
        string="Název výdejního místa",
    )

    _TRACKING_URL_MAP = {
        "packeta": "https://tracking.packeta.com/cs/?id={number}",
        "dpd": (
            "https://tracking.dpd.de/parcelstatus"
            "?query={number}&locale=cs_CZ"
        ),
        "czech_post": (
            "https://www.postaonline.cz/trackandtrace/-/zasilka/cislo"
            "?telecastka={number}"
        ),
    }

    @api.depends("carrier_type", "tracking_number")
    def _compute_tracking_url(self):
        """Generate tracking URL based on carrier type and tracking number."""
        for shipment in self:
            if shipment.tracking_number and shipment.carrier_type:
                template = self._TRACKING_URL_MAP.get(shipment.carrier_type)
                if template:
                    shipment.tracking_url = template.format(
                        number=shipment.tracking_number,
                    )
                else:
                    shipment.tracking_url = False
            else:
                shipment.tracking_url = False

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequence number on creation."""
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("label.shipment")
                    or "New"
                )
        return super().create(vals_list)

    def action_send(self):
        """Odeslat zásilku – nastaví stav na 'sent'."""
        for shipment in self:
            shipment.state = "sent"

    def action_in_transit(self):
        """Zásilka na cestě – nastaví stav na 'in_transit'."""
        for shipment in self:
            shipment.state = "in_transit"

    def action_deliver(self):
        """Zásilka doručena – nastaví stav na 'delivered'."""
        for shipment in self:
            shipment.state = "delivered"

    def action_cancel(self):
        """Zrušit zásilku – nastaví stav na 'cancelled'."""
        for shipment in self:
            shipment.state = "cancelled"

    def action_reset_to_draft(self):
        """Vrátit zásilku do konceptu."""
        for shipment in self:
            shipment.state = "draft"
