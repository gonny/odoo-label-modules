from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestLabelShipment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        """Set up test data for shipment tests."""
        super().setUpClass()
        # Create a customer
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Customer",
        })
        # Create delivery address with carrier info
        cls.delivery_address = cls.env["res.partner"].create({
            "name": "Test Delivery",
            "type": "delivery",
            "parent_id": cls.partner.id,
            "label_preferred_carrier": "packeta",
            "label_carrier_service": "Z-Box",
            "label_pickup_point_id": "12345",
            "label_pickup_point_name": "Packeta Z-Box Praha",
        })

    def test_delivery_address_carrier_fields(self):
        """Test that carrier fields are properly set on delivery address."""
        self.assertEqual(
            self.delivery_address.label_preferred_carrier, "packeta",
        )
        self.assertEqual(
            self.delivery_address.label_carrier_service, "Z-Box",
        )
        self.assertEqual(
            self.delivery_address.label_pickup_point_id, "12345",
        )
        self.assertEqual(
            self.delivery_address.label_pickup_point_name,
            "Packeta Z-Box Praha",
        )

    def test_multiple_delivery_addresses(self):
        """Test multiple delivery addresses with different carriers."""
        addr2 = self.env["res.partner"].create({
            "name": "DPD Delivery",
            "type": "delivery",
            "parent_id": self.partner.id,
            "label_preferred_carrier": "dpd",
            "label_carrier_service": "DPD Classic",
        })
        self.assertEqual(addr2.label_preferred_carrier, "dpd")
        self.assertEqual(
            self.delivery_address.label_preferred_carrier, "packeta",
        )

    def _create_sale_order(self):
        """Helper to create a sale order with a product."""
        product = self.env["product.product"].create({
            "name": "Test Product",
            "list_price": 100,
        })
        return self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "partner_shipping_id": self.delivery_address.id,
            "order_line": [(0, 0, {
                "product_id": product.id,
                "product_uom_qty": 1,
                "price_unit": 100,
            })],
        })

    def test_shipment_creation(self):
        """Test creating a shipment record."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
            "carrier_service": "Z-Box",
            "pickup_point_id": "12345",
            "pickup_point_name": "Packeta Z-Box Praha",
        })
        self.assertEqual(shipment.state, "draft")
        self.assertEqual(shipment.weight, 0.5)
        self.assertEqual(shipment.partner_id, self.partner)
        self.assertEqual(shipment.partner_shipping_id, self.delivery_address)
        self.assertTrue(shipment.name)  # sequence should be set

    def test_shipment_state_transitions(self):
        """Test shipment state transitions."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        self.assertEqual(shipment.state, "draft")
        shipment.action_send()
        self.assertEqual(shipment.state, "sent")
        shipment.action_in_transit()
        self.assertEqual(shipment.state, "in_transit")
        shipment.action_deliver()
        self.assertEqual(shipment.state, "delivered")

    def test_shipment_cancel_and_reset(self):
        """Test shipment cancellation and reset."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "dpd",
        })
        shipment.action_cancel()
        self.assertEqual(shipment.state, "cancelled")
        shipment.action_reset_to_draft()
        self.assertEqual(shipment.state, "draft")

    def test_tracking_url_computation(self):
        """Test tracking URL is correctly computed."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
            "tracking_number": "Z123456",
        })
        self.assertIn("Z123456", shipment.tracking_url)
        self.assertIn("packeta", shipment.tracking_url)

    def test_shipment_count_on_sale_order(self):
        """Test shipment count on sale order."""
        so = self._create_sale_order()
        self.assertEqual(so.label_shipment_count, 0)
        self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        so.invalidate_recordset()
        self.assertEqual(so.label_shipment_count, 1)

    def test_sale_order_carrier_related_fields(self):
        """Test that sale order reads carrier info from shipping address."""
        so = self._create_sale_order()
        self.assertEqual(so.label_shipping_carrier, "packeta")
        self.assertEqual(so.label_shipping_service, "Z-Box")
        self.assertEqual(
            so.label_shipping_pickup_point, "Packeta Z-Box Praha",
        )

    def test_action_create_shipment(self):
        """Test that action_create_shipment returns correct context."""
        so = self._create_sale_order()
        action = so.action_create_shipment()
        self.assertEqual(action["res_model"], "label.shipment")
        self.assertEqual(action["view_mode"], "form")
        ctx = action["context"]
        self.assertEqual(ctx["default_sale_order_id"], so.id)
        self.assertEqual(ctx["default_carrier_type"], "packeta")
        self.assertEqual(ctx["default_carrier_service"], "Z-Box")
        self.assertEqual(ctx["default_pickup_point_id"], "12345")
        self.assertEqual(
            ctx["default_pickup_point_name"], "Packeta Z-Box Praha",
        )

    def test_action_create_shipment_no_carrier(self):
        """Test action_create_shipment defaults to packeta when no carrier."""
        addr_no_carrier = self.env["res.partner"].create({
            "name": "No Carrier Delivery",
            "type": "delivery",
            "parent_id": self.partner.id,
        })
        so = self._create_sale_order()
        so.partner_shipping_id = addr_no_carrier
        action = so.action_create_shipment()
        self.assertEqual(
            action["context"]["default_carrier_type"], "packeta",
        )

    def test_shipment_sequence_format(self):
        """Test that shipment sequence follows ZAS/XXXXX format."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        self.assertTrue(shipment.name.startswith("ZAS/"))
        # Check padding: ZAS/ + 5 digits
        seq_part = shipment.name.replace("ZAS/", "")
        self.assertEqual(len(seq_part), 5)
        self.assertTrue(seq_part.isdigit())

    def test_api_send_packeta_mocked(self):
        """Test Packeta API send with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
            "pickup_point_id": "12345",
        })
        # Set API keys
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_key", "test_key")
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api.create_packet"
        ) as mock_create:
            mock_create.return_value = (True, {"id": "Z987654"})
            shipment.action_api_send()
        self.assertEqual(shipment.state, "sent")
        self.assertEqual(shipment.tracking_number, "Z987654")

    def test_api_send_dpd_mocked(self):
        """Test DPD API send with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "dpd",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.create_shipment"
        ) as mock_create:
            mock_create.return_value = (
                True, [{"parcels": [{"parcelNumber": "DPD123456"}]}],
            )
            shipment.action_api_send()
        self.assertEqual(shipment.state, "sent")
        self.assertEqual(shipment.tracking_number, "DPD123456")

    def test_api_send_czech_post_mocked(self):
        """Test Czech Post API send with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "czech_post",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.czech_post_api_key", "test_key")
        ICP.set_param("label_shipping.czech_post_secret_key", "test_secret")

        with patch(
            "odoo.addons.label_shipping.services.czech_post_api"
            ".create_shipment"
        ) as mock_create:
            mock_create.return_value = (
                True, {"trackingNumber": "CP123456"},
            )
            shipment.action_api_send()
        self.assertEqual(shipment.state, "sent")
        self.assertEqual(shipment.tracking_number, "CP123456")

    def test_api_send_error_no_keys(self):
        """Test API send fails gracefully when no keys configured."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        # Ensure keys are empty
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_key", "")
        ICP.set_param("label_shipping.packeta_api_password", "")
        shipment.action_api_send()
        self.assertEqual(shipment.state, "error")
        self.assertTrue(shipment.error_message)

    def test_api_send_error_response(self):
        """Test API send handles error response gracefully."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_key", "test_key")
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api.create_packet"
        ) as mock_create:
            mock_create.return_value = (False, "Invalid API key")
            shipment.action_api_send()
        self.assertEqual(shipment.state, "error")
        self.assertIn("Invalid API key", shipment.error_message)

    def test_download_label_mocked(self):
        """Test downloading a label PDF with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
            "tracking_number": "Z987654",
            "state": "sent",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_key", "test_key")
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api"
            ".get_packet_label"
        ) as mock_label:
            mock_label.return_value = (True, b"%PDF-1.4 fake content")
            shipment.action_download_label()
        self.assertTrue(shipment.label_pdf)
        self.assertEqual(
            shipment.label_pdf_filename, f"label_{shipment.name}.pdf",
        )

    def test_api_cancel_mocked(self):
        """Test cancelling a shipment via API with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
            "tracking_number": "Z987654",
            "state": "sent",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.packeta_api_key", "test_key")
        ICP.set_param("label_shipping.packeta_api_password", "test_pass")

        with patch(
            "odoo.addons.label_shipping.services.packeta_api.cancel_packet"
        ) as mock_cancel:
            mock_cancel.return_value = (True, {"status": "cancelled"})
            shipment.action_api_cancel()
        self.assertEqual(shipment.state, "cancelled")

    def test_action_open_pickup_widget_packeta(self):
        """Test opening Packeta pickup widget."""
        result = self.delivery_address.action_open_pickup_widget()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertIn("packeta", result["url"])
        self.assertEqual(result["target"], "new")

    def test_action_open_pickup_widget_no_carrier(self):
        """Test opening pickup widget with no carrier shows notification."""
        addr = self.env["res.partner"].create({
            "name": "No Carrier",
            "type": "delivery",
            "parent_id": self.partner.id,
            "label_preferred_carrier": "none",
        })
        result = addr.action_open_pickup_widget()
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")

    def test_action_open_pickup_widget_dpd(self):
        """Test opening DPD pickup widget."""
        addr = self.env["res.partner"].create({
            "name": "DPD Address",
            "type": "delivery",
            "parent_id": self.partner.id,
            "label_preferred_carrier": "dpd",
        })
        result = addr.action_open_pickup_widget()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertIn("dpd", result["url"])

    def test_action_open_pickup_widget_czech_post(self):
        """Test opening Czech Post pickup widget."""
        addr = self.env["res.partner"].create({
            "name": "CP Address",
            "type": "delivery",
            "parent_id": self.partner.id,
            "label_preferred_carrier": "czech_post",
        })
        result = addr.action_open_pickup_widget()
        self.assertEqual(result["type"], "ir.actions.act_url")
        self.assertIn("cpost", result["url"])

    def test_shipment_cancel_from_sent(self):
        """Test cancelling a shipment that is in 'sent' state."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        shipment.action_send()
        self.assertEqual(shipment.state, "sent")
        shipment.action_cancel()
        self.assertEqual(shipment.state, "cancelled")

    def test_shipment_reset_from_error(self):
        """Test resetting a shipment from 'error' state to 'draft'."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        shipment.write({"state": "error", "error_message": "Test error"})
        self.assertEqual(shipment.state, "error")
        shipment.action_reset_to_draft()
        self.assertEqual(shipment.state, "draft")

    def test_tracking_url_dpd(self):
        """Test tracking URL computation for DPD carrier."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "dpd",
            "tracking_number": "DPD999",
        })
        self.assertIn("DPD999", shipment.tracking_url)
        self.assertIn("dpd.de", shipment.tracking_url)

    def test_tracking_url_czech_post(self):
        """Test tracking URL computation for Czech Post carrier."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "czech_post",
            "tracking_number": "CP999",
        })
        self.assertIn("CP999", shipment.tracking_url)
        self.assertIn("postaonline", shipment.tracking_url)

    def test_tracking_url_empty_when_no_number(self):
        """Test tracking URL is empty when no tracking number."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        self.assertFalse(shipment.tracking_url)

    def test_action_view_shipments(self):
        """Test view shipments action from sale order."""
        so = self._create_sale_order()
        self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "dpd",
        })
        so.invalidate_recordset()
        action = so.action_view_shipments()
        self.assertEqual(action["res_model"], "label.shipment")
        self.assertEqual(action["view_mode"], "list,form")

    def test_action_view_shipments_single(self):
        """Test view shipments opens form when only one shipment."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        so.invalidate_recordset()
        action = so.action_view_shipments()
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["res_id"], shipment.id)

    def test_download_label_dpd_mocked(self):
        """Test downloading DPD label PDF with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "dpd",
            "tracking_number": "DPD123",
            "state": "sent",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.get_labels"
        ) as mock_label:
            mock_label.return_value = (True, b"%PDF-1.4 dpd label")
            shipment.action_download_label()
        self.assertTrue(shipment.label_pdf)

    def test_download_label_czech_post_mocked(self):
        """Test downloading Czech Post label PDF with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "czech_post",
            "tracking_number": "CP123",
            "state": "sent",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.czech_post_api_key", "test_key")
        ICP.set_param("label_shipping.czech_post_secret_key", "test_secret")

        with patch(
            "odoo.addons.label_shipping.services.czech_post_api"
            ".get_shipment_label"
        ) as mock_label:
            mock_label.return_value = (True, b"%PDF-1.4 cp label")
            shipment.action_download_label()
        self.assertTrue(shipment.label_pdf)

    def test_api_cancel_dpd_mocked(self):
        """Test cancelling a DPD shipment via API with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "dpd",
            "tracking_number": "DPD123",
            "state": "sent",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_api_key", "test_key")
        ICP.set_param("label_shipping.dpd_api_dsw", "test_dsw")

        with patch(
            "odoo.addons.label_shipping.services.dpd_api.cancel_shipment"
        ) as mock_cancel:
            mock_cancel.return_value = (True, {"status": "cancelled"})
            shipment.action_api_cancel()
        self.assertEqual(shipment.state, "cancelled")

    def test_api_cancel_czech_post_mocked(self):
        """Test cancelling Czech Post shipment via API with mocked response."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "czech_post",
            "tracking_number": "CP123",
            "state": "sent",
        })
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.czech_post_api_key", "test_key")
        ICP.set_param("label_shipping.czech_post_secret_key", "test_secret")

        with patch(
            "odoo.addons.label_shipping.services.czech_post_api"
            ".cancel_shipment"
        ) as mock_cancel:
            mock_cancel.return_value = (True, {"status": "cancelled"})
            shipment.action_api_cancel()
        self.assertEqual(shipment.state, "cancelled")

    def test_pickup_point_fields_persist(self):
        """Test that pickup point fields on delivery address persist."""
        addr = self.env["res.partner"].create({
            "name": "Test Persist",
            "type": "delivery",
            "parent_id": self.partner.id,
            "label_preferred_carrier": "packeta",
            "label_pickup_point_id": "99999",
            "label_pickup_point_name": "Test Point",
        })
        # Re-read from database
        addr.invalidate_recordset()
        addr_reloaded = self.env["res.partner"].browse(addr.id)
        self.assertEqual(addr_reloaded.label_pickup_point_id, "99999")
        self.assertEqual(addr_reloaded.label_pickup_point_name, "Test Point")

    def test_download_label_no_tracking_number(self):
        """Test downloading label fails when no tracking number."""
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "packeta",
        })
        shipment.action_download_label()
        self.assertEqual(shipment.state, "error")
        self.assertTrue(shipment.error_message)

    def test_dpd_test_mode_setting(self):
        """Test DPD test mode config parameter."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_test_mode", "True")
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "dpd",
        })
        params = shipment._get_carrier_api_params()
        self.assertTrue(params["test_mode"])

    def test_dpd_test_mode_disabled(self):
        """Test DPD test mode returns False when disabled."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("label_shipping.dpd_test_mode", "False")
        so = self._create_sale_order()
        shipment = self.env["label.shipment"].create({
            "sale_order_id": so.id,
            "carrier_type": "dpd",
        })
        params = shipment._get_carrier_api_params()
        self.assertFalse(params["test_mode"])
