from odoo import api, fields, models


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

    # === VIP pole ===
    label_pricing_profile_id = fields.Many2one(
        "label.pricing.profile",
        string="Cenový profil",
        help="Cenový profil zákazníka. VIP zákazníci mají vlastní "
        "množstevní hladiny s lepšími parametry.",
    )

    label_is_vip = fields.Boolean(
        string="VIP zákazník",
        default=False,
        help="VIP zákazníci mají vlastní cenové hladiny a nemají "
        "nárok na procentuální slevu.",
    )

    label_vip_eligible = fields.Boolean(
        string="Nárok na VIP",
        compute="_compute_label_vip_eligible",
        store=False,  # Always recompute from current invoices
        help="Informativní pole – zákazník splňuje podmínky pro VIP.",
    )

    @api.depends("invoice_ids.state", "invoice_ids.invoice_line_ids.price_subtotal")
    def _compute_label_total_invoiced(self):
        for partner in self:
            # Součet z potvrzených faktur (posted)
            invoices = self.env["account.move"].search(
                [
                    ("partner_id", "=", partner.id),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                ]
            )
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

    @api.depends(
        "label_discount_tier_id",
        "label_discount_override",
        "label_is_vip",
    )
    def _compute_label_effective_discount(self):
        """Efektivní sleva: VIP = 0, jinak override nebo auto."""
        for partner in self:
            if partner.label_is_vip:
                partner.label_effective_discount = 0
            elif partner.label_discount_override > 0:
                partner.label_effective_discount = partner.label_discount_override
            elif partner.label_discount_tier_id:
                partner.label_effective_discount = (
                    partner.label_discount_tier_id.discount_pct
                )
            else:
                partner.label_effective_discount = 0

    @api.depends_context("uid")
    def _compute_label_vip_eligible(self):
        """Kontrola nároku na VIP status.

        Podmínky:
        - Posledních 3 potvrzených faktur
        - Každá faktura > 3000 CZK (EUR se převede na CZK)
        - Každá faktura má alespoň 1 řádek s quantity > 300
        """
        czk = self.env.ref("base.CZK", raise_if_not_found=False)
        for partner in self:
            # Already-VIP partners don't need the eligibility badge
            if partner.label_is_vip:
                partner.label_vip_eligible = False
                continue

            invoices = self.env["account.move"].search(
                [
                    ("partner_id", "=", partner.id),
                    ("move_type", "=", "out_invoice"),
                    ("state", "=", "posted"),
                ],
                order="invoice_date desc, id desc",
                limit=3,
            )

            if len(invoices) < 3:
                partner.label_vip_eligible = False
                continue

            all_qualify = True
            for inv in invoices:
                # Převod na CZK pokud je faktura v jiné měně
                amount = inv.amount_total
                if czk and inv.currency_id != czk:
                    amount = inv.currency_id._convert(
                        amount,
                        czk,
                        inv.company_id,
                        inv.invoice_date or fields.Date.today(),
                    )

                if amount <= 3000:
                    all_qualify = False
                    break

                has_large_qty = any(
                    line.quantity > 300
                    for line in inv.invoice_line_ids
                    if not line.display_type
                )
                if not has_large_qty:
                    all_qualify = False
                    break

            partner.label_vip_eligible = all_qualify

    @api.onchange("label_is_vip")
    def _onchange_label_is_vip(self):
        """Při změně VIP statusu nastaví/resetuje profil."""
        if self.label_is_vip:
            if (
                not self.label_pricing_profile_id
                or not self.label_pricing_profile_id.is_vip
            ):
                # Nastav první VIP profil
                vip_profile = self.env["label.pricing.profile"].search(
                    [("is_vip", "=", True)],
                    order="sequence",
                    limit=1,
                )
                if vip_profile:
                    self.label_pricing_profile_id = vip_profile
        else:
            # Revert na Standard
            default_profile = self.env["label.pricing.profile"].search(
                [("is_default", "=", True)],
                limit=1,
            )
            self.label_pricing_profile_id = default_profile or False
