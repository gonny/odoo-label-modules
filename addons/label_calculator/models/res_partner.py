from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Celková útrata z potvrzených faktur
    label_total_invoiced = fields.Float(
        string="Útrata za štítky",
        compute="_compute_label_total_invoiced",
        store=True,
        help="Celková fakturovaná částka za produkty s kalkulačkou.",
    )

    # Automaticky přiřazená hladina
    label_discount_tier_id = fields.Many2one(
        "partner.discount.tier",
        string="Slevová hladina (auto)",
        compute="_compute_label_discount_tier",
        store=True,
        help="Automaticky přiřazená hladina podle celkové útraty.",
    )

    # Ruční přetížení slevy
    label_discount_override = fields.Float(
        string="Ruční sleva (%)",
        default=0,
        help="Přetíží automatickou slevu. 0 = použít automatickou hladinu.",
    )

    # Efektivní sleva (to co se reálně použije)
    label_effective_discount = fields.Float(
        string="Efektivní sleva (%)",
        compute="_compute_label_effective_discount",
        store=True,
        help="Sleva, která se aplikuje na nové objednávky.",
    )

    @api.depends("invoice_ids.state", "invoice_ids.invoice_line_ids.price_subtotal")
    def _compute_label_total_invoiced(self):
        for partner in self:
            # Součet z potvrzených faktur (posted)
            invoices = self.env["account.move"].search([
                ("partner_id", "=", partner.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
            ])
            total = 0
            for inv in invoices:
                for line in inv.invoice_line_ids:
                    if line.label_material_id:
                        total += line.price_subtotal
            partner.label_total_invoiced = total

    @api.depends("label_total_invoiced")
    def _compute_label_discount_tier(self):
        tiers = self.env["partner.discount.tier"].search(
            [("active", "=", True)],
            order="min_spent desc",
        )
        for partner in self:
            partner.label_discount_tier_id = False
            for tier in tiers:
                if partner.label_total_invoiced >= tier.min_spent:
                    partner.label_discount_tier_id = tier
                    break

    @api.depends("label_discount_tier_id", "label_discount_override")
    def _compute_label_effective_discount(self):
        for partner in self:
            if partner.label_discount_override > 0:
                partner.label_effective_discount = partner.label_discount_override
            elif partner.label_discount_tier_id:
                partner.label_effective_discount = (
                    partner.label_discount_tier_id.discount_pct
                )
            else:
                partner.label_effective_discount = 0
