from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestLabelShipment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """Set up test data for shipment tests."""
        super().setUpClass()
        # Create a customer
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Customer",
                "email": "test@example.com",
                "phone": "+420123456789",
            }
        )
        # Create delivery address with carrier info (PUDO)
        cls.delivery_pudo = cls.env["res.partner"].create(
            {
                "name": "Test Delivery PUDO",
                "type": "delivery",
                "parent_id": cls.partner.id,
                "email": "pudo@example.com",
                "phone": "+420111222333",
                "label_preferred_carrier": "packeta",
                "label_pickup_point_id": "12345",
                "label_pickup_point_name": "Packeta Z-Box Praha",
            }
        )
        # Create delivery address for home delivery (no pickup point)
        cls.delivery_hd = cls.env["res.partner"].create(
            {
                "name": "Test Delivery HD",
                "type": "delivery",
                "parent_id": cls.partner.id,
                "email": "hd@example.com",
                "phone": "+420444555666",
                "street": "Hlavní 1",
                "city": "Praha",
                "zip": "110 00",
                "label_preferred_carrier": "packeta",
                "label_carrier_service_code": "106",
            }
        )

    def _create_sale_order(self, shipping_addr=None):
        """Helper to create a sale order with a product."""
        product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 100,
            }
        )
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_shipping_id": (shipping_addr or self.delivery_pudo).id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )

    # ── Phase 1: Delivery address fields ──────────────────────────

    def test_delivery_address_carrier_fields(self):
        """Test that carrier fields are properly set on delivery address."""
        self.assertEqual(
            self.delivery_pudo.label_preferred_carrier,
            "packeta",
        )
        self.assertEqual(
            self.delivery_pudo.label_pickup_point_id,
            "12345",
        )
        self.assertEqual(
            self.delivery_pudo.label_pickup_point_name,
            "Packeta Z-Box Praha",
        )

    def test_delivery_address_service_code(self):
        """Test carrier service code on home delivery address."""
        self.assertEqual(
            self.delivery_hd.label_carrier_service_code,
            "106",
        )
        # No pickup point → home delivery
        self.assertFalse(self.delivery_hd.label_pickup_point_id)

    def test_multiple_delivery_addresses(self):
        """Test multiple delivery addresses with different carriers."""
        addr_dpd = self.env["res.partner"].create(
            {
                "name": "DPD Delivery",
                "type": "delivery",
                "parent_id": self.partner.id,
                "label_preferred_carrier": "dpd",
                "label_carrier_service_code": "337",
            }
        )
        self.assertEqual(addr_dpd.label_preferred_carrier, "dpd")
        self.assertEqual(
            self.delivery_pudo.label_preferred_carrier,
            "packeta",
        )

    def test_pickup_point_fields_persist(self):
        """Test that pickup point fields on delivery address persist."""
        addr = self.env["res.partner"].create(
            {
                "name": "Test Persist",
                "type": "delivery",
                "parent_id": self.partner.id,
                "label_preferred_carrier": "packeta",
                "label_pickup_point_id": "99999",
                "label_pickup_point_name": "Test Point",
            }
        )
        addr.invalidate_recordset()
        addr_reloaded = self.env["res.partner"].browse(addr.id)
        self.assertEqual(addr_reloaded.label_pickup_point_id, "99999")
        self.assertEqual(addr_reloaded.label_pickup_point_name, "Test Point")

    # ── Shipment creation and fields ──────────────────────────────

    def test_shipment_creation(self):
        """Test creating a shipment record linked to sale order."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
                "pickup_point_id": "12345",
                "pickup_point_name": "Packeta Z-Box Praha",
            }
        )
        self.assertEqual(shipment.state, "draft")
        self.assertEqual(shipment.weight, 0.5)
        self.assertEqual(shipment.partner_id, self.partner)
        self.assertEqual(
            shipment.partner_shipping_id,
            self.delivery_pudo,
        )
        self.assertTrue(shipment.name)

    def test_shipment_sequence_format(self):
        """Test that shipment sequence follows ZAS/XXXXX format."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        self.assertTrue(shipment.name.startswith("ZAS/"))
        seq_part = shipment.name.replace("ZAS/", "")
        self.assertEqual(len(seq_part), 5)
        self.assertTrue(seq_part.isdigit())

    # ── State transitions ─────────────────────────────────────────

    def test_shipment_state_transitions(self):
        """Test shipment state transitions (draft → sent → delivered)."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        self.assertEqual(shipment.state, "draft")
        shipment.action_send()
        self.assertEqual(shipment.state, "sent")

    def test_shipment_cancel_from_draft(self):
        """Test cancelling a shipment from draft state."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        shipment.action_cancel()
        self.assertEqual(shipment.state, "cancelled")

    def test_shipment_cancel_from_sent(self):
        """Test cancelling a shipment from sent state."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        shipment.action_send()
        shipment.action_cancel()
        self.assertEqual(shipment.state, "cancelled")

    def test_shipment_reset_from_cancelled(self):
        """Test reset to draft from cancelled state."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        shipment.action_cancel()
        shipment.action_reset_to_draft()
        self.assertEqual(shipment.state, "draft")

    def test_shipment_reset_from_error(self):
        """Test reset to draft from error state clears error."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        shipment.write({"state": "error", "error_message": "Test error"})
        shipment.action_reset_to_draft()
        self.assertEqual(shipment.state, "draft")
        self.assertFalse(shipment.error_message)

    # ── Tracking URL computation ──────────────────────────────────

    def test_tracking_url_packeta(self):
        """Test tracking URL computation for Packeta."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
                "tracking_number": "Z123456",
            }
        )
        self.assertIn("Z123456", shipment.tracking_url)
        self.assertIn("tracking.packeta.com", shipment.tracking_url)

    def test_tracking_url_dpd(self):
        """Test tracking URL computation for DPD."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
                "tracking_number": "DPD999",
            }
        )
        self.assertIn("DPD999", shipment.tracking_url)
        self.assertIn("tracking.dpd.de", shipment.tracking_url)

    def test_tracking_url_empty_when_no_number(self):
        """Test tracking URL is empty when no tracking number."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        self.assertFalse(shipment.tracking_url)

    # ── Sale order integration ────────────────────────────────────

    def test_shipment_count_on_sale_order(self):
        """Test shipment count computation on sale order."""
        so = self._create_sale_order()
        self.assertEqual(so.label_shipment_count, 0)
        self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        so.invalidate_recordset()
        self.assertEqual(so.label_shipment_count, 1)

    def test_sale_order_carrier_related_fields(self):
        """Test that sale order reads carrier info from shipping address."""
        so = self._create_sale_order()
        self.assertEqual(so.label_shipping_carrier, "packeta")

    def test_action_create_shipment(self):
        """Test that action_create_shipment returns correct context."""
        so = self._create_sale_order()
        action = so.action_create_shipment()
        self.assertEqual(action["res_model"], "label.shipment")
        self.assertEqual(action["view_mode"], "form")
        ctx = action["context"]
        self.assertEqual(ctx["default_sale_order_id"], so.id)
        self.assertEqual(ctx["default_carrier_type"], "packeta")
        self.assertEqual(ctx["default_pickup_point_id"], "12345")
        self.assertEqual(ctx["default_weight"], 0.5)

    def test_action_create_shipment_hd(self):
        """Test create shipment for home delivery address."""
        so = self._create_sale_order(shipping_addr=self.delivery_hd)
        action = so.action_create_shipment()
        ctx = action["context"]
        self.assertEqual(ctx["default_carrier_service_code"], "106")
        self.assertFalse(ctx.get("default_pickup_point_id"))

    def test_action_create_shipment_no_carrier(self):
        """Test action_create_shipment defaults to packeta."""
        addr_no_carrier = self.env["res.partner"].create(
            {
                "name": "No Carrier",
                "type": "delivery",
                "parent_id": self.partner.id,
            }
        )
        so = self._create_sale_order(shipping_addr=addr_no_carrier)
        action = so.action_create_shipment()
        self.assertEqual(
            action["context"]["default_carrier_type"],
            "packeta",
        )

    def test_action_view_shipments(self):
        """Test view shipments action from sale order."""
        so = self._create_sale_order()
        self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        so.invalidate_recordset()
        action = so.action_view_shipments()
        self.assertEqual(action["res_model"], "label.shipment")
        self.assertEqual(action["view_mode"], "list,form")

    def test_action_view_shipments_single(self):
        """Test view shipments opens form when only one shipment."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        so.invalidate_recordset()
        action = so.action_view_shipments()
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["res_id"], shipment.id)

    # ── Packeta API mocked ────────────────────────────────────────

    def test_api_send_packeta_pudo_mocked(self):
        """Test Packeta PUDO API send with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
                "pickup_point_id": "12345",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api.create_packet"
        ) as mock_create:
            mock_create.return_value = (
                True,
                {
                    "id": "4376064580",
                    "barcode": "Z4376064580",
                    "barcodeText": "Z 437 6064 580",
                },
            )
            shipment.action_api_send()
        self.assertEqual(shipment.state, "sent")
        self.assertEqual(shipment.carrier_packet_id, "4376064580")
        self.assertEqual(shipment.tracking_number, "Z4376064580")

    def test_api_send_packeta_hd_mocked(self):
        """Test Packeta home delivery API send with mocked response."""
        so = self._create_sale_order(shipping_addr=self.delivery_hd)
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
                "carrier_service_code": "106",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api.create_packet"
        ) as mock_create:
            mock_create.return_value = (
                True,
                {
                    "id": "4376064581",
                    "barcode": "Z4376064581",
                    "barcodeText": "Z 437 6064 581",
                },
            )
            shipment.action_api_send()
        self.assertEqual(shipment.state, "sent")
        self.assertEqual(shipment.carrier_packet_id, "4376064581")
        # Verify no pickup_point was passed (HD)
        self.assertFalse(shipment.pickup_point_id)

    def test_api_send_packeta_error(self):
        """Test Packeta API error response sets error state."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
                "pickup_point_id": "12345",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_password", "wrong_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api.create_packet"
        ) as mock_create:
            mock_create.return_value = (False, "Unauthorized API password")
            shipment.action_api_send()
        self.assertEqual(shipment.state, "error")
        self.assertIn("Unauthorized", shipment.error_message)

    def test_download_label_packeta_mocked(self):
        """Test Packeta label download with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
                "carrier_packet_id": "4376064580",
                "tracking_number": "Z4376064580",
                "state": "sent",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api" ".get_packet_label"
        ) as mock_label:
            mock_label.return_value = (True, b"%PDF-1.4 fake content")
            shipment.action_download_label()
        self.assertTrue(shipment.label_pdf)
        self.assertEqual(
            shipment.label_pdf_filename,
            f"label_{shipment.name}.pdf",
        )

    def test_api_cancel_packeta_mocked(self):
        """Test Packeta cancel with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
                "carrier_packet_id": "4376064580",
                "tracking_number": "Z4376064580",
                "state": "sent",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api.cancel_packet"
        ) as mock_cancel:
            mock_cancel.return_value = (True, {})
            shipment.action_api_cancel()
        self.assertEqual(shipment.state, "cancelled")

    # ── DPD API mocked ────────────────────────────────────────────

    def test_api_send_dpd_mocked(self):
        """Test DPD API send with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.create_shipment"
        ) as mock_create:
            mock_create.return_value = (
                True,
                {
                    "shipmentId": "SH123",
                    "parcels": [
                        {
                            "parcelIdent": "PI456",
                            "parcelNumber": "DPD123456",
                        }
                    ],
                },
            )
            shipment.action_api_send()
        self.assertEqual(shipment.state, "sent")
        self.assertEqual(shipment.carrier_packet_id, "PI456")
        self.assertEqual(shipment.tracking_number, "DPD123456")

    def test_api_send_dpd_error(self):
        """Test DPD API error response sets error state."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.create_shipment"
        ) as mock_create:
            mock_create.return_value = (False, "Invalid API key")
            shipment.action_api_send()
        self.assertEqual(shipment.state, "error")
        self.assertIn("Invalid API key", shipment.error_message)

    def test_download_label_dpd_mocked(self):
        """Test DPD label download with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
                "carrier_packet_id": "PI456",
                "tracking_number": "DPD123",
                "state": "sent",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.get_labels"
        ) as mock_label:
            mock_label.return_value = (True, b"%PDF-1.4 dpd label")
            shipment.action_download_label()
        self.assertTrue(shipment.label_pdf)

    def test_api_cancel_dpd_mocked(self):
        """Test DPD cancel with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
                "carrier_packet_id": "PI456",
                "tracking_number": "DPD123",
                "state": "sent",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.cancel_shipment"
        ) as mock_cancel:
            mock_cancel.return_value = (True, {"status": "cancelled"})
            shipment.action_api_cancel()
        self.assertEqual(shipment.state, "cancelled")

    # ── Error handling ────────────────────────────────────────────

    def test_api_send_error_no_keys(self):
        """Test API send fails when no keys configured."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_password", "")
        shipment.action_api_send()
        self.assertEqual(shipment.state, "error")
        self.assertTrue(shipment.error_message)

    def test_download_label_no_carrier_packet_id(self):
        """Test label download fails when no carrier packet ID."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        shipment.action_download_label()
        self.assertTrue(shipment.error_message)

    def test_api_cancel_no_carrier_packet_id(self):
        """Test cancel without carrier_packet_id just sets cancelled."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        shipment.action_api_cancel()
        self.assertEqual(shipment.state, "cancelled")

    # ── DPD test mode ─────────────────────────────────────────────

    def test_dpd_test_mode_enabled(self):
        """Test DPD test mode config parameter enabled."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_test_mode", "True")
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        params = shipment._get_carrier_api_params()
        self.assertTrue(params["test_mode"])

    def test_dpd_test_mode_disabled(self):
        """Test DPD test mode config parameter disabled."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_test_mode", "False")
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        params = shipment._get_carrier_api_params()
        self.assertFalse(params["test_mode"])

    # ── DPD array payload ─────────────────────────────────────────

    def test_dpd_api_sends_array_payload(self):
        """Test that DPD create_shipment wraps payload in an array."""
        from unittest.mock import MagicMock

        from odoo.addons.label_shipping.services import dpd_api

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.requests.post"
        ) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "shipmentId": "SH1",
                    "parcels": [{"parcelIdent": "P1", "parcelNumber": "N1"}],
                }
            ]
            mock_response.text = "[]"
            mock_post.return_value = mock_response

            success, result = dpd_api.create_shipment(
                "key",
                "dsw",
                {"parcels": [{"weight": 500}]},
            )
            # Verify the json= arg was an array (list)
            call_kwargs = mock_post.call_args
            json_body = call_kwargs.kwargs.get(
                "json",
                call_kwargs[1].get("json"),
            )
            self.assertIsInstance(json_body, list)
            self.assertEqual(len(json_body), 1)
            self.assertTrue(success)

    def test_dpd_api_unwraps_array_response(self):
        """Test that DPD create_shipment unwraps array response."""
        from unittest.mock import MagicMock

        from odoo.addons.label_shipping.services import dpd_api

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.requests.post"
        ) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "shipmentId": "SH99",
                    "parcels": [{"parcelIdent": "P99", "parcelNumber": "N99"}],
                }
            ]
            mock_response.text = "[]"
            mock_post.return_value = mock_response

            success, result = dpd_api.create_shipment(
                "key",
                "dsw",
                {"parcels": [{"weight": 500}]},
            )
            self.assertTrue(success)
            # Result should be the unwrapped first element, not array
            self.assertIsInstance(result, dict)
            self.assertEqual(result["shipmentId"], "SH99")

    # ── Packeta field validation ──────────────────────────────────

    def test_packeta_validation_missing_email(self):
        """Test Packeta validation catches missing email."""
        addr = self.env["res.partner"].create(
            {
                "name": "No Email",
                "type": "delivery",
                "parent_id": self.partner.id,
                "label_preferred_carrier": "packeta",
                "label_pickup_point_id": "12345",
            }
        )
        so = self._create_sale_order(shipping_addr=addr)
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
                "pickup_point_id": "12345",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")
        shipment.action_api_send()
        self.assertEqual(shipment.state, "error")
        self.assertIn("email", shipment.error_message)

    def test_packeta_validation_hd_missing_address(self):
        """Test Packeta HD validation catches missing address fields."""
        addr = self.env["res.partner"].create(
            {
                "name": "No Address",
                "type": "delivery",
                "parent_id": self.partner.id,
                "email": "test@example.com",
                "phone": "+420123456789",
                "label_preferred_carrier": "packeta",
            }
        )
        so = self._create_sale_order(shipping_addr=addr)
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "packeta",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")
        shipment.action_api_send()
        self.assertEqual(shipment.state, "error")
        self.assertIn("kód služby", shipment.error_message)

    # ── DPD payload structure ─────────────────────────────────────

    def test_dpd_payload_has_shipment_type(self):
        """Test DPD payload includes shipmentType field."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")
        data = shipment._prepare_dpd_data()
        self.assertEqual(data["shipmentType"], "Standard")

    def test_dpd_payload_has_sender_contact(self):
        """Test DPD payload includes sender contact section."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create(
            {
                "sale_order_id": so.id,
                "carrier_type": "dpd",
            }
        )
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")
        data = shipment._prepare_dpd_data()
        self.assertIn("contact", data["sender"])
        self.assertIn("name", data["sender"]["contact"])
        self.assertIn("phone", data["sender"]["contact"])
        self.assertIn("email", data["sender"]["contact"])

    # ── Onchange sale_order_id ────────────────────────────────────

    def test_onchange_sale_order_id_fills_carrier(self):
        """Test that selecting a sale order auto-fills carrier info."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].new(
            {
                "carrier_type": "dpd",
            }
        )
        shipment.sale_order_id = so
        shipment._onchange_sale_order_id()
        self.assertEqual(shipment.carrier_type, "packeta")
        self.assertEqual(shipment.pickup_point_id, "12345")
        self.assertEqual(
            shipment.pickup_point_name,
            "Packeta Z-Box Praha",
        )

    def test_onchange_sale_order_id_hd(self):
        """Test onchange fills carrier service code for HD."""
        so = self._create_sale_order(shipping_addr=self.delivery_hd)
        shipment = self.env["label.shipment"].new(
            {
                "carrier_type": "dpd",
            }
        )
        shipment.sale_order_id = so
        shipment._onchange_sale_order_id()
        self.assertEqual(shipment.carrier_type, "packeta")
        self.assertEqual(shipment.carrier_service_code, "106")
