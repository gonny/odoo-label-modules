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

    def _get_carrier_api_params(self):
        """Read carrier API keys from ir.config_parameter.

        Returns:
            Dict with API keys for the current carrier_type.
        """
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        if self.carrier_type == "packeta":
            return {
                "api_key": ICP.get_param(
                    "label_shipping.packeta_api_key", "",
                ),
                "api_password": ICP.get_param(
                    "label_shipping.packeta_api_password", "",
                ),
            }
        elif self.carrier_type == "dpd":
            return {
                "api_key": ICP.get_param(
                    "label_shipping.dpd_api_key", "",
                ),
                "dsw": ICP.get_param("label_shipping.dpd_api_dsw", ""),
                "test_mode": ICP.get_param(
                    "label_shipping.dpd_test_mode", "True",
                ) in ("True", "1"),
            }
        elif self.carrier_type == "czech_post":
            return {
                "api_key": ICP.get_param(
                    "label_shipping.czech_post_api_key", "",
                ),
                "secret_key": ICP.get_param(
                    "label_shipping.czech_post_secret_key", "",
                ),
            }
        return {}

    def _prepare_packeta_data(self):
        """Prepare payload for Packeta API create packet call.

        Returns:
            Dict with packet data for Packeta API.
        """
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_id
        name_parts = (partner.name or "").split(" ", 1)
        return {
            "number": self.name,
            "name": name_parts[0] if name_parts else "",
            "surname": name_parts[1] if len(name_parts) > 1 else "",
            "email": partner.email or "",
            "phone": partner.phone or "",
            "addressId": (
                int(self.pickup_point_id)
                if self.pickup_point_id
                and self.pickup_point_id.strip().isdigit()
                else 0
            ),
            "value": self.sale_order_id.amount_total or 0,
            "weight": self.weight,
            "eshop": self.env.company.name or "Odoo",
        }

    def _prepare_dpd_data(self):
        """Prepare payload for DPD GeoAPI create shipment call.

        Returns:
            Dict with shipment data for DPD API.
        """
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_id
        company = self.env.company
        return {
            "sender": {
                "address": {
                    "street": company.street or "",
                    "city": company.city or "",
                    "zipCode": (company.zip or "").replace(" ", ""),
                    "countryCode": (
                        company.country_id.code
                        if company.country_id
                        else "CZ"
                    ),
                },
            },
            "receiver": {
                "address": {
                    "street": partner.street or "",
                    "city": partner.city or "",
                    "zipCode": (partner.zip or "").replace(" ", ""),
                    "countryCode": (
                        partner.country_id.code
                        if partner.country_id
                        else "CZ"
                    ),
                },
                "contact": {
                    "name": partner.name or "",
                    "phone": partner.phone or "",
                    "email": partner.email or "",
                },
            },
            "parcels": [
                {"weight": self.weight},
            ],
            "services": ["classic"],
        }

    def _prepare_czech_post_data(self):
        """Prepare payload for Czech Post B2B API create shipment call.

        Returns:
            Dict with shipment data for Czech Post API.
        """
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_id
        return {
            "recipientName": partner.name or "",
            "recipientStreet": partner.street or "",
            "recipientCity": partner.city or "",
            "recipientZipCode": (partner.zip or "").replace(" ", ""),
            "recipientCountryCode": (
                partner.country_id.code
                if partner.country_id
                else "CZ"
            ),
            "recipientPhone": partner.phone or "",
            "recipientEmail": partner.email or "",
            "weight": self.weight,
            "value": self.sale_order_id.amount_total or 0,
            "pickupPointId": self.pickup_point_id or "",
        }

    def action_api_send(self):
        """Send shipment via carrier API.

        Creates the shipment through the appropriate carrier API,
        stores the tracking number, and updates the state.
        """
        for shipment in self:
            params = shipment._get_carrier_api_params()
            if not any(params.values()):
                shipment.write({
                    "state": "error",
                    "error_message": (
                        "API klíče nejsou nastaveny."
                        " Zkontrolujte nastavení."
                    ),
                })
                continue

            success = False
            result = ""

            if shipment.carrier_type == "packeta":
                from ..services import packeta_api
                data = shipment._prepare_packeta_data()
                success, result = packeta_api.create_packet(
                    params["api_key"], params["api_password"], data,
                )
                if success and isinstance(result, dict):
                    tracking = str(
                        result.get("id", result.get("barcode", ""))
                    )
                    shipment.write({
                        "tracking_number": tracking,
                        "state": "sent",
                        "error_message": False,
                    })

            elif shipment.carrier_type == "dpd":
                from ..services import dpd_api
                data = shipment._prepare_dpd_data()
                success, result = dpd_api.create_shipment(
                    params["api_key"], params["dsw"], data,
                    test_mode=params.get("test_mode", True),
                )
                if success and isinstance(result, (dict, list)):
                    # DPD returns list of shipment results
                    res = result[0] if isinstance(result, list) else result
                    parcels = res.get("parcels", [])
                    tracking = (
                        parcels[0].get("parcelNumber", "")
                        if parcels
                        else ""
                    )
                    shipment.write({
                        "tracking_number": tracking,
                        "state": "sent",
                        "error_message": False,
                    })

            elif shipment.carrier_type == "czech_post":
                from ..services import czech_post_api
                data = shipment._prepare_czech_post_data()
                success, result = czech_post_api.create_shipment(
                    params["api_key"], params["secret_key"], data,
                )
                if success and isinstance(result, dict):
                    tracking = str(
                        result.get(
                            "trackingNumber", result.get("id", ""),
                        )
                    )
                    shipment.write({
                        "tracking_number": tracking,
                        "state": "sent",
                        "error_message": False,
                    })

            if not success:
                error_msg = (
                    result if isinstance(result, str) else str(result)
                )
                shipment.write({
                    "state": "error",
                    "error_message": error_msg,
                })

    def action_download_label(self):
        """Download shipping label PDF from carrier API."""
        for shipment in self:
            if not shipment.tracking_number:
                shipment.write({
                    "state": "error",
                    "error_message": "Zásilka nemá sledovací číslo.",
                })
                continue

            params = shipment._get_carrier_api_params()
            success = False
            result = ""

            if shipment.carrier_type == "packeta":
                from ..services import packeta_api
                success, result = packeta_api.get_packet_label(
                    params["api_key"], params["api_password"],
                    shipment.tracking_number,
                )
            elif shipment.carrier_type == "dpd":
                from ..services import dpd_api
                success, result = dpd_api.get_labels(
                    params["api_key"], [shipment.tracking_number],
                    test_mode=params.get("test_mode", True),
                )
            elif shipment.carrier_type == "czech_post":
                from ..services import czech_post_api
                success, result = czech_post_api.get_shipment_label(
                    params["api_key"], params["secret_key"],
                    shipment.tracking_number,
                )

            if success and isinstance(result, bytes):
                import base64
                shipment.write({
                    "label_pdf": base64.b64encode(result),
                    "label_pdf_filename": f"label_{shipment.name}.pdf",
                    "error_message": False,
                })
            elif not success:
                error_msg = (
                    result if isinstance(result, str) else str(result)
                )
                shipment.write({
                    "error_message": (
                        f"Chyba stahování štítku: {error_msg}"
                    ),
                })

    def action_api_track(self):
        """Get tracking status from carrier API."""
        for shipment in self:
            if not shipment.tracking_number:
                continue

            params = shipment._get_carrier_api_params()
            success = False
            result = ""

            if shipment.carrier_type == "packeta":
                from ..services import packeta_api
                success, result = packeta_api.get_packet_tracking(
                    params["api_key"], params["api_password"],
                    shipment.tracking_number,
                )
            elif shipment.carrier_type == "dpd":
                from ..services import dpd_api
                success, result = dpd_api.get_tracking(
                    params["api_key"], shipment.tracking_number,
                    test_mode=params.get("test_mode", True),
                )
            elif shipment.carrier_type == "czech_post":
                from ..services import czech_post_api
                success, result = czech_post_api.get_shipment_tracking(
                    params["api_key"], params["secret_key"],
                    shipment.tracking_number,
                )

            if success and isinstance(result, dict):
                # Try to determine delivery status from tracking data
                status = str(
                    result.get("statusCode", result.get("status", ""))
                ).lower()
                if status in ("delivered", "doručeno", "5"):
                    shipment.state = "delivered"
                elif status in ("in_transit", "na_ceste", "2", "3", "4"):
                    shipment.state = "in_transit"
                shipment.error_message = False
            elif not success:
                error_msg = (
                    result if isinstance(result, str) else str(result)
                )
                shipment.error_message = (
                    f"Chyba sledování: {error_msg}"
                )

    def action_api_cancel(self):
        """Cancel shipment via carrier API."""
        for shipment in self:
            if not shipment.tracking_number:
                shipment.state = "cancelled"
                continue

            params = shipment._get_carrier_api_params()
            success = False
            result = ""

            if shipment.carrier_type == "packeta":
                from ..services import packeta_api
                success, result = packeta_api.cancel_packet(
                    params["api_key"], params["api_password"],
                    shipment.tracking_number,
                )
            elif shipment.carrier_type == "dpd":
                from ..services import dpd_api
                success, result = dpd_api.cancel_shipment(
                    params["api_key"], shipment.tracking_number,
                    test_mode=params.get("test_mode", True),
                )
            elif shipment.carrier_type == "czech_post":
                from ..services import czech_post_api
                success, result = czech_post_api.cancel_shipment(
                    params["api_key"], params["secret_key"],
                    shipment.tracking_number,
                )

            if success:
                shipment.write({
                    "state": "cancelled",
                    "error_message": False,
                })
            else:
                error_msg = (
                    result if isinstance(result, str) else str(result)
                )
                shipment.write({
                    "state": "error",
                    "error_message": f"Chyba rušení: {error_msg}",
                })
