from . import models


def _post_init_configure(env):
    """Post-install configuration for the label calculator module.

    Configures Odoo for a Czech non-VAT-payer (neplátce DPH) business:
    - Disables all default sale taxes
    - Archives USD currency, activates EUR currency, sets CZK as default
    - Enables cash rounding in Invoicing settings
    - Sets profit/loss accounts on cash rounding records
    """
    # ── 1. Disable default sale taxes ──
    env["ir.config_parameter"].sudo().set_param(
        "account.default_sale_tax_id", "",
    )
    sale_taxes = env["account.tax"].sudo().search([
        ("type_tax_use", "=", "sale"),
        ("active", "=", True),
    ])
    if sale_taxes:
        sale_taxes.write({"active": False})

    # ── 2. Currency configuration: archive USD, activate EUR ──
    usd = env.ref("base.USD", raise_if_not_found=False)
    if usd:
        usd.active = False

    eur = env.ref("base.EUR", raise_if_not_found=False)
    if eur:
        eur.active = True

    # Set CZK as default company currency
    czk = env.ref("base.CZK", raise_if_not_found=False)
    if czk:
        czk.active = True
        company = env["res.company"].sudo().search([], limit=1)
        if company and company.currency_id != czk:
            company.currency_id = czk

    # ── 3. Enable cash rounding in Invoicing settings ──
    env["ir.config_parameter"].sudo().set_param(
        "account.use_invoice_cash_rounding", "True",
    )

    # ── 4. Set profit/loss accounts on cash rounding records ──
    # Odoo 19 uses account types like 'income_other' and 'expense'
    income_account = env["account.account"].sudo().search(
        [("account_type", "=", "income_other")], limit=1,
    )
    if not income_account:
        income_account = env["account.account"].sudo().search(
            [("account_type", "ilike", "income")], limit=1,
        )
    expense_account = env["account.account"].sudo().search(
        [("account_type", "=", "expense")], limit=1,
    )
    if not expense_account:
        expense_account = env["account.account"].sudo().search(
            [("account_type", "ilike", "expense")], limit=1,
        )
    if income_account or expense_account:
        roundings = env["account.cash.rounding"].sudo().search([])
        vals = {}
        if income_account:
            vals["profit_account_id"] = income_account.id
        if expense_account:
            vals["loss_account_id"] = expense_account.id
        if vals and roundings:
            roundings.write(vals)