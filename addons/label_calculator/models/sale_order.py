from odoo import models, fields, api
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"

    label_partner_history_ids = fields.One2many(
        "sale.order.line",
        compute="_compute_partner_history",
        string="Historie štítků zákazníka",
    )

    label_pricing_profile_id = fields.Many2one(
        "label.pricing.profile",
        string="Cenový profil zákazníka",
        related="partner_id.label_pricing_profile_id",
        store=False,
        readonly=True,
    )

    @api.depends("partner_id")
    def _compute_partner_history(self):
        for order in self:
            if not order.partner_id:
                order.label_partner_history_ids = False
                continue

            domain = [
                ("order_id.partner_id", "=", order.partner_id.id),
                ("pricing_type", "=", "calculator"),
                ("order_id.state", "in", ["sale", "done"]),
            ]
            if order.id and isinstance(order.id, int):
                domain.append(("order_id", "!=", order.id))

            lines = self.env["sale.order.line"].search(
                domain,
                order="order_id desc, sequence asc",
                limit=100,
            )
            order.label_partner_history_ids = lines

    def action_open_partner_history(self):
        """Otevře historii zákazníka v standalone okně s groupby."""
        self.ensure_one()
        if not self.partner_id:
            return

        domain = [
            ("order_id.partner_id", "=", self.partner_id.id),
            ("pricing_type", "=", "calculator"),
            ("order_id.state", "in", ["sale", "done"]),
        ]
        if self.id and isinstance(self.id, int):
            domain.append(("order_id", "!=", self.id))

        return {
            "name": f"Historie – {self.partner_id.name}",
            "type": "ir.actions.act_window",
            "res_model": "sale.order.line",
            "view_mode": "list",
            "views": [
                (self.env.ref(
                    "label_calculator.view_label_history_list"
                ).id, "list"),
            ],
            "domain": domain,
            "context": {
                "group_by": ["order_id"],
                "active_order_id": self.id,
            },
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Nastaví výchozí commitment_date (datum dodání)."""
        for vals in vals_list:
            if "commitment_date" not in vals:
                # Výchozí datum dodání = dnes + 7 pracovních dní
                today = fields.Date.context_today(self)
                vals["commitment_date"] = today + timedelta(days=10)
        return super().create(vals_list)

    def write(self, vals):
        """Přepočítá kalkulační pole při změně měny nebo ceníku.

        When the order currency or pricelist changes, all calculator lines
        must have their price_unit re-converted to the new currency.
        The label_calculated_price (CZK amount) stays unchanged.
        """
        res = super().write(vals)
        if "currency_id" in vals or "pricelist_id" in vals:
            for order in self:
                calculator_lines = order.order_line.filtered(
                    lambda l: (
                        l.pricing_type == "calculator"
                        and l.label_material_id
                        and l.label_calculated_price
                    )
                )
                for line in calculator_lines:
                    # Only convert price – do NOT rerun calculator (CZK price stays)
                    converted = line._convert_price_to_order_currency(
                        line.label_calculated_price,
                    )
                    # Use context flag to signal this is a currency-only update,
                    # preventing unnecessary re-calculation in line.write()
                    line.with_context(
                        label_currency_conversion_only=True,
                    ).write({"price_unit": converted})
        return res
