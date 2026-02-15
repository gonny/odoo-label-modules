from odoo import models, fields, api
import re
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # Variabilní symbol
    label_variable_symbol = fields.Char(
        string="Variabilní symbol",
        compute="_compute_variable_symbol",
        store=True,
    )

    @api.depends("name")
    def _compute_variable_symbol(self):
        """Variabilní symbol = číslo faktury bez písmen."""
        for move in self:
            if move.name and move.name != "/":
                digits = re.sub(r"[^0-9]", "", move.name)
                move.label_variable_symbol = digits[-10:]
            else:
                move.label_variable_symbol = ""

    @api.model_create_multi
    def create(self, vals_list):
        """Nastaví výchozí cash rounding podle měny faktury."""
        for vals in vals_list:
            if "invoice_cash_rounding_id" not in vals:
                # Zjisti měnu faktury
                currency_id = vals.get("currency_id")
                if not currency_id:
                    # Fallback na měnu společnosti
                    currency_id = self.env.company.currency_id.id

                currency = self.env["res.currency"].browse(currency_id)

                # Najdi cash rounding pro tuto měnu
                # Hledáme podle názvu (konvence: "CZK ..." nebo "EUR ...")
                rounding = self.env["account.cash.rounding"].search(
                    [("name", "ilike", currency.name)],
                    limit=1,
                )

                # Fallback – první dostupný
                if not rounding:
                    rounding = self.env["account.cash.rounding"].search(
                        [], limit=1
                    )

                if rounding:
                    vals["invoice_cash_rounding_id"] = rounding.id

        return super().create(vals_list)

    def _get_spd_string(self):
        """Generuje SPD řetězec pro QR kód (česká platba)."""
        self.ensure_one()

        if self.currency_id.name != "CZK":
            return ""

        company = self.company_id
        bank_account = company.partner_id.bank_ids.filtered(
            lambda b: b.currency_id == self.currency_id
            or (not b.currency_id and self.currency_id == company.currency_id)
        )[:1]

        if not bank_account:
            bank_account = company.partner_id.bank_ids[:1]

        if not bank_account:
            return ""

        acc = bank_account.acc_number or ""
        # Odstraň mezery z IBAN
        acc = acc.replace(" ", "")

        parts = [
            "SPD*1.0",
            f"ACC:{acc}",
            f"AM:{self.amount_residual:.2f}",
            "CC:CZK",
        ]

        if self.label_variable_symbol:
            parts.append(f"X-VS:{self.label_variable_symbol}")

        if self.name and self.name != "/":
            parts.append(f"MSG:Faktura {self.name}")

        return "*".join(parts)
