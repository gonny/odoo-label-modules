from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    label_partner_history_ids = fields.One2many(
        "sale.order.line",
        compute="_compute_partner_history",
        string="Historie štítků zákazníka",
    )

    @api.depends("partner_id")
    def _compute_partner_history(self):
        for order in self:
            if not order.partner_id:
                order.label_partner_history_ids = False
                continue

            # Najdi všechny řádky s kalkulačkou pro tohoto zákazníka
            # z potvrzených objednávek (ne z aktuální)
            domain = [
                ("order_id.partner_id", "=", order.partner_id.id),
                ("pricing_type", "=", "calculator"),
                ("order_id.state", "in", ["sale", "done"]),
            ]
            if order.id:
                domain.append(("order_id", "!=", order.id))

            lines = self.env["sale.order.line"].search(
                domain,
                order="create_date desc",
                limit=50,
            )
            order.label_partner_history_ids = lines
