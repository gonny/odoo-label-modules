import base64

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
        ],
        string="Dopravce",
        required=True,
    )
    carrier_service_code = fields.Char(
        string="Kód služby",
        help="Kód služby dopravce (Packeta carrier ID, DPD service code).",
    )
    carrier_packet_id = fields.Char(
        string="ID zásilky u dopravce",
        readonly=True,
        help="Interní ID zásilky u dopravce (pro stahování štítků a rušení).",
    )
    tracking_number = fields.Char(
        string="Sledovací číslo",
        readonly=True,
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
        readonly=True,
        help="PDF štítek vygenerovaný přes API dopravce.",
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
            "https://tracking.dpd.de/status/cs_CZ/parcel/{number}"
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
        """Označit zásilku jako odesláno (ruční, bez API)."""
        for shipment in self:
            shipment.state = "sent"

    def action_cancel(self):
        """Zrušit zásilku – nastaví stav na 'cancelled'."""
        for shipment in self:
            shipment.state = "cancelled"

    def action_reset_to_draft(self):
        """Vrátit zásilku do konceptu."""
        for shipment in self:
            shipment.state = "draft"
            shipment.error_message = False

    def _get_carrier_api_params(self):
        """Read carrier API keys from ir.config_parameter.

        Returns:
            Dict with API keys for the current carrier_type.
        """
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        if self.carrier_type == "packeta":
            return {
                "api_password": ICP.get_param(
                    "label_shipping.packeta_api_password", "",
                ),
                "indication": ICP.get_param(
                    "label_shipping.packeta_indication",
                    "Vylaď to etiketou",
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
        return {}

    def _prepare_packeta_data(self):
        """Prepare payload dict for Packeta XML API createPacket call.

        Returns:
            Dict with packet attributes for XML builder.
        """
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_id
        name_parts = (partner.name or "").split(" ", 1)
        params = self._get_carrier_api_params()
        data = {
            "number": self.sale_order_id.name or self.name,
            "name": name_parts[0] if name_parts else "",
            "surname": name_parts[1] if len(name_parts) > 1 else "",
            "company": partner.commercial_company_name or "",
            "email": partner.email or "",
            "phone": partner.phone or "",
            "value": self.sale_order_id.amount_total or 0,
            "currency": "CZK",
            "weight": self.weight,
            "eshop": params.get("indication", "Vylaď to etiketou"),
        }
        # For home delivery add address fields
        if not self.pickup_point_id:
            data["carrier_service_code"] = self.carrier_service_code or ""
            data["street"] = partner.street or ""
            data["city"] = partner.city or ""
            data["zip"] = (partner.zip or "").replace(" ", "")
        return data

    def _prepare_dpd_data(self):
        """Prepare payload for DPD GeoAPI v1 create shipment call.

        Weight is converted from kg to grams as required by DPD API.

        Returns:
            Dict with shipment data for DPD API.
        """
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_id
        company = self.env.company
        params = self._get_carrier_api_params()
        weight_grams = round(self.weight * 1000)
        payload = {
            "customer": {"dsw": params.get("dsw", "")},
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
                {"weight": weight_grams},
            ],
        }
        # If pickup point is set, add it to parcel services
        if self.pickup_point_id:
            payload["parcels"][0]["services"] = {
                "pickupPoint": self.pickup_point_id,
            }
        return payload

    def _validate_packeta_fields(self):
        """Validate required fields for Packeta API before sending.

        Returns:
            Error message string if validation fails, or False if OK.
        """
        self.ensure_one()
        partner = self.partner_shipping_id or self.partner_id
        missing = []
        if not (partner.email or "").strip():
            missing.append("email")
        if not (partner.phone or "").strip():
            missing.append("telefon")
        if not (partner.name or "").strip():
            missing.append("jméno příjemce")
        if not self.pickup_point_id:
            # Home delivery requires carrier service code + address
            if not (self.carrier_service_code or "").strip():
                missing.append("kód služby dopravce (carrierId)")
            if not (partner.street or "").strip():
                missing.append("ulice")
            if not (partner.city or "").strip():
                missing.append("město")
            if not (partner.zip or "").strip():
                missing.append("PSČ")
        if missing:
            return (
                "Chybí povinné údaje pro Packeta API: "
                + ", ".join(missing) + "."
            )
        return False

    def action_api_send(self):
        """Send shipment via carrier API.

        Creates the shipment through the appropriate carrier API,
        stores the tracking number and carrier packet ID, and updates the state.
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
                validation_error = shipment._validate_packeta_fields()
                if validation_error:
                    shipment.write({
                        "state": "error",
                        "error_message": validation_error,
                    })
                    continue
                from ..services import packeta_api
                data = shipment._prepare_packeta_data()
                success, result = packeta_api.create_packet(
                    params["api_password"],
                    data,
                    pickup_point_id=shipment.pickup_point_id or None,
                )
                if success and isinstance(result, dict):
                    shipment.write({
                        "carrier_packet_id": result.get("id", ""),
                        "tracking_number": result.get("barcode", ""),
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
                if success and isinstance(result, dict):
                    # DPD response contains shipment and parcel identifiers
                    shipment_id = str(result.get("shipmentId", ""))
                    parcels = result.get("parcels", [])
                    parcel_ident = ""
                    tracking = ""
                    if parcels:
                        parcel_ident = str(
                            parcels[0].get("parcelIdent", "")
                        )
                        tracking = str(
                            parcels[0].get("parcelNumber", "")
                        )
                    shipment.write({
                        "carrier_packet_id": (
                            parcel_ident or shipment_id
                        ),
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
            if not shipment.carrier_packet_id:
                shipment.write({
                    "error_message": (
                        "Zásilka nemá ID u dopravce."
                        " Nejprve odešlete přes API."
                    ),
                })
                continue

            params = shipment._get_carrier_api_params()
            success = False
            result = ""

            if shipment.carrier_type == "packeta":
                from ..services import packeta_api
                success, result = packeta_api.get_packet_label(
                    params["api_password"],
                    shipment.carrier_packet_id,
                )
            elif shipment.carrier_type == "dpd":
                from ..services import dpd_api
                success, result = dpd_api.get_labels(
                    params["api_key"],
                    shipment.carrier_packet_id,
                    test_mode=params.get("test_mode", True),
                )

            if success and isinstance(result, bytes):
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

    def action_api_cancel(self):
        """Cancel shipment via carrier API."""
        for shipment in self:
            if not shipment.carrier_packet_id:
                shipment.state = "cancelled"
                continue

            params = shipment._get_carrier_api_params()
            success = False
            result = ""

            if shipment.carrier_type == "packeta":
                from ..services import packeta_api
                success, result = packeta_api.cancel_packet(
                    params["api_password"],
                    shipment.carrier_packet_id,
                )
            elif shipment.carrier_type == "dpd":
                from ..services import dpd_api
                success, result = dpd_api.cancel_shipment(
                    params["api_key"],
                    shipment.carrier_packet_id,
                    test_mode=params.get("test_mode", True),
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
