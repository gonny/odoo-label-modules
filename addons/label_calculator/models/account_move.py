from odoo import models, fields, api
import base64
import io
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
        """Auto-set cash rounding and bank account by invoice currency."""
        for vals in vals_list:
            currency_id = vals.get("currency_id")
            if not currency_id:
                currency_id = self.env.company.currency_id.id

            currency = self.env["res.currency"].browse(currency_id)

            # ── Phase 3: Cash rounding by currency ──
            if "invoice_cash_rounding_id" not in vals:
                rounding = self.env["account.cash.rounding"].search(
                    [("name", "ilike", currency.name)],
                    limit=1,
                )
                if not rounding:
                    rounding = self.env["account.cash.rounding"].search(
                        [], limit=1
                    )
                if rounding:
                    vals["invoice_cash_rounding_id"] = rounding.id

            # ── Phase 4: Bank account by currency ──
            if "partner_bank_id" not in vals:
                company_partner = self.env.company.partner_id
                bank = company_partner.bank_ids.filtered(
                    lambda b: b.currency_id == currency
                    or (
                        not b.currency_id
                        and currency == self.env.company.currency_id
                    )
                )[:1]
                if not bank:
                    bank = company_partner.bank_ids[:1]
                if bank:
                    vals["partner_bank_id"] = bank.id

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

    def _get_qr_code_base64(self):
        """Return QR code image as base64-encoded PNG for the SPD string.

        Returns empty string if not a CZK invoice or qrcode is not installed.
        """
        self.ensure_one()
        spd = self._get_spd_string()
        if not spd:
            return ""

        try:
            import qrcode
        except ImportError:
            _logger.warning("qrcode package not installed – QR code skipped")
            return ""

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(spd)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        try:
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        finally:
            buffer.close()
