from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Related fields from shipping address
    label_shipping_carrier = fields.Selection(
        related="partner_shipping_id.label_preferred_carrier",
        string="Dopravce",
        readonly=True,
    )
    label_shipping_service = fields.Char(
        string="Služba dopravce",
        related="partner_shipping_id.label_carrier_service",
        readonly=True,
    )
    label_shipping_pickup_point = fields.Char(
        string="Výdejní místo",
        related="partner_shipping_id.label_pickup_point_name",
        readonly=True,
    )

    # Shipments
    shipment_ids = fields.One2many(
        "label.shipment",
        "sale_order_id",
        string="Zásilky",
    )
    label_shipment_count = fields.Integer(
        string="Počet zásilek",
        compute="_compute_label_shipment_count",
    )

    @api.depends("shipment_ids")
    def _compute_label_shipment_count(self):
        """Compute the number of shipments linked to this sale order."""
        for order in self:
            order.label_shipment_count = len(order.shipment_ids)

    def action_create_shipment(self):
        """Otevře formulář pro vytvoření nové zásilky."""
        self.ensure_one()
        carrier = self.partner_shipping_id.label_preferred_carrier or "packeta"
        if carrier == "none":
            carrier = "packeta"
        return {
            "name": "Nová zásilka",
            "type": "ir.actions.act_window",
            "res_model": "label.shipment",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_sale_order_id": self.id,
                "default_carrier_type": carrier,
                "default_carrier_service": (
                    self.partner_shipping_id.label_carrier_service or ""
                ),
                "default_pickup_point_id": (
                    self.partner_shipping_id.label_pickup_point_id or ""
                ),
                "default_pickup_point_name": (
                    self.partner_shipping_id.label_pickup_point_name or ""
                ),
            },
        }

    def action_view_shipments(self):
        """Otevře seznam zásilek pro tuto objednávku."""
        self.ensure_one()
        action = {
            "name": "Zásilky",
            "type": "ir.actions.act_window",
            "res_model": "label.shipment",
            "view_mode": "list,form",
            "domain": [("sale_order_id", "=", self.id)],
            "context": {"default_sale_order_id": self.id},
        }
        if self.label_shipment_count == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.shipment_ids.id
        return action
