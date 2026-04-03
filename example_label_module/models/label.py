"""Label model for managing product labels."""

import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class Label(models.Model):
    """Model for managing product labels."""

    _name = "label.label"
    _description = "Product Label"
    _order = "name"
    _rec_name = "name"

    name = fields.Char(
        string="Label Name", required=True, index=True, help="Name of the label"
    )

    description = fields.Text(
        string="Description", help="Detailed description of the label"
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        ondelete="cascade",
        help="Product associated with this label",
    )

    barcode = fields.Char(
        string="Barcode",
        related="product_id.barcode",
        readonly=True,
        help="Product barcode",
    )

    label_type = fields.Selection(
        [
            ("qr", "QR Code"),
            ("barcode", "Barcode"),
            ("text", "Text Only"),
        ],
        string="Label Type",
        default="barcode",
        required=True,
    )

    quantity = fields.Integer(
        string="Quantity", default=1, help="Number of labels to print"
    )

    size = fields.Selection(
        [
            ("small", "Small (4x6cm)"),
            ("medium", "Medium (10x10cm)"),
            ("large", "Large (15x20cm)"),
        ],
        string="Label Size",
        default="medium",
        required=True,
    )

    active = fields.Boolean(
        string="Active", default=True, help="Set to false to archive the label"
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("printed", "Printed"),
        ],
        string="State",
        default="draft",
        tracking=True,
    )

    printed_date = fields.Datetime(
        string="Printed Date", readonly=True, help="Date when the label was printed"
    )

    notes = fields.Html(string="Notes", help="Additional notes about the label")

    @api.constrains("quantity")
    def _check_quantity(self):
        """Validate that quantity is positive."""
        for record in self:
            if record.quantity <= 0:
                raise ValidationError("Quantity must be greater than zero")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """Update label name when product changes."""
        if self.product_id:
            self.name = f"Label - {self.product_id.name}"

    def action_confirm(self):
        """Confirm the label."""
        self.ensure_one()
        self.write({"state": "confirmed"})
        _logger.info("Label %s confirmed", self.name)
        return True

    def action_print(self):
        """Mark the label as printed."""
        self.ensure_one()
        self.write({"state": "printed", "printed_date": fields.Datetime.now()})
        _logger.info("Label %s printed", self.name)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": f"Label {self.name} has been printed",
                "type": "success",
                "sticky": False,
            },
        }

    def action_reset_to_draft(self):
        """Reset label to draft state."""
        self.ensure_one()
        self.write({"state": "draft"})
        _logger.info("Label %s reset to draft", self.name)
        return True
