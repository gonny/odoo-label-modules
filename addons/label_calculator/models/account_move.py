import base64
import io
import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # Variabilní symbol
    label_variable_symbol = fields.Char(
        string="Variabilní symbol",
        compute="_compute_variable_symbol",
        store=True,
    )

    # Pole pro zobrazení cenového profilu vedle jména zákazníka (pro VIP / Standard)
    label_pricing_profile_display = fields.Char(
        compute="_compute_label_pricing_profile_display",
        store=False,
    )

    @api.depends("partner_id.label_pricing_profile_id")
    def _compute_label_pricing_profile_display(self):
        """Zobrazí název VIP cenového profilu vedle jména zákazníka, pokud je zákazník VIP."""
        for move in self:
            profile = move.partner_id.label_pricing_profile_id
            if profile and profile.is_vip:
                move.label_pricing_profile_display = profile.name
            else:
                move.label_pricing_profile_display = ""

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
                    [
                        ("name", "ilike", currency.name),
                        ("profit_account_id", "!=", False),
                        ("loss_account_id", "!=", False),
                    ],
                    limit=1,
                )
                if not rounding:
                    rounding = self.env["account.cash.rounding"].search(
                        [
                            ("profit_account_id", "!=", False),
                            ("loss_account_id", "!=", False),
                        ],
                        limit=1,
                    )
                if rounding:
                    vals["invoice_cash_rounding_id"] = rounding.id

            # ── Phase 4: Bank account by currency ──
            if "partner_bank_id" not in vals:
                company_partner = self.env.company.partner_id
                bank = company_partner.bank_ids.filtered(
                    lambda b: b.currency_id == currency
                    or (not b.currency_id and currency == self.env.company.currency_id)
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

    def _get_epc_string(self):
        """Generate EPC QR code string for EUR SEPA payments.

        EPC (European Payments Council) QR format is a newline-separated
        standard for SEPA credit transfers, used by banking apps in the EU.

        Returns empty string if not an EUR invoice or no EUR bank account found.
        """
        self.ensure_one()

        if self.currency_id.name != "EUR":
            return ""

        company = self.company_id
        bank_account = company.partner_id.bank_ids.filtered(
            lambda b: b.currency_id.name == "EUR"
        )[:1]

        if not bank_account:
            return ""

        iban = (bank_account.acc_number or "").replace(" ", "")
        bic = (bank_account.bank_id.bic or "") if bank_account.bank_id else ""
        # EPC standard: beneficiary name max 70 characters
        beneficiary = (company.name or "")[:70]
        amount = f"EUR{self.amount_residual:.2f}"

        # Invoice reference for the payment message
        msg = ""
        if self.name and self.name != "/":
            msg = f"Invoice {self.name}"

        # EPC QR format (newline-separated)
        lines = [
            "BCD",  # Service Tag
            "002",  # Version
            "1",  # Character set (UTF-8)
            "SCT",  # Identification code
            bic,  # BIC of beneficiary bank (may be empty)
            beneficiary,  # Beneficiary name
            iban,  # IBAN
            amount,  # Amount (EUR + value)
            "",  # Purpose (empty)
            "",  # Remittance reference (empty)
            msg,  # Remittance text
        ]
        return "\n".join(lines)

    def _get_qr_code_base64(self):
        """Return QR code image as base64-encoded PNG.

        Generates QR code from:
        - SPD format for CZK invoices (Czech domestic payments)
        - EPC format for EUR invoices (SEPA payments)
        - Empty string for other currencies

        Returns empty string if qrcode package is not installed.
        """
        self.ensure_one()

        # Determine QR data based on currency
        if self.currency_id.name == "CZK":
            qr_data = self._get_spd_string()
        elif self.currency_id.name == "EUR":
            qr_data = self._get_epc_string()
        else:
            return ""

        if not qr_data:
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
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        try:
            img.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        finally:
            buffer.close()
