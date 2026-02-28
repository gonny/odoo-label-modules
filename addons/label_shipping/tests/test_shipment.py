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
