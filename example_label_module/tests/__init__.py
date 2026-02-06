"""Tests for Label model."""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestLabel(TransactionCase):
    """Test cases for Label model."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.Label = self.env['label.label']
        
        # Create a test product
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'barcode': '1234567890',
        })

    def test_create_label(self):
        """Test creating a label."""
        label = self.Label.create({
            'name': 'Test Label',
            'product_id': self.product.id,
            'quantity': 5,
        })
        
        self.assertEqual(label.name, 'Test Label')
        self.assertEqual(label.product_id.id, self.product.id)
        self.assertEqual(label.quantity, 5)
        self.assertEqual(label.state, 'draft')

    def test_quantity_constraint(self):
        """Test quantity constraint validation."""
        with self.assertRaises(ValidationError):
            self.Label.create({
                'name': 'Invalid Label',
                'product_id': self.product.id,
                'quantity': 0,
            })

    def test_onchange_product(self):
        """Test product onchange method."""
        label = self.Label.new({
            'product_id': self.product.id,
        })
        label._onchange_product_id()
        
        expected_name = f"Label - {self.product.name}"
        self.assertEqual(label.name, expected_name)

    def test_action_confirm(self):
        """Test confirming a label."""
        label = self.Label.create({
            'name': 'Test Label',
            'product_id': self.product.id,
        })
        
        label.action_confirm()
        self.assertEqual(label.state, 'confirmed')

    def test_action_print(self):
        """Test printing a label."""
        label = self.Label.create({
            'name': 'Test Label',
            'product_id': self.product.id,
            'state': 'confirmed',
        })
        
        result = label.action_print()
        
        self.assertEqual(label.state, 'printed')
        self.assertTrue(label.printed_date)
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_action_reset_to_draft(self):
        """Test resetting label to draft."""
        label = self.Label.create({
            'name': 'Test Label',
            'product_id': self.product.id,
            'state': 'printed',
        })
        
        label.action_reset_to_draft()
        self.assertEqual(label.state, 'draft')

    def test_barcode_related_field(self):
        """Test that barcode is correctly related to product."""
        label = self.Label.create({
            'name': 'Test Label',
            'product_id': self.product.id,
        })
        
        self.assertEqual(label.barcode, self.product.barcode)
