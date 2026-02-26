from . import models


def _post_init_configure(env):
    """Post-install configuration for label calculator module.

    Runs after l10n_cz is installed (it's in depends).
    Company currency should already be CZK from l10n_cz.
    """

    # ── Phase 1: Disable default sale tax (non-VAT-payer) ──
    env["ir.config_parameter"].sudo().set_param(
        "account.default_sale_tax_id", False,
    )
    sale_taxes = env["account.tax"].sudo().search([
        ("type_tax_use", "=", "sale"),
        ("active", "=", True),
    ])
    if sale_taxes:
        sale_taxes.write({"active": False})

    # ── Phase 2: Ensure CZK is company currency ──
    czk = env.ref("base.CZK", raise_if_not_found=False)
    if czk:
        czk.sudo().write({"active": True})
        company = env.company.sudo()
        if company.currency_id != czk:
            company.write({"currency_id": czk.id})

    # ── Phase 3: Activate EUR, set rate, archive USD ──
    eur = env.ref("base.EUR", raise_if_not_found=False)
    if eur:
        eur.sudo().write({"active": True})
        # Set EUR rate: 1 EUR = 24 CZK → Odoo rate = 1/24
        existing_rate = env["res.currency.rate"].sudo().search([
            ("currency_id", "=", eur.id),
        ], limit=1)
        if existing_rate:
            existing_rate.write({"rate": round(1 / 24, 6)})
        else:
            env["res.currency.rate"].sudo().create({
                "currency_id": eur.id,
                "rate": round(1 / 24, 6),
            })

    usd = env.ref("base.USD", raise_if_not_found=False)
    if usd and usd.active:
        company = env.company
        if company.currency_id.name != "USD":
            try:
                usd.sudo().write({"active": False})
            except Exception:
                pass

    # ── Phase 4: Enable cash rounding ──
    env["ir.config_parameter"].sudo().set_param(
        "account.use_invoice_cash_rounding", "True",
    )

    # ── Phase 5: Set rounding accounts ──
    income_account = env["account.account"].sudo().search(
        [("account_type", "=", "income")], limit=1,
    )
    expense_account = env["account.account"].sudo().search(
        [("account_type", "=", "expense")], limit=1,
    )
    if income_account and expense_account:
        roundings = env["account.cash.rounding"].sudo().search([])
        for rounding in roundings:
            vals = {}
            if not rounding.profit_account_id:
                vals["profit_account_id"] = income_account.id
            if not rounding.loss_account_id:
                vals["loss_account_id"] = expense_account.id
            if vals:
                rounding.write(vals)