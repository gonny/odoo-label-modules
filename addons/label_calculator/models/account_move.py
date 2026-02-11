from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        """Nastaví výchozí cash rounding na faktuře."""
        # Najdi výchozí cash rounding
        default_rounding = self.env["account.cash.rounding"].search(
            [], limit=1
        )

        for vals in vals_list:
            # Cash rounding
            if (
                "invoice_cash_rounding_id" not in vals
                and default_rounding
            ):
                vals["invoice_cash_rounding_id"] = default_rounding.id

        return super().create(vals_list)

    # Variabilní symbol
    label_variable_symbol = fields.Char(
        string="Variabilní symbol",
        compute="_compute_variable_symbol",
        store=True,
    )

    @api.depends("name")
    def _compute_variable_symbol(self):
        """Variabilní symbol = číslo faktury bez písmen."""
        import re
        for move in self:
            if move.name and move.name != "/":
                # INV/2026/00001 → 202600001
                digits = re.sub(r"[^0-9]", "", move.name)
                move.label_variable_symbol = digits[-10:]  # max 10 číslic
            else:
                move.label_variable_symbol = ""

    def _get_spd_string(self):
        """Generuje SPD řetězec pro QR kód."""
        self.ensure_one()
        company = self.company_id

        # Najdi bankovní účet firmy
        bank_account = company.partner_id.bank_ids[:1]
        if not bank_account:
            return ""

        # IBAN nebo české číslo účtu
        acc = bank_account.acc_number or ""
        # Pokud je IBAN, převeď na české číslo
        # (nebo použij IBAN přímo – SPD podporuje obojí)

        parts = [
            "SPD*1.0",
            f"ACC:{acc}",
            f"AM:{self.amount_residual:.2f}",
            "CC:CZK",
            f"X-VS:{self.label_variable_symbol}",
        ]

        if self.name and self.name != "/":
            parts.append(f"MSG:Faktura {self.name}")

        return "*".join(parts)
